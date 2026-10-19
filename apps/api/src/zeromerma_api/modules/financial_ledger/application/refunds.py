"""Refund admission and CASH_FIRST settlement inside the caller's locked command."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.financial_ledger.application.recording import (
    FinancialCommandScope,
    create_financial_operation,
    record_confirmed_entry,
)
from zeromerma_api.modules.financial_ledger.application.refund_schemas import (
    FinancialRefundEntryView,
    FinancialRefundView,
)
from zeromerma_api.modules.financial_ledger.application.session_queries import (
    read_session_financials,
)
from zeromerma_api.modules.financial_ledger.domain.constants import (
    Direction,
    OperationKind,
    PaymentMethod,
)
from zeromerma_api.modules.financial_ledger.domain.money import (
    ZERO,
    FinancialModelError,
    financial_calculation,
    require_money,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment

COLLECTION_KINDS = ("SALE_COLLECTION", "ORDER_ADVANCE", "ORDER_SETTLEMENT")
REFUND_KINDS = ("SALE_REFUND", "ORDER_REFUND")


@financial_calculation
def _collections(
    session: Session, *, subject_type: str, subject_id: UUID, branch_id: UUID, currency_code: str
) -> tuple[list[UUID], Decimal]:
    operations = list(
        session.scalars(
            select(FinancialOperation)
            .where(
                FinancialOperation.subject_type == subject_type,
                FinancialOperation.subject_id == subject_id,
                FinancialOperation.branch_id == branch_id,
                FinancialOperation.currency_code == currency_code,
                FinancialOperation.kind.in_((*COLLECTION_KINDS, "OPENING_OBLIGATION")),
            )
            .order_by(FinancialOperation.occurred_at, FinancialOperation.id)
        )
    )
    valid = [
        op
        for op in operations
        if op.kind in COLLECTION_KINDS
        or (op.opening_obligation_kind == "CUSTOMER_ADVANCE" and subject_type == "ORDER")
    ]
    ids = [op.id for op in valid]
    entries = (
        list(
            session.scalars(
                select(FinancialEntry).where(
                    FinancialEntry.financial_operation_id.in_(ids),
                    FinancialEntry.state == "CONFIRMED",
                )
            )
        )
        if ids
        else []
    )
    reversals = (
        list(
            session.scalars(
                select(FinancialEntry).where(
                    FinancialEntry.reverses_entry_id.in_([entry.id for entry in entries]),
                    FinancialEntry.state == "CONFIRMED",
                )
            )
        )
        if entries
        else []
    )
    paid = sum((entry.amount for entry in entries), ZERO) - sum(
        (entry.amount for entry in reversals), ZERO
    )
    paid += sum((op.amount_due for op in valid if op.kind == "OPENING_OBLIGATION"), ZERO)
    return ids, paid


@financial_calculation
def read_refund(session: Session, operation: FinancialOperation) -> FinancialRefundView:
    entries = list(
        session.scalars(
            select(FinancialEntry)
            .where(
                FinancialEntry.financial_operation_id == operation.id,
            )
            .order_by(FinancialEntry.occurred_at, FinancialEntry.id)
        )
    )
    settled = sum((entry.amount for entry in entries if entry.state == "CONFIRMED"), ZERO)
    pending = operation.amount_due - settled
    states = {entry.state for entry in entries}
    state = (
        "UNKNOWN"
        if "UNKNOWN" in states
        else "PROCESSING"
        if "PROCESSING" in states
        else "COMPLETED"
        if pending == ZERO
        else "PARTIALLY_SETTLED"
        if settled > ZERO
        else "PENDING"
    )
    original_ids, _ = _collections(
        session,
        subject_type=operation.subject_type,
        subject_id=operation.subject_id,
        branch_id=operation.branch_id,
        currency_code=operation.currency_code,
    )
    return FinancialRefundView(
        financial_operation_id=operation.id,
        source_type=operation.source_type,
        source_id=operation.source_id,
        amount_due=operation.amount_due,
        amount_settled=settled,
        amount_pending=pending,
        state=state,
        cash_settled_amount=sum(
            (
                entry.amount
                for entry in entries
                if entry.state == "CONFIRMED" and entry.payment_method_code == "CASH"
            ),
            ZERO,
        ),
        card_settled_amount=sum(
            (
                entry.amount
                for entry in entries
                if entry.state == "CONFIRMED" and entry.payment_method_code == "CARD"
            ),
            ZERO,
        ),
        original_collection_operation_ids=original_ids,
        entries=[
            FinancialRefundEntryView(
                id=entry.id,
                payment_method_code=entry.payment_method_code,
                execution_mode=entry.execution_mode,
                state=entry.state,
                amount=entry.amount,
                cash_session_id=entry.cash_session_id,
                occurred_at=entry.occurred_at,
            )
            for entry in entries
        ],
    )


def find_refund(
    session: Session, *, source_type: str, source_id: UUID
) -> FinancialRefundView | None:
    operation = session.scalar(
        select(FinancialOperation).where(
            FinancialOperation.source_type == source_type,
            FinancialOperation.source_id == source_id,
            FinancialOperation.kind.in_(REFUND_KINDS),
        )
    )
    return read_refund(session, operation) if operation is not None else None


@financial_calculation
def admit_refund(
    session: Session,
    *,
    source_type: str,
    source_id: UUID,
    subject_type: str,
    subject_id: UUID,
    amount_due: Decimal,
    currency_code: str,
    scope: FinancialCommandScope,
    occurred_at: datetime,
) -> FinancialRefundView:
    """Caller holds the original SALE/ORDER row after acquiring the actual drawer lock."""
    require_money(amount_due)
    original_ids, paid = _collections(
        session,
        subject_type=subject_type,
        subject_id=subject_id,
        branch_id=scope.branch_id,
        currency_code=currency_code,
    )
    admitted = (
        session.scalar(
            select(func.coalesce(func.sum(FinancialOperation.amount_due), ZERO)).where(
                FinancialOperation.subject_type == subject_type,
                FinancialOperation.subject_id == subject_id,
                FinancialOperation.branch_id == scope.branch_id,
                FinancialOperation.currency_code == currency_code,
                FinancialOperation.kind.in_(REFUND_KINDS),
            )
        )
        or ZERO
    )
    if amount_due + admitted > paid:
        raise FinancialModelError(
            "Refund obligations exceed the original confirmed financial entitlement."
        )
    operation = create_financial_operation(
        session,
        kind=OperationKind.SALE_REFUND if subject_type == "SALE" else OperationKind.ORDER_REFUND,
        source_type=source_type,
        source_id=source_id,
        subject_type=subject_type,
        subject_id=subject_id,
        amount_due=amount_due,
        currency_code=currency_code,
        scope=scope,
        occurred_at=occurred_at,
        related_operation_id=original_ids[0] if original_ids else None,
        relation_kind="REFUND_OF" if original_ids else None,
    )
    return settle_refund_cash(session, operation=operation, scope=scope, occurred_at=occurred_at)


@financial_calculation
def settle_refund_cash(
    session: Session,
    *,
    operation: FinancialOperation,
    scope: FinancialCommandScope,
    occurred_at: datetime | None = None,
) -> FinancialRefundView:
    """Only unallocated remainder can move to a new cash leg; uncertain legs stay reserved."""
    session.refresh(operation, with_for_update=True)
    if (
        operation.kind not in REFUND_KINDS
        or operation.branch_id != scope.branch_id
        or scope.cash_session_id is None
        or scope.workstation_id is None
    ):
        raise FinancialModelError("Refund settlement requires the original authorized obligation.")
    cash = read_session_financials(session, scope.cash_session_id)
    if not cash.opening_valid:
        raise FinancialModelError("Refund settlement requires a validated canonical cash opening.")
    reserved = (
        session.scalar(
            select(func.coalesce(func.sum(FinancialEntry.amount), ZERO)).where(
                FinancialEntry.financial_operation_id == operation.id,
                FinancialEntry.state.not_in(("REJECTED", "CANCELLED")),
            )
        )
        or ZERO
    )
    amount = min(max(operation.amount_due - reserved, ZERO), max(cash.expected_cash_amount, ZERO))
    if amount > ZERO:
        owner = execution(session)
        if owner is None or owner.record is None or not owner.action_running:
            raise FinancialModelError("Refund settlement requires its admitted command.")
        instant = occurred_at or datetime.now(UTC)
        entry = record_confirmed_entry(
            session,
            operation=operation,
            leg_key=str(owner.record.id),
            payment_method=PaymentMethod.CASH,
            direction=Direction.OUT,
            amount=amount,
            scope=scope,
            occurred_at=instant,
        )
        if operation.subject_type == "ORDER":
            sequence = (
                int(
                    session.scalar(
                        select(func.coalesce(func.max(CustomerOrderPayment.sequence), 0)).where(
                            CustomerOrderPayment.customer_order_id == operation.subject_id,
                        )
                    )
                    or 0
                )
                + 1
            )
            session.add(
                CustomerOrderPayment(
                    customer_order_id=operation.subject_id,
                    financial_entry_id=entry.id,
                    sequence=sequence,
                    payment_type="REFUND",
                    payment_method_code="CASH",
                    amount=amount,
                    currency_code=operation.currency_code,
                    workstation_id=scope.workstation_id,
                    cash_session_id=scope.cash_session_id,
                    recorded_by_user_id=scope.actor_id,
                    recorded_at_utc=instant,
                )
            )
            session.flush()
    return read_refund(session, operation)
