# apps/backend/src/zeromerma_api/services/inventory_service.py
# PURPOSE:
#   Inventory calculations based on the immutable inventory ledger (inventory_movement).
#   MVP = compute on-hand using SUM(qty) per (branch_id, product_id).
#
#   Later, if you add a snapshot table (Inventory), this module becomes the single place
#   to change the implementation.

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.models.inventory_movement import InventoryMovement

QTY_PLACES = Decimal("0.001")


def to_decimal(value: float | int | str) -> Decimal:
    return Decimal(str(value))


def qty(value: Decimal) -> Decimal:
    return value.quantize(QTY_PLACES, rounding=ROUND_HALF_UP)


def get_on_hand(db: Session, *, branch_id: int, product_id: int) -> Decimal:
    """
    On-hand = SUM(all movements.qty) for this branch/product.
    If no rows exist, on-hand = 0.
    """
    stmt = (
        select(func.coalesce(func.sum(InventoryMovement.qty), 0))
        .where(InventoryMovement.branch_id == branch_id)
        .where(InventoryMovement.product_id == product_id)
    )
    val = db.scalar(stmt)
    return qty(to_decimal(val or 0))
