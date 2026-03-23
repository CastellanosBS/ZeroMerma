# apps/backend/src/zeromerma_api/schemas/payment.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import ORMReadSchema, PositiveMoney, StrictInputSchema

PaymentMethodLiteral = Literal["CASH", "CARD", "TRANSFER", "OTHER"]


class PaymentCreate(StrictInputSchema):
    """
    Append a payment to an existing sale.

    Notes:
    - sale_id is taken from the path parameter, not from the body.
    - amount must be strictly positive.
    """

    method: PaymentMethodLiteral | str
    amount: PositiveMoney
    reference: str | None = Field(default=None, max_length=64)


class PaymentOut(ORMReadSchema):
    """
    Canonical payment response model.
    """

    id: int
    sale_id: int
    method: PaymentMethodLiteral | str
    amount: Decimal
    reference: str | None = None
    created_at: datetime
