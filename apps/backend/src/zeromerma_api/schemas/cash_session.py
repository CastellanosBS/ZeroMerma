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

    Security:
    - closed_by_id is derived from the authenticated user, never from the client payload.
    """

    closing_amount: NonNegativeMoney


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

    status: CashSessionStatusLiteral | str

    created_at: datetime
    updated_at: datetime
