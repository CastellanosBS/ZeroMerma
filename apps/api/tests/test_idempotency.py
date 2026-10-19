"""PostgreSQL acceptance probes for the shared executor; no product route is adopted here."""

from __future__ import annotations

import json
import secrets
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier, Event
from typing import Annotated, Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.concurrency import CommandConcurrencyConflict
from zeromerma_api.db.session import SessionLocal, get_session
from zeromerma_api.main import create_app
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.idempotency.application.canonicalization import canonical_fingerprint
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import (
    DeterministicRejection,
    IdempotencyBoundaryError,
    IdempotencyInProgress,
    IdempotencyKeyReused,
    IdempotencyResultUnknown,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.idempotency.presentation.http import (
    IdempotencyRejectionSnapshot,
    idempotency_response,
    require_idempotency_key,
)
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.session_services import SessionAuthentication
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.presentation.dependencies import get_current_authentication
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.sessions import login_headers

PROBE_OPERATION = "validation.idempotency_probe"
PROBE_EVENT = "validation.idempotency_probe.completed"


class ProbePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(default=Decimal("12.30"), ge=0, max_digits=12, decimal_places=2)
    labels: list[str] = Field(default_factory=list)


class ProbeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    resource_id: UUID
    amount: Decimal
    state: str = "COMPLETED"


def new_key() -> UUID:
    """Generate test UUIDv7 values without introducing a runtime client dependency."""
    return UUID(
        int=(time.time_ns() // 1_000_000 << 80)
        | (7 << 76)
        | (secrets.randbits(12) << 64)
        | (2 << 62)
        | secrets.randbits(62)
    )


def context_for(workstation_code: str = SEED_WORKSTATION_CODE) -> CommandContext:
    with SessionLocal() as session:
        workstation = session.scalars(
            select(Workstation).where(Workstation.code == workstation_code)
        ).one()
        actor = session.scalars(select(User.id).where(User.email == SEED_USER_EMAIL)).one()
        return CommandContext(
            actor_user_id=actor,
            surface="POS",
            branch_id=workstation.branch_id,
            workstation_id=workstation.id,
        )


def authorize(session: Session, context: CommandContext) -> None:
    actor = session.get(User, context.actor_user_id)
    if actor is None or not actor.is_active or actor.is_locked:
        raise HTTPException(status_code=403, detail="The current actor is not authorized.")
    user = resolve_authorization(session, actor, surface=context.surface)
    require_branches(user, "pos.operate", [context.branch_id] if context.branch_id else [])


def create_effect(
    session: Session, context: CommandContext, payload: ProbePayload
) -> CommandResult:
    """Write distinct document, monetary movement, audit and outbox effects in one transaction."""
    now = datetime.now(UTC)
    document = CashSession(
        id=uuid4(),
        branch_id=context.branch_id,
        workstation_id=context.workstation_id,
        user_id=context.actor_user_id,
        opening_amount=payload.amount,
        status="CLOSED",
        opened_at=now,
        closed_at=now,
    )
    session.add(document)
    session.flush()
    session.add(
        CashMovement(
            cash_session_id=document.id,
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            operator_id=context.actor_user_id,
            movement_type="VALIDATION_PROBE",
            direction="IN",
            payment_method_code="CASH",
            amount=payload.amount,
        )
    )
    AuditRecorder().record(
        session,
        actor_id=context.actor_user_id,
        action=PROBE_EVENT,
        resource_type="cash_session",
        resource_id=str(document.id),
        branch_id=context.branch_id,
        request_id="probe-effect",
        metadata={"amount": str(payload.amount)},
    )
    OutboxWriter().append(
        session,
        aggregate_type="cash_session",
        aggregate_id=str(document.id),
        event_name=PROBE_EVENT,
        payload={"resource_id": str(document.id)},
    )
    session.flush()
    return CommandResult(
        status_code=201,
        snapshot=ProbeSnapshot(resource_id=document.id, amount=payload.amount),
        resource_type="cash_session",
        resource_id=str(document.id),
    )


def execute_probe(
    key: UUID,
    context: CommandContext,
    *,
    payload: ProbePayload | None = None,
    action: Callable[[Session], CommandResult] | None = None,
    authorization: Callable[[Session, CommandContext], None] = authorize,
    policy: ResponsePolicy | None = None,
    operation: str = PROBE_OPERATION,
    request_id: str = "first-request",
    lock_timeout_ms: int = 2000,
) -> IdempotencyResult:
    payload = payload or ProbePayload()
    with SessionLocal() as session:
        return IdempotencyExecutor(lock_timeout_ms=lock_timeout_ms).execute(
            session,
            key=key,
            operation_code=operation,
            payload=payload,
            resolve_context=lambda _session, _saved: context,
            authorize=authorization,
            action=action or (lambda current: create_effect(current, context, payload)),
            response_policy=policy or ResponsePolicy(snapshot_model=ProbeSnapshot),
            request_id=request_id,
        )


def assert_effects(count: int, *, records: int | None = None) -> None:
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashSession)) == count
        assert (
            session.scalar(
                select(func.count())
                .select_from(CashMovement)
                .where(CashMovement.movement_type == "VALIDATION_PROBE")
            )
            == count
        )
        assert (
            session.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == PROBE_EVENT)
            )
            == count
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.event_name == PROBE_EVENT)
            )
            == count
        )
        assert session.scalar(select(func.count()).select_from(IdempotencyRecord)) == (
            count if records is None else records
        )


