from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product
from zeromerma_api.services.inventory_balance_service import (
    atomic_increment_on_hand,
    ensure_balance_row,
    qty,
    to_decimal,
)
from zeromerma_api.services.pos_audit_service import record_pos_audit_event


@dataclass(frozen=True)
class FinishedGoodsStockLine:
    """
    Normalized finished-goods stock registration line.
    """

    product_id: int
    qty: Decimal


def _normalize_lines(raw_items: list[dict[str, Any]]) -> list[FinishedGoodsStockLine]:
    """
    Normalize and aggregate requested stock lines by product_id.

    This allows the frontend to submit repeated product lines during fast
    keyboard-driven capture without creating ambiguous duplicate movements in
    the final persisted effect.
    """
    aggregated: dict[int, Decimal] = {}

    for item in raw_items:
        product_id = int(item["product_id"])
        line_qty = qty(to_decimal(item["qty"]))

        if line_qty <= 0:
            raise DomainValidationError(
                message="All stock registration quantities must be greater than zero.",
                details={
                    "product_id": product_id,
                    "qty": str(line_qty),
                },
            )

        aggregated[product_id] = aggregated.get(product_id, Decimal("0.000")) + line_qty

    return [
        FinishedGoodsStockLine(product_id=product_id, qty=qty(total_qty))
        for product_id, total_qty in aggregated.items()
    ]


def _load_products_for_stock_in(
    db: Session,
    *,
    product_ids: list[int],
) -> dict[int, Product]:
    """
    Load all products referenced by the request.

    Validation rules:
    - every product must exist
    - product must be active
    - product must not be an input
    - product must be POS sellable
    """
    stmt = select(Product).where(Product.id.in_(product_ids))
    products = list(db.scalars(stmt).all())

    found_ids = {int(product.id) for product in products}
    missing_ids = sorted(set(product_ids) - found_ids)
    if missing_ids:
        raise DomainNotFoundError(
            message="Some products do not exist.",
            details={"missing_product_ids": missing_ids},
        )

    by_id = {int(product.id): product for product in products}

    invalid_ids: list[int] = []
    for product_id in product_ids:
        product = by_id[product_id]
        if not product.is_active or product.is_input or not product.is_sellable_in_pos:
            invalid_ids.append(product_id)

    if invalid_ids:
        raise DomainConflictError(
            message=(
                "Only active POS-sellable finished goods can be registered through "
                "the POS stock endpoint."
            ),
            details={"invalid_product_ids": sorted(invalid_ids)},
        )

    return by_id


def register_finished_goods_stock(
    db: Session,
    *,
    branch_id: int,
    actor_user_id: int,
    items: list[dict[str, Any]],
    note: str | None = None,
) -> dict[str, Any]:
    """
    Register newly available finished goods directly from the POS flow.

    Guarantees:
    - only active POS-sellable finished goods are accepted
    - inventory_balance is updated immediately
    - inventory_movement receives a non-ambiguous reason
    - one audit event groups the batch operation
    """
    normalized_note = note.strip() if note is not None else None
    if normalized_note == "":
        normalized_note = None

    lines = _normalize_lines(items)
    product_ids = [line.product_id for line in lines]
    products = _load_products_for_stock_in(db, product_ids=product_ids)

    audit_event = record_pos_audit_event(
        db,
        branch_id=int(branch_id),
        actor_user_id=int(actor_user_id),
        entity_type="BRANCH",
        entity_id=int(branch_id),
        event_type="FINISHED_GOODS_STOCK_REGISTERED",
        payload={
            "branch_id": int(branch_id),
            "note": normalized_note,
            "requested_items": [
                {
                    "product_id": int(line.product_id),
                    "qty": str(line.qty),
                }
                for line in lines
            ],
            "status": "PENDING",
        },
    )

    applied_lines: list[dict[str, Any]] = []

    for line in lines:
        product = products[int(line.product_id)]

        ensure_balance_row(
            db,
            branch_id=int(branch_id),
            product_id=int(line.product_id),
        )

        new_on_hand = atomic_increment_on_hand(
            db,
            branch_id=int(branch_id),
            product_id=int(line.product_id),
            amount=line.qty,
        )

        movement = InventoryMovement(
            branch_id=int(branch_id),
            product_id=int(line.product_id),
            qty=float(line.qty),
            reason=MovementReason.POS_FINISHED_GOODS_STOCK_IN.value,
            ref_type="POS_AUDIT_EVENT",
            ref_id=int(audit_event.id),
            note=normalized_note,
            created_by_id=int(actor_user_id),
        )
        db.add(movement)

        applied_lines.append(
            {
                "product_id": int(product.id),
                "sku": product.sku,
                "name": product.name,
                "quick_name": product.quick_name,
                "qty_added": line.qty,
                "new_on_hand": new_on_hand,
            }
        )

    audit_event.payload = {
        "branch_id": int(branch_id),
        "note": normalized_note,
        "applied_count": len(applied_lines),
        "items": [
            {
                "product_id": int(line["product_id"]),
                "sku": line["sku"],
                "name": line["name"],
                "quick_name": line["quick_name"],
                "qty_added": str(line["qty_added"]),
                "new_on_hand": str(line["new_on_hand"]),
            }
            for line in applied_lines
        ],
        "movement_reason": MovementReason.POS_FINISHED_GOODS_STOCK_IN.value,
        "status": "COMPLETED",
    }

    db.flush()

    return {
        "branch_id": int(branch_id),
        "audit_event_id": int(audit_event.id),
        "applied_count": len(applied_lines),
        "note": normalized_note,
        "items": applied_lines,
    }
