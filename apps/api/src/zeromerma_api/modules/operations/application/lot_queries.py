"""Physical lot choices include expired goods so an operator can record their waste."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryLotBalance,
)


class OperationInventoryLotView(BaseModel):
    lot_id: UUID
    lot_code: str
    expires_at: datetime | None
    unidentified: bool
    location_code: str
    quantity_on_hand: Decimal
    quantity_reserved: Decimal
    available_quantity: Decimal


def operation_lot_choices(
    session: Session, *, branch_id: UUID, product_id: UUID, location_code: str | None = None
) -> list[OperationInventoryLotView]:
    query = (
        select(InventoryLot, InventoryLotBalance)
        .join(InventoryLotBalance, InventoryLotBalance.lot_id == InventoryLot.id)
        .where(
            InventoryLotBalance.branch_id == branch_id,
            InventoryLotBalance.product_id == product_id,
            InventoryLotBalance.location_code.in_(["BACKROOM", "COUNTER", "QUARANTINE"]),
            InventoryLotBalance.quantity_on_hand > 0,
        )
        .order_by(InventoryLot.expires_at.asc().nulls_last(), InventoryLot.id)
    )
    if location_code is not None:
        query = query.where(InventoryLotBalance.location_code == location_code)
    return [
        OperationInventoryLotView(
            lot_id=lot.id,
            lot_code=lot.lot_code,
            expires_at=lot.expires_at,
            unidentified=lot.unidentified,
            location_code=balance.location_code,
            quantity_on_hand=balance.quantity_on_hand,
            quantity_reserved=balance.quantity_reserved,
            available_quantity=max(
                Decimal(0), balance.quantity_on_hand - balance.quantity_reserved
            ),
        )
        for lot, balance in session.execute(query)
    ]