def test_replay_recovers_committed_result_without_repeating_any_effect() -> None:
    context, key = context_for(), new_key()
    first = execute_probe(key, context)
    calls: list[str] = []

    def current_authorization(session: Session, value: CommandContext) -> None:
        calls.append("authorize")
        authorize(session, value)

    def forbidden_action(_session: Session) -> CommandResult:
        raise AssertionError("A replay must not execute domain logic.")

    replay = execute_probe(
        key,
        context,
        payload=ProbePayload(amount=Decimal("12.300")),
        action=forbidden_action,
        authorization=current_authorization,
        request_id="different-request-after-response-loss",
    )
    assert first.payload == replay.payload
    assert first.status_code == replay.status_code == 201
    assert first.record_id == replay.record_id
    assert not first.replayed and replay.replayed
    assert calls == ["authorize"]
    assert_effects(1)
    with SessionLocal() as session:
        row = session.get(IdempotencyRecord, first.record_id)
        assert row is not None and row.first_request_id == "first-request"
        assert row.status == "COMPLETED"


def test_replay_uses_saved_cash_context_after_close_but_new_command_requires_open_cash() -> None:
    context, key, fresh_key = context_for(), new_key(), new_key()
    historical_cash_id = uuid4()
    with SessionLocal() as session:
        session.add(
            CashSession(
                id=historical_cash_id,
                branch_id=context.branch_id,
                workstation_id=context.workstation_id,
                user_id=context.actor_user_id,
                opening_amount=Decimal("0.00"),
                status="OPEN",
                opened_at=datetime.now(UTC),
            )
        )
        session.commit()
    expected_context = context.model_copy(update={"cash_session_id": historical_cash_id})
    resolved_contexts: list[CommandContext | None] = []
    action_calls = 0

    def resolve_context(session: Session, saved: CommandContext | None) -> CommandContext:
        resolved_contexts.append(saved)
        if saved is not None:
            assert saved == expected_context
            return context.model_copy(update={"cash_session_id": saved.cash_session_id})
        cash_id = session.scalar(
            select(CashSession.id).where(
                CashSession.workstation_id == context.workstation_id,
                CashSession.user_id == context.actor_user_id,
                CashSession.status == "OPEN",
            )
        )
        if cash_id is None:
            raise HTTPException(status_code=409, detail="An open cash session is required.")
        return context.model_copy(update={"cash_session_id": cash_id})

    def action(session: Session) -> CommandResult:
        nonlocal action_calls
        action_calls += 1
        return create_effect(session, expected_context, ProbePayload())

    def submit(command_key: UUID) -> IdempotencyResult:
        with SessionLocal() as session:
            return IdempotencyExecutor().execute(
                session,
                key=command_key,
                operation_code=PROBE_OPERATION,
                payload=ProbePayload(),
                resolve_context=resolve_context,
                authorize=authorize,
                action=action,
                response_policy=ResponsePolicy(snapshot_model=ProbeSnapshot),
            )

    first = submit(key)
    with SessionLocal() as session:
        historical = session.get(CashSession, historical_cash_id)
        assert historical is not None
        historical.status = "CLOSED"
        historical.closed_at = datetime.now(UTC)
        session.commit()

    replay = submit(key)
    assert replay.replayed and replay.record_id == first.record_id
    assert replay.payload == first.payload
    assert resolved_contexts == [None, expected_context]
    with pytest.raises(HTTPException) as rejected:
        submit(fresh_key)
    assert rejected.value.status_code == 409
    assert rejected.value.detail == "An open cash session is required."
    assert resolved_contexts == [None, expected_context, None]
    assert action_calls == 1
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashSession)) == 2
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 1
        assert (
            session.scalar(
                select(func.count()).select_from(AuditLog).where(AuditLog.action == PROBE_EVENT)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.event_name == PROBE_EVENT)
            )
            == 1
        )
        assert session.scalar(select(func.count()).select_from(IdempotencyRecord)) == 1
        assert (
            session.scalar(
                select(IdempotencyRecord.id).where(IdempotencyRecord.idempotency_key == fresh_key)
            )
            is None
        )
        record = session.get(IdempotencyRecord, first.record_id)
        assert record is not None and record.cash_session_id == historical_cash_id


