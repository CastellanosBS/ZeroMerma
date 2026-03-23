from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import ORMReadSchema

ReceiptPaymentMethod = Literal["CASH", "CARD", "OTHER"]


class PosReceiptLineOut(ORMReadSchema):
    """
    One printable receipt line.

    This is a snapshot-oriented projection intended for rendering/printing.
    It should remain stable even if catalog/product master data changes later.
    """

    product_id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    qty: Decimal
    unit_price: Decimal
    line_total: Decimal


class PosReceiptOut(ORMReadSchema):
    """
    Canonical printable receipt payload.

    This schema is reused by:
    - checkout response
    - reprint response

    The goal is to keep one single receipt contract across the POS kernel.
    """

    sale_id: int
    branch_id: int
    cash_session_id: int
    created_at: datetime

    payment_method: ReceiptPaymentMethod
    amount_tendered: Decimal | None = None
    change_due: Decimal

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    items: list[PosReceiptLineOut] = Field(default_factory=list)
