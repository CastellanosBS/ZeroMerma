from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from zeromerma_api.modules.cash.application.command_context import (
    authorize_cash_command,
    resolve_cash_command_context,
)
from zeromerma_api.modules.discounts.application.schemas import (
    CreateOperationalDiscountRequest,
    OperationalDiscountCommitResultView,
)
from zeromerma_api.modules.discounts.application.services import DiscountsCommandService
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser

OPERATION_CODE = "operational_discount.commit"
RESPONSE_POLICY = ResponsePolicy(snapshot_model=OperationalDiscountCommitResultView)


class OperationalDiscountCommitService:
    def __init__(self, command_service: DiscountsCommandService | None = None) -> None:
        self._commands = command_service or DiscountsCommandService()

    def commit(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CreateOperationalDiscountRequest,
        key: UUID,
        request_id: str | None,
    ) -> IdempotencyResult:
        def action(current: Session) -> CommandResult:
            owner = execution(current)
            if owner is None or owner.record is None:
                raise IdempotencyBoundaryError("A cash command requires its reservation.")
            snapshot = self._commands.create_discount(
                current,
                current_user=current_user,
                command=command,
                idempotency_key=key,
                operation_id=owner.record.id,
                request_id=request_id,
            )
            return CommandResult(
                status_code=201,
                snapshot=snapshot,
                resource_type="operational_discount",
                resource_id=str(snapshot.id),
            )

        return IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            payload=command,
            resolve_context=lambda current, _saved: resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=command.workstation_code,
                cash_session_id=command.cash_session_id,
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "discounts.manage"
            ),
            action=action,
            response_policy=RESPONSE_POLICY,
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
        return IdempotencyExecutor().recover(
            session,
            key=key,
            operation_code=OPERATION_CODE,
            resolve_context=lambda current, _saved: resolve_cash_command_context(
                current,
                current_user=current_user,
                workstation_code=workstation_code,
                cash_session_id=cash_session_id,
            ),
            authorize=lambda current, context: authorize_cash_command(
                current, current_user, context, "discounts.manage"
            ),
            response_policy=RESPONSE_POLICY,
        )
