"""Read-only physical choices for an original class sale, with no future receipts."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.application.availability import read_product_availability
from zeromerma_api.modules.inventory.domain.quantities import inventory_calculation
from zeromerma_api.modules.inventory.infrastructure.attribution_models import (
    ClassInventoryAttribution,
    ClassInventoryObligation,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLotBalance,
    InventoryMovementLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)


@dataclass(frozen=True)
class AttributionChoice:
    product_id: UUID
    product_code: str
    product_name: str
    lot_id: UUID | None
    lot_code: str | None
    expires_at: datetime | None
    available_quantity: Decimal | None
    is_inventory_tracked: bool
    lot_tracking_enabled: bool


@dataclass(frozen=True)
class AttributionProgress:
    attributed_quantity: Decimal
    remaining_quantity: Decimal
    attributions: tuple[ClassInventoryAttribution, ...]
    product_class_id: UUID
    status: str


@dataclass(frozen=True)
class AttributionProjection:
    remaining_quantity: Decimal
    options: tuple[AttributionChoice, ...]
    attributions: tuple[ClassInventoryAttribution, ...]


@inventory_calculation
def read_attribution_progress(
    session: Session, *, branch_id: UUID, sale_line_ids: Sequence[UUID]
) -> dict[UUID, AttributionProgress]:
    """Read obligation progress and immutable history without evaluating stock choices."""
    if not sale_line_ids:
        return {}
    with session.no_autoflush:
        obligations = list(
            session.scalars(
                select(ClassInventoryObligation).where(
                    ClassInventoryObligation.branch_id == branch_id,
                    ClassInventoryObligation.sale_line_id.in_(sale_line_ids),
                )
            )
        )
        if not obligations:
            return {}
        history: dict[UUID, list[ClassInventoryAttribution]] = {}
        for attribution in session.scalars(
            select(ClassInventoryAttribution)
            .where(
                ClassInventoryAttribution.obligation_id.in_([o.id for o in obligations]),
            )
            .order_by(ClassInventoryAttribution.occurred_at, ClassInventoryAttribution.id)
        ):
            history.setdefault(attribution.obligation_id, []).append(attribution)
        return {
            o.sale_line_id: AttributionProgress(
                attributed_quantity=o.attributed_quantity,
                remaining_quantity=o.required_quantity - o.attributed_quantity,
                attributions=tuple(history.get(o.id, ())),
                product_class_id=o.product_class_id,
                status=o.status,
            )
            for o in obligations
        }


@inventory_calculation
def read_attribution_projections(
    session: Session, *, branch_id: UUID, sale_line_ids: Sequence[UUID], sold_at: datetime
) -> dict[UUID, AttributionProjection]:
    with session.no_autoflush:
        progress = read_attribution_progress(
            session, branch_id=branch_id, sale_line_ids=sale_line_ids
        )
        if not progress:
            return {}
        products = list(
            session.scalars(
                select(Product)
                .where(
                    Product.product_class_id.in_(
                        [row.product_class_id for row in progress.values()]
                    ),
                    Product.is_active.is_(True),
                    Product.is_sellable.is_(True),
                    Product.created_at <= sold_at,
                )
                .order_by(Product.code, Product.id)
            )
        )
        product_ids = [p.id for p in products]
        balances = {
            b.product_id: b
            for b in session.scalars(
                select(InventoryBalance).where(
                    InventoryBalance.branch_id == branch_id,
                    InventoryBalance.location_code == "COUNTER",
                    InventoryBalance.product_id.in_(product_ids),
                )
            )
        }
        movements = list(
            session.scalars(
                select(InventoryMovement).where(
                    InventoryMovement.branch_id == branch_id,
                    InventoryMovement.location_code == "COUNTER",
                    InventoryMovement.product_id.in_(product_ids),
                )
            )
        )
        by_movement = {m.id: m for m in movements}
        allocations = list(
            session.scalars(
                select(InventoryMovementLotAllocation).where(
                    InventoryMovementLotAllocation.movement_id.in_(by_movement),
                )
            )
        )
        lot_reserved = {
            b.lot_id: b.quantity_reserved
            for b in session.scalars(
                select(InventoryLotBalance).where(
                    InventoryLotBalance.branch_id == branch_id,
                    InventoryLotBalance.location_code == "COUNTER",
                    InventoryLotBalance.product_id.in_(product_ids),
                )
            )
        }
        available = read_product_availability(
            session, branch_id=branch_id, products=products, at=sold_at
        )

        def historical_quantity(movement: InventoryMovement, quantity: Decimal) -> Decimal:
            if movement.direction == "OUT":
                return -quantity
            return quantity if movement.occurred_at <= sold_at else Decimal(0)

        choices: dict[UUID, list[AttributionChoice]] = {}
        for product in products:
            stock = available[product.id]
            product_choices = choices.setdefault(product.product_class_id, [])
            if not product.is_inventory_tracked:
                product_choices.append(
                    AttributionChoice(
                        product.id, product.code, product.name, None, None, None, None, False, False
                    )
                )
            elif product.lot_tracking_enabled:
                for lot in stock.lots:
                    historic = sum(
                        (
                            historical_quantity(by_movement[a.movement_id], a.quantity)
                            for a in allocations
                            if a.lot_id == lot.lot_id
                        ),
                        Decimal(0),
                    ) - lot_reserved.get(lot.lot_id, Decimal(0))
                    quantity = max(min(lot.available_quantity, historic), Decimal(0))
                    if quantity > 0:
                        product_choices.append(
                            AttributionChoice(
                                product.id,
                                product.code,
                                product.name,
                                lot.lot_id,
                                lot.lot_code,
                                lot.expires_at,
                                quantity,
                                True,
                                True,
                            )
                        )
            else:
                balance = balances.get(product.id)
                historic = sum(
                    (
                        historical_quantity(m, m.quantity)
                        for m in movements
                        if m.product_id == product.id
                    ),
                    Decimal(0),
                ) - (balance.quantity_reserved if balance else Decimal(0))
                quantity = max(min(stock.available_quantity or Decimal(0), historic), Decimal(0))
                if quantity > 0:
                    product_choices.append(
                        AttributionChoice(
                            product.id,
                            product.code,
                            product.name,
                            None,
                            None,
                            None,
                            quantity,
                            True,
                            False,
                        )
                    )
        return {
            sale_line_id: AttributionProjection(
                row.remaining_quantity,
                tuple(choices.get(row.product_class_id, [])) if row.status == "OPEN" else (),
                row.attributions,
            )
            for sale_line_id, row in progress.items()
        }
