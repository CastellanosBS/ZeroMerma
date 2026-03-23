# apps/backend/src/zeromerma_api/schemas/sale.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import (
    NonNegativeMoney,
    ORMReadSchema,
    PositiveQuantity,
    StrictInputSchema,
)

SaleStatusLiteral = Literal["OPEN", "CANCELED"]


class SaleItemCreate(StrictInputSchema):
    """
    One sale line in the sale creation payload.

    Notes:
    - unit_price is optional so the backend can resolve effective price server-side.
    """

    product_id: int = Field(ge=1)
    qty: PositiveQuantity
    unit_price: NonNegativeMoney | None = None


class SaleCreate(StrictInputSchema):
    """
    Create a sale transactionally.

    Security:
    - created_by_id is derived from the authenticated user, never from the client payload.
    """

    branch_id: int = Field(ge=1)
    cash_session_id: int = Field(ge=1)
    items: list[SaleItemCreate] = Field(min_length=1)


class SaleItemOut(ORMReadSchema):
    """
    Sale line returned by the API.
    """

    id: int
    product_id: int
    qty: Decimal
    unit_price: Decimal
    line_total: Decimal


class PaymentEmbeddedOut(ORMReadSchema):
    """
    Embedded payment representation used in sale detail responses.
    """

    id: int
    sale_id: int
    method: str
    amount: Decimal
    reference: str | None = None
    created_at: datetime


class SaleOut(ORMReadSchema):
    """
    Canonical sale response model.
    """

    id: int
    branch_id: int
    cash_session_id: int
    created_by_id: int

    created_at: datetime
    updated_at: datetime

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    status: SaleStatusLiteral | str

    items: list[SaleItemOut] = Field(default_factory=list)


class SaleDetailOut(SaleOut):
    """
    Extended sale view including payments and derived amounts.
    """

    payments: list[PaymentEmbeddedOut] = Field(default_factory=list)
    paid_amount: Decimal = Decimal("0")
    balance_due: Decimal = Decimal("0")