def test_executor_rejects_already_flushed_business_writes_without_adopting_transaction() -> None:
    context, key = context_for(), new_key()
    calls: list[str] = []

    def resolve_context(_session: Session, _saved: CommandContext | None) -> CommandContext:
        calls.append("resolve")
        return context

    def action(_session: Session) -> CommandResult:
        raise AssertionError("A command cannot adopt an existing business transaction.")

    with SessionLocal() as session:
        prior_effect = create_effect(session, context, ProbePayload())
        assert not session.new and not session.dirty and not session.deleted
        original_transaction = session.get_transaction()
        assert original_transaction is not None and original_transaction.is_active
        with pytest.raises(IdempotencyBoundaryError, match="before business writes"):
            IdempotencyExecutor().execute(
                session,
                key=key,
                operation_code=PROBE_OPERATION,
                payload=ProbePayload(),
                resolve_context=resolve_context,
                authorize=authorize,
                action=action,
                response_policy=ResponsePolicy(snapshot_model=ProbeSnapshot),
            )
        assert calls == []
        assert session.get_transaction() is original_transaction
        assert original_transaction.is_active
        assert prior_effect.resource_id is not None
        assert session.get(CashSession, UUID(prior_effect.resource_id)) is not None
        # A separate connection cannot see a commit, and no key has been reserved.
        assert_effects(0)
        session.rollback()
    assert_effects(0)


@pytest.mark.parametrize(
    "difference",
    ["payload", "operation", "actor", "branch", "station", "surface", "cash", "related"],
)
def test_global_key_reuse_rejects_incompatible_intention(difference: str) -> None:
    context, key = context_for(), new_key()
    first = execute_probe(key, context)
    kwargs: dict[str, Any] = {}
    if difference == "payload":
        kwargs["payload"] = ProbePayload(amount=Decimal("13.00"))
    elif difference == "operation":
        kwargs["operation"] = "validation.another_operation"
    elif difference == "actor":
        with SessionLocal() as session:
            actor = session.scalars(select(User.id).where(User.email == SEED_ADMIN_EMAIL)).one()
        context = context.model_copy(update={"actor_user_id": actor})
    elif difference == "branch":
        context = context.model_copy(
            update={"branch_id": context_for(SEED_DESTINATION_WORKSTATION_CODE).branch_id}
        )
    elif difference == "station":
        context = context.model_copy(
            update={"workstation_id": context_for(SEED_DESTINATION_WORKSTATION_CODE).workstation_id}
        )
    elif difference == "cash":
        context = context.model_copy(update={"cash_session_id": UUID(first.payload["resource_id"])})
    elif difference == "related":
        context = context.model_copy(
            update={
                "related_branch_ids": (context_for(SEED_DESTINATION_WORKSTATION_CODE).branch_id,)
            }
        )
    else:
        context = context.model_copy(update={"surface": "BACKOFFICE"})
    with pytest.raises(IdempotencyKeyReused):
        execute_probe(key, context, **kwargs)
    assert_effects(1)


