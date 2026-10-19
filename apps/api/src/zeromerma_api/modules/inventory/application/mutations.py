from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, SessionTransaction

from zeromerma_api.db.access_scope import authorization_scope
from zeromerma_api.db.operation_context import get_operation_context
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.application.authorization import require_branches
from zeromerma_api.modules.inventory.application.lots import LockedInventoryLots
from zeromerma_api.modules.inventory.domain.constants import (
    RESERVABLE_INVENTORY_LOCATIONS,
    VALID_INVENTORY_LOCATION_CODES,
    VALID_INVENTORY_MOVEMENT_TYPES,
)
from zeromerma_api.modules.inventory.domain.costs import value_effect
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import (
    InventoryLotQuantity,
    convert_quantity,
    exact_decimal,
    inventory_calculation,
    normalize_uom,
)
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLot,
    InventoryMovementLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryReservation,
    InventoryReservationEvent,
)
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine


@dataclass(frozen=True, order=True)
class InventoryBalanceKey:
    branch_id: uuid.UUID
    product_id: uuid.UUID
    location_code: str


def _command(session: Session, branch_id: uuid.UUID, actor_id: uuid.UUID) -> dict[str, Any]:
    owner = execution(session)
    if owner is None or owner.record is None or not owner.action_running:
        raise IdempotencyBoundaryError("Inventory facts require an admitted idempotent command.")
    context = get_operation_context(session)
    if owner.record.actor_user_id != actor_id or context.operation_id != owner.record.id:
        raise IdempotencyBoundaryError("Inventory facts require the command's actor and identity.")
    branches = {context.branch_id, *context.related_branch_ids}
    if branch_id not in branches:
        raise IdempotencyBoundaryError("Inventory facts require the command's authorized branches.")
    return dict(
        context_version=1,
        idempotency_record_id=owner.record.id,
        source_app=context.source_app.value,
        operation_code=owner.record.operation_code,
        correlation_id=context.correlation_id,
        causation_id=context.causation_id,
        request_id=context.request_id,
        workstation_id=context.workstation_id,
        cash_session_id=context.cash_session_id,
        related_branch_ids=sorted(str(branch) for branch in branches if branch is not None),
    )


def _effect(value: str) -> str:
    if not value.strip() or len(value) > 160:
        raise InventoryValidationError("An explicit bounded inventory effect key is required.")
    return value


def create_inventory_lot(
    session: Session,
    *,
    product_id: uuid.UUID,
    lot_code: str,
    expires_at: datetime | None,
    source_document_type: str,
    source_document_id: uuid.UUID,
    source_line_id: uuid.UUID | None,
    branch_id: uuid.UUID,
    operator_user_id: uuid.UUID,
    produced_at: datetime | None = None,
    unidentified: bool = False,
) -> InventoryLot:
    lineage = _command(session, branch_id, operator_user_id)
    product = session.get(Product, product_id)
    if product is None or not product.is_inventory_tracked or not product.lot_tracking_enabled:
        raise InventoryValidationError("This product does not use inventory lots.")
    code = lot_code.strip()
    if not code or len(code) > 120:
        raise InventoryValidationError("An explicit bounded lot code is required.")
    if any(value is not None and value.utcoffset() is None for value in (expires_at, produced_at)):
        raise InventoryValidationError("Lot dates require an explicit timezone.")
    if unidentified and expires_at is not None:
        raise InventoryValidationError("An unidentified lot cannot claim an expiry date.")
    if product.expiry_required and expires_at is None and not unidentified:
        raise InventoryValidationError("This product requires a recorded lot expiry.")
    if produced_at is not None and expires_at is not None and produced_at >= expires_at:
        raise InventoryValidationError("Lot production must precede its expiry.")
    query = select(InventoryLot).where(
        InventoryLot.product_id == product_id, InventoryLot.lot_code == code
    )
    lot = session.scalar(query)
    if lot is None:
        try:
            with session.begin_nested():
                lot = InventoryLot(
                    id=uuid.uuid4(),
                    product_id=product_id,
                    lot_code=code,
                    expires_at=expires_at,
                    produced_at=produced_at,
                    unidentified=unidentified,
                    source_document_type=source_document_type,
                    source_document_id=source_document_id,
                    source_line_id=source_line_id,
                    idempotency_record_id=lineage["idempotency_record_id"],
                    operator_user_id=operator_user_id,
                )
                session.add(lot)
                session.flush()
        except IntegrityError as error:
            if (
                getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                != "uq_inventory_lot_product_code"
            ):
                raise
            lot = session.scalars(query).one()
    if (
        lot.expires_at != expires_at
        or lot.produced_at != produced_at
        or lot.unidentified != unidentified
    ):
        raise InventoryValidationError(
            "The existing lot identity has different immutable metadata."
        )
    return lot


