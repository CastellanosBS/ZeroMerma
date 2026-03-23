from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from .common import ORMReadSchema, PositiveQuantity, StrictInputSchema

PosOrderStatus = Literal[
    "CREATED",
    "SENT_TO_BAKERY",
    "READY",
    "DELIVERED",
    "CANCELED",
]


class PosOrderCreateItemIn(StrictInputSchema):
    """
    One order line for an existing finished-good product.
    """

    product_id: int = Field(ge=1)
    qty: PositiveQuantity


class PosOrderCreateIn(StrictInputSchema):
    """
    Create a customer order from POS/front-of-house.

    2B.1 semantics:
    - finished goods only
    - no inventory mutation
    - price snapshots frozen at creation time
    """

    branch_id: int = Field(ge=1)
    customer_name: str | None = Field(default=None, max_length=120)
    customer_phone: str | None = Field(default=None, max_length=32)
    note: str | None = Field(default=None, max_length=1000)
    requested_for_at: datetime | None = None
    items: list[PosOrderCreateItemIn] = Field(min_length=1)


class PosOrderItemOut(ORMReadSchema):
    """
    One order line as shown back to POS/admin/bakers.

    Product labels come from current product master data in 2B.1, while price
    commitments come from frozen snapshot fields.
    """

    product_id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    qty: Decimal
    unit_price_snapshot: Decimal
    line_total_snapshot: Decimal


class PosOrderSummaryOut(ORMReadSchema):
    """
    Summary projection for order listing screens.
    """

    id: int
    branch_id: int
    created_by_id: int
    delivered_sale_id: int | None = None

    status: PosOrderStatus | str

    customer_name: str | None = None
    customer_phone: str | None = None
    note: str | None = None

    requested_for_at: datetime | None = None
    sent_to_bakery_at: datetime | None = None
    ready_at: datetime | None = None
    delivered_at: datetime | None = None
    canceled_at: datetime | None = None

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    created_at: datetime
    updated_at: datetime


class PosOrderDetailOut(PosOrderSummaryOut):
    """
    Full detail projection for one order.
    """

    sent_to_bakery_by_id: int | None = None
    ready_by_id: int | None = None
    delivered_by_id: int | None = None
    canceled_by_id: int | None = None

    items: list[PosOrderItemOut] = Field(default_factory=list)
