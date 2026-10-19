"""Physical return allocations never duplicate the economic refund entitlement."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from typing import TypedDict, cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.application.attribution_queries import (
    read_attribution_projections,
)
from zeromerma_api.modules.inventory.application.class_inventory import (
    attribute_class_inventory,
    lock_class_obligations,
)
from zeromerma_api.modules.inventory.application.lots import load_movement_lots
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    create_inventory_lot,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.attribution_models import (
    ClassInventoryAttribution,
    ClassInventoryObligation,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import InventoryLot
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.returns.application.schemas import (
    ReturnDispositionAllocationRequest,
    ReturnPhysicalOptionView,
)
from zeromerma_api.modules.returns.domain.exceptions import (
    SaleReturnConflictError,
    SaleReturnValidationError,
)
from zeromerma_api.modules.returns.infrastructure.models import (
    ReturnDispositionAllocation,
    SaleReturn,
    SaleReturnLine,
)
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine

DISPOSITION_LOCATION = {
    "RESTOCK_COUNTER": "COUNTER",
    "RESTOCK_BACKROOM": "BACKROOM",
    "QUARANTINE": "QUARANTINE",
    "SEND_TO_WASTE": "WASTE",
}
ZERO = Decimal("0")


class ReturnProductOption(TypedDict):
    product_id: UUID
    product_code: str
    product_name: str
    is_inventory_tracked: bool
    lot_tracking_enabled: bool


def original_movements(
    session: Session, line_id: UUID, product_id: UUID
) -> list[InventoryMovement]:
    movements = list(
        session.scalars(
            select(InventoryMovement)
            .where(
                InventoryMovement.source_line_id == line_id,
                InventoryMovement.product_id == product_id,
                InventoryMovement.movement_type.in_(("SALE_DIRECT", "SALE_CLASS_ATTRIBUTION")),
                InventoryMovement.direction == "OUT",
            )
            .order_by(InventoryMovement.occurred_at, InventoryMovement.id)
        )
    )
    load_movement_lots(session, movements)
    return movements


def returned_allocations(
    session: Session, line_id: UUID, product_id: UUID, exclude_return_id: UUID | None = None
) -> list[ReturnDispositionAllocation]:
    query = (
        select(ReturnDispositionAllocation)
        .join(SaleReturnLine, SaleReturnLine.id == ReturnDispositionAllocation.sale_return_line_id)
        .where(
            SaleReturnLine.original_sale_line_id == line_id,
            ReturnDispositionAllocation.returned_product_id == product_id,
        )
    )
    if exclude_return_id is not None:
        query = query.where(SaleReturnLine.sale_return_id != exclude_return_id)
    return list(session.scalars(query))


def attributed_quantity(session: Session, line: SaleLine, product_id: UUID) -> Decimal:
    if line.capture_mode == "PRODUCT_DIRECT":
        return line.quantity if line.product_id == product_id else ZERO
    return Decimal(
        session.scalar(
            select(func.coalesce(func.sum(ClassInventoryAttribution.quantity), 0))
            .join(
                ClassInventoryObligation,
                ClassInventoryObligation.id == ClassInventoryAttribution.obligation_id,
            )
            .where(
                ClassInventoryObligation.sale_line_id == line.id,
                ClassInventoryAttribution.product_id == product_id,
            )
        )
        or ZERO
    )


def lot_quantity(movements: Sequence[InventoryMovement], lot_id: UUID) -> Decimal:
    return sum(
        (
            allocation.quantity
            for movement in movements
            for allocation in movement.lot_allocations
            if allocation.lot_id == lot_id
        ),
        ZERO,
    )


def unknown_lot(session: Session, row: ReturnDispositionAllocation) -> bool:
    lot = session.get(InventoryLot, row.lot_id) if row.lot_id else None
    return lot is None or lot.unidentified


def original_lot_value(movement: InventoryMovement, lot_id: UUID | None) -> Decimal | None:
    """Distribute the frozen weighted value with a deterministic rounding residual."""
    if movement.total_cost is None or lot_id is None:
        return movement.total_cost
    cumulative_quantity = ZERO
    cumulative_value = ZERO
    with localcontext() as context:
        context.prec = 50
        for allocation in sorted(movement.lot_allocations, key=lambda row: row.lot_id):
            cumulative_quantity += allocation.quantity
            value = (movement.total_cost * cumulative_quantity / movement.quantity).quantize(
                Decimal("0.00000001")
            )
            allocated_value = value - cumulative_value
            if allocation.lot_id == lot_id:
                return allocated_value
            cumulative_value = value
    return ZERO


def apply_return_inventory(
    session: Session,
    *,
    sale_return: SaleReturn,
    allocations: Sequence[
        tuple[SaleReturnLine, ReturnDispositionAllocation, ReturnDispositionAllocationRequest]
    ],
) -> list[UUID]:
    products = {
        p.id: p
        for p in session.scalars(
            select(Product).where(
                Product.id.in_([a.returned_product_id for _, a, _ in allocations])
            )
        )
    }
    originals = {
        line.id: line
        for line in session.scalars(
            select(SaleLine).where(
                SaleLine.id.in_([line.original_sale_line_id for line, _, _ in allocations])
            )
        )
    }
    keys = set()
    for line, allocation, _ in allocations:
        product = products[allocation.returned_product_id]
        if product.is_inventory_tracked:
            if allocation.disposition_code in DISPOSITION_LOCATION:
                keys.add(
                    InventoryBalanceKey(
                        sale_return.branch_id,
                        product.id,
                        DISPOSITION_LOCATION[allocation.disposition_code],
                    )
                )
            if line.original_capture_mode == "CLASS_CAPTURE":
                keys.add(InventoryBalanceKey(sale_return.branch_id, product.id, "COUNTER"))
    balances = lock_inventory_balances(session, list(keys))
    obligations = lock_class_obligations(
        session, [line.id for line in originals.values() if line.capture_mode == "CLASS_CAPTURE"]
    )
    used: dict[tuple[UUID, UUID], Decimal] = defaultdict(lambda: ZERO)
    used_lots: dict[tuple[UUID, UUID, UUID | None], Decimal] = defaultdict(lambda: ZERO)
    movement_ids = []
    processed: list[tuple[UUID, ReturnDispositionAllocation, InventoryMovement]] = []
    for return_line, allocation, command in allocations:
        product = products[allocation.returned_product_id]
        original = originals[return_line.original_sale_line_id]
        restock = allocation.disposition_code in {"RESTOCK_COUNTER", "RESTOCK_BACKROOM"}
        if allocation.disposition_code == "NO_STOCK":
            if product.is_inventory_tracked:
                raise SaleReturnConflictError(
                    "RETURN_NO_STOCK_NOT_ALLOWED: this product is inventory tracked."
                )
            if not sale_return.notes:
                raise SaleReturnValidationError(
                    "NO_STOCK requires a documented reason in the return notes."
                )
        elif not product.is_inventory_tracked:
            raise SaleReturnValidationError("A non-inventory product requires NO_STOCK.")
        if restock and not command.restock_safe_acknowledged:
            raise SaleReturnValidationError(
                "Inspect and explicitly confirm the product is safe before restocking."
            )
        if allocation.disposition_code == "RESTOCK_COUNTER" and (
            not product.is_active or not product.is_sellable
        ):
            raise SaleReturnConflictError(
                "Only active sellable products may return to the counter."
            )
        lot = session.get(InventoryLot, command.lot_id) if command.lot_id else None
        if command.lot_id and (
            not product.lot_tracking_enabled or lot is None or lot.product_id != product.id
        ):
            raise SaleReturnConflictError("The lot does not belong to this lot-tracked product.")
        if (
            product.lot_tracking_enabled
            and restock
            and (
                lot is None
                or lot.unidentified
                or (product.expiry_required and lot.expires_at is None)
                or (lot.expires_at is not None and lot.expires_at <= datetime.now(UTC))
            )
        ):
            raise SaleReturnConflictError(
                "A traceable, unexpired original lot is required for restocking."
            )
        prior = returned_allocations(session, original.id, product.id, sale_return.id)
        pair = (original.id, product.id)
        remaining = (
            attributed_quantity(session, original, product.id)
            - sum((row.quantity for row in prior), ZERO)
            - used[pair]
        )
        movements = original_movements(session, original.id, product.id)
        if command.lot_id:
            prior_lot = sum(
                (
                    row.quantity
                    for row in prior
                    if row.lot_id == command.lot_id or unknown_lot(session, row)
                ),
                ZERO,
            )
            remaining = min(
                remaining,
                lot_quantity(movements, command.lot_id)
                - prior_lot
                - used_lots[(*pair, command.lot_id)]
                - used_lots[(*pair, None)],
            )
        remaining = max(ZERO, remaining)
        needed = max(ZERO, allocation.quantity - remaining)
        if needed > 0 and original.capture_mode == "CLASS_CAPTURE":
            obligation = obligations.get(original.id)
            if obligation is None:
                raise SaleReturnConflictError(
                    "The original class obligation is missing; "
                    "reconcile the historical evidence first."
                )
            if product.lot_tracking_enabled and command.lot_id is None:
                raise SaleReturnConflictError(
                    "Identify the original lot before attributing a pending class sale."
                )
            attribute_class_inventory(
                session,
                balances=balances,
                obligation=obligation,
                product=product,
                quantity=needed,
                actor_id=sale_return.created_by_user_id,
                source_document_type="SALE_RETURN",
                source_document_id=sale_return.id,
                causal_effect_code=f"return:{allocation.id}:attribute",
                lot_allocations=[InventoryLotQuantity(command.lot_id, needed)]
                if command.lot_id
                else None,
            )
            session.flush()
            movements = original_movements(session, original.id, product.id)
            remaining += needed
        if remaining < allocation.quantity:
            raise SaleReturnConflictError(
                "The return exceeds the original product or lot attribution."
            )
        used[pair] += allocation.quantity
        used_lots[(*pair, command.lot_id)] += allocation.quantity
        if not product.is_inventory_tracked:
            continue
        if not movements:
            raise SaleReturnConflictError(
                "Original physical sale evidence is missing; no stock will be invented."
            )
        lots = None
        if product.lot_tracking_enabled:
            if lot is None:
                lot = create_inventory_lot(
                    session,
                    product_id=product.id,
                    lot_code=f"UNIDENTIFIED:{allocation.id}",
                    expires_at=None,
                    source_document_type="SALE_RETURN",
                    source_document_id=sale_return.id,
                    source_line_id=allocation.id,
                    branch_id=sale_return.branch_id,
                    operator_user_id=sale_return.created_by_user_id,
                    unidentified=True,
                )
            allocation.lot_id = lot.id
            lots = [InventoryLotQuantity(lot.id, allocation.quantity)]
        eligible = [
            (m, lot_quantity([m], command.lot_id) if command.lot_id else m.quantity)
            for m in movements
        ]
        eligible = [(m, quantity) for m, quantity in eligible if quantity > 0]
        total_cost = None
        earlier = [
            (row, session.get(InventoryMovement, row.inventory_movement_id))
            for row in prior
            if row.inventory_movement_id
        ]
        earlier.extend(
            (row, fact)
            for original_id, row, fact in processed
            if original_id == original.id and row.returned_product_id == product.id
        )
        relevant = [
            (row, fact)
            for row, fact in earlier
            if command.lot_id is None or row.lot_id == command.lot_id or unknown_lot(session, row)
        ]
        ambiguous_lot_cost = command.lot_id is not None and any(
            unknown_lot(session, row) for row, _ in relevant
        )
        if (
            eligible
            and not ambiguous_lot_cost
            and all(m.total_cost is not None for m, _ in eligible)
            and all(fact is not None and fact.total_cost is not None for _, fact in relevant)
        ):
            with localcontext() as context:
                context.prec = 50
                pool_value = sum(
                    (cast(Decimal, original_lot_value(m, command.lot_id)) for m, _ in eligible),
                    ZERO,
                ).quantize(Decimal("0.00000001"))
                pool_quantity = sum((quantity for _, quantity in eligible), ZERO)
                remaining_value = pool_value - sum(
                    (cast(Decimal, fact.total_cost) for _, fact in relevant if fact is not None),
                    ZERO,
                )
                remaining_quantity = pool_quantity - sum(
                    (row.quantity for row, _ in relevant), ZERO
                )
                if remaining_value < 0 or remaining_quantity < allocation.quantity:
                    raise SaleReturnConflictError("Original return valuation does not reconcile.")
                total_cost = (
                    remaining_value
                    if remaining_quantity == allocation.quantity
                    else (remaining_value * allocation.quantity / remaining_quantity).quantize(
                        Decimal("0.00000001")
                    )
                )
        movement = balances.apply_delta(
            key=InventoryBalanceKey(
                sale_return.branch_id, product.id, DISPOSITION_LOCATION[allocation.disposition_code]
            ),
            delta=allocation.quantity,
            movement_type={"QUARANTINE": "RETURN_QUARANTINE", "SEND_TO_WASTE": "RETURN_WASTE"}.get(
                allocation.disposition_code, "RETURN_RESTOCK"
            ),
            unit_of_measure=product.unit_of_measure,
            source_document_type="SALE_RETURN",
            source_document_id=sale_return.id,
            source_line_id=allocation.id,
            causal_effect_code=f"return:{allocation.id}:in",
            operator_user_id=sale_return.created_by_user_id,
            reason=sale_return.reason_code,
            notes=sale_return.notes,
            total_cost=total_cost,
            cost_evidence_reference=f"SALE_LINE:{original.id}" if total_cost is not None else None,
            lot_allocations=lots,
        )
        allocation.inventory_movement_id = movement.id
        movement_ids.append(movement.id)
        processed.append((original.id, allocation, movement))
    session.add_all([allocation for _, allocation, _ in allocations])
    return movement_ids


def physical_return_options(session: Session, line_id: UUID) -> list[ReturnPhysicalOptionView]:
    line = session.get(SaleLine, line_id)
    sale = session.get(Sale, line.sale_id) if line else None
    if line is None or sale is None:
        return []
    products = session.scalars(
        select(Product).where(Product.id == line.product_id)
        if line.product_id
        else select(Product).where(Product.product_class_id == line.product_class_id)
    ).all()
    projection = read_attribution_projections(
        session, branch_id=sale.branch_id, sale_line_ids=[line.id], sold_at=sale.confirmed_at
    ).get(line.id)
    pending = projection.remaining_quantity if projection else ZERO
    pending_choices = (
        {
            (option.product_id, option.lot_id): min(
                pending,
                option.available_quantity if option.available_quantity is not None else pending,
            )
            for option in projection.options
        }
        if projection
        else {}
    )
    options = []
    for product in products:
        movements = original_movements(session, line.id, product.id)
        prior = returned_allocations(session, line.id, product.id)
        remaining = max(
            ZERO,
            attributed_quantity(session, line, product.id)
            - sum((row.quantity for row in prior), ZERO),
        )
        base: ReturnProductOption = dict(
            product_id=product.id,
            product_code=product.code,
            product_name=product.name,
            is_inventory_tracked=product.is_inventory_tracked,
            lot_tracking_enabled=product.lot_tracking_enabled,
        )
        if not product.lot_tracking_enabled:
            available_pending = pending_choices.get((product.id, None), ZERO)
            options.append(
                ReturnPhysicalOptionView(
                    **base,
                    lot_id=None,
                    lot_code=None,
                    expires_at=None,
                    remaining_quantity=remaining + available_pending,
                )
            )
            continue
        lot_ids = {a.lot_id for m in movements for a in m.lot_allocations}
        lot_ids.update(
            lot_id
            for (product_id, lot_id) in pending_choices
            if product_id == product.id and lot_id is not None
        )
        for lot in session.scalars(
            select(InventoryLot)
            .where(InventoryLot.id.in_(lot_ids))
            .order_by(InventoryLot.expires_at.asc().nulls_last(), InventoryLot.id)
        ):
            previous = sum(
                (
                    row.quantity
                    for row in prior
                    if row.lot_id == lot.id or unknown_lot(session, row)
                ),
                ZERO,
            )
            available = max(ZERO, lot_quantity(movements, lot.id) - previous)
            eligible_pending = pending_choices.get((product.id, lot.id), ZERO)
            options.append(
                ReturnPhysicalOptionView(
                    **base,
                    lot_id=lot.id,
                    lot_code=lot.lot_code,
                    expires_at=lot.expires_at,
                    remaining_quantity=min(remaining, available) + eligible_pending,
                )
            )
        if remaining > 0:
            options.append(
                ReturnPhysicalOptionView(
                    **base,
                    lot_id=None,
                    lot_code=None,
                    expires_at=None,
                    remaining_quantity=remaining,
                )
            )
    return options
