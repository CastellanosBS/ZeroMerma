"""Idempotent continuation of an admitted refund in the operator's actual drawer."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    lock_cash_session,
    resolve_cash_command_context,
)
from zeromerma_api.modules.financial_ledger.application.recording import FinancialCommandScope
from zeromerma_api.modules.financial_ledger.application.refund_schemas import (
    FinancialRefundView,
    RefundSettlementCommand,
)
from zeromerma_api.modules.financial_ledger.application.refunds import (
    read_refund,
    settle_refund_cash,
)
from zeromerma_api.modules.financial_ledger.domain.money import FinancialModelError
from zeromerma_api.modules.financial_ledger.infrastructure.models import FinancialOperation
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import (
    IdempotencyBoundaryError,
    IdempotencyError,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrder
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.infrastructure.models import Sale

RefundSource = Literal["SALE_RETURN", "ORDER_CANCELLATION"]
REFUND_SETTLEMENT_RESPONSE_POLICY = ResponsePolicy(snapshot_model=FinancialRefundView)


class RefundSettlementService:
    def __init__(self, source_type: RefundSource) -> None:
        self.source_type = source_type
        self.operation_code = (
            "return.refund_settle" if source_type == "SALE_RETURN" else "order.refund_settle"
        )
        self.capability: CapabilityCode = (
            "returns_corrections.manage" if source_type == "SALE_RETURN" else "orders.cancel"
        )

    def settle(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: RefundSettlementCommand,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("Refund settlement requires its admitted command.")
            context = owner.record
            if context.branch_id is None or context.workstation_id is None:
                raise IdempotencyBoundaryError("Refund settlement requires its actual drawer.")
            lock_cash_session(
                current,
                current_user=current_user,
                branch_id=context.branch_id,
                workstation_id=context.workstation_id,
                cash_session_id=command.cash_session_id,
            )
            # Match the admission order: actual drawer, economic source, then obligation.
            self._lock_source(current, command.source_id, context.branch_id)
            operation = current.scalar(
                select(FinancialOperation).where(
                    FinancialOperation.source_type == self.source_type,
                    FinancialOperation.source_id == command.source_id,
                    FinancialOperation.branch_id == context.branch_id,
                    FinancialOperation.kind.in_(("SALE_REFUND", "ORDER_REFUND")),
                )
            )
            if operation is None:
                raise IdempotencyError(
                    "REFUND_NOT_FOUND", 404, "The refund obligation was not found."
                )
            before = read_refund(current, operation)
            try:
                result = settle_refund_cash(
                    current,
                    operation=operation,
                    scope=FinancialCommandScope(
                        branch_id=context.branch_id,
                        workstation_id=context.workstation_id,
                        cash_session_id=command.cash_session_id,
                        actor_id=current_user.id,
                    ),
                )
            except FinancialModelError as error:
                raise IdempotencyError("REFUND_SETTLEMENT_CONFLICT", 409, str(error)) from error
            payload = {
                **result.model_dump(mode="json"),
                "new_entry_ids": [
                    str(entry.id)
                    for entry in result.entries
                    if entry.id not in {prior.id for prior in before.entries}
                ],
                "settled_this_command": str(result.amount_settled - before.amount_settled),
            }
            AuditRecorder().record(
                current,
                actor_id=current_user.id,
                action="financial_refund.settlement_recorded",
                resource_type="financial_operation",
                resource_id=str(operation.id),
                branch_id=context.branch_id,
                request_id=request_id,
                metadata=payload,
            )
            OutboxWriter().append(
                current,
                aggregate_type="financial_operation",
                aggregate_id=str(operation.id),
                event_name="financial_refund.settlement_recorded.v1",
                payload=payload,
            )
            return CommandResult(
                status_code=200,
                snapshot=result,
                resource_type="financial_operation",
                resource_id=str(operation.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=self.operation_code,
            payload=command,
            resolve_context=lambda current, _saved: self._context(
                current, current_user, command.workstation_code, command.cash_session_id
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, self.capability
            ),
            action=action,
            response_policy=REFUND_SETTLEMENT_RESPONSE_POLICY,
            request_id=request_id,
        )

    def recover(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        key: UUID,
        workstation_code: str,
        cash_session_id: UUID,
    ) -> IdempotencyResult:
        bind_authorization_scope(
            session,
            user=current_user,
            capabilities=(self.capability,),
            mutation=False,
            surface="POS",
        )
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=self.operation_code,
            resolve_context=lambda current, _saved: self._context(
                current, current_user, workstation_code, cash_session_id
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, self.capability
            ),
            response_policy=REFUND_SETTLEMENT_RESPONSE_POLICY,
        )

    @staticmethod
    def _context(
        session: Session, user: AuthenticatedUser, workstation_code: str, cash_session_id: UUID
    ) -> CommandContext:
        return resolve_cash_command_context(
            session,
            current_user=user,
            workstation_code=workstation_code,
            cash_session_id=cash_session_id,
        )

    def _lock_source(self, session: Session, source_id: UUID, branch_id: UUID) -> None:
        if self.source_type == "SALE_RETURN":
            sale_id = session.scalar(
                select(SaleReturn.original_sale_id).where(
                    SaleReturn.id == source_id,
                    SaleReturn.branch_id == branch_id,
                )
            )
            found = (
                session.scalar(
                    select(Sale.id)
                    .where(
                        Sale.id == sale_id,
                        Sale.branch_id == branch_id,
                    )
                    .with_for_update(key_share=True)
                )
                if sale_id is not None
                else None
            )
        else:
            found = session.scalar(
                select(CustomerOrder.id)
                .where(
                    CustomerOrder.id == source_id,
                    CustomerOrder.branch_id == branch_id,
                )
                .with_for_update(key_share=True)
            )
        if found is None:
            raise IdempotencyError(
                "REFUND_SOURCE_NOT_FOUND", 404, "The refund source was not found."
            )
