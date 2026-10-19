"""Scoped reads of confirmed order effects, with no legacy payment fallback."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Select, and_, case, or_, select
from sqlalchemy.orm import Session, aliased

from zeromerma_api.db.access_scope import authorization_scope
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash_close.infrastructure.models import CashSessionClose
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.orders.application.services import _build_order_folio
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrder, CustomerOrderPayment

ORDER_FINANCIAL_KINDS = ("ORDER_ADVANCE", "ORDER_SETTLEMENT", "ORDER_REFUND")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class OrderFinancialEntry:
    financial_entry_id: UUID
    financial_operation_id: UUID
    order_id: UUID
    order_folio: str
    order_status: str
    order_payment_id: UUID
    payment_type: str
    operation_kind: str
    payment_method_code: str
    direction: str
    amount: Decimal
    currency_code: str
    cash_session_id: UUID
    workstation_id: UUID
    workstation_name: str
    branch_id: UUID
    branch_name: str
    operator_id: UUID | None
    operator_name: str
    occurred_at: datetime
    cash_cut_id: UUID | None

    @property
    def signed_amount(self) -> Decimal:
        return self.amount if self.direction == "IN" else -self.amount


def _order_financial_entries_statement() -> Select[
    tuple[
        FinancialEntry,
        FinancialOperation,
        CustomerOrderPayment,
        CustomerOrder,
        str,
        str,
        str,
        UUID,
    ]
]:
    """Keep detail reads and SQL filters on the same confirmed causal graph."""
    original_entry = aliased(FinancialEntry, name="original_order_financial_entry")
    original_operation = aliased(FinancialOperation, name="original_order_financial_operation")
    is_reversal = FinancialOperation.kind == "TECHNICAL_REVERSAL"
    causal_payment_id = case(
        (is_reversal, original_operation.source_id), else_=FinancialOperation.source_id
    )
    causal_source_type = case(
        (is_reversal, original_operation.source_type), else_=FinancialOperation.source_type
    )
    causal_entry_id = case((is_reversal, original_entry.id), else_=FinancialEntry.id)
    return (
        select(
            FinancialEntry,
            FinancialOperation,
            CustomerOrderPayment,
            CustomerOrder,
            Branch.name,
            Workstation.name,
            User.full_name,
            CashSessionClose.id,
        )
        .select_from(FinancialEntry)
        .join(FinancialOperation, FinancialOperation.id == FinancialEntry.financial_operation_id)
        .outerjoin(original_entry, original_entry.id == FinancialEntry.reverses_entry_id)
        .outerjoin(
            original_operation, original_operation.id == original_entry.financial_operation_id
        )
        .join(
            CustomerOrderPayment,
            or_(
                and_(
                    causal_source_type == "ORDER_PAYMENT",
                    CustomerOrderPayment.id == causal_payment_id,
                ),
                and_(
                    causal_source_type == "ORDER_CANCELLATION",
                    CustomerOrderPayment.financial_entry_id == causal_entry_id,
                    CustomerOrderPayment.payment_type == "REFUND",
                ),
            ),
        )
        .join(
            CustomerOrder,
            and_(
                CustomerOrder.id == CustomerOrderPayment.customer_order_id,
                CustomerOrder.id == FinancialOperation.subject_id,
                CustomerOrder.branch_id == FinancialEntry.branch_id,
            ),
        )
        .join(Branch, Branch.id == FinancialEntry.branch_id)
        .join(Workstation, Workstation.id == FinancialEntry.workstation_id)
        .outerjoin(User, User.id == FinancialEntry.actor_id)
        .outerjoin(
            CashSessionClose, CashSessionClose.cash_session_id == FinancialEntry.cash_session_id
        )
        .where(
            FinancialEntry.state == "CONFIRMED",
            FinancialOperation.subject_type == "ORDER",
            FinancialEntry.cash_session_id.is_not(None),
            or_(
                and_(
                    FinancialOperation.kind.in_(ORDER_FINANCIAL_KINDS),
                    FinancialOperation.source_type.in_(("ORDER_PAYMENT", "ORDER_CANCELLATION")),
                ),
                and_(
                    is_reversal,
                    FinancialOperation.source_type == "FINANCIAL_ENTRY",
                    original_operation.kind.in_(ORDER_FINANCIAL_KINDS),
                    original_operation.source_type.in_(("ORDER_PAYMENT", "ORDER_CANCELLATION")),
                    original_operation.subject_type == "ORDER",
                    original_operation.subject_id == CustomerOrder.id,
                    original_entry.state == "CONFIRMED",
                ),
            ),
        )
        .order_by(FinancialEntry.occurred_at, FinancialEntry.id)
    )


def order_financial_session_ids_statement(
    *, payment_method: str | None = None, refunds_only: bool = False
) -> Select[tuple[UUID | None]]:
    """Build a scoped ORM subquery without loading historical ledger rows in Python."""
    statement = (
        _order_financial_entries_statement()
        .with_only_columns(FinancialEntry.cash_session_id)
        .order_by(None)
        .distinct()
        .correlate(None)
    )
    if payment_method is not None:
        statement = statement.where(FinancialEntry.payment_method_code == payment_method)
    if refunds_only:
        statement = statement.where(FinancialOperation.kind == "ORDER_REFUND")
    return statement


def read_order_financial_entries(
    session: Session, *, cash_session_ids: Sequence[UUID] | None = None
) -> list[OrderFinancialEntry]:
    """Participate in the caller's authorized scope without adding BO-only capabilities.

    Reads financial entries once; CustomerOrderPayment is causal metadata, never a
    second amount source. Reversal lineage must reach an adopted order payment.
    No flush, commit, scope replacement or unscoped/Core bypass is performed.
    """
    if authorization_scope(session) is None:
        raise HTTPException(
            status_code=403, detail="An explicit authorization context is required."
        )
    if cash_session_ids is not None and not cash_session_ids:
        return []
    statement = _order_financial_entries_statement()
    if cash_session_ids is not None:
        statement = statement.where(FinancialEntry.cash_session_id.in_(cash_session_ids))
    result: list[OrderFinancialEntry] = []
    with session.no_autoflush:
        for (
            entry,
            operation,
            payment,
            order,
            branch_name,
            station_name,
            actor_name,
            close_id,
        ) in session.execute(statement):
            assert entry.cash_session_id is not None and entry.workstation_id is not None
            result.append(
                OrderFinancialEntry(
                    financial_entry_id=entry.id,
                    financial_operation_id=operation.id,
                    order_id=order.id,
                    order_folio=_build_order_folio(order.id),
                    order_status=order.status,
                    order_payment_id=payment.id,
                    payment_type=(
                        "TECHNICAL_REVERSAL"
                        if operation.kind == "TECHNICAL_REVERSAL"
                        else payment.payment_type
                    ),
                    operation_kind=operation.kind,
                    payment_method_code=entry.payment_method_code,
                    direction=entry.direction,
                    amount=entry.amount,
                    currency_code=entry.currency_code,
                    cash_session_id=entry.cash_session_id,
                    workstation_id=entry.workstation_id,
                    workstation_name=station_name,
                    branch_id=entry.branch_id,
                    branch_name=branch_name,
                    operator_id=entry.actor_id,
                    operator_name=actor_name or "Sistema",
                    occurred_at=entry.occurred_at,
                    cash_cut_id=close_id,
                )
            )
    return result


def order_cash_amounts(entries: Sequence[OrderFinancialEntry]) -> dict[str, Decimal]:
    cash = [entry for entry in entries if entry.payment_method_code == "CASH"]
    return {
        "cash_order_collections_amount": sum(
            (e.amount for e in cash if e.operation_kind in {"ORDER_ADVANCE", "ORDER_SETTLEMENT"}),
            ZERO,
        ),
        "cash_order_refunds_amount": sum(
            (e.amount for e in cash if e.operation_kind == "ORDER_REFUND"), ZERO
        ),
        "cash_order_technical_reversal_amount": sum(
            (e.signed_amount for e in cash if e.operation_kind == "TECHNICAL_REVERSAL"), ZERO
        ),
        "total_cash_in": sum((e.amount for e in cash if e.direction == "IN"), ZERO),
        "total_cash_out": sum((e.amount for e in cash if e.direction == "OUT"), ZERO),
    }
