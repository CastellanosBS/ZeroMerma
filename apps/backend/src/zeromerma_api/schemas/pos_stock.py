from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from .common import ORMReadSchema, PositiveQuantity, StrictInputSchema


class PosFinishedGoodsStockItemIn(StrictInputSchema):
    """
    One finished-goods stock registration line.

    This contract is intentionally minimal for fast branch-side capture.
    """

    product_id: int = Field(ge=1)
    qty: PositiveQuantity


class PosFinishedGoodsStockIn(StrictInputSchema):
    """
    Fast finished-goods stock registration payload for POS.

    Semantics:
    - branch scoped
    - finished goods only
    - POS-sellable products only
    - immediate inventory snapshot update
    """

    branch_id: int = Field(ge=1)
    items: list[PosFinishedGoodsStockItemIn] = Field(min_length=1)
    note: str | None = Field(default=None, max_length=500)


class PosFinishedGoodsStockLineOut(ORMReadSchema):
    """
    One applied stock-in line.
    """

    product_id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    qty_added: Decimal
    new_on_hand: Decimal


class PosFinishedGoodsStockOut(ORMReadSchema):
    """
    Response for one finished-goods stock registration batch.
    """

    branch_id: int
    audit_event_id: int
    applied_count: int
    note: str | None = None
    items: list[PosFinishedGoodsStockLineOut] = Field(default_factory=list)
