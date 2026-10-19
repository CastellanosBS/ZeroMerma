"""Real PostgreSQL balance contention, without sleeps or a global inventory lock."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from queue import Queue
from threading import Event
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.bootstrap.seed_local import SEED_BRANCH_CODE, SEED_USER_EMAIL
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.inventory.application.mutations import (
    InventoryBalanceKey,
    LockedInventoryBalances,
    lock_inventory_balances,
)
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryAdjustment,
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.concurrency import (
    TransactionProbe,
    transaction_probe,
    wait_until_blocked,
)
from zeromerma_api.testing.idempotency import new_idempotency_key


def _fixture() -> tuple[list[InventoryBalanceKey], UUID]:
    with SessionLocal() as session:
        branches = session.scalars(select(Branch.id).order_by(Branch.id)).all()
        products = session.scalars(select(Product.id).order_by(Product.id).limit(2)).all()
        actor = session.scalars(select(User.id).where(User.email == SEED_USER_EMAIL)).one()
        return (
            [
                InventoryBalanceKey(branch, product, "BACKROOM")
                for branch in branches[:2]
                for product in products
            ],
            actor,
        )


def _apply(
    balances: LockedInventoryBalances, key: InventoryBalanceKey, actor: UUID, quantity: str
) -> InventoryMovement:
    source_id = uuid4()
    product = balances._session.get(Product, key.product_id)
    assert product is not None
    return balances.apply_delta(
        key,
        delta=Decimal(quantity),
        movement_type="MANUAL_ADJUSTMENT",
        unit_of_measure=product.unit_of_measure,
        source_document_type="INVENTORY_CONCURRENCY_TEST",
        source_document_id=source_id,
        causal_effect_code=f"concurrency:{source_id}",
        operator_user_id=actor,
        reason="Concurrency acceptance",
        notes=None,
    )


def _assert_reconciled(key: InventoryBalanceKey, expected: str, count: int) -> None:
    with SessionLocal() as session:
        rows = session.scalars(
            select(InventoryBalance).where(
                InventoryBalance.branch_id == key.branch_id,
                InventoryBalance.product_id == key.product_id,
                InventoryBalance.location_code == key.location_code,
            )
        ).all()
        movements = session.scalars(
            select(InventoryMovement).where(
                InventoryMovement.branch_id == key.branch_id,
                InventoryMovement.product_id == key.product_id,
                InventoryMovement.location_code == key.location_code,
            )
        ).all()
        assert len(rows) == 1
        assert rows[0].quantity_on_hand == Decimal(expected)
        assert len(movements) == count
        assert (
            sum(
                (item.quantity if item.direction == "IN" else -item.quantity for item in movements),
                Decimal(0),
            )
            == rows[0].quantity_on_hand
        )


class _Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    complete: bool = True


def _command(
    session: Session,
    keys: list[InventoryBalanceKey],
    actor: UUID,
    action: Callable[[Session], None],
) -> None:
    def run(current: Session) -> CommandResult:
        action(current)
        return CommandResult(status_code=201, snapshot=_Result(complete=True))

    IdempotencyExecutor(command_lock_timeout_ms=10000).execute(
        session,
        key=new_idempotency_key(),
        operation_code="inventory.concurrency_test",
        payload={},
        resolve_context=lambda current, saved: CommandContext(
            actor_user_id=actor,
            surface="BACKOFFICE",
            branch_id=keys[0].branch_id,
            related_branch_ids=tuple(sorted({key.branch_id for key in keys})),
        ),
        authorize=lambda current, context: None,
        action=run,
        response_policy=ResponsePolicy(snapshot_model=_Result),
    )


def _seed(key: InventoryBalanceKey, actor: UUID, quantity: str) -> None:
    with SessionLocal() as session:

        def action(current: Session) -> None:
            _apply(lock_inventory_balances(current, [key]), key, actor, quantity)

        _command(session, [key], actor, action)


@pytest.mark.parametrize("existing", [False, True])
def test_two_entries_serialize_existing_or_first_balance(
    client: TestClient, existing: bool
) -> None:
    keys, actor = _fixture()
    key = keys[0]
    if existing:
        _seed(key, actor, "1")
    probes: Queue[TransactionProbe] = Queue()

    def second() -> None:
        with SessionLocal() as session:

            def action(current: Session) -> None:
                probes.put(transaction_probe(current))
                _apply(lock_inventory_balances(current, [key]), key, actor, "3")

            _command(session, [key], actor, action)

    with ThreadPoolExecutor(max_workers=1) as pool, SessionLocal() as session:
        pending = []

        def first(current: Session) -> None:
            first_probe = transaction_probe(current)
            _apply(lock_inventory_balances(current, [key]), key, actor, "2")
            current.flush()
            pending.append(pool.submit(second))
            second_probe = probes.get(timeout=5)
            assert second_probe.transaction_id != first_probe.transaction_id
            wait_until_blocked(second_probe.backend_pid, first_probe.backend_pid)

        _command(session, [key], actor, first)
        pending[0].result(timeout=10)
    _assert_reconciled(key, "6" if existing else "5", 3 if existing else 2)


@pytest.mark.parametrize(
    "initial,first_delta,second_delta,expected,rejected",
    [("5", "2", "-3", "4", False), ("5", "-3", "-3", "2", True)],
)
def test_concurrent_deltas_refresh_preloaded_identity_and_check_stock(
    client: TestClient,
    initial: str,
    first_delta: str,
    second_delta: str,
    expected: str,
    rejected: bool,
) -> None:
    keys, actor = _fixture()
    key = keys[0]
    _seed(key, actor, initial)
    probes: Queue[TransactionProbe] = Queue()
    start_lock = Event()

    def second() -> bool:
        with SessionLocal() as session:
            stale = session.scalars(select(InventoryBalance)).one()
            assert stale.quantity_on_hand == Decimal(initial)

            def action(current: Session) -> None:
                probes.put(transaction_probe(current))
                assert start_lock.wait(timeout=10)
                balances = lock_inventory_balances(current, [key])
                assert balances.balance(key) is stale
                _apply(balances, key, actor, second_delta)

            try:
                _command(session, [key], actor, action)
                return False
            except InventoryValidationError:
                return True

    with ThreadPoolExecutor(max_workers=1) as pool, SessionLocal() as session:
        future = pool.submit(second)
        second_probe = probes.get(timeout=5)

        def first(current: Session) -> None:
            first_probe = transaction_probe(current)
            _apply(lock_inventory_balances(current, [key]), key, actor, first_delta)
            current.flush()
            start_lock.set()
            wait_until_blocked(second_probe.backend_pid, first_probe.backend_pid)

        _command(session, [key], actor, first)
        assert future.result(timeout=10) is rejected
    _assert_reconciled(key, expected, 2 if rejected else 3)


def test_repeated_product_deltas_keep_all_pending_changes_without_flush(client: TestClient) -> None:
    keys, actor = _fixture()
    key = keys[0]
    with SessionLocal() as session:

        def action(current: Session) -> None:
            balances = lock_inventory_balances(current, [key, key])
            first = _apply(balances, key, actor, "2.125")
            second = _apply(balances, key, actor, "3.500")
            third = _apply(balances, key, actor, "-1.125")
            assert [first.balance_after, second.balance_after, third.balance_after] == [
                Decimal("2.125"),
                Decimal("5.625"),
                Decimal("4.500"),
            ]

        _command(session, [key], actor, action)
    _assert_reconciled(key, "4.500", 3)


@pytest.mark.parametrize("other_index", [1, 2])
def test_different_products_or_branches_progress_while_another_key_is_locked(
    client: TestClient,
    other_index: int,
) -> None:
    keys, actor = _fixture()
    with ThreadPoolExecutor(max_workers=1) as pool, SessionLocal() as session:

        def first(current: Session) -> None:
            _apply(lock_inventory_balances(current, [keys[0]]), keys[0], actor, "2")
            current.flush()
            # Independent command must commit while this command still holds its stock lock.
            pool.submit(_seed, keys[other_index], actor, "3").result(timeout=5)

        _command(session, [keys[0]], actor, first)
    _assert_reconciled(keys[other_index], "3", 1)


def test_opposite_input_orders_lock_the_same_complete_set_before_effects(
    client: TestClient,
) -> None:
    keys, actor = _fixture()
    keys = sorted(
        [
            keys[2],
            keys[1],
            keys[0],
            InventoryBalanceKey(keys[0].branch_id, keys[0].product_id, "COUNTER"),
        ]
    )
    with SessionLocal() as session:

        def prepare(current: Session) -> None:
            balances = lock_inventory_balances(current, keys)
            for key in keys:
                _apply(balances, key, actor, "1")

        _command(session, keys, actor, prepare)
    probes: Queue[TransactionProbe] = Queue()

    def second() -> None:
        with SessionLocal() as session:

            def action(current: Session) -> None:
                probes.put(transaction_probe(current))
                balances = lock_inventory_balances(current, reversed(keys))
                for key in reversed(keys):
                    _apply(balances, key, actor, "3")

            _command(session, keys, actor, action)

    with ThreadPoolExecutor(max_workers=1) as pool, SessionLocal() as session:
        pending = []

        def first(current: Session) -> None:
            first_probe = transaction_probe(current)
            _apply(lock_inventory_balances(current, [keys[0]]), keys[0], actor, "2")
            current.flush()
            pending.append(pool.submit(second))
            second_probe = probes.get(timeout=5)
            wait_until_blocked(second_probe.backend_pid, first_probe.backend_pid)
            # Reversed input must block at the minimum key, without locking any later row.
            with SessionLocal() as observer:
                for key in keys[1:]:
                    assert (
                        observer.scalar(
                            select(InventoryBalance)
                            .where(
                                InventoryBalance.branch_id == key.branch_id,
                                InventoryBalance.product_id == key.product_id,
                                InventoryBalance.location_code == key.location_code,
                            )
                            .with_for_update(nowait=True)
                        )
                        is not None
                    )

        _command(session, [keys[0]], actor, first)
        pending[0].result(timeout=10)
    _assert_reconciled(keys[0], "6", 3)
    for key in keys[1:]:
        _assert_reconciled(key, "4", 2)


def test_unrelated_integrity_error_is_not_reclassified_as_duplicate_balance(
    client: TestClient,
) -> None:
    keys, _ = _fixture()
    with SessionLocal() as session, pytest.raises(IntegrityError) as failure:
        lock_inventory_balances(
            session, [InventoryBalanceKey(keys[0].branch_id, uuid4(), "BACKROOM")]
        )
    assert (
        failure.value.orig.diag.constraint_name != "uq_inventory_balances_product_branch_location"
    )


def test_locked_handle_cannot_mutate_after_its_transaction_ends(client: TestClient) -> None:
    keys, actor = _fixture()
    with SessionLocal() as session:
        balances = lock_inventory_balances(session, [keys[0]])
        session.commit()
        with pytest.raises(RuntimeError, match="original transaction"):
            _apply(balances, keys[0], actor, "1")


def test_adjustment_rollback_after_movement_preserves_atomic_business_audit_outbox(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = owner_headers()
    with SessionLocal() as session:
        branch_id = session.scalars(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE)).one()
        product_id = session.scalars(select(Product.id).order_by(Product.id).limit(1)).one()
        before = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                InventoryAdjustment,
                InventoryBalance,
                InventoryMovement,
                AuditLog,
                OutboxEvent,
            )
        )
    original = OutboxWriter.append

    def fail_after_outbox(self: OutboxWriter, session: Session, **kwargs: object) -> None:
        original(self, session, **kwargs)
        session.flush()
        raise RuntimeError("Injected failure after inventory and outbox flush")

    key = new_idempotency_key()
    body = {
        "branch_id": str(branch_id),
        "product_id": str(product_id),
        "location_code": "BACKROOM",
        "adjustment_type": "INCREASE",
        "quantity": "2",
        "reason": "Rollback acceptance",
    }
    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail_after_outbox)
        with pytest.raises(RuntimeError, match="Injected failure"):
            client.post(
                "/v1/admin/inventory/adjustments",
                headers={**headers, "Idempotency-Key": key},
                json=body,
            )
    with SessionLocal() as session:
        after = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                InventoryAdjustment,
                InventoryBalance,
                InventoryMovement,
                AuditLog,
                OutboxEvent,
            )
        )
    assert after == before
    response = client.post(
        "/v1/admin/inventory/adjustments", headers={**headers, "Idempotency-Key": key}, json=body
    )
    assert response.status_code == 201, response.text
    _assert_reconciled(InventoryBalanceKey(branch_id, product_id, "BACKROOM"), "2", 1)
