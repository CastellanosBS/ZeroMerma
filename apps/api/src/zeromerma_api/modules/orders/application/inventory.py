"""Reserve complete exact-product orders and consume only those reservations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryReservation
from zeromerma_api.modules.orders.domain.exceptions import OrderStateConflictError
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrder, CustomerOrderItem


def apply_order_inventory(
    session: Session, *, order: CustomerOrder, actor_id: UUID, action: str
) -> None:
    items = session.scalars(
        select(CustomerOrderItem)
        .where(CustomerOrderItem.customer_order_id == order.id)
        .order_by(CustomerOrderItem.id)
    ).all()
    products = {
        p.id: p
        for p in session.scalars(
            select(Product).where(Product.id.in_([item.product_id for item in items]))
        )
    }
    tracked = [item for item in items if products[item.product_id].is_inventory_tracked]
    balances = lock_inventory_balances(
        session,
        [InventoryBalanceKey(order.branch_id, item.product_id, "COUNTER") for item in tracked],
    )
    if action == "reserve":
        for item in tracked:
            balances.reserve(
                key=InventoryBalanceKey(order.branch_id, item.product_id, "COUNTER"),
                quantity=item.quantity,
                unit_of_measure=products[item.product_id].unit_of_measure,
                source_document_type="CUSTOMER_ORDER",
                source_document_id=order.id,
                source_line_id=item.id,
                causal_effect_code=f"order:{item.id}:reserve",
                operator_user_id=actor_id,
            )
        return
    if action not in {"consume", "release"}:
        raise ValueError("Unknown order inventory action.")
    reservations = session.scalars(
        select(InventoryReservation)
        .where(
            InventoryReservation.source_document_type == "CUSTOMER_ORDER",
            InventoryReservation.source_document_id == order.id,
        )
        .order_by(InventoryReservation.id)
    ).all()
    by_line = {reservation.source_line_id: reservation for reservation in reservations}
    if len(by_line) != len(reservations):
        raise OrderStateConflictError("Order reservation evidence is duplicated.")
    for item in tracked:
        reservation = by_line.get(item.id)
        if reservation is None:
            if action == "release" and order.status == "PENDING":
                continue
            raise OrderStateConflictError("The order has no complete physical reservation.")
        remaining = (
            reservation.quantity - reservation.consumed_quantity - reservation.released_quantity
        )
        if action == "consume":
            if remaining != item.quantity:
                raise OrderStateConflictError(
                    "The complete order reservation is required for delivery."
                )
            balances.consume(
                reservation.id,
                quantity=remaining,
                movement_type="ORDER_DELIVERY",
                source_document_type="CUSTOMER_ORDER",
                source_document_id=order.id,
                source_line_id=item.id,
                causal_effect_code=f"order:{item.id}:consume",
                operator_user_id=actor_id,
            )
        elif remaining > 0:
            balances.release(
                reservation.id,
                quantity=remaining,
                causal_effect_code=f"order:{item.id}:release",
                reason="ORDER_CANCELLED",
            )
