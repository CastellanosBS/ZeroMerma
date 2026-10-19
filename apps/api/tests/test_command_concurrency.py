"""Real PostgreSQL conflicts roll back the entire command and retain retry identity."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Barrier
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.errors import DeadlockDetected, SerializationFailure, UniqueViolation
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session
from test_idempotency import (
    PROBE_OPERATION,
    ProbePayload,
    ProbeSnapshot,
    assert_effects,
    authorize,
    context_for,
    create_effect,
    execute_probe,
    new_key,
)

from zeromerma_api.db.concurrency import (
    CommandConcurrencyConflict,
    is_retryable_transaction_error,
)
from zeromerma_api.db.session import SessionLocal, engine
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.presentation.errors import install_error_handlers
from zeromerma_api.presentation.operation_context import OperationContextMiddleware
from zeromerma_api.testing.concurrency import (
    TransactionProbe,
    transaction_probe,
    wait_until_blocked,
)


def _execute(
    key: UUID,
    context: CommandContext,
    action: Callable[[Session], CommandResult],
    *,
    timeout_ms: int = 5000,
) -> IdempotencyResult:
    with SessionLocal() as session:
        return IdempotencyExecutor(command_lock_timeout_ms=timeout_ms).execute(
            session,
            key=key,
            operation_code=PROBE_OPERATION,
            payload=ProbePayload(),
            resolve_context=lambda _session, _saved: context,
            authorize=authorize,
            action=action,
            response_policy=ResponsePolicy(snapshot_model=ProbeSnapshot),
        )


def _product_ids() -> list[UUID]:
    with SessionLocal() as session:
        return list(session.scalars(select(Product.id).order_by(Product.id).limit(2)))


def _lock_product(session: Session, product_id: UUID) -> None:
    session.scalars(select(Product).where(Product.id == product_id).with_for_update()).one()


def test_real_lock_timeout_rolls_back_all_effects_and_retries_the_same_key() -> None:
    context, key = context_for(), new_key()
    product_id = _product_ids()[0]
    waiter: Queue[TransactionProbe] = Queue()

    def action(session: Session) -> CommandResult:
        result = create_effect(session, context, ProbePayload())
        waiter.put(transaction_probe(session))
        _lock_product(session, product_id)
        return result

    with SessionLocal() as blocking, ThreadPoolExecutor(max_workers=1) as pool:
        _lock_product(blocking, product_id)
        holder = transaction_probe(blocking)
        future = pool.submit(_execute, key, context, action, timeout_ms=2000)
        try:
            waiting = waiter.get(timeout=10)
            assert waiting.backend_pid != holder.backend_pid
            assert waiting.transaction_id != holder.transaction_id
            wait_until_blocked(waiting.backend_pid, holder.backend_pid)
            with pytest.raises(CommandConcurrencyConflict) as caught:
                future.result(timeout=10)
            assert isinstance(caught.value.__cause__, DBAPIError)
            assert caught.value.__cause__.orig.sqlstate == "55P03"
            assert_effects(0)
        finally:
            blocking.rollback()
    first = execute_probe(key, context)
    replay = execute_probe(key, context)
    assert first.payload == replay.payload
    assert replay.replayed
    assert_effects(1)


def test_real_deadlock_rolls_back_victim_and_same_intention_succeeds_after_retry() -> None:
    context = context_for()
    products = _product_ids()
    assert len(products) == 2
    keys = [new_key(), new_key()]
    first_locks = Barrier(2, timeout=10)
    probes: Queue[TransactionProbe] = Queue()

    def run(index: int) -> IdempotencyResult:
        def action(session: Session) -> CommandResult:
            # Product rows are independent of the probe's document/money foreign keys.
            # Reverse acquisition deliberately creates a real PostgreSQL deadlock.
            _lock_product(session, products[index])
            result = create_effect(session, context, ProbePayload())
            probes.put(transaction_probe(session))
            first_locks.wait()
            _lock_product(session, products[1 - index])
            return result

        return _execute(keys[index], context, action)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, index) for index in range(2)]
        observed = [probes.get(timeout=15), probes.get(timeout=15)]
        assert len({probe.backend_pid for probe in observed}) == 2
        assert len({probe.transaction_id for probe in observed}) == 2
        victims = []
        for index, future in enumerate(futures):
            try:
                assert future.result(timeout=15).status_code == 201
            except CommandConcurrencyConflict as error:
                assert isinstance(error.__cause__, DBAPIError)
                assert error.__cause__.orig.sqlstate == "40P01"
                victims.append(index)
    assert len(victims) == 1
    assert_effects(1)
    retried = execute_probe(keys[victims[0]], context)
    assert not retried.replayed
    for key in keys:
        assert execute_probe(key, context).replayed
    assert_effects(2)


def test_command_restores_prior_transaction_timeout_after_success_and_replay() -> None:
    context, key = context_for(), new_key()
    seen: list[str] = []
    with engine.connect() as connection, SessionLocal(bind=connection) as session:
        # A session setting makes leakage observable on this same pooled connection.
        previous = str(session.scalar(select(func.current_setting("lock_timeout"))))
        session.execute(select(func.set_config("lock_timeout", "7s", False)))
        session.commit()
        try:
            for _ in range(2):
                session.execute(select(func.set_config("lock_timeout", "9s", True)))

                def action(current: Session) -> CommandResult:
                    seen.append(str(current.scalar(select(func.current_setting("lock_timeout")))))
                    return create_effect(current, context, ProbePayload())

                IdempotencyExecutor(command_lock_timeout_ms=1234).execute(
                    session,
                    key=key,
                    operation_code=PROBE_OPERATION,
                    payload=ProbePayload(),
                    resolve_context=lambda _session, _saved: context,
                    authorize=authorize,
                    action=action,
                    response_policy=ResponsePolicy(snapshot_model=ProbeSnapshot),
                )
                assert session.scalar(select(func.current_setting("lock_timeout"))) == "7s"
                session.rollback()
        finally:
            session.execute(select(func.set_config("lock_timeout", previous, False)))
            session.commit()
    assert seen == ["1234ms"]
    assert_effects(1)


@pytest.mark.parametrize("error_type", [DeadlockDetected, SerializationFailure])
def test_only_known_transaction_abort_codes_are_retryable(error_type: type[Exception]) -> None:
    error = DBAPIError("private statement", {}, error_type("private parameters"), False)
    assert is_retryable_transaction_error(error)
    assert not is_retryable_transaction_error(error.orig)
    assert not is_retryable_transaction_error(DBAPIError("", {}, UniqueViolation(), False))
    assert not is_retryable_transaction_error(RuntimeError("deadlock-like application error"))


def test_retryable_http_conflict_uses_canonical_safe_error_contract() -> None:
    app = FastAPI()
    install_error_handlers(app)
    app.add_middleware(OperationContextMiddleware)

    @app.get("/conflict")
    def conflict() -> None:
        raise CommandConcurrencyConflict() from RuntimeError("private SQL and parameters")

    with TestClient(app) as client:
        response = client.get(
            "/conflict", headers={"X-Request-ID": "e1232bb2-ae23-55d0-94ce-159ce7c484e1"}
        )
    assert response.status_code == 409
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Retry-After"] == "1"
    assert response.json() == {
        "code": "CONCURRENCY_RETRY",
        "message": CommandConcurrencyConflict.message,
        "details": {"retryable": True},
        "request_id": "e1232bb2-ae23-55d0-94ce-159ce7c484e1",
        "field_errors": None,
    }
    assert "private" not in response.text


@pytest.mark.parametrize("timeout_ms", [0, -1, 60001])
def test_command_timeout_must_be_bounded(timeout_ms: int) -> None:
    with pytest.raises(ValueError, match="command lock timeout"):
        IdempotencyExecutor(command_lock_timeout_ms=timeout_ms)
