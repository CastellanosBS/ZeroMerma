# apps/backend/src/zeromerma_api/schemas/inventory.py
# PURPOSE: Response schemas (Pydantic) for inventory endpoints.
#          They declare exactly what the API returns and keep routers clean.

from __future__ import (
    annotations,
)  # Postpone type-hint evaluation; avoids certain import cycles.

from datetime import datetime  # We will return created_at on movement rows.

from pydantic import BaseModel  # Base class for our response models.


class StockRow(BaseModel):
    """
    One aggregated stock record, grouped by (branch, product).
    """

    branch_id: int  # Which branch this stock is for.
    product_id: int  # Which product this stock is for.
    sku: str | None  # Optional SKU (nullable in DB/API).
    product_name: str  # Human-friendly name.
    qty: float  # Aggregated quantity: SUM(qty) across movements.

    class Config:
        orm_mode = True  # Allows returning ORM-ish rows or named tuples.


class MovementRow(BaseModel):
    """
    One immutable ledger movement (as returned by the API).
    """

    id: int
    branch_id: int
    product_id: int
    qty: float
    reason: str
    ref_type: str | None
    ref_id: int | None
    note: str | None
    created_by_id: int | None
    created_at: datetime

    class Config:
        orm_mode = True