def test_concurrent_same_key_executes_once() -> None:
    context, key = context_for(), new_key()
    barrier = Barrier(4)

    def submit(_index: int) -> IdempotencyResult:
        barrier.wait(timeout=10)
        return execute_probe(key, context)

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(submit, range(4)))
    assert len({result.record_id for result in results}) == 1
    assert sum(not result.replayed for result in results) == 1
    assert all(result.payload == results[0].payload for result in results)
    assert_effects(1)


@pytest.mark.parametrize("separate_branches", [False, True])
def test_distinct_keys_enter_domain_concurrently_without_global_lock(
    separate_branches: bool,
) -> None:
    contexts = [
        context_for(),
        context_for(
            SEED_DESTINATION_WORKSTATION_CODE if separate_branches else SEED_WORKSTATION_CODE
        ),
    ]
    barrier = Barrier(2)

    def submit(context: CommandContext) -> IdempotencyResult:
        def action(session: Session) -> CommandResult:
            barrier.wait(timeout=10)
            return create_effect(session, context, ProbePayload())

        return execute_probe(new_key(), context, action=action)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, contexts))
    assert all(not result.replayed for result in results)
    assert_effects(2)


def test_contention_is_bounded_and_retry_recovers_winner() -> None:
    context, key = context_for(), new_key()
    admitted, release = Event(), Event()

    def blocked_action(session: Session) -> CommandResult:
        admitted.set()
        assert release.wait(timeout=10)
        return create_effect(session, context, ProbePayload())

    with ThreadPoolExecutor(max_workers=1) as pool:
        first = pool.submit(execute_probe, key, context, action=blocked_action)
        try:
            assert admitted.wait(timeout=10)
            started = time.monotonic()
            with pytest.raises(IdempotencyInProgress):
                execute_probe(key, context, lock_timeout_ms=50)
            assert time.monotonic() - started < 5
        finally:
            release.set()
        winner = first.result(timeout=10)
    replay = execute_probe(key, context)
    assert replay.replayed and replay.payload == winner.payload
    assert_effects(1)


@pytest.mark.parametrize("failure", [RuntimeError("simulated disconnect"), HTTPException(500)])
def test_failure_before_commit_rolls_back_all_effects_and_allows_retry(failure: Exception) -> None:
    context, key = context_for(), new_key()

    def action(session: Session) -> CommandResult:
        create_effect(session, context, ProbePayload())
        raise failure

    with pytest.raises(type(failure)):
        execute_probe(key, context, action=action)
    assert_effects(0)
    assert not execute_probe(key, context).replayed
    assert_effects(1)


def test_rejected_command_rolls_back_domain_and_replays_terminal_rejection() -> None:
    context, key = context_for(), new_key()
    policy = ResponsePolicy(
        snapshot_model=ProbeSnapshot, rejection_model=IdempotencyRejectionSnapshot
    )

    def rejected(session: Session) -> CommandResult:
        create_effect(session, context, ProbePayload())
        raise DeterministicRejection(
            code="PROBE_REJECTED",
            status_code=409,
            message="The requested state is unavailable.",
            snapshot=IdempotencyRejectionSnapshot(
                code="PROBE_REJECTED",
                message="The requested state is unavailable.",
                details={"state": "CLOSED"},
            ),
        )

    first = execute_probe(key, context, action=rejected, policy=policy)
    replay = execute_probe(key, context, policy=policy)
    assert first.status == replay.status == "REJECTED"
    assert first.status_code == replay.status_code == 409
    assert first.payload == replay.payload and replay.replayed
    assert_effects(0, records=1)


@pytest.mark.parametrize("status_code", [401, 403])
def test_authorization_failure_does_not_consume_key(status_code: int) -> None:
    context, key = context_for(), new_key()

    def deny(_session: Session, _context: CommandContext) -> None:
        raise HTTPException(status_code=status_code)

    with pytest.raises(HTTPException) as rejected:
        execute_probe(key, context, authorization=deny)
    assert rejected.value.status_code == status_code
    assert_effects(0)
    execute_probe(key, context)
    assert_effects(1)


def test_lost_permission_prevents_replay_without_destroying_result() -> None:
    context, key = context_for(), new_key()
    execute_probe(key, context)
    with SessionLocal() as session:
        actor = session.get(User, context.actor_user_id)
        assert actor is not None
        actor.is_active = False
        session.commit()
    with pytest.raises(HTTPException) as rejected:
        execute_probe(key, context)
    assert rejected.value.status_code == 403
    assert_effects(1)


