"""Canonical stock, reservations, valuation and FEFO under actual admitted commands."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    LockedInventoryBalances,
    create_inventory_lot,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import InventoryLotQuantity
from zeromerma_api.modules.inventory.infrastructure.lot_models import (
    InventoryLotBalance,
    InventoryMovementLotAllocation,
    InventoryReservationLotAllocation,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryReservation,
    InventoryReservationEvent,
)
from zeromerma_api.testing.idempotency import new_idempotency_key


class StockResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[UUID] = []


def _fixture(*, lots: bool = False) -> tuple[InventoryBalanceKey, UUID, str]:
    with SessionLocal() as session:
        branch = session.scalars(select(Branch).order_by(Branch.code)).first()
        product = session.scalars(
            select(Product).where(Product.is_inventory_tracked.is_(True))
        ).first()
        actor = session.scalars(select(User.id)).first()
        assert branch and product and actor
        product.lot_tracking_enabled = lots
        product.expiry_required = lots
        session.commit()
        return (
            InventoryBalanceKey(branch.id, product.id, "BACKROOM"),
            actor,
            product.unit_of_measure,
        )


def _run(
    key: InventoryBalanceKey,
    actor: UUID,
    action: Callable[[Session], list[UUID]],
    *,
    request_key: str | None = None,
) -> IdempotencyResult:
    with SessionLocal() as session:
        return IdempotencyExecutor().execute(
            session,
            key=request_key or new_idempotency_key(),
            operation_code="inventory.core_test",
            payload={},
            resolve_context=lambda current, saved: CommandContext(
                actor_user_id=actor, surface="BACKOFFICE", branch_id=key.branch_id
            ),
            authorize=lambda current, context: None,
            action=lambda current: CommandResult(
                status_code=201, snapshot=StockResult(ids=action(current))
            ),
            response_policy=ResponsePolicy(snapshot_model=StockResult),
        )


def _move(
    locked: LockedInventoryBalances,
    key: InventoryBalanceKey,
    actor: UUID,
    unit: str,
    delta: str,
    *,
    effect: str = "stock",
    cost: str | None = None,
    lots: list[InventoryLotQuantity] | None = None,
    movement_type: str = "PURCHASE_RECEIPT",
) -> InventoryMovement:
    return locked.apply_delta(
        key,
        delta=Decimal(delta),
        movement_type=movement_type,
        unit_of_measure=unit,
        source_document_type="SYNTHETIC_ACCEPTANCE",
        source_document_id=uuid4(),
        operator_user_id=actor,
        reason="Synthetic evidence",
        notes=None,
        causal_effect_code=effect,
        unit_cost=Decimal(cost) if cost else None,
        cost_evidence_reference="synthetic-receipt" if cost else None,
        lot_allocations=lots,
    )


def test_admitted_effect_replays_once_and_immutable_cause_cannot_change() -> None:
    key, actor, unit = _fixture()
    request_key = new_idempotency_key()

    def action(session: Session) -> list[UUID]:
        return [_move(lock_inventory_balances(session, [key]), key, actor, unit, "10", cost="2").id]

    first = _run(key, actor, action, request_key=request_key)
    assert _run(key, actor, action, request_key=request_key).replayed
    with SessionLocal() as session:
        movement = session.scalars(select(InventoryMovement)).one()
        balance = session.scalars(select(InventoryBalance)).one()
        assert str(movement.id) == first.payload["ids"][0]
        assert movement.idempotency_record_id == first.record_id
        assert balance.inventory_value == Decimal(20) and balance.quantity_on_hand == Decimal(10)
        movement.quantity = Decimal(9)
        with pytest.raises(IntegrityError, match="immutable"):
            session.flush()


def test_owner_is_required_and_pending_duplicate_effect_rolls_back() -> None:
    key, actor, unit = _fixture()
    with SessionLocal() as session, pytest.raises(IdempotencyBoundaryError):
        _move(lock_inventory_balances(session, [key]), key, actor, unit, "1")

    def action(session: Session) -> list[UUID]:
        locked = lock_inventory_balances(session, [key])
        _move(locked, key, actor, unit, "1")
        _move(locked, key, actor, unit, "1")
        return []

    with pytest.raises(InventoryValidationError, match="already applied"):
        _run(key, actor, action)
    with SessionLocal() as session:
        assert session.scalar(select(InventoryMovement.id)) is None
        assert session.scalar(select(InventoryBalance.id)) is None


def test_reservation_consumption_release_and_weighted_value_conserve_stock() -> None:
    key, actor, unit = _fixture()

    def prepare(session: Session) -> list[UUID]:
        locked = lock_inventory_balances(session, [key])
        _move(locked, key, actor, unit, "10", cost="2", effect="receipt-1")
        _move(locked, key, actor, unit, "10", cost="4", effect="receipt-2")
        reservation = locked.reserve(
            key,
            quantity=Decimal(8),
            unit_of_measure=unit,
            source_document_type="SYNTHETIC_PLAN",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="reserve",
            operator_user_id=actor,
        )
        assert locked.available(key) == Decimal(12)
        return [reservation.id]

    reservation_id = UUID(_run(key, actor, prepare).payload["ids"][0])

    def consume(session: Session) -> list[UUID]:
        locked = lock_inventory_balances(session, [key])
        movement = locked.consume(
            reservation_id,
            quantity=Decimal(5),
            movement_type="PRODUCTION_CONSUMPTION",
            source_document_type="SYNTHETIC_RUN",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="consume",
            operator_user_id=actor,
        )
        locked.release(reservation_id, quantity=Decimal(3), causal_effect_code="release")
        assert movement.total_cost == Decimal(15) and locked.available(key) == Decimal(15)
        return [movement.id]

    _run(key, actor, consume)
    with SessionLocal() as session:
        balance = session.scalars(select(InventoryBalance)).one()
        assert balance.quantity_on_hand == Decimal(15) and balance.quantity_reserved == 0
        assert balance.inventory_value == Decimal(45)
        events = list(session.scalars(select(InventoryReservationEvent)))
        assert {event.event_type: event.quantity for event in events} == {
            "RESERVE": Decimal(8),
            "CONSUME": Decimal(5),
            "RELEASE": Decimal(3),
        }


def test_fefo_selects_earliest_expiry_without_changing_weighted_average_cost() -> None:
    key, actor, unit = _fixture(lots=True)
    now = datetime.now(UTC)

    def prepare(session: Session) -> list[UUID]:
        lots = [
            create_inventory_lot(
                session,
                product_id=key.product_id,
                lot_code=f"LOT-{days}",
                expires_at=now + timedelta(days=days),
                source_document_type="SYNTHETIC_RECEIPT",
                source_document_id=uuid4(),
                source_line_id=None,
                branch_id=key.branch_id,
                operator_user_id=actor,
            )
            for days in [10, 2]
        ]
        locked = lock_inventory_balances(session, [key])
        for index, lot in enumerate(lots):
            _move(
                locked,
                key,
                actor,
                unit,
                "5",
                effect=f"receipt-{index}",
                cost=str(2 + index * 2),
                lots=[InventoryLotQuantity(lot.id, Decimal(5))],
            )
        return [lot.id for lot in lots]

    lot_ids = [UUID(value) for value in _run(key, actor, prepare).payload["ids"]]

    def sell(session: Session) -> list[UUID]:
        movement = _move(
            lock_inventory_balances(session, [key]),
            key,
            actor,
            unit,
            "-6",
            movement_type="SALE_DIRECT",
        )
        assert movement.total_cost == Decimal(18)
        assert {item.lot_id: item.quantity for item in movement.lot_allocations} == {
            lot_ids[1]: Decimal(5),
            lot_ids[0]: Decimal(1),
        }
        return [movement.id]

    _run(key, actor, sell)
    with SessionLocal() as session:
        assert (
            sum(row.quantity_on_hand for row in session.scalars(select(InventoryLotBalance))) == 4
        )


def test_unidentified_lot_can_enter_quarantine_but_never_sellable_stock() -> None:
    key, actor, unit = _fixture(lots=True)

    def quarantine(session: Session) -> list[UUID]:
        lot = create_inventory_lot(
            session,
            product_id=key.product_id,
            lot_code="UNIDENTIFIED:1",
            expires_at=None,
            source_document_type="SYNTHETIC_RETURN",
            source_document_id=uuid4(),
            source_line_id=None,
            branch_id=key.branch_id,
            operator_user_id=actor,
            unidentified=True,
        )
        target = InventoryBalanceKey(key.branch_id, key.product_id, "QUARANTINE")
        _move(
            lock_inventory_balances(session, [target]),
            target,
            actor,
            unit,
            "1",
            lots=[InventoryLotQuantity(lot.id, Decimal(1))],
            movement_type="RETURN_QUARANTINE",
        )
        return [lot.id]

    lot_id = UUID(_run(key, actor, quarantine).payload["ids"][0])

    def release(session: Session) -> list[UUID]:
        _move(
            lock_inventory_balances(session, [key]),
            key,
            actor,
            unit,
            "1",
            lots=[InventoryLotQuantity(lot_id, Decimal(1))],
        )
        return []

    with pytest.raises(InventoryValidationError, match="expired|unidentified"):
        _run(key, actor, release)


@pytest.mark.parametrize("unidentified", [False, True])
def test_quarantine_disposal_removes_expired_or_unknown_stock_without_releasing_it(
    unidentified: bool,
) -> None:
    key, actor, unit = _fixture(lots=True)
    quarantine = InventoryBalanceKey(key.branch_id, key.product_id, "QUARANTINE")
    waste = InventoryBalanceKey(key.branch_id, key.product_id, "WASTE")

    def prepare(session: Session) -> list[UUID]:
        lot = create_inventory_lot(
            session,
            product_id=key.product_id,
            lot_code="DISPOSAL-ONLY",
            expires_at=None if unidentified else datetime.now(UTC) - timedelta(days=1),
            source_document_type="SYNTHETIC_RETURN",
            source_document_id=uuid4(),
            source_line_id=None,
            branch_id=key.branch_id,
            operator_user_id=actor,
            unidentified=unidentified,
        )
        _move(
            lock_inventory_balances(session, [quarantine]),
            quarantine,
            actor,
            unit,
            "2",
            lots=[InventoryLotQuantity(lot.id, Decimal(2))],
            movement_type="RETURN_QUARANTINE",
        )
        return [lot.id]

    lot_id = UUID(_run(key, actor, prepare).payload["ids"][0])

    def transfer(session: Session, destination: InventoryBalanceKey) -> list[UUID]:
        balances = lock_inventory_balances(session, [quarantine, destination])
        selected = [InventoryLotQuantity(lot_id, Decimal(2))]
        outgoing = _move(
            balances,
            quarantine,
            actor,
            unit,
            "-2",
            effect="dispose-out",
            lots=selected,
            movement_type="QUARANTINE_RELEASE",
        )
        incoming = _move(
            balances,
            destination,
            actor,
            unit,
            "2",
            effect="dispose-in",
            lots=selected,
            movement_type="QUARANTINE_RELEASE",
        )
        return [outgoing.id, incoming.id]

    with pytest.raises(InventoryValidationError, match="quarantine"):
        _run(key, actor, lambda session: transfer(session, key))
    _run(key, actor, lambda session: transfer(session, waste))
    with SessionLocal() as session:
        quantities = {
            row.location_code: row.quantity_on_hand
            for row in session.scalars(select(InventoryBalance))
        }
        assert quantities == {"QUARANTINE": Decimal(0), "WASTE": Decimal(2)}
        assert len(list(session.scalars(select(InventoryMovement)))) == 3


def test_partial_compensations_preserve_original_value_residue_and_reject_overrefund() -> None:
    key, actor, unit = _fixture()

    def opening(session: Session) -> list[UUID]:
        movement = lock_inventory_balances(session, [key]).apply_delta(
            key,
            delta=Decimal(3),
            movement_type="OPENING_ADJUSTMENT",
            unit_of_measure=unit,
            source_document_type="SYNTHETIC_COUNT",
            source_document_id=uuid4(),
            operator_user_id=actor,
            reason="Synthetic count",
            notes=None,
            causal_effect_code="opening",
            total_cost=Decimal(1),
            cost_evidence_reference="count-value",
        )
        return [movement.id]

    original_id = UUID(_run(key, actor, opening).payload["ids"][0])

    def reverse(session: Session) -> list[UUID]:
        movement = lock_inventory_balances(session, [key]).apply_delta(
            key,
            delta=Decimal(-1),
            movement_type="REVERSAL",
            unit_of_measure=unit,
            source_document_type="SYNTHETIC_COMPENSATION",
            source_document_id=uuid4(),
            operator_user_id=actor,
            reason="Partial documentary compensation",
            notes=None,
            causal_effect_code="reverse",
            reversal_of_movement_id=original_id,
        )
        return [movement.id]

    for _ in range(3):
        _run(key, actor, reverse)
    with SessionLocal() as session:
        reversals = list(
            session.scalars(
                select(InventoryMovement)
                .where(InventoryMovement.reversal_of_movement_id == original_id)
                .order_by(InventoryMovement.recorded_at)
            )
        )
        assert [item.total_cost for item in reversals] == [
            Decimal("0.33333333"),
            Decimal("0.33333333"),
            Decimal("0.33333334"),
        ]
        original = session.get(InventoryMovement, original_id)
        assert original and original.total_cost == 1 and original.quantity == 3
        balance = session.scalars(select(InventoryBalance)).one()
        assert balance.quantity_on_hand == 0 and balance.inventory_value == 0
    with pytest.raises(InventoryValidationError):
        _run(key, actor, reverse)


def test_reserved_lot_expiry_requires_resolution_and_does_not_switch_lots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key, actor, unit = _fixture(lots=True)
    now = datetime.now(UTC)

    def prepare(session: Session) -> list[UUID]:
        lots = [
            create_inventory_lot(
                session,
                product_id=key.product_id,
                lot_code=f"RESERVED-{days}",
                expires_at=now + timedelta(days=days),
                source_document_type="SYNTHETIC_RECEIPT",
                source_document_id=uuid4(),
                source_line_id=None,
                branch_id=key.branch_id,
                operator_user_id=actor,
            )
            for days in (1, 10)
        ]
        locked = lock_inventory_balances(session, [key])
        for index, lot in enumerate(lots):
            _move(
                locked,
                key,
                actor,
                unit,
                "5",
                effect=f"receipt-{index}",
                lots=[InventoryLotQuantity(lot.id, Decimal(5))],
            )
        reservation = locked.reserve(
            key,
            quantity=Decimal(3),
            unit_of_measure=unit,
            source_document_type="SYNTHETIC_PLAN",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="reserve",
            operator_user_id=actor,
        )
        return [reservation.id, lots[0].id, lots[1].id]

    reservation_id, expired_lot_id, usable_lot_id = [
        UUID(value) for value in _run(key, actor, prepare).payload["ids"]
    ]

    class FutureDateTime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:
            return now + timedelta(days=2)

    from zeromerma_api.modules.inventory.application import lots as lot_module

    monkeypatch.setattr(lot_module, "datetime", FutureDateTime)

    def consume(session: Session) -> list[UUID]:
        movement = lock_inventory_balances(session, [key]).consume(
            reservation_id,
            quantity=Decimal(3),
            movement_type="PRODUCTION_CONSUMPTION",
            source_document_type="SYNTHETIC_RUN",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="consume",
            operator_user_id=actor,
        )
        return [movement.id]

    with pytest.raises(InventoryValidationError, match="reserved lot expired"):
        _run(key, actor, consume)
    with SessionLocal() as session:
        balance = session.scalars(select(InventoryBalance)).one()
        assert balance.quantity_on_hand == 10 and balance.quantity_reserved == 3
        assert len(list(session.scalars(select(InventoryMovement)))) == 2

    waste_key = InventoryBalanceKey(key.branch_id, key.product_id, "WASTE")

    def dispose(session: Session) -> list[UUID]:
        balances = lock_inventory_balances(session, [key, waste_key])
        movement = balances.consume(
            reservation_id,
            quantity=Decimal(3),
            movement_type="PRODUCTION_WASTE",
            source_document_type="SYNTHETIC_RUN",
            source_document_id=uuid4(),
            source_line_id=None,
            causal_effect_code="explicit-reserved-waste",
            operator_user_id=actor,
        )
        incoming = _move(
            balances,
            waste_key,
            actor,
            unit,
            "3",
            effect="waste-destination",
            lots=[InventoryLotQuantity(expired_lot_id, Decimal(3))],
            movement_type="PRODUCTION_WASTE",
        )
        return [movement.id, incoming.id]

    request_key = new_idempotency_key()
    disposed = _run(key, actor, dispose, request_key=request_key)
    replay = _run(key, actor, dispose, request_key=request_key)
    assert replay.payload == disposed.payload
    with SessionLocal() as session:
        balances = {row.location_code: row for row in session.scalars(select(InventoryBalance))}
        assert balances["BACKROOM"].quantity_on_hand == 7
        assert balances["WASTE"].quantity_on_hand == 3
        assert all(row.quantity_reserved == 0 for row in balances.values())
        reservation = session.get(InventoryReservation, reservation_id)
        assert (
            reservation and reservation.consumed_quantity == 3 and reservation.status == "CONSUMED"
        )
        reserved = session.scalars(select(InventoryReservationLotAllocation)).one()
        assert reserved.lot_id == expired_lot_id and reserved.consumed_quantity == 3
        usable = session.scalars(
            select(InventoryLotBalance).where(
                InventoryLotBalance.lot_id == usable_lot_id,
                InventoryLotBalance.location_code == "BACKROOM",
            )
        ).one()
        assert usable.quantity_on_hand == 5 and usable.quantity_reserved == 0
        assert len(list(session.scalars(select(InventoryMovement)))) == 4
        effects = session.scalars(
            select(InventoryMovementLotAllocation).where(
                InventoryMovementLotAllocation.movement_id.in_(
                    [UUID(value) for value in disposed.payload["ids"]]
                )
            )
        ).all()
        assert len(effects) == 2
        assert all(row.lot_id == expired_lot_id and row.quantity == 3 for row in effects)


def test_disposable_stock_fixture_emits_real_cause_and_is_only_opt_in() -> None:
    key, actor, _ = _fixture()
    from zeromerma_api.testing.inventory import seed_test_inventory

    with SessionLocal() as session:
        assert session.scalar(select(InventoryMovement.id)) is None
        ids = seed_test_inventory(
            session,
            branch_id=key.branch_id,
            actor_user_id=actor,
            product_quantities={key.product_id: Decimal(5)},
            location_code=key.location_code,
            fixture_reference="Explicit core acceptance",
            unit_cost=Decimal(2),
        )
        movement = session.scalars(select(InventoryMovement)).one()
        assert movement.id == ids[0] and movement.context_version == 1
        assert movement.source_document_type == "TEST_INVENTORY_OPENING"
        assert movement.total_cost == 10
