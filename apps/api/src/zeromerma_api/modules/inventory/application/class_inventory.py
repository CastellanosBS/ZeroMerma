"""One physical attribution per exact product, backed by the original class sale."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    LockedInventoryBalances,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.attribution_models import (
    ClassInventoryAttribution,
    ClassInventoryObligation,
)
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine


def capture_sale_inventory(
    session: Session, *, sale: Sale, lines: Sequence[SaleLine]
) -> list[UUID]:
    """Capture DIRECT stock and CLASS obligations in the sale owner's transaction."""
    products = {
        p.id: p
        for p in session.scalars(
            select(Product).where(
                Product.id.in_([line.product_id for line in lines if line.product_id])
            )
        )
    }
    keys = [
        InventoryBalanceKey(sale.branch_id, product.id, "COUNTER")
        for product in products.values()
        if product.is_inventory_tracked
    ]
    balances = lock_inventory_balances(session, keys)
    movement_ids: list[UUID] = []
    for line in lines:
        if line.capture_mode == "CLASS_CAPTURE":
            session.add(
                ClassInventoryObligation(
                    sale_line_id=line.id,
                    branch_id=sale.branch_id,
                    product_class_id=line.product_class_id,
                    required_quantity=line.quantity,
                )
            )
            continue
        if line.product_id is None:
            raise ValueError("A direct sale line requires an exact product.")
        product = products[line.product_id]
        if not product.is_inventory_tracked:
            continue
        movement = balances.apply_delta(
            key=InventoryBalanceKey(sale.branch_id, product.id, "COUNTER"),
            delta=-line.quantity,
            movement_type="SALE_DIRECT",
            unit_of_measure=product.unit_of_measure,
            source_document_type="SALE",
            source_document_id=sale.id,
            source_line_id=line.id,
            causal_effect_code=f"sale:{line.id}:out",
            operator_user_id=sale.operator_id,
            reason=None,
            notes=None,
        )
        movement_ids.append(movement.id)
    return movement_ids


def lock_class_obligations(
    session: Session, sale_line_ids: Sequence[UUID]
) -> dict[UUID, ClassInventoryObligation]:
    """Call only after all affected inventory balances have been locked."""
    return {
        row.sale_line_id: row
        for row in session.scalars(
            select(ClassInventoryObligation)
            .where(ClassInventoryObligation.sale_line_id.in_(sale_line_ids))
            .order_by(ClassInventoryObligation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }


def attribute_class_inventory(
    session: Session,
    *,
    balances: LockedInventoryBalances,
    obligation: ClassInventoryObligation,
    product: Product,
    quantity: Decimal,
    actor_id: UUID,
    source_document_type: str,
    source_document_id: UUID,
    causal_effect_code: str,
    lot_allocations: Sequence[InventoryLotQuantity] | None = None,
) -> ClassInventoryAttribution:
    owner = execution(session)
    if owner is None or owner.record is None:
        raise RuntimeError("Class attribution requires an idempotent command owner.")
    if product.product_class_id != obligation.product_class_id:
        raise HTTPException(
            409,
            detail={
                "code": "CLASS_ATTRIBUTION_PRODUCT_MISMATCH",
                "message": "The exact product must belong to the original class.",
            },
        )
    if quantity <= 0 or quantity > obligation.required_quantity - obligation.attributed_quantity:
        raise HTTPException(
            409,
            detail={
                "code": "CLASS_ATTRIBUTION_QUANTITY_EXCEEDED",
                "message": "Attribution exceeds the remaining physical obligation.",
            },
        )
    movement = None
    if product.is_inventory_tracked:
        sale_time = session.scalar(
            select(Sale.confirmed_at)
            .join(SaleLine, SaleLine.sale_id == Sale.id)
            .where(SaleLine.id == obligation.sale_line_id)
        )
        movement = balances.apply_delta(
            key=InventoryBalanceKey(obligation.branch_id, product.id, "COUNTER"),
            delta=-quantity,
            movement_type="SALE_CLASS_ATTRIBUTION",
            unit_of_measure=product.unit_of_measure,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            source_line_id=obligation.sale_line_id,
            causal_effect_code=causal_effect_code,
            operator_user_id=actor_id,
            lot_allocations=lot_allocations,
            eligibility_at=sale_time,
            reason=None,
            notes=None,
        )
    attribution = ClassInventoryAttribution(
        obligation_id=obligation.id,
        product_id=product.id,
        quantity=quantity,
        inventory_movement_id=movement.id if movement else None,
        inventory_movement=movement,
        idempotency_record_id=owner.record.id,
        causal_effect_code=causal_effect_code,
        source_document_type=source_document_type,
        source_document_id=source_document_id,
        actor_id=actor_id,
    )
    session.add(attribution)
    obligation.attributed_quantity += quantity
    if obligation.attributed_quantity == obligation.required_quantity:
        obligation.status = "FULFILLED"
        line = session.get(SaleLine, obligation.sale_line_id)
        if line is not None:
            line.physical_attribution_status = "RECONCILED"
    return attribution