@pytest.mark.parametrize("method", ["commit", "rollback"])
def test_domain_cannot_own_the_transaction_boundary(method: str) -> None:
    context, key = context_for(), new_key()

    def action(session: Session) -> CommandResult:
        result = create_effect(session, context, ProbePayload())
        getattr(session, method)()
        return result

    with pytest.raises(IdempotencyBoundaryError):
        execute_probe(key, context, action=action)
    assert_effects(0)


def test_executor_restores_command_timeout_after_key_reservation() -> None:
    context = context_for()
    observed: list[str] = []
    with SessionLocal() as session:
        session.execute(text("SET LOCAL lock_timeout = '7s'"))

        def action(current: Session) -> CommandResult:
            observed.append(str(current.scalar(text("SHOW lock_timeout"))))
            return create_effect(current, context, ProbePayload())

        IdempotencyExecutor(lock_timeout_ms=50).execute(
            session,
            key=new_key(),
            operation_code=PROBE_OPERATION,
            payload=ProbePayload(),
            resolve_context=lambda _session, _saved: context,
            authorize=authorize,
            action=action,
            response_policy=ResponsePolicy(snapshot_model=ProbeSnapshot),
        )
    # The key reservation restores the business command budget before the action.
    assert observed == ["5s"]


def test_persisted_record_contains_no_original_payload_or_session_credential() -> None:
    context, key = context_for(), new_key()
    execute_probe(key, context, payload=ProbePayload(labels=["request-only-marker-0192"]))
    with SessionLocal() as session:
        row = session.execute(text("SELECT row_to_json(r) FROM idempotency_records r")).scalar_one()
    stored = json.dumps(row, default=str)
    assert "request-only-marker-0192" not in stored
    assert "credential" not in stored and "password" not in stored
    assert "request_fingerprint" in row


def test_replay_benchmark_records_baseline_without_imposing_an_invented_sla(
    record_testsuite_property: Any,
) -> None:
    context = context_for()
    started = time.perf_counter()
    key = new_key()
    execute_probe(key, context)
    miss_ms = (time.perf_counter() - started) * 1000
    samples = []
    for _ in range(8):
        started = time.perf_counter()
        assert execute_probe(key, context).replayed
        samples.append((time.perf_counter() - started) * 1000)
    record_testsuite_property("idempotency_miss_ms", round(miss_ms, 3))
    record_testsuite_property("idempotency_replay_mean_ms", round(sum(samples) / len(samples), 3))
    assert_effects(1)


@pytest.fixture
def probe_client() -> Any:
    app = create_app()

    @app.post("/__validation/idempotency")
    def probe_command(
        payload: ProbePayload,
        request: Request,
        session: Annotated[Session, Depends(get_session)],
        authentication: Annotated[SessionAuthentication, Depends(get_current_authentication)],
        key: Annotated[UUID, Depends(require_idempotency_key)],
    ) -> JSONResponse:
        user = authentication.user
        workstation_id = authentication.record.workstation_id
        assert workstation_id is not None
        workstation = session.get(Workstation, workstation_id)
        assert workstation is not None
        context = CommandContext(
            actor_user_id=user.id,
            surface="POS",
            branch_id=workstation.branch_id,
            workstation_id=workstation_id,
        )
        bind_authorization_scope(
            session, user=user, capabilities=("pos.operate",), mutation=True, surface="POS"
        )

        def action(current: Session) -> CommandResult:
            result = create_effect(current, context, payload)
            if payload.labels == ["reject"]:
                raise DeterministicRejection(
                    code="PROBE_REJECTED",
                    status_code=409,
                    message="The command was rejected.",
                    snapshot=IdempotencyRejectionSnapshot(
                        code="PROBE_REJECTED", message="The command was rejected."
                    ),
                )
            return result

        result = IdempotencyExecutor().execute(
            session,
            key=key,
            operation_code=PROBE_OPERATION,
            payload=payload,
            resolve_context=lambda _session, _saved: context,
            authorize=authorize,
            action=action,
            request_id=request.headers.get("X-Request-ID"),
            response_policy=ResponsePolicy(
                snapshot_model=ProbeSnapshot, rejection_model=IdempotencyRejectionSnapshot
            ),
        )
        if payload.labels == ["lose-response"] and not result.replayed:
            raise RuntimeError("Injected response loss after successful commit.")
        return idempotency_response(result, request)

    with TestClient(app, base_url="https://testserver") as client:
        yield client


