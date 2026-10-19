"""Explain immutable inventory policy conflicts before the database guard is reached."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryReservation,
)


def inventory_policy_conflict(
    session: Session,
    product: Product,
    *,
    unit_of_measure: str | None = None,
    lot_tracking_enabled: bool | None = None,
    expiry_required: bool | None = None,
    is_inventory_tracked: bool | None = None,
) -> str | None:
    changed = (
        unit_of_measure is not None
        and unit_of_measure.strip().upper() != product.unit_of_measure.strip().upper()
    ) or any(
        requested is not None and requested != existing
        for requested, existing in (
            (lot_tracking_enabled, product.lot_tracking_enabled),
            (expiry_required, product.expiry_required),
            (is_inventory_tracked, product.is_inventory_tracked),
        )
    )
    if changed and any(
        session.scalar(select(model.id).where(model.product_id == product.id).limit(1)) is not None
        for model in (InventoryMovement, InventoryReservation, InventoryBalance)
    ):
        return (
            "Inventory units and tracking policy require explicit reconciliation "
            "after stock evidence exists."
        )
    return None
