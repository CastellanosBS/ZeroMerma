# apps/backend/src/zeromerma_api/schemas/inventory.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from .common import ORMReadSchema


class StockRow(ORMReadSchema):
    """
    One aggregated stock record grouped by (branch, product).
    """

    branch_id: int
    product_id: int
    sku: str | None = None
    product_name: str
    qty: Decimal


class MovementRow(ORMReadSchema):
    """
    One immutable inventory ledger movement.
    """

    id: int
    branch_id: int
    product_id: int
    qty: Decimal
    reason: str
    ref_type: str | None = None
    ref_id: int | None = None
    note: str | None = None
    created_by_id: int | None = None
    created_at: datetime