def probe_headers(client: TestClient, key: UUID | str) -> dict[str, str]:
    return {
        **login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD),
        "Idempotency-Key": str(key),
        "X-Request-ID": "first-http-request",
    }


def test_http_replay_conflict_and_current_correlation(probe_client: TestClient) -> None:
    headers = probe_headers(probe_client, new_key())
    first = probe_client.post(
        "/__validation/idempotency", headers=headers, json={"amount": "12.30"}
    )
    assert first.status_code == 201, first.text
    assert first.headers["Idempotency-Replayed"] == "false"
    replay = probe_client.post(
        "/__validation/idempotency",
        headers={**headers, "X-Request-ID": "retry-http-request"},
        json={"amount": "12.300", "labels": []},
    )
    assert replay.status_code == 201, replay.text
    assert replay.json() == first.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    mismatch = probe_client.post(
        "/__validation/idempotency", headers=headers, json={"amount": "14.00"}
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert mismatch.json()["request_id"] == "first-http-request"
    assert_effects(1)


@pytest.mark.parametrize("invalid", [None, "", str(uuid4()), "x" * 1000, "bad-key"])
def test_http_invalid_keys_are_rejected_before_admission(
    probe_client: TestClient, invalid: str | None
) -> None:
    headers = probe_headers(probe_client, invalid or "")
    if invalid is None:
        headers.pop("Idempotency-Key")
    response = probe_client.post("/__validation/idempotency", headers=headers, json={})
    assert response.status_code == 422
    assert_effects(0)


def test_http_duplicate_header_and_unauthenticated_request_do_not_consume_key(
    probe_client: TestClient,
) -> None:
    key = new_key()
    headers = probe_headers(probe_client, key)
    response = probe_client.post(
        "/__validation/idempotency",
        headers=[*headers.items(), ("Idempotency-Key", str(new_key()))],
        json={},
    )
    assert response.status_code == 422
    anonymous = probe_client.post(
        "/__validation/idempotency",
        json={},
        headers={
            "Idempotency-Key": str(key),
            "X-ZeroMerma-Surface": "POS",
            "Origin": headers["Origin"],
        },
    )
    assert anonymous.status_code == 401
    assert_effects(0)


def test_http_schema_failure_leaves_key_available(probe_client: TestClient) -> None:
    headers = probe_headers(probe_client, new_key())
    invalid = probe_client.post("/__validation/idempotency", headers=headers, json={"amount": "-1"})
    assert invalid.status_code == 422
    assert_effects(0)
    valid = probe_client.post("/__validation/idempotency", headers=headers, json={})
    assert valid.status_code == 201, valid.text
    assert_effects(1)


def test_http_rejection_replay_uses_current_request_id(probe_client: TestClient) -> None:
    headers = probe_headers(probe_client, new_key())
    first = probe_client.post(
        "/__validation/idempotency", headers=headers, json={"labels": ["reject"]}
    )
    assert first.status_code == 409, first.text
    assert first.json()["code"] == "PROBE_REJECTED"
    replay = probe_client.post(
        "/__validation/idempotency",
        headers={**headers, "X-Request-ID": "rejected-retry"},
        json={"labels": ["reject"]},
    )
    assert replay.status_code == 409
    assert replay.json() == {**first.json(), "request_id": "rejected-retry"}
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert_effects(0, records=1)


def test_http_result_survives_new_login_and_revocation_denies_old_session(
    probe_client: TestClient,
) -> None:
    key = new_key()
    old_headers = probe_headers(probe_client, key)
    first = probe_client.post("/__validation/idempotency", headers=old_headers, json={})
    assert first.status_code == 201, first.text
    new_headers = probe_headers(probe_client, key)
    stale = probe_client.post("/__validation/idempotency", headers=old_headers, json={})
    assert stale.status_code == 401
    replay = probe_client.post("/__validation/idempotency", headers=new_headers, json={})
    assert replay.status_code == 201, replay.text
    assert replay.json() == first.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert_effects(1)


def test_response_loss_after_commit_is_recovered_by_http_retry(probe_client: TestClient) -> None:
    headers = probe_headers(probe_client, new_key())
    with pytest.raises(RuntimeError, match="Injected response loss"):
        probe_client.post(
            "/__validation/idempotency", headers=headers, json={"labels": ["lose-response"]}
        )
    assert_effects(1)
    recovered = probe_client.post(
        "/__validation/idempotency", headers=headers, json={"labels": ["lose-response"]}
    )
    assert recovered.status_code == 201
    assert recovered.headers["Idempotency-Replayed"] == "true"
    assert_effects(1)


def test_actual_postgres_connection_loss_before_commit_rolls_back_every_effect() -> None:
    context, key = context_for(), new_key()

    def interrupted(session: Session) -> CommandResult:
        outcome = create_effect(session, context, ProbePayload())
        backend_pid = session.scalar(select(func.pg_backend_pid()))
        with SessionLocal() as controller:
            assert controller.scalar(select(func.pg_terminate_backend(backend_pid))) is True
        session.execute(select(1))
        return outcome

    with pytest.raises(DBAPIError):
        execute_probe(key, context, action=interrupted)
    assert_effects(0)
    assert not execute_probe(key, context).replayed
    assert_effects(1)


@pytest.mark.parametrize("sqlstate", ["40001", "40P01"])
def test_postgres_transient_failure_after_writes_releases_the_key(sqlstate: str) -> None:
    context, key = context_for(), new_key()

    def interrupted(session: Session) -> CommandResult:
        outcome = create_effect(session, context, ProbePayload())
        # Fixed test-only SQLSTATE values inject PostgreSQL transaction failures.
        statement = {
            "40001": "DO $$ BEGIN RAISE EXCEPTION 'injected' USING ERRCODE='40001'; END $$",
            "40P01": "DO $$ BEGIN RAISE EXCEPTION 'injected' USING ERRCODE='40P01'; END $$",
        }
        session.execute(text(statement[sqlstate]))
        return outcome

    with pytest.raises(CommandConcurrencyConflict) as failure:
        execute_probe(key, context, action=interrupted)
    assert isinstance(failure.value.__cause__, DBAPIError)
    assert failure.value.__cause__.orig.sqlstate == sqlstate
    assert_effects(0)
    execute_probe(key, context)
    assert_effects(1)


def test_authorization_callback_cannot_commit_after_domain_effects() -> None:
    context, key = context_for(), new_key()
    calls = 0

    def malicious_authorize(session: Session, value: CommandContext) -> None:
        nonlocal calls
        calls += 1
        authorize(session, value)
        if calls == 2:
            session.commit()
            raise AssertionError("The callback was allowed to commit.")

    with pytest.raises(IdempotencyBoundaryError):
        execute_probe(key, context, authorization=malicious_authorize)
    assert calls == 2
    assert_effects(0)


def test_unknown_external_outcome_never_reexecutes_the_action() -> None:
    context, key = context_for(), new_key()
    with SessionLocal() as session:
        session.add(
            IdempotencyRecord(
                idempotency_key=key,
                operation_code=PROBE_OPERATION,
                fingerprint_version=1,
                request_fingerprint=canonical_fingerprint(
                    operation_code=PROBE_OPERATION, context=context, payload=ProbePayload()
                ),
                actor_user_id=context.actor_user_id,
                branch_id=context.branch_id,
                workstation_id=context.workstation_id,
                cash_session_id=None,
                context_data={"surface": context.surface, "related_branch_ids": []},
                status="UNKNOWN",
            )
        )
        session.commit()
    with pytest.raises(IdempotencyResultUnknown):
        execute_probe(key, context)
    assert_effects(0, records=1)


def _retained_result() -> tuple[UUID, CommandContext, IdempotencyResult, ResponsePolicy]:
    context, key = context_for(), new_key()

    def restore(_session: Session, reference: BaseModel) -> BaseModel:
        return ProbeSnapshot.model_validate(reference.model_dump())

    policy = ResponsePolicy(
        snapshot_model=ProbeSnapshot,
        reference_model=ProbeSnapshot,
        restore=restore,
        payload_retention=timedelta(minutes=30),
    )

    def action(session: Session) -> CommandResult:
        outcome = create_effect(session, context, ProbePayload())
        return CommandResult(
            outcome.status_code,
            outcome.snapshot,
            outcome.resource_type,
            outcome.resource_id,
            reference=outcome.snapshot,
        )

    with SessionLocal() as session:
        historical = session.scalar(select(func.clock_timestamp())) - timedelta(days=1)
    with patch(
        "zeromerma_api.modules.idempotency.application.service.datetime", wraps=datetime
    ) as clock:
        clock.now.return_value = historical
        result = execute_probe(key, context, action=action, policy=policy)
    return key, context, result, policy


def test_expired_payload_cleanup_preserves_identity_and_exact_replay() -> None:
    key, context, first, policy = _retained_result()
    with SessionLocal() as session:
        assert (
            IdempotencyExecutor().purge_expired_payloads(
                session, operation_code=PROBE_OPERATION, response_policy=policy
            )
            == 1
        )
    with SessionLocal() as session:
        row = session.get(IdempotencyRecord, first.record_id)
        assert row is not None and row.response_payload is None
        assert row.response_reference is not None and row.response_fingerprint is not None
    replay = execute_probe(key, context, policy=policy)
    assert replay.replayed and replay.payload == first.payload
    with pytest.raises(IdempotencyKeyReused):
        execute_probe(key, context, payload=ProbePayload(amount=Decimal("99.00")), policy=policy)
    assert_effects(1)


@pytest.mark.parametrize("attempt", ["write", "text_write", "commit", "changed_result"])
def test_cleanup_resolver_cannot_mutate_commit_or_change_result(attempt: str) -> None:
    _key, context, result, policy = _retained_result()

    def bad_restore(session: Session, reference: BaseModel) -> BaseModel:
        if attempt == "write":
            actor = session.get(User, context.actor_user_id)
            assert actor is not None
            actor.is_active = False
            session.flush()
        elif attempt == "text_write":
            session.execute(
                text("UPDATE users SET is_active=false WHERE id=:actor"),
                {"actor": context.actor_user_id},
            )
        elif attempt == "commit":
            session.commit()
        else:
            return ProbeSnapshot(resource_id=uuid4(), amount=Decimal("99.00"))
        return reference

    bad_policy = ResponsePolicy(
        snapshot_model=ProbeSnapshot,
        reference_model=ProbeSnapshot,
        restore=bad_restore,
        payload_retention=policy.payload_retention,
    )
    with SessionLocal() as session, pytest.raises(IdempotencyBoundaryError):
        IdempotencyExecutor().purge_expired_payloads(
            session, operation_code=PROBE_OPERATION, response_policy=bad_policy
        )
    with SessionLocal() as session:
        assert session.get(User, context.actor_user_id).is_active
        assert session.get(IdempotencyRecord, result.record_id).response_payload is not None
    assert_effects(1)


def test_replay_rejects_changed_reference_result_after_payload_purge() -> None:
    key, context, _first, policy = _retained_result()
    with SessionLocal() as session:
        IdempotencyExecutor().purge_expired_payloads(
            session, operation_code=PROBE_OPERATION, response_policy=policy
        )
    changed_policy = ResponsePolicy(
        snapshot_model=ProbeSnapshot,
        reference_model=ProbeSnapshot,
        restore=lambda _session, _reference: ProbeSnapshot(
            resource_id=uuid4(), amount=Decimal("99")
        ),
        payload_retention=policy.payload_retention,
    )
    with pytest.raises(IdempotencyBoundaryError):
        execute_probe(key, context, policy=changed_policy)
    assert_effects(1)


def test_sensitive_response_failure_rolls_back_the_entire_command() -> None:
    class UnsafeSnapshot(BaseModel):
        model_config = ConfigDict(extra="forbid")
        password: str

    context, key = context_for(), new_key()

    def unsafe(session: Session) -> CommandResult:
        create_effect(session, context, ProbePayload())
        return CommandResult(201, UnsafeSnapshot(password="never-persist-this-value"))

    with pytest.raises(IdempotencyBoundaryError):
        execute_probe(
            key, context, action=unsafe, policy=ResponsePolicy(snapshot_model=UnsafeSnapshot)
        )
    assert_effects(0)
