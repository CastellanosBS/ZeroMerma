"""Read-only eligible stock projection; admission still locks and validates inventory."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.domain.quantities import inventory_calculation
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryLotBalance,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryBalance


@dataclass(frozen=True)
class AvailableLot:
    lot_id: UUID
    lot_code: str
    expires_at: datetime | None
    available_quantity: Decimal


@dataclass(frozen=True)
class ProductAvailability:
    available_quantity: Decimal | None
    reserved_quantity: Decimal
    lots: tuple[AvailableLot, ...]


@inventory_calculation
def read_product_availability(
    session: Session,
    *,
    branch_id: UUID,
    products: Sequence[Product],
    location_code: str = "COUNTER",
    at: datetime | None = None,
) -> dict[UUID, ProductAvailability]:
    """Constrain lot availability by both aggregate and eligible physical balances."""
    if not products:
        return {}
    instant = at or datetime.now(UTC)
    product_ids = [product.id for product in products]
    with session.no_autoflush:
        balances = {
            row.product_id: row
            for row in session.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.branch_id == branch_id,
                    InventoryBalance.location_code == location_code,
                    InventoryBalance.product_id.in_(product_ids),
                )
            )
        }
        lot_rows = session.execute(
            select(InventoryLot, InventoryLotBalance)
            .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
            .where(
                InventoryLotBalance.branch_id == branch_id,
                InventoryLotBalance.location_code == location_code,
                InventoryLotBalance.product_id.in_(product_ids),
                InventoryLot.unidentified.is_(False),
            )
            .order_by(InventoryLot.expires_at.asc().nulls_last(), InventoryLot.id)
        ).all()
        result = {}
        for product in products:
            balance = balances.get(product.id)
            reserved = balance.quantity_reserved if balance else Decimal(0)
            available = (
                max(balance.quantity_on_hand - reserved, Decimal(0)) if balance else Decimal(0)
            )
            lots = []
            if product.is_inventory_tracked and product.lot_tracking_enabled:
                capacity = available
                for lot, lot_balance in lot_rows:
                    if lot.product_id != product.id:
                        continue
                    if lot.expires_at is None and product.expiry_required:
                        continue
                    if lot.expires_at is not None and lot.expires_at <= instant:
                        continue
                    quantity = min(
                        max(
                            lot_balance.quantity_on_hand - lot_balance.quantity_reserved, Decimal(0)
                        ),
                        capacity,
                    )
                    if quantity > 0:
                        lots.append(AvailableLot(lot.id, lot.lot_code, lot.expires_at, quantity))
                        capacity -= quantity
                available = sum((lot.available_quantity for lot in lots), Decimal(0))
            result[product.id] = ProductAvailability(
                available if product.is_inventory_tracked else None,
                reserved if product.is_inventory_tracked else Decimal(0),
                tuple(lots),
            )
    return result