class LockedInventoryBalances:
    """Command-local locked rows; never refresh a row after applying a movement."""

    def __init__(
        self,
        session: Session,
        transaction: SessionTransaction,
        balances: dict[InventoryBalanceKey, InventoryBalance],
    ) -> None:
        self._session = session
        self._transaction = transaction
        self._balances = balances
        self._reservations: dict[uuid.UUID, InventoryReservation] = {}
        self._effects: set[str] = set()
        tracked = set(
            session.scalars(
                select(Product.id).where(
                    Product.id.in_({key.product_id for key in balances}),
                    Product.lot_tracking_enabled.is_(True),
                )
            )
        )
        self._lots = {
            key: LockedInventoryLots(session, key.branch_id, key.product_id, key.location_code)
            for key in sorted(balances)
            if key.product_id in tracked
        }

    def balance(self, key: InventoryBalanceKey) -> InventoryBalance:
        if self._session.get_transaction() is not self._transaction:
            raise RuntimeError("Inventory locks belong to the original transaction.")
        if key not in self._balances:
            raise InventoryValidationError("The complete inventory write set must be locked first.")
        return self._balances[key]

    def quantity(self, key: InventoryBalanceKey) -> Decimal:
        return Decimal(self.balance(key).quantity_on_hand)

    def reserved(self, key: InventoryBalanceKey) -> Decimal:
        return Decimal(self.balance(key).quantity_reserved)

    @inventory_calculation
    def available(self, key: InventoryBalanceKey) -> Decimal:
        return self.quantity(key) - self.reserved(key)

    @inventory_calculation
    def eligible_lot_quantity_at(
        self, key: InventoryBalanceKey, lot_id: uuid.UUID, at: datetime
    ) -> Decimal:
        """Read a locked lot's historical capacity without flushing this command."""
        available = self.available(key)
        if key not in self._lots:
            raise InventoryValidationError("Historical lot eligibility requires a tracked lot.")
        return max(Decimal(0), min(available, self._lots[key].eligible_quantity_at(lot_id, at)))

    def _product_uom(self, key: InventoryBalanceKey, unit_of_measure: str) -> str:
        product = self._session.get(Product, key.product_id)
        if product is None or not product.is_inventory_tracked:
            raise InventoryValidationError("This product is not inventory tracked.")
        unit = normalize_uom(unit_of_measure)
        if unit != normalize_uom(product.unit_of_measure):
            raise InventoryValidationError("Inventory base unit does not match the product.")
        return unit

    def _admit_effect(self, effect: str) -> None:
        _effect(effect)
        if effect in self._effects:
            raise InventoryValidationError(
                "The inventory effect was already applied in this command."
            )
        self._effects.add(effect)

    @inventory_calculation
    def apply_delta(
        self,
        key: InventoryBalanceKey,
        *,
        delta: Decimal,
        movement_type: str,
        unit_of_measure: str,
        source_document_type: str,
        source_document_id: uuid.UUID,
        operator_user_id: uuid.UUID,
        reason: str | None,
        notes: str | None,
        causal_effect_code: str,
        adjustment_id: uuid.UUID | None = None,
        allow_negative: bool = False,
        source_line_id: uuid.UUID | None = None,
        source_quantity: Decimal | None = None,
        source_uom: str | None = None,
        conversion_factor: Decimal = Decimal("1"),
        reversal_of_movement_id: uuid.UUID | None = None,
        unit_cost: Decimal | None = None,
        total_cost: Decimal | None = None,
        cost_evidence_reference: str | None = None,
        lot_allocations: Sequence[InventoryLotQuantity] | None = None,
        eligibility_at: datetime | None = None,
    ) -> InventoryMovement:
        balance = self.balance(key)
        lineage = _command(self._session, key.branch_id, operator_user_id)
        delta = exact_decimal(delta)
        if delta == 0:
            raise InventoryValidationError("Inventory movement requires a finite nonzero quantity.")
        unit = self._product_uom(key, unit_of_measure)
        converted = convert_quantity(
            abs(delta) if source_quantity is None else source_quantity,
            source_uom or unit,
            unit,
            conversion_factor,
        )
        if converted.quantity_base != abs(delta):
            raise InventoryValidationError(
                "Source conversion does not explain the inventory delta."
            )
        if movement_type not in VALID_INVENTORY_MOVEMENT_TYPES:
            raise InventoryValidationError("Unsupported inventory movement type.")
        if eligibility_at is not None:
            if (
                movement_type != "SALE_CLASS_ATTRIBUTION"
                or source_line_id is None
                or eligibility_at.utcoffset() is None
                or eligibility_at > datetime.now(UTC)
            ):
                raise InventoryValidationError(
                    "Historical lot eligibility is limited to the original class sale."
                )
            sale = self._session.execute(
                select(Sale, SaleLine)
                .join(SaleLine, SaleLine.sale_id == Sale.id)
                .where(SaleLine.id == source_line_id)
            ).one_or_none()
            product = self._session.get(Product, key.product_id)
            if (
                sale is None
                or sale.Sale.branch_id != key.branch_id
                or sale.Sale.confirmed_at != eligibility_at
                or sale.SaleLine.capture_mode != "CLASS_CAPTURE"
                or product is None
                or sale.SaleLine.product_class_id != product.product_class_id
            ):
                raise InventoryValidationError(
                    "The original class sale does not authorize this lot date."
                )
        if not source_document_type.strip() or len(source_document_type) > 64:
            raise InventoryValidationError("An explicit inventory source document is required.")
        physical_count_outflow = (
            delta < 0
            and lineage["operation_code"] == "inventory.adjust"
            and movement_type in {"MANUAL_ADJUSTMENT", "STOCK_COUNT_ADJUSTMENT"}
        )
        if allow_negative or physical_count_outflow:
            scope = authorization_scope(self._session)
            if (
                scope is None
                or scope.user.id != operator_user_id
                or not reason
                or not reason.strip()
                or lineage["operation_code"] != "inventory.adjust"
                or movement_type not in {"MANUAL_ADJUSTMENT", "STOCK_COUNT_ADJUSTMENT"}
            ):
                raise InventoryValidationError(
                    "Negative stock requires an explicit authorized adjustment."
                )
            require_branches(scope.user, "inventory.adjust", [key.branch_id])
        quantity = exact_decimal(Decimal(balance.quantity_on_hand) + delta)
        if delta < 0 and self.available(key) + delta < 0 and not allow_negative:
            raise InventoryValidationError("Inventory stock is insufficient.")
        if eligibility_at is not None and delta < 0 and key not in self._lots:
            # A later receipt cannot explain a sale that already happened, even without lots.
            historical_movements = list(
                self._session.scalars(
                    select(InventoryMovement).where(
                        InventoryMovement.branch_id == key.branch_id,
                        InventoryMovement.product_id == key.product_id,
                        InventoryMovement.location_code == key.location_code,
                    )
                )
            )
            historical_movements.extend(
                movement
                for movement in self._session.new
                if isinstance(movement, InventoryMovement)
                and movement.branch_id == key.branch_id
                and movement.product_id == key.product_id
                and movement.location_code == key.location_code
            )
            historical = sum(
                (
                    movement.quantity
                    if movement.direction == "IN" and movement.occurred_at <= eligibility_at
                    else -movement.quantity
                    if movement.direction == "OUT"
                    else Decimal(0)
                    for movement in historical_movements
                ),
                Decimal(0),
            )
            if historical - balance.quantity_reserved + delta < 0:
                raise InventoryValidationError(
                    "Later receipts cannot explain an earlier class sale."
                )
        if reversal_of_movement_id is not None:
            original = self._session.get(InventoryMovement, reversal_of_movement_id)
            if (
                original is None
                or original.branch_id != key.branch_id
                or original.product_id != key.product_id
                or original.location_code != key.location_code
                or normalize_uom(original.unit_of_measure) != unit
                or original.direction == ("IN" if delta > 0 else "OUT")
            ):
                raise InventoryValidationError(
                    "A reversal must compensate its original stock identity and direction."
                )
            # The already-held aggregate balance lock serializes all compensations of this fact.
            # Include pending rows so several lines within one command obey the same bound.
            with self._session.no_autoflush:
                previous = list(
                    self._session.scalars(
                        select(InventoryMovement).where(
                            InventoryMovement.reversal_of_movement_id == original.id
                        )
                    )
                )
            previous.extend(
                item
                for item in self._session.new
                if isinstance(item, InventoryMovement)
                and item.reversal_of_movement_id == original.id
            )
            reversed_quantity = sum((item.quantity for item in previous), Decimal(0))
            if reversed_quantity + abs(delta) > original.quantity:
                raise InventoryValidationError("The original movement is already compensated.")
            if key in self._lots:
                if not lot_allocations:
                    raise InventoryValidationError("A reversal requires its original lot trace.")
                originals = {
                    item.lot_id: item.quantity
                    for item in self._session.scalars(
                        select(InventoryMovementLotAllocation).where(
                            InventoryMovementLotAllocation.movement_id == original.id
                        )
                    )
                }
                previous_ids = [item.id for item in previous]
                prior_lots: dict[uuid.UUID, Decimal] = {}
                with self._session.no_autoflush:
                    prior_allocations = list(
                        self._session.scalars(
                            select(InventoryMovementLotAllocation).where(
                                InventoryMovementLotAllocation.movement_id.in_(previous_ids)
                            )
                        )
                    )
                prior_allocations.extend(
                    item
                    for item in self._session.new
                    if isinstance(item, InventoryMovementLotAllocation)
                    and item.movement_id in previous_ids
                )
                for allocation in prior_allocations:
                    prior_lots[allocation.lot_id] = (
                        prior_lots.get(allocation.lot_id, Decimal(0)) + allocation.quantity
                    )
                for selected_allocation in lot_allocations:
                    if selected_allocation.quantity + prior_lots.get(
                        selected_allocation.lot_id, Decimal(0)
                    ) > originals.get(selected_allocation.lot_id, Decimal(0)):
                        raise InventoryValidationError(
                            "Reversal exceeds the original lot quantity."
                        )
            if original.total_cost is None:
                unit_cost = total_cost = None
            else:
                previous_value = sum(
                    (item.total_cost or Decimal(0) for item in previous), Decimal(0)
                )
                total_cost = (
                    original.total_cost - previous_value
                    if reversed_quantity + abs(delta) == original.quantity
                    else (original.total_cost * abs(delta) / original.quantity).quantize(
                        Decimal("0.00000001")
                    )
                )
                unit_cost = None  # Derive the exact proportional unit snapshot, preserving residue.
            cost_evidence_reference = (
                f"movement:{original.id}" if original.total_cost is not None else None
            )
        elif movement_type == "REVERSAL":
            raise InventoryValidationError("A reversal requires its original movement.")
        documented_outflow = reversal_of_movement_id is not None or (
            key.location_code == "IN_TRANSIT"
            and movement_type
            in {"TRANSFER_RECEIPT", "TRANSFER_RETURN", "TRANSFER_DISPOSITION", "WASTE_RECORD"}
        )
        cost = value_effect(
            quantity_before=Decimal(balance.quantity_on_hand),
            value_before=balance.inventory_value,
            delta=delta,
            unit_cost=unit_cost,
            total_cost=total_cost,
            use_documented_outflow=documented_outflow,
        )
        if cost.total_cost is not None:
            if delta < 0 and not documented_outflow:
                cost_evidence_reference = (
                    f"weighted_average:{balance.id}:{lineage['idempotency_record_id']}"
                )
            if not cost_evidence_reference or len(cost_evidence_reference) > 240:
                raise InventoryValidationError(
                    "Known inventory cost requires its evidence reference."
                )
        elif cost_evidence_reference is not None:
            raise InventoryValidationError("Unknown inventory cost cannot carry a valuation claim.")
        self._admit_effect(causal_effect_code)
        movement = InventoryMovement(
            id=uuid.uuid4(),
            product_id=key.product_id,
            branch_id=key.branch_id,
            location_code=key.location_code,
            movement_type=movement_type,
            direction="IN" if delta > 0 else "OUT",
            quantity=abs(delta),
            occurred_at=datetime.now(UTC),
            unit_of_measure=unit,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            operator_user_id=operator_user_id,
            reason=reason,
            notes=notes,
            adjustment_id=adjustment_id,
            balance_after=quantity,
            source_line_id=source_line_id,
            source_quantity=converted.source_quantity,
            source_uom=converted.source_uom,
            conversion_factor=converted.conversion_factor,
            causal_effect_code=causal_effect_code,
            reversal_of_movement_id=reversal_of_movement_id,
            unit_cost=cost.unit_cost,
            total_cost=cost.total_cost,
            cost_evidence_reference=cost_evidence_reference,
            **lineage,
        )
        if key in self._lots:
            if allow_negative:
                raise InventoryValidationError(
                    "Lot quantities cannot be invented by a negative adjustment."
                )
            self._lots[key].apply(
                movement,
                lot_allocations,
                eligibility_at=eligibility_at,
                allow_expired=(
                    physical_count_outflow
                    or (movement_type == "QUARANTINE_RELEASE" and key.location_code == "QUARANTINE")
                    or (
                        movement_type == "INVENTORY_COMPENSATION"
                        and key.location_code in {"WASTE", "QUARANTINE"}
                    )
                    or movement_type
                    in {
                        "WASTE_RECORD",
                        "PRODUCTION_WASTE",
                        "TRANSFER_DISPOSITION",
                        "RETURN_WASTE",
                        "RETURN_QUARANTINE",
                        "CLOSE_WASTE_ADJUSTMENT",
                    }
                ),
            )
        else:
            if lot_allocations:
                raise InventoryValidationError(
                    "Lot allocations require lot tracking for this product."
                )
            movement.lot_allocations = []
        balance.quantity_on_hand = quantity
        balance.inventory_value = cost.balance_value
        self._session.add(movement)
        return movement

    @inventory_calculation
    def reserve(
        self,
        key: InventoryBalanceKey,
        *,
        quantity: Decimal,
        unit_of_measure: str,
        source_document_type: str,
        source_document_id: uuid.UUID,
        source_line_id: uuid.UUID | None,
        causal_effect_code: str,
        operator_user_id: uuid.UUID,
        reason: str | None = None,
        notes: str | None = None,
    ) -> InventoryReservation:
        balance = self.balance(key)
        lineage = _command(self._session, key.branch_id, operator_user_id)
        unit = self._product_uom(key, unit_of_measure)
        quantity = exact_decimal(quantity)
        if key.location_code not in RESERVABLE_INVENTORY_LOCATIONS:
            raise InventoryValidationError(
                "This location is not eligible for inventory reservation."
            )
        if quantity <= 0 or self.available(key) < quantity:
            raise InventoryValidationError("Inventory stock is insufficient for this reservation.")
        self._admit_effect(causal_effect_code)
        reservation = InventoryReservation(
            id=uuid.uuid4(),
            branch_id=key.branch_id,
            product_id=key.product_id,
            location_code=key.location_code,
            quantity=quantity,
            consumed_quantity=Decimal(0),
            released_quantity=Decimal(0),
            unit_of_measure=unit,
            status="ACTIVE",
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            source_line_id=source_line_id,
            idempotency_record_id=lineage["idempotency_record_id"],
            causal_effect_code=causal_effect_code,
            operator_user_id=operator_user_id,
        )
        balance.quantity_reserved = exact_decimal(self.reserved(key) + quantity)
        self._session.add(reservation)
        self._reservations[reservation.id] = reservation
        event = self._reservation_event(
            reservation, "RESERVE", quantity, causal_effect_code, reason
        )
        if key in self._lots:
            self._lots[key].reserve(reservation, event)
        return reservation

    def _reservation(self, reservation_id: uuid.UUID) -> InventoryReservation:
        if reservation_id not in self._reservations:
            reservation = self._session.get(InventoryReservation, reservation_id)
            if reservation is None:
                raise InventoryValidationError("Inventory reservation was not found.")
            self.balance(
                InventoryBalanceKey(
                    reservation.branch_id, reservation.product_id, reservation.location_code
                )
            )
            reservation = self._session.scalars(
                select(InventoryReservation)
                .where(InventoryReservation.id == reservation_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).one()
            self._reservations[reservation_id] = reservation
        return self._reservations[reservation_id]

    def _reservation_event(
        self,
        reservation: InventoryReservation,
        event_type: str,
        quantity: Decimal,
        effect: str,
        reason: str | None,
        movement_id: uuid.UUID | None = None,
    ) -> InventoryReservationEvent:
        owner = execution(self._session)
        if owner is None or owner.record is None:
            raise IdempotencyBoundaryError("Reservation effects require the command owner.")
        _command(self._session, reservation.branch_id, owner.record.actor_user_id)
        event = InventoryReservationEvent(
            id=uuid.uuid4(),
            reservation_id=reservation.id,
            reservation=reservation,
            branch_id=reservation.branch_id,
            event_type=event_type,
            quantity=quantity,
            inventory_movement_id=movement_id,
            idempotency_record_id=owner.record.id,
            causal_effect_code=effect,
            operator_user_id=owner.record.actor_user_id,
            reason=reason,
        )
        self._session.add(event)
        return event

    @inventory_calculation
    def _remaining(
        self, reservation: InventoryReservation, quantity: Decimal
    ) -> InventoryBalanceKey:
        quantity = exact_decimal(quantity)
        remaining = (
            reservation.quantity - reservation.consumed_quantity - reservation.released_quantity
        )
        if quantity <= 0 or quantity > remaining:
            raise InventoryValidationError("The reservation has insufficient remaining quantity.")
        return InventoryBalanceKey(
            reservation.branch_id, reservation.product_id, reservation.location_code
        )

    @staticmethod
    def _reservation_status(reservation: InventoryReservation) -> None:
        if reservation.consumed_quantity == reservation.quantity:
            reservation.status = "CONSUMED"
        elif reservation.consumed_quantity + reservation.released_quantity == reservation.quantity:
            reservation.status = "RELEASED"
        elif reservation.consumed_quantity > 0:
            reservation.status = "PARTIALLY_CONSUMED"
        else:
            reservation.status = "ACTIVE"

    @inventory_calculation
    def release(
        self,
        reservation_id: uuid.UUID,
        *,
        quantity: Decimal,
        causal_effect_code: str,
        reason: str | None = None,
    ) -> InventoryReservationEvent:
        reservation = self._reservation(reservation_id)
        key = self._remaining(reservation, quantity)
        self._admit_effect(causal_effect_code)
        event = self._reservation_event(
            reservation, "RELEASE", quantity, causal_effect_code, reason
        )
        balance = self.balance(key)
        if balance.quantity_reserved < quantity:
            raise InventoryValidationError("Reserved balance does not reconcile with its evidence.")
        balance.quantity_reserved -= quantity
        if key in self._lots:
            selected = self._lots[key].take_reservation(reservation_id, quantity, consume=False)
            self._lots[key]._record_event(event, selected)
        reservation.released_quantity += quantity
        self._reservation_status(reservation)
        return event

    @inventory_calculation
    def consume(
        self,
        reservation_id: uuid.UUID,
        *,
        quantity: Decimal,
        movement_type: str,
        source_document_type: str,
        source_document_id: uuid.UUID,
        source_line_id: uuid.UUID | None,
        causal_effect_code: str,
        operator_user_id: uuid.UUID,
        reason: str | None = None,
        notes: str | None = None,
        unit_cost: Decimal | None = None,
        cost_evidence_reference: str | None = None,
    ) -> InventoryMovement:
        reservation = self._reservation(reservation_id)
        key = self._remaining(reservation, quantity)
        _command(self._session, key.branch_id, operator_user_id)
        balance = self.balance(key)
        if balance.quantity_reserved < quantity:
            raise InventoryValidationError("Reserved balance does not reconcile with its evidence.")
        balance.quantity_reserved -= quantity
        selected = (
            self._lots[key].take_reservation(
                reservation_id,
                quantity,
                consume=True,
                allow_expired=movement_type == "PRODUCTION_WASTE",
            )
            if key in self._lots
            else None
        )
        movement = self.apply_delta(
            key,
            delta=-quantity,
            movement_type=movement_type,
            unit_of_measure=reservation.unit_of_measure,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            source_line_id=source_line_id,
            causal_effect_code=causal_effect_code,
            operator_user_id=operator_user_id,
            reason=reason,
            notes=notes,
            unit_cost=unit_cost,
            cost_evidence_reference=cost_evidence_reference,
            lot_allocations=selected,
        )
        reservation.consumed_quantity += quantity
        self._reservation_status(reservation)
        event = self._reservation_event(
            reservation, "CONSUME", quantity, causal_effect_code, reason, movement.id
        )
        event.inventory_movement = movement
        if selected is not None:
            self._lots[key]._record_event(event, selected)
        return movement


def lock_inventory_balances(
    session: Session, keys: Iterable[InventoryBalanceKey]
) -> LockedInventoryBalances:
    """Lock the complete write set in branch/product/location order before any stock effects."""
    balances: dict[InventoryBalanceKey, InventoryBalance] = {}
    for key in sorted(set(keys)):
        if key.location_code not in VALID_INVENTORY_LOCATION_CODES:
            raise InventoryValidationError("Unsupported inventory location.")
        statement = (
            select(InventoryBalance)
            .where(
                InventoryBalance.branch_id == key.branch_id,
                InventoryBalance.product_id == key.product_id,
                InventoryBalance.location_code == key.location_code,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        balance = session.scalar(statement)
        if balance is None:
            try:
                # ORM inserts retain the branch authorization guard. Only this insert is retried.
                with session.begin_nested():
                    balance = InventoryBalance(
                        product_id=key.product_id,
                        branch_id=key.branch_id,
                        location_code=key.location_code,
                        quantity_on_hand=Decimal(0),
                        quantity_reserved=Decimal(0),
                        inventory_value=Decimal(0),
                    )
                    session.add(balance)
                    session.flush()
            except IntegrityError as error:
                if getattr(getattr(error.orig, "diag", None), "constraint_name", None) != (
                    "uq_inventory_balances_product_branch_location"
                ):
                    raise
                balance = session.scalars(statement).one()
        balances[key] = balance
    transaction = session.get_transaction()
    if transaction is None:
        transaction = session.begin()
    return LockedInventoryBalances(session, transaction, balances)
