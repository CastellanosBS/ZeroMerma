"""Cash command acceptance against guarded, disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from decimal import Decimal
from http.cookies import SimpleCookie
from importlib import import_module
from statistics import median
from threading import Barrier, Event
from time import monotonic, perf_counter
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash.domain.exceptions import CashSessionConflictError
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.infrastructure.models import (
    BranchCounterSnapshot,
    BranchCounterSnapshotLine,
    CashSessionClose,
    CashSessionCloseClassReconciliation,
    CashSessionCloseDiscrepancyResolution,
    CashSessionClosePaymentMethodCount,
    CashSessionCloseProductCount,
    CashSessionCloseReconciliationAttribution,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.discounts.infrastructure.models import OperationalDiscount
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.schemas import IdempotencyResult
from zeromerma_api.modules.idempotency.domain.exceptions import (
    IdempotencyError,
    IdempotencyInProgress,
    IdempotencyResultUnknown,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    COOKIE_NAMES,
    SessionAuthentication,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.payments.infrastructure.models import OperationalPayment
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers

COMMANDS = {
    "open": ("cash", "/v1/cash-sessions", "/open", "cash_session.open", 201),
    "payment": ("payments", "/v1/payments", "", "operational_payment.commit", 201),
    "discount": ("discounts", "/v1/discounts", "", "operational_discount.commit", 201),
    "close": ("cash_close", "/v1/cash-close", "/commit", "cash_session.close", 200),
}
EVENTS = {
    "open": "cash.session.opened.v1",
    "payment": "operational_payment.committed.v1",
    "discount": "operational_discount.committed.v1",
    "close": "cash_session.closed.v1",
}


def _login(client: TestClient, workstation: str = SEED_WORKSTATION_CODE) -> dict[str, str]:
    return login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )


def _body(kind: str, cash_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"workstation_code": SEED_WORKSTATION_CODE}
    if kind == "open":
        return {**body, "opening_amount": "0.00"}
    body["cash_session_id"] = cash_id
    if kind == "close":
        return {
            **body,
            "close_mode": "WITH_COUNT",
            "counter_empty_confirmed": True,
            "counted_payment_methods": [{"payment_method_code": "CASH", "counted_amount": "0"}],
            "notes": "Private closing instructions",
        }
    return {
        **body,
        "payee_name" if kind == "payment" else "subject_name": "Private counterpart",
        "concept": "Private operational concept",
        "payment_method_code": "CASH",
        "total_amount": "10.00",
        "notes": "Private movement instructions",
    }


def _post(
    client: TestClient, kind: str, headers: dict[str, str], body: dict[str, Any], key: str
) -> Any:
    _, prefix, suffix, _, _ = COMMANDS[kind]
    return client.post(prefix + suffix, headers={**headers, "Idempotency-Key": key}, json=body)


def _recover(
    client: TestClient, kind: str, headers: dict[str, str], body: dict[str, Any], key: str
) -> Any:
    return client.get(
        f"{COMMANDS[kind][1]}/confirmations/{key}",
        headers=headers,
        params={
            name: body[name] for name in ("workstation_code", "cash_session_id") if name in body
        },
    )


def _setup(client: TestClient, kind: str) -> tuple[dict[str, str], dict[str, Any]]:
    headers = _login(client)
    if kind == "open":
        # Test cleanup truncates the singleton created by migration 0040. Restore
        # it before competing commands so its initialization cannot mask cash locks.
        with SessionLocal() as session:
            user = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
            bind_authorization_scope(
                session,
                user=resolve_authorization(session, user, surface="POS"),
                capabilities=("pos.operate",),
                mutation=True,
                surface="POS",
            )
            session.commit()
        return headers, _body(kind)
    opened = _post(
        client,
        "open",
        headers,
        {**_body("open"), "opening_amount": "100.00"},
        new_idempotency_key(),
    )
    assert opened.status_code == 201
    return headers, _body(kind, opened.json()["id"])


def _state() -> dict[str, Any]:
    with SessionLocal() as session:
        state = {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (
                CashSession,
                CashSessionClose,
                CashSessionClosePaymentMethodCount,
                CashSessionCloseProductCount,
                CashSessionCloseClassReconciliation,
                CashSessionCloseReconciliationAttribution,
                CashSessionCloseDiscrepancyResolution,
                BranchCounterSnapshot,
                BranchCounterSnapshotLine,
                OperationalPayment,
                OperationalDiscount,
                CashMovement,
                FinancialOperation,
                FinancialEntry,
                IdempotencyRecord,
            )
        }
        state["outbox_events"] = session.scalar(
            select(func.count())
            .select_from(OutboxEvent)
            .where(
                OutboxEvent.aggregate_type.in_(
                    [
                        "cash_session",
                        "cash_session_close",
                        "operational_payment",
                        "operational_discount",
                    ]
                )
            )
        )
        state["audit_log"] = session.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(
                AuditLog.action.in_(
                    [
                        "cash_session.opened",
                        "cash_close.committed",
                        "operational_payment.committed",
                        "operational_discount.committed",
                        "operational_discount.high_value_alert_requested",
                    ]
                )
            )
        )
        state["sessions"] = session.execute(
            select(CashSession.id, CashSession.status, CashSession.closed_at).order_by(
                CashSession.id
            )
        ).all()
        state["movements"] = session.execute(
            select(
                CashMovement.id,
                CashMovement.cash_session_id,
                CashMovement.amount,
                CashMovement.direction,
            ).order_by(CashMovement.id)
        ).all()
        state["financial_facts"] = session.execute(
            select(
                FinancialEntry.id,
                FinancialEntry.financial_operation_id,
                FinancialEntry.cash_session_id,
                FinancialEntry.payment_method_code,
                FinancialEntry.direction,
                FinancialEntry.amount,
                FinancialEntry.state,
            ).order_by(FinancialEntry.id)
        ).all()
        state["operational_financial_entries"] = session.scalar(
            select(func.count())
            .select_from(FinancialEntry)
            .join(
                FinancialOperation,
                FinancialOperation.id == FinancialEntry.financial_operation_id,
            )
            .where(FinancialOperation.kind.in_(("OPERATIONAL_PAYMENT", "OPERATIONAL_CHARGE")))
        )
        return state


@pytest.mark.parametrize("kind", COMMANDS)
def test_cash_replay_and_recovery_preserve_exact_result_and_all_effects(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    original = _post(client, kind, headers, body, key)
    assert original.status_code == COMMANDS[kind][4]
    if kind == "close":
        headers = _login(client)
    before = _state()
    replay = _post(
        client, kind, {**headers, "X-Request-ID": "69c557b2-ba73-5788-ae47-6c728571a809"}, body, key
    )
    recovered = _recover(client, kind, headers, body, key)
    assert replay.status_code == original.status_code and recovered.status_code == 200
    assert replay.json() == recovered.json() == original.json()
    assert original.headers["Idempotency-Replayed"] == "false"
    assert (
        replay.headers["Idempotency-Replayed"]
        == recovered.headers["Idempotency-Replayed"]
        == "true"
    )
    assert recovered.headers["Cache-Control"] == "no-store"
    assert _state() == before
    snapshot = original.json()
    assert (
        not {
            "notes",
            "payee_name",
            "subject_name",
            "concept",
            "user_email",
            "user_full_name",
            "created_by",
            "audit_summary",
        }
        & snapshot.keys()
    )
    with SessionLocal() as session:
        record = session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        )
        assert record.response_payload == snapshot and record.status == "COMPLETED"
        assert record.operation_code == COMMANDS[kind][3]
        assert record.cash_session_id == (None if kind == "open" else UUID(body["cash_session_id"]))
        audit = session.scalar(select(AuditLog).where(AuditLog.resource_id == snapshot["id"]))
        assert audit.metadata_["idempotency_key"] == key
        events = session.scalars(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == snapshot["id"])
        )
        assert all(event.headers["idempotency_key"] == key for event in events)


@pytest.mark.parametrize("kind", COMMANDS)
def test_changed_cash_payload_never_mutates_previous_command(client: TestClient, kind: str) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    assert _post(client, kind, headers, body, key).status_code == COMMANDS[kind][4]
    if kind == "close":
        headers = _login(client)
    before = _state()
    changed = deepcopy(body)
    if kind == "open":
        changed["opening_amount"] = "1.00"
    else:
        changed["notes"] = "Changed economic intention"
    result = _post(client, kind, headers, changed, key)
    assert result.status_code == 409 and result.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _state() == before


@pytest.mark.parametrize("kind", COMMANDS)
@pytest.mark.parametrize("invalid", ["missing", "uuid4", "duplicate"])
def test_cash_keys_are_required_uuid7_and_unique_header_values(
    client: TestClient, kind: str, invalid: str
) -> None:
    headers, body = _setup(client, kind)
    before = _state()
    outgoing = list(headers.items())
    if invalid == "uuid4":
        outgoing.append(("Idempotency-Key", str(uuid4())))
    elif invalid == "duplicate":
        outgoing += [("Idempotency-Key", new_idempotency_key()) for _ in range(2)]
    result = client.post(COMMANDS[kind][1] + COMMANDS[kind][2], headers=outgoing, json=body)
    assert result.status_code == 422
    assert _state() == before


@pytest.mark.parametrize("kind", COMMANDS)
def test_cash_effects_roll_back_after_actual_outbox_flush(
    client: TestClient, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client, kind)
    key, before, append = new_idempotency_key(), _state(), OutboxWriter.append

    def fail(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == EVENTS[kind]:
            session.flush()
            assert result.id is not None
            assert (
                session.scalar(select(OutboxEvent.id).where(OutboxEvent.id == result.id))
                == result.id
            )
            raise RuntimeError("Injected cash failure after actual flush")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail)
        with pytest.raises(RuntimeError, match="Injected cash failure"):
            _post(client, kind, headers, body, key)
    assert _state() == before
    assert _post(client, kind, headers, body, key).status_code == COMMANDS[kind][4]


@pytest.mark.parametrize("kind", COMMANDS)
def test_lost_cash_acknowledgement_recovers_without_repeating_effects(
    client: TestClient, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    router = import_module(f"zeromerma_api.modules.{COMMANDS[kind][0]}.presentation.router")

    def lost(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Lost cash acknowledgement after commit")

    with monkeypatch.context() as patch:
        patch.setattr(router, "idempotency_response", lost)
        with pytest.raises(RuntimeError, match="Lost cash acknowledgement"):
            _post(client, kind, headers, body, key)
    committed = _state()
    if kind == "close":
        headers = _login(client)
    recovered = _recover(client, kind, headers, body, key)
    replay = _post(client, kind, headers, body, key)
    assert recovered.status_code == 200 and replay.status_code == COMMANDS[kind][4]
    assert recovered.json() == replay.json()
    assert _state() == committed


@pytest.mark.parametrize("kind", COMMANDS)
def test_cash_history_replays_after_shift_change_without_touching_new_session(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    original = _post(client, kind, headers, body, key)
    assert original.status_code == COMMANDS[kind][4]
    old_cash_id = original.json()["id"] if kind == "open" else body["cash_session_id"]
    if kind != "close":
        assert (
            _post(
                client, "close", headers, _body("close", old_cash_id), new_idempotency_key()
            ).status_code
            == 200
        )
    fresh = _login(client)
    opened = _post(client, "open", fresh, _body("open"), new_idempotency_key())
    assert opened.status_code == 201 and opened.json()["id"] != old_cash_id
    before = _state()
    assert _post(client, kind, fresh, body, key).json() == original.json()
    assert _recover(client, kind, fresh, body, key).json() == original.json()
    assert _state() == before
    if kind in {"payment", "discount"}:
        result = _post(client, kind, fresh, body, new_idempotency_key())
        assert result.status_code == 409
        assert _state()["movements"] == before["movements"]
        assert _state()["financial_facts"] == before["financial_facts"]
    with SessionLocal() as session:
        assert session.get(CashSession, UUID(opened.json()["id"])).status == "OPEN"


@pytest.mark.parametrize("kind", COMMANDS)
def test_cash_recovery_reauthorizes_surface_station_cash_and_branch_scope(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    assert _post(client, kind, headers, body, key).status_code == COMMANDS[kind][4]
    if kind == "close":
        headers = _login(client)
    before = _state()
    if kind != "open":
        assert (
            _recover(
                client, kind, headers, {**body, "cash_session_id": str(uuid4())}, key
            ).status_code
            == 409
        )
    assert _recover(client, kind, owner_headers(), body, key).status_code in {401, 403}
    other = _login(client, SEED_DESTINATION_WORKSTATION_CODE)
    assert (
        _recover(
            client,
            kind,
            other,
            {**body, "workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
            key,
        ).status_code
        == 409
    )
    fresh = _login(client)
    assert _recover(client, kind, fresh, body, key).status_code == 200
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        for grant in session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == user.id)
        ):
            grant.is_active = False
        session.commit()
    denied = _recover(client, kind, fresh, body, key)
    assert denied.status_code == 401 and denied.json()["code"] == "SESSION_REVOKED"
    assert _state() == before


@pytest.mark.parametrize("kind", ["payment", "discount"])
@pytest.mark.parametrize("method", ["CASH", "CARD"])
def test_distinct_operational_intentions_create_correct_single_cash_effects(
    client: TestClient, kind: str, method: str
) -> None:
    headers, body = _setup(client, kind)
    body["payment_method_code"] = method
    results = [_post(client, kind, headers, body, new_idempotency_key()) for _ in range(2)]
    assert all(result.status_code == 201 for result in results)
    snapshots = [result.json() for result in results]
    assert snapshots[0]["id"] != snapshots[1]["id"]
    state = _state()
    assert state["operational_payments" if kind == "payment" else "operational_discounts"] == 2
    assert state["cash_movements"] == 0
    assert state["operational_financial_entries"] == 2
    with SessionLocal() as session:
        for snapshot in snapshots:
            assert snapshot["cash_movement_id"] is None
            operation = session.scalars(
                select(FinancialOperation).where(
                    FinancialOperation.source_id == UUID(snapshot["id"])
                )
            ).one()
            entry = session.scalars(
                select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
            ).one()
            assert operation.kind == (
                "OPERATIONAL_PAYMENT" if kind == "payment" else "OPERATIONAL_CHARGE"
            )
            assert entry.direction == ("OUT" if kind == "payment" else "IN")
            assert entry.payment_method_code == method
            assert entry.amount == operation.amount_due == Decimal(body["total_amount"])
            assert entry.state == "CONFIRMED"
            assert entry.execution_mode == ("LOCAL" if method == "CASH" else "ACCOUNTING_ONLY")
            assert (
                entry.cash_session_id == operation.cash_session_id == UUID(body["cash_session_id"])
            )


def test_already_closed_session_has_one_durable_conflict_for_a_new_key(client: TestClient) -> None:
    headers, body = _setup(client, "close")
    original = _post(client, "close", headers, body, new_idempotency_key())
    assert original.status_code == 200
    headers = _login(client)
    before, key = _state(), new_idempotency_key()
    rejected = _post(client, "close", headers, body, key)
    assert rejected.status_code == 409 and rejected.json()["code"] == "CASH_CLOSE_ALREADY_EXISTS"
    for result in (
        _post(client, "close", headers, body, key),
        _recover(client, "close", headers, body, key),
    ):
        assert result.status_code == 409 and result.json()["code"] == "CASH_CLOSE_ALREADY_EXISTS"
        assert result.headers["Idempotency-Replayed"] == "true"
    after = _state()
    assert after.pop("idempotency_records") == before.pop("idempotency_records") + 1
    assert after == before


def test_close_without_count_remains_invalid_and_does_not_consume_identity(
    client: TestClient,
) -> None:
    headers, body = _setup(client, "close")
    key, before = new_idempotency_key(), _state()
    invalid = {**body, "close_mode": "WITHOUT_COUNT", "counted_payment_methods": []}
    assert _post(client, "close", headers, invalid, key).status_code in {400, 422}
    assert _state() == before
    assert _post(client, "close", headers, body, key).status_code == 200


def test_negative_expected_cash_rejects_close_without_a_partial_commit(client: TestClient) -> None:
    headers, payment = _setup(client, "payment")
    payment["total_amount"] = "150.00"
    assert _post(client, "payment", headers, payment, new_idempotency_key()).status_code == 201
    close, before, key = _body("close", payment["cash_session_id"]), _state(), new_idempotency_key()
    for _ in range(2):
        result = _post(client, "close", headers, close, key)
        assert result.status_code == 400
        assert "negative" in result.json()["message"].lower()
        assert _state() == before


def _domain(
    kind: str,
    headers: dict[str, str],
    body: dict[str, Any],
    key: str,
    *,
    recover: bool = False,
    backend_pid: dict[str, int] | None = None,
    entered: Event | None = None,
) -> IdempotencyResult:
    """Use real authority without HTTP identity locks masking cash contention."""
    classes = {
        "open": ("CashSessionOpenService", "OpenCashSessionRequest", "open"),
        "payment": ("OperationalPaymentCommitService", "CreateOperationalPaymentRequest", "commit"),
        "discount": (
            "OperationalDiscountCommitService",
            "CreateOperationalDiscountRequest",
            "commit",
        ),
        "close": ("CashCloseCommitService", "CashCloseCommitRequest", "commit"),
    }
    module = f"zeromerma_api.modules.{COMMANDS[kind][0]}.application"
    service_name, schema_name, method = classes[kind]
    service = getattr(import_module(module + ".idempotency"), service_name)()
    schema = getattr(import_module(module + ".schemas"), schema_name)
    cookies = SimpleCookie()
    cookies.load(headers["Cookie"])
    credential = cookies[COOKIE_NAMES["POS"]].value
    with SessionLocal() as session:
        if backend_pid is not None:
            backend_pid["pid"] = session.scalar(select(func.pg_backend_pid()))
        record = session.scalars(
            select(AuthSession).where(
                AuthSession.credential_hash == secret_hash(credential),
                AuthSession.audience == "POS",
                AuthSession.status == "ACTIVE",
            )
        ).one()
        user = resolve_authorization(session, session.get(User, record.user_id), surface="POS")
        session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("discounts.manage" if kind == "discount" else "pos.operate",),
            mutation=not recover,
            surface="POS",
        )
        if entered is not None:
            entered.set()
        if recover:
            context = {"workstation_code": body["workstation_code"]}
            if kind != "open":
                context["cash_session_id"] = UUID(body["cash_session_id"])
            return service.recover(session, current_user=user, key=UUID(key), **context)
        return getattr(service, method)(
            session,
            current_user=user,
            command=schema.model_validate(body),
            key=UUID(key),
            request_id="cash-concurrency-probe",
        )


@pytest.mark.parametrize("kind", COMMANDS)
def test_same_cash_key_contention_is_bounded_and_uncommitted_result_unknown(
    client: TestClient, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client, kind)
    held, release, key = Event(), Event(), new_idempotency_key()
    append = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == EVENTS[kind] and not held.is_set():
            held.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(_domain, kind, headers, body, key)
        try:
            assert held.wait(timeout=15)
            started = monotonic()
            with pytest.raises(IdempotencyInProgress):
                _domain(kind, headers, body, key)
            assert monotonic() - started < 5
            with pytest.raises(IdempotencyResultUnknown):
                _domain(kind, headers, body, key, recover=True)
        finally:
            release.set()
        result = first.result(timeout=15)
    if kind == "close":
        headers = _login(client)
    replay = _domain(kind, headers, body, key)
    assert replay.replayed and replay.payload == result.payload


@pytest.mark.parametrize("kind", ["open", "payment", "discount"])
def test_two_http_clients_receive_one_cash_operation(client: TestClient, kind: str) -> None:
    headers, body = _setup(client, kind)
    key, barrier = new_idempotency_key(), Barrier(2)

    def submit() -> Any:
        with TestClient(create_app(), base_url="https://testserver") as other:
            barrier.wait(timeout=15)
            return _post(other, kind, headers, body, key)

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = [
            future.result(timeout=30) for future in [pool.submit(submit) for _ in range(2)]
        ]
    assert all(response.status_code == COMMANDS[kind][4] for response in responses)
    assert responses[0].json() == responses[1].json()
    assert sorted(response.headers["Idempotency-Replayed"] for response in responses) == [
        "false",
        "true",
    ]
    table = {
        "open": "cash_sessions",
        "payment": "operational_payments",
        "discount": "operational_discounts",
    }[kind]
    assert _state()[table] == 1


def _contend(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
    first_kind: str,
    first_body: dict[str, Any],
    second_kind: str,
    second_body: dict[str, Any],
) -> tuple[IdempotencyResult, IdempotencyResult | Exception]:
    held, release, entered, pid = Event(), Event(), Event(), {}
    append = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == EVENTS[first_kind] and not held.is_set():
            held.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(_domain, first_kind, headers, first_body, new_idempotency_key())
        try:
            assert held.wait(timeout=15)
            second = pool.submit(
                _domain,
                second_kind,
                headers,
                second_body,
                new_idempotency_key(),
                backend_pid=pid,
                entered=entered,
            )
            assert entered.wait(timeout=10)
            deadline, blocked = monotonic() + 10, False
            while monotonic() < deadline:
                with SessionLocal() as probe:
                    blocked = bool(probe.scalar(select(func.pg_blocking_pids(pid["pid"]))))
                if blocked:
                    break
                assert not second.done(), (
                    "Competing cash command must serialize before its decision"
                )
                Event().wait(0.025)
            assert blocked, "The rival must wait on the original cash transaction"
        finally:
            release.set()
        first_result = first.result(timeout=15)
        try:
            second_result: IdempotencyResult | Exception = second.result(timeout=15)
        except Exception as error:
            second_result = error
    return first_result, second_result


@pytest.mark.parametrize("kind", ["open", "close"])
def test_different_keys_cannot_duplicate_opening_or_close_under_postgres_contention(
    client: TestClient,
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, body = _setup(client, kind)
    first, second = _contend(monkeypatch, headers, kind, body, kind, body)
    assert first.status_code == COMMANDS[kind][4]
    if kind == "open":
        assert isinstance(second, CashSessionConflictError)
        assert _state()["cash_sessions"] == 1
    else:
        assert isinstance(second, IdempotencyResult)
        assert second.status_code == 409 and second.error_code == "CASH_CLOSE_ALREADY_EXISTS"
        assert _state()["cash_session_closes"] == 1


@pytest.mark.parametrize("kind", COMMANDS)
def test_distinct_cash_reservations_do_not_deadlock_when_both_precede_domain_locks(
    client: TestClient,
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, body = _setup(client, kind)
    # Reservation FKs hold KEY SHARE locks. Both commands must reserve before either
    # requests its economic row lock, exercising the otherwise hidden lock upgrade.
    module = import_module(
        "zeromerma_api.modules.cash.application.idempotency"
        if kind == "open"
        else f"zeromerma_api.modules.{COMMANDS[kind][0]}.application.services"
    )
    lock_name = "lock_cash_opening" if kind == "open" else "lock_cash_session"
    lock, barrier = getattr(module, lock_name), Barrier(2)

    def simultaneous(*args: Any, **kwargs: Any) -> Any:
        barrier.wait(timeout=15)
        return lock(*args, **kwargs)

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(module, lock_name, simultaneous)
        futures = [
            pool.submit(_domain, kind, headers, body, new_idempotency_key()) for _ in range(2)
        ]
        results: list[IdempotencyResult | CashSessionConflictError] = []
        for future in futures:
            try:
                results.append(future.result(timeout=25))
            except CashSessionConflictError as error:
                results.append(error)
    if kind == "open":
        assert (
            sum(
                isinstance(result, IdempotencyResult) and result.status_code == 201
                for result in results
            )
            == 1
        )
        assert sum(isinstance(result, CashSessionConflictError) for result in results) == 1
        assert _state()["cash_sessions"] == 1
    elif kind == "close":
        assert all(isinstance(result, IdempotencyResult) for result in results)
        assert sorted(result.status_code for result in results) == [200, 409]
        assert _state()["cash_session_closes"] == 1
    else:
        assert all(
            isinstance(result, IdempotencyResult) and result.status_code == 201
            for result in results
        )
        assert len({result.payload["id"] for result in results}) == 2
        assert _state()["cash_movements"] == 0
        assert _state()["operational_financial_entries"] == 2


@pytest.mark.parametrize("movement", ["payment", "discount"])
@pytest.mark.parametrize("close_first", [False, True])
def test_cash_movements_and_close_revalidate_under_same_session_lock(
    client: TestClient,
    movement: str,
    close_first: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, movement_body = _setup(client, movement)
    close_body = _body("close", movement_body["cash_session_id"])
    first_kind, first_body, second_kind, second_body = (
        ("close", close_body, movement, movement_body)
        if close_first
        else (movement, movement_body, "close", close_body)
    )
    first, second = _contend(monkeypatch, headers, first_kind, first_body, second_kind, second_body)
    assert first.status_code == COMMANDS[first_kind][4]
    assert _state()["cash_movements"] == 0
    if close_first:
        assert isinstance(second, IdempotencyError) and second.code == "CASH_SESSION_CLOSED"
        assert _state()["operational_financial_entries"] == 0
    else:
        assert isinstance(second, IdempotencyResult) and second.status_code == 200
        expected = "90.00" if movement == "payment" else "110.00"
        assert second.payload["expected_cash_amount"] == expected
        assert _state()["operational_financial_entries"] == 1
    assert _state()["cash_session_closes"] == 1


def test_high_value_discount_replay_never_repeats_alerts(
    client: TestClient,
) -> None:
    headers, body = _setup(client, "discount")
    body.update(total_amount="99999.00", high_value_acknowledged=True)
    key = new_idempotency_key()
    response = _post(client, "discount", headers, body, key)
    assert response.status_code == 201
    before = _state()
    assert _post(client, "discount", headers, body, key).json() == response.json()
    assert _state() == before
    with SessionLocal() as session:
        events = list(
            session.scalars(
                select(OutboxEvent).where(OutboxEvent.aggregate_id == response.json()["id"])
            )
        )
        assert len(events) == 2 and len({event.event_name for event in events}) == 2


def test_one_key_cannot_change_from_cash_outflow_to_inflow(client: TestClient) -> None:
    headers, body = _setup(client, "payment")
    key = new_idempotency_key()
    assert _post(client, "payment", headers, body, key).status_code == 201
    before = _state()
    changed = _body("discount", body["cash_session_id"])
    response = _post(client, "discount", headers, changed, key)
    assert response.status_code == 409 and response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _recover(client, "discount", headers, changed, key).status_code == 409
    assert _state() == before


def test_counted_close_replay_preserves_real_class_attributions_and_baseline(
    client: TestClient,
) -> None:
    headers, body = _setup(client, "close")
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(body["cash_session_id"]))
        product = session.scalar(
            select(Product).where(Product.code == SEED_PRODUCT_CONCHA_VAN_CODE)
        )
        product_class = session.get(ProductClass, product.product_class_id)
        product_id, class_id = str(product.id), str(product_class.id)
        baseline = BranchCounterSnapshot(
            branch_id=cash.branch_id,
            source_cash_session_close_id=None,
            snapshot_type="CLOSE_BASELINE",
            captured_by_user_id=cash.user_id,
        )
        session.add(baseline)
        session.flush()
        session.add(
            BranchCounterSnapshotLine(
                snapshot_id=baseline.id,
                product_id=product.id,
                product_code_snapshot=product.code,
                product_name_snapshot=product.name,
                product_class_id=product_class.id,
                product_class_code_snapshot=product_class.code,
                product_class_name_snapshot=product_class.name,
                quantity=3,
                bucket_code="COUNTER",
            )
        )
        session.commit()
    sale = client.post(
        "/v1/sales/confirm",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "cash_session_id": body["cash_session_id"],
            "lines": [
                {"capture_mode": "CLASS_CAPTURE", "product_class_id": class_id, "quantity": "1"}
            ],
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "100.00"}],
        },
    )
    assert sale.status_code == 201
    summary = client.get(
        "/v1/cash-close/summary",
        headers=headers,
        params={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert summary.status_code == 200
    body.update(
        counter_empty_confirmed=False,
        counted_product_lines=[{"product_id": product_id, "counted_quantity": "2.000"}],
        counted_payment_methods=[
            {
                "payment_method_code": "CASH",
                "counted_amount": summary.json()["expected_cash_amount"],
            }
        ],
    )
    key = new_idempotency_key()
    original = _post(client, "close", headers, body, key)
    assert original.status_code == 200
    before = _state()
    assert before["cash_session_close_class_reconciliations"] == 1
    assert before["cash_session_close_reconciliation_attributions"] == 1
    assert before["branch_counter_snapshots"] == 2
    fresh = _login(client)
    assert _post(client, "close", fresh, body, key).json() == original.json()
    assert _recover(client, "close", fresh, body, key).json() == original.json()
    assert _state() == before


@pytest.mark.parametrize("kind", COMMANDS)
def test_other_authorized_operator_cannot_recover_cash_command(
    client: TestClient, kind: str
) -> None:
    headers, body = _setup(client, kind)
    key = new_idempotency_key()
    original = _post(client, kind, headers, body, key)
    assert original.status_code == COMMANDS[kind][4]
    with SessionLocal() as session:
        source = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        actor = User(
            email="cash.other@validation.invalid",
            full_name="Other cash operator",
            password_hash=source.password_hash,
            allowed_surfaces=["POS"],
            default_surface="POS",
        )
        session.add(actor)
        session.flush()
        session.add(
            UserBranchAssignment(
                user_id=actor.id, branch_id=UUID(original.json()["branch_id"]), is_default=True
            )
        )
        for assignment in session.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id == source.id)
        ).all():
            clone = UserRoleAssignment(
                user_id=actor.id, role_id=assignment.role_id, scope_type=assignment.scope_type
            )
            session.add(clone)
            session.flush()
            for scope in session.scalars(
                select(UserRoleAssignmentBranchScope).where(
                    UserRoleAssignmentBranchScope.assignment_id == assignment.id
                )
            ):
                session.add(
                    UserRoleAssignmentBranchScope(assignment_id=clone.id, branch_id=scope.branch_id)
                )
        session.commit()
    other = login_headers(
        client,
        email="cash.other@validation.invalid",
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    before = _state()
    assert _recover(client, kind, other, body, key).status_code == 409
    assert _post(client, kind, other, body, key).status_code == 409
    assert _state() == before


def test_cash_command_latency_is_observed_without_a_production_sla(
    client: TestClient,
    record_testsuite_property: Any,
) -> None:
    headers, body = _setup(client, "payment")
    timings: dict[str, list[float]] = {"new": [], "replay": []}
    for _ in range(5):
        key = new_idempotency_key()
        for path in timings:
            start = perf_counter()
            assert _post(client, "payment", headers, body, key).status_code == 201
            timings[path].append((perf_counter() - start) * 1000)
    record_testsuite_property(
        "cash_latency_environment", "TestClient / disposable PostgreSQL / CASH payment"
    )
    record_testsuite_property("cash_latency_samples_per_path", 5)
    for path, samples in timings.items():
        record_testsuite_property(f"cash_latency_{path}_median_ms", round(median(samples), 3))
