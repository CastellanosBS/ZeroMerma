# apps/backend/src/zeromerma_api/schemas/cash_session.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import NonNegativeMoney, ORMReadSchema, StrictInputSchema

CashSessionStatusLiteral = Literal["OPEN", "CLOSED", "CANCELED"]


class CashSessionOpenIn(StrictInputSchema):
    """
    Request payload to open a cash session.

    Security:
    - opened_by_id is derived from the authenticated user, never from the client payload.
    """

    branch_id: int = Field(ge=1)
    opening_amount: NonNegativeMoney


class CashSessionCloseIn(StrictInputSchema):
    """
    Request payload to close a cash session.

    Backward compatibility:
    - closing_amount remains the counted real cash in drawer.
    - non-cash counted totals are optional; when omitted, the backend assumes
      they match the expected values and marks that assumption in the
      reconciliation snapshot.
    """

    closing_amount: NonNegativeMoney
    counted_card_total: NonNegativeMoney | None = None
    counted_transfer_total: NonNegativeMoney | None = None
    counted_other_total: NonNegativeMoney | None = None
    note: str | None = Field(default=None, max_length=500)


class CashSessionPaymentMethodTotalsOut(ORMReadSchema):
    """
    Canonical payment totals by method.

    This projection is used for expected POS payment totals that come from
    persisted payments linked to sales in the cash session.
    """

    cash: Decimal
    card: Decimal
    transfer: Decimal
    other: Decimal


class CashSessionNonCashTotalsOut(ORMReadSchema):
    """
    Canonical non-cash totals used during close reconciliation.
    """

    card: Decimal
    transfer: Decimal
    other: Decimal


class CashSessionReconciliationOut(ORMReadSchema):
    """
    Persisted operational reconciliation evidence captured at close time.
    """

    expected_payment_totals_by_method: CashSessionPaymentMethodTotalsOut
    expected_non_cash_totals_by_method: CashSessionNonCashTotalsOut
    counted_non_cash_totals_by_method: CashSessionNonCashTotalsOut
    non_cash_differences_by_method: CashSessionNonCashTotalsOut

    expected_cash: Decimal
    counted_cash: Decimal
    cash_difference: Decimal

    total_expected_non_cash: Decimal
    total_counted_non_cash: Decimal
    total_difference: Decimal

    assumed_counted_non_cash_methods: list[str] = Field(default_factory=list)
    note: str | None = None


class CashSessionOut(ORMReadSchema):
    """
    Canonical cash session response model.
    """

    id: int
    branch_id: int
    opened_by_id: int
    closed_by_id: int | None = None

    opened_at: datetime
    closed_at: datetime | None = None

    opening_amount: Decimal
    closing_amount: Decimal | None = None
    expected_cash: Decimal | None = None

    reconciliation_snapshot: CashSessionReconciliationOut | None = None

    status: CashSessionStatusLiteral | str

    created_at: datetime
    updated_at: datetime
