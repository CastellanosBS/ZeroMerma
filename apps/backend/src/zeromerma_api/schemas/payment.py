# apps/backend/src/zeromerma_api/schemas/payment.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from zeromerma_api.core.payment_method import PaymentMethod

from .common import ORMReadSchema, PositiveMoney, StrictInputSchema


class PaymentCreate(StrictInputSchema):
    """
    Append a payment to an existing sale.

    Notes:
    - sale_id is taken from the path parameter, not from the body.
    - amount must be strictly positive.
    - method is validated against the canonical shared PaymentMethod enum.
    """

    method: PaymentMethod
    amount: PositiveMoney
    reference: str | None = Field(default=None, max_length=64)


class PaymentOut(ORMReadSchema):
    """
    Canonical payment response model.
    """

    id: int
    sale_id: int
    method: PaymentMethod
    amount: Decimal
    reference: str | None = None
    created_at: datetime
