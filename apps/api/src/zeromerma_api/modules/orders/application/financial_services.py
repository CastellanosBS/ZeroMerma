"""Canonical financial facts for actual order payment records, within their command."""

from __future__ import annotations

from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from sqlalchemy import and_, case, select
from sqlalchemy.orm import Session

from zeromerma_api.db.operation_context import get_operation_context
from zeromerma_api.modules.financial_ledger.domain.constants import (
    Direction,
    EntryState,
    EvidenceKind,
    ExecutionMode,
    OperationKind,
    PaymentMethod,
)
from zeromerma_api.modules.financial_ledger.domain.money import (
    ZERO,
    FinancialModelError,
    require_currency,
    require_money,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.orders.domain.exceptions import OrderValidationError
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment

_PAYMENT_KINDS = {
    "ADVANCE": OperationKind.ORDER_ADVANCE,
    "SETTLEMENT": OperationKind.ORDER_SETTLEMENT,
    "REFUND": OperationKind.ORDER_REFUND,
}


@dataclass(frozen=True)
class OrderPaymentFinancialReference:
    payment_id: UUID
    financial_operation_id: UUID
    financial_entry_id: UUID

    def trace_fields(self) -> dict[str, str]:
        return {
            "payment_id": str(self.payment_id),
            "financial_operation_id": str(self.financial_operation_id),
            "financial_entry_id": str(self.financial_entry_id),
        }


def record_order_payment(
    session: Session, *, payment: CustomerOrderPayment, branch_id: UUID
) -> OrderPaymentFinancialReference:
    """Flush one receipt and its fact; the idempotent command owns commit and rollback.

    CARD is an operator's external accounting declaration, not provider capture evidence.
    Existing order capture records exact applied CASH; it has no tender/change workflow.
    """
    owner = execution(session)
    if owner is None or owner.record is None or not owner.action_running:
        raise IdempotencyBoundaryError("Order payments require the admitted command action.")
    if payment.payment_type not in {"ADVANCE", "SETTLEMENT"}:
        raise OrderValidationError(
            "Los reembolsos requieren su obligación financiera y capacidad de caja."
        )
    context = replace(
        get_operation_context(session),
        actor_id=payment.recorded_by_user_id,
        branch_id=branch_id,
        workstation_id=payment.workstation_id,
        cash_session_id=payment.cash_session_id,
    )
    if (
        owner.record.actor_user_id != context.actor_id
        or owner.record.branch_id != branch_id
        or owner.record.workstation_id != payment.workstation_id
        or owner.record.cash_session_id != payment.cash_session_id
    ):
        raise IdempotencyBoundaryError("Order payment facts must use the admitted actual session.")
    try:
        amount = require_money(payment.amount, positive=True)
        require_currency(payment.currency_code)
    except FinancialModelError as error:
        raise OrderValidationError(
            "Los pagos de pedidos requieren importes válidos en MXN, sin conversión de moneda."
        ) from error
    method = PaymentMethod(payment.payment_method_code)
    kind = _PAYMENT_KINDS[payment.payment_type]
    direction = Direction.IN
    session.add(payment)
    session.flush()
    lineage = dict(
        branch_id=branch_id,
        workstation_id=payment.workstation_id,
        cash_session_id=payment.cash_session_id,
        actor_id=payment.recorded_by_user_id,
        currency_code=payment.currency_code,
        context_version=1,
        source_app=context.source_app.value,
        actor_type=context.actor_type,
        operation_id=context.operation_id,
        operation_code=context.operation_code,
        correlation_id=context.correlation_id,
        causation_id=context.causation_id,
        request_id=context.request_id,
        idempotency_key=context.idempotency_key,
        related_branch_ids=sorted(
            {str(branch_id), *(str(item) for item in context.related_branch_ids)}
        ),
        occurred_at=payment.recorded_at_utc,
    )
    operation = FinancialOperation(
        id=uuid4(),
        kind=kind.value,
        source_type="ORDER_PAYMENT",
        source_id=payment.id,
        effect_code=kind.value,
        subject_type="ORDER",
        subject_id=payment.customer_order_id,
        amount_due=amount,
        **lineage,
    )
    session.add(operation)
    session.flush()
    entry = FinancialEntry(
        id=uuid4(),
        financial_operation_id=operation.id,
        leg_key="payment",
        payment_method_code=method.value,
        direction=direction.value,
        amount=amount,
        tendered_amount=amount
        if method == PaymentMethod.CASH and direction == Direction.IN
        else None,
        change_amount=ZERO,
        execution_mode=(
            ExecutionMode.LOCAL if method == PaymentMethod.CASH else ExecutionMode.ACCOUNTING_ONLY
        ).value,
        state=EntryState.CONFIRMED.value,
        confirmed_at=payment.recorded_at_utc,
        resolution_kind=(
            EvidenceKind.LOCAL_CASH
            if method == PaymentMethod.CASH
            else EvidenceKind.EXTERNAL_RECORDING
        ).value,
        resolution_reference=payment.id if method == PaymentMethod.CARD else None,
        **lineage,
    )
    session.add(entry)
    session.flush()
    return OrderPaymentFinancialReference(payment.id, operation.id, entry.id)


def order_payment_financial_references(
    session: Session, *, order_id: UUID, branch_id: UUID
) -> dict[UUID, tuple[UUID, UUID]]:
    """Return only exact causal links; unadopted demo history has no fabricated references."""
    expected_kind = case(_PAYMENT_KINDS, value=CustomerOrderPayment.payment_type)
    statement = (
        select(CustomerOrderPayment.id, FinancialOperation.id, FinancialEntry.id)
        .join(
            FinancialOperation,
            and_(
                FinancialOperation.source_type == "ORDER_PAYMENT",
                FinancialOperation.source_id == CustomerOrderPayment.id,
                FinancialOperation.kind == expected_kind,
                FinancialOperation.subject_type == "ORDER",
                FinancialOperation.subject_id == CustomerOrderPayment.customer_order_id,
                FinancialOperation.branch_id == branch_id,
            ),
        )
        .join(
            FinancialEntry,
            and_(
                FinancialEntry.financial_operation_id == FinancialOperation.id,
                FinancialEntry.leg_key == "payment",
                FinancialEntry.amount == CustomerOrderPayment.amount,
                FinancialEntry.currency_code == CustomerOrderPayment.currency_code,
                FinancialEntry.payment_method_code == CustomerOrderPayment.payment_method_code,
                FinancialEntry.workstation_id == CustomerOrderPayment.workstation_id,
                FinancialEntry.cash_session_id == CustomerOrderPayment.cash_session_id,
                FinancialEntry.actor_id == CustomerOrderPayment.recorded_by_user_id,
            ),
        )
        .where(CustomerOrderPayment.customer_order_id == order_id)
    )
    references = {
        payment_id: (operation_id, entry_id)
        for payment_id, operation_id, entry_id in session.execute(statement)
    }
    refund_rows = session.execute(
        select(CustomerOrderPayment.id, FinancialOperation.id, FinancialEntry.id)
        .join(FinancialEntry, FinancialEntry.id == CustomerOrderPayment.financial_entry_id)
        .join(FinancialOperation, FinancialOperation.id == FinancialEntry.financial_operation_id)
        .where(
            CustomerOrderPayment.customer_order_id == order_id,
            CustomerOrderPayment.payment_type == "REFUND",
            FinancialOperation.kind == "ORDER_REFUND",
            FinancialOperation.source_type == "ORDER_CANCELLATION",
            FinancialOperation.subject_type == "ORDER",
            FinancialOperation.subject_id == order_id,
            FinancialOperation.branch_id == branch_id,
            FinancialEntry.state == "CONFIRMED",
            FinancialEntry.amount == CustomerOrderPayment.amount,
            FinancialEntry.currency_code == CustomerOrderPayment.currency_code,
            FinancialEntry.actor_id == CustomerOrderPayment.recorded_by_user_id,
            FinancialEntry.cash_session_id == CustomerOrderPayment.cash_session_id,
            FinancialEntry.workstation_id == CustomerOrderPayment.workstation_id,
            FinancialEntry.payment_method_code == CustomerOrderPayment.payment_method_code,
        )
    )
    references.update(
        {payment_id: (operation_id, entry_id) for payment_id, operation_id, entry_id in refund_rows}
    )
    return references
