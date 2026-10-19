"""Cash-session projections from canonical financial facts only."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import authorization_scope
from zeromerma_api.modules.financial_ledger.domain.money import financial_calculation
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)

ZERO = Decimal("0.00")


@dataclass(frozen=True)
class SessionFinancials:
    opening_amount: Decimal
    opening_valid: bool
    entries: tuple[tuple[FinancialOperation, FinancialEntry], ...]
    unresolved_count: int

    @financial_calculation
    def amount(
        self, *, method: str, kind: str | None = None, direction: str | None = None
    ) -> Decimal:
        return sum(
            (
                entry.amount
                for operation, entry in self.entries
                if entry.payment_method_code == method
                and (kind is None or operation.kind == kind)
                and (direction is None or entry.direction == direction)
            ),
            ZERO,
        )

    @financial_calculation
    def net(self, method: str) -> Decimal:
        return self.amount(method=method, direction="IN") - self.amount(
            method=method, direction="OUT"
        )

    @property
    @financial_calculation
    def total_cash_in(self) -> Decimal:
        return self.amount(method="CASH", direction="IN") - self.opening_amount

    @property
    def total_cash_out(self) -> Decimal:
        return self.amount(method="CASH", direction="OUT")

    @property
    def expected_cash_amount(self) -> Decimal:
        return self.net("CASH")

    @property
    def expected_card_amount(self) -> Decimal:
        return self.net("CARD")


@financial_calculation
def read_session_financials(session: Session, cash_session_id: UUID) -> SessionFinancials:
    """One statement snapshot; caller owns authorization and cash admission locks.

    Include entries posted in this turn even when their obligation originated in
    an earlier one. An unassigned refund remainder is a debt, not an admitted leg;
    only PENDING/PROCESSING/UNKNOWN legs can still change this turn.
    """
    if authorization_scope(session) is None:
        raise HTTPException(
            status_code=403, detail="An explicit authorization context is required."
        )
    statement = (
        select(FinancialOperation, FinancialEntry)
        .outerjoin(FinancialEntry, FinancialEntry.financial_operation_id == FinancialOperation.id)
        .where(
            or_(
                FinancialOperation.cash_session_id == cash_session_id,
                FinancialEntry.cash_session_id == cash_session_id,
            )
        )
        .execution_options(populate_existing=True)
    )
    opening: dict[UUID, FinancialOperation] = {}
    confirmed: list[tuple[FinancialOperation, FinancialEntry]] = []
    unresolved = 0
    with session.no_autoflush:
        for operation, entry in session.execute(statement):
            if operation.kind == "CASH_OPENING" and operation.cash_session_id == cash_session_id:
                opening[operation.id] = operation
            if entry is None or entry.cash_session_id != cash_session_id:
                continue
            if entry.state == "CONFIRMED":
                confirmed.append((operation, entry))
            elif entry.state in {"PENDING", "PROCESSING", "UNKNOWN"}:
                unresolved += 1
    opening_amount = sum((o.amount_due for o in opening.values()), ZERO)
    opening_posted = sum((e.amount for o, e in confirmed if o.kind == "CASH_OPENING"), ZERO)
    return SessionFinancials(
        opening_amount=opening_posted,
        opening_valid=len(opening) == 1 and opening_amount == opening_posted,
        entries=tuple(confirmed),
        unresolved_count=unresolved,
    )
