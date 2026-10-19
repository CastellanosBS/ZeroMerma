"""FEFO allocation under the already acquired aggregate balance locks."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, attributes

from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import (
    InventoryLotQuantity,
    exact_decimal,
    inventory_calculation,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryLotBalance,
    InventoryMovementLotAllocation,
    InventoryReservationEventLotAllocation,
    InventoryReservationLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryMovement,
    InventoryReservation,
    InventoryReservationEvent,
)


def load_movement_lots(session: Session, movements: Sequence[InventoryMovement]) -> None:
    """Load mapped children through the branch guard, without implicit loader projections."""
    if not movements:
        return
    by_movement: dict[UUID, list[InventoryMovementLotAllocation]] = {
        movement.id: [] for movement in movements
    }
    with session.no_autoflush:
        for allocation in session.scalars(
            select(InventoryMovementLotAllocation)
            .where(InventoryMovementLotAllocation.movement_id.in_(by_movement))
            .order_by(
                InventoryMovementLotAllocation.movement_id,
                InventoryMovementLotAllocation.lot_id,
            )
        ):
            by_movement[allocation.movement_id].append(allocation)
        for pending in session.new:
            if (
                isinstance(pending, InventoryMovementLotAllocation)
                and pending.movement_id in by_movement
            ):
                by_movement[pending.movement_id].append(pending)
        for movement in movements:
            attributes.set_committed_value(movement, "lot_allocations", by_movement[movement.id])


class LockedInventoryLots:
    def __init__(self, session: Session, branch_id: UUID, product_id: UUID, location_code: str):
        self.session = session
        self.branch_id, self.product_id, self.location_code = branch_id, product_id, location_code
        self.rows = {
            row.lot_id: row
            for row in session.scalars(
                select(InventoryLotBalance)
                .where(
                    InventoryLotBalance.branch_id == branch_id,
                    InventoryLotBalance.product_id == product_id,
                    InventoryLotBalance.location_code == location_code,
                )
                .order_by(InventoryLotBalance.lot_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        }
        self.lots: dict[UUID, InventoryLot] = {}
        self.reservations: dict[UUID, list[InventoryReservationLotAllocation]] = {}

    def lot(self, lot_id: UUID) -> InventoryLot:
        if lot_id not in self.lots:
            lot = self.session.get(InventoryLot, lot_id)
            if lot is None or lot.product_id != self.product_id:
                raise InventoryValidationError("Inventory lot does not belong to this product.")
            self.lots[lot_id] = lot
        return self.lots[lot_id]

    def _order(self, lot_id: UUID) -> tuple[datetime, UUID]:
        lot = self.lot(lot_id)
        return lot.expires_at or datetime.max.replace(tzinfo=UTC), lot.id

    def _eligible(self, lot_id: UUID, at: datetime) -> bool:
        lot = self.lot(lot_id)
        return not lot.unidentified and (lot.expires_at is None or lot.expires_at > at)

    @inventory_calculation
    def _before_sale(self, lot_id: UUID, at: datetime) -> Decimal:
        rows = self.session.execute(
            select(
                InventoryMovement.direction,
                InventoryMovement.occurred_at,
                InventoryMovementLotAllocation.quantity,
            )
            .join(
                InventoryMovementLotAllocation,
                InventoryMovementLotAllocation.movement_id == InventoryMovement.id,
            )
            .where(
                InventoryMovement.branch_id == self.branch_id,
                InventoryMovement.product_id == self.product_id,
                InventoryMovement.location_code == self.location_code,
                InventoryMovementLotAllocation.lot_id == lot_id,
            )
        ).all()
        persisted = sum(
            (
                quantity
                if direction == "IN" and occurred_at <= at
                else -quantity
                if direction == "OUT"
                else Decimal(0)
                for direction, occurred_at, quantity in rows
            ),
            Decimal(0),
        )
        pending = sum(
            (
                allocation.quantity
                if movement.direction == "IN" and movement.occurred_at <= at
                else -allocation.quantity
                if movement.direction == "OUT"
                else Decimal(0)
                for movement in self.session.new
                if isinstance(movement, InventoryMovement)
                and movement.branch_id == self.branch_id
                and movement.product_id == self.product_id
                and movement.location_code == self.location_code
                for allocation in movement.lot_allocations
                if allocation.lot_id == lot_id
            ),
            Decimal(0),
        )
        return persisted + pending

    @inventory_calculation
    def eligible_quantity_at(self, lot_id: UUID, at: datetime) -> Decimal:
        """Read capacity at an original sale time, retaining pending physical effects."""
        if at.tzinfo is None or at.utcoffset() is None:
            raise InventoryValidationError("Historical lot eligibility requires an aware time.")
        with self.session.no_autoflush:
            row = self.rows.get(lot_id)
            if row is None or not self._eligible(lot_id, at):
                return Decimal(0)
            return max(
                Decimal(0),
                min(
                    row.quantity_on_hand - row.quantity_reserved,
                    self._before_sale(lot_id, at) - row.quantity_reserved,
                ),
            )

    @inventory_calculation
    def select_outflow(
        self,
        quantity: Decimal,
        allocations: Sequence[InventoryLotQuantity] | None,
        *,
        allow_expired: bool = False,
        eligibility_at: datetime | None = None,
    ) -> list[InventoryLotQuantity]:
        at = eligibility_at or datetime.now(UTC)
        if allocations is not None:
            selected = list(allocations)
            if len({entry.lot_id for entry in selected}) != len(selected):
                raise InventoryValidationError("A physical effect cannot repeat the same lot.")
            if sum((entry.quantity for entry in selected), Decimal(0)) != quantity:
                raise InventoryValidationError(
                    "Lot allocations do not equal the physical quantity."
                )
        else:
            selected = []
            pending = quantity
            for lot_id in sorted(self.rows, key=self._order):
                if not allow_expired and not self._eligible(lot_id, at):
                    continue
                balance = self.rows[lot_id]
                available = balance.quantity_on_hand - balance.quantity_reserved
                if eligibility_at is not None:
                    available = min(
                        available, self._before_sale(lot_id, at) - balance.quantity_reserved
                    )
                take = min(pending, available)
                if take > 0:
                    selected.append(InventoryLotQuantity(lot_id, take))
                    pending -= take
                if pending == 0:
                    break
            if pending != 0:
                raise InventoryValidationError("Eligible lot stock is insufficient.")
        for entry in selected:
            if exact_decimal(entry.quantity) <= 0:
                raise InventoryValidationError("Lot allocation quantity must be positive.")
            if not allow_expired and not self._eligible(entry.lot_id, at):
                raise InventoryValidationError("Expired or unidentified lots are not eligible.")
            selected_balance = self.rows.get(entry.lot_id)
            if (
                selected_balance is None
                or selected_balance.quantity_on_hand - selected_balance.quantity_reserved
                < entry.quantity
            ):
                raise InventoryValidationError("The selected lot has insufficient available stock.")
            if (
                eligibility_at is not None
                and self._before_sale(entry.lot_id, at) - selected_balance.quantity_reserved
                < entry.quantity
            ):
                raise InventoryValidationError(
                    "Later receipts cannot explain an earlier class sale."
                )
        return selected

    @inventory_calculation
    def apply(
        self,
        movement: InventoryMovement,
        allocations: Sequence[InventoryLotQuantity] | None,
        *,
        allow_expired: bool = False,
        eligibility_at: datetime | None = None,
    ) -> None:
        if movement.direction == "OUT":
            selected = self.select_outflow(
                movement.quantity,
                allocations,
                allow_expired=allow_expired,
                eligibility_at=eligibility_at,
            )
            for entry in selected:
                self.rows[entry.lot_id].quantity_on_hand -= entry.quantity
        else:
            if not allocations:
                raise InventoryValidationError(
                    "Tracked incoming stock requires explicit lot evidence."
                )
            selected = list(allocations)
            if (
                len({entry.lot_id for entry in selected}) != len(selected)
                or sum((entry.quantity for entry in selected), Decimal(0)) != movement.quantity
            ):
                raise InventoryValidationError("Incoming lot allocations do not reconcile.")
            for entry in selected:
                if exact_decimal(entry.quantity) <= 0:
                    raise InventoryValidationError("Incoming lot quantity must be positive.")
                lot = self.lot(entry.lot_id)
                if self.location_code not in {"QUARANTINE", "WASTE"}:
                    if lot.unidentified or not self._eligible(lot.id, datetime.now(UTC)):
                        raise InventoryValidationError(
                            "Unidentified or expired stock requires quarantine."
                        )
                if entry.lot_id not in self.rows:
                    self.rows[entry.lot_id] = InventoryLotBalance(
                        id=uuid4(),
                        branch_id=self.branch_id,
                        product_id=self.product_id,
                        location_code=self.location_code,
                        lot_id=entry.lot_id,
                        quantity_on_hand=Decimal(0),
                        quantity_reserved=Decimal(0),
                    )
                    self.session.add(self.rows[entry.lot_id])
                self.rows[entry.lot_id].quantity_on_hand += entry.quantity
        movement.lot_allocations = [
            InventoryMovementLotAllocation(
                id=uuid4(),
                movement_id=movement.id,
                branch_id=self.branch_id,
                lot_id=entry.lot_id,
                quantity=entry.quantity,
            )
            for entry in selected
        ]

    def _record_event(
        self, event: InventoryReservationEvent, selected: Sequence[InventoryLotQuantity]
    ) -> None:
        self.session.add_all(
            [
                InventoryReservationEventLotAllocation(
                    id=uuid4(),
                    reservation_event_id=event.id,
                    reservation_event=event,
                    branch_id=self.branch_id,
                    lot_id=entry.lot_id,
                    quantity=entry.quantity,
                )
                for entry in selected
            ]
        )

    @inventory_calculation
    def reserve(self, reservation: InventoryReservation, event: InventoryReservationEvent) -> None:
        selected = self.select_outflow(reservation.quantity, None)
        rows = []
        for entry in selected:
            self.rows[entry.lot_id].quantity_reserved += entry.quantity
            rows.append(
                InventoryReservationLotAllocation(
                    id=uuid4(),
                    reservation_id=reservation.id,
                    reservation=reservation,
                    branch_id=self.branch_id,
                    lot_id=entry.lot_id,
                    quantity=entry.quantity,
                    consumed_quantity=Decimal(0),
                    released_quantity=Decimal(0),
                )
            )
        self.reservations[reservation.id] = rows
        self.session.add_all(rows)
        self._record_event(event, selected)

    @inventory_calculation
    def take_reservation(
        self,
        reservation_id: UUID,
        quantity: Decimal,
        *,
        consume: bool,
        allow_expired: bool = False,
    ) -> list[InventoryLotQuantity]:
        if reservation_id not in self.reservations:
            self.reservations[reservation_id] = list(
                self.session.scalars(
                    select(InventoryReservationLotAllocation)
                    .where(InventoryReservationLotAllocation.reservation_id == reservation_id)
                    .order_by(InventoryReservationLotAllocation.lot_id)
                    .with_for_update()
                    .execution_options(populate_existing=True)
                )
            )
        pending = quantity
        selected = []
        for row in sorted(
            self.reservations[reservation_id], key=lambda item: self._order(item.lot_id)
        ):
            take = min(pending, row.quantity - row.consumed_quantity - row.released_quantity)
            if take <= 0:
                continue
            if consume and not allow_expired and not self._eligible(row.lot_id, datetime.now(UTC)):
                raise InventoryValidationError(
                    "A reserved lot expired; explicit resolution is required."
                )
            if self.rows[row.lot_id].quantity_reserved < take:
                raise InventoryValidationError("The reserved lot projection does not reconcile.")
            self.rows[row.lot_id].quantity_reserved -= take
            if consume:
                row.consumed_quantity += take
            else:
                row.released_quantity += take
            selected.append(InventoryLotQuantity(row.lot_id, take))
            pending -= take
            if pending == 0:
                break
        if pending != 0:
            raise InventoryValidationError("Reservation lot evidence is incomplete.")
        return selected
