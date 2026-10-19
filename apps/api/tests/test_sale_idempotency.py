"""Sale confirmation acceptance against guarded, disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from http.cookies import SimpleCookie
from statistics import median
from threading import Barrier, Event
from time import perf_counter
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.schemas import IdempotencyResult
from zeromerma_api.modules.idempotency.domain.exceptions import (
    IdempotencyInProgress,
    IdempotencyResultUnknown,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    SessionAuthentication,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.application.idempotency import SaleConfirmationService
from zeromerma_api.modules.sales.application.schemas import ConfirmSaleRequest
from zeromerma_api.modules.sales.application.services import SaleCommandService
from zeromerma_api.modules.sales.infrastructure.models import (
    CashMovement,
    Sale,
    SaleLine,
    SalePayment,
)
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email

ENDPOINT = "/v1/sales/confirm"


def _login(client: TestClient, workstation: str = SEED_WORKSTATION_CODE) -> dict[str, str]:
    return login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )


def _setup(
    client: TestClient, workstation: str = SEED_WORKSTATION_CODE
) -> tuple[dict[str, str], dict[str, Any]]:
    headers = login_headers(
        client,
        email=transfer_cashier_email(workstation),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": workstation, "opening_amount": "100.00"},
    )
    assert opened.status_code == 201
    with SessionLocal() as session:
        cash_id = UUID(opened.json()["id"])
        product_id = session.scalars(
            select(Product.id).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
        ).one()
        class_id = session.scalars(
            select(ProductClass.id).where(ProductClass.code == SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
        ).one()
    return headers, {
        "workstation_code": workstation,
        "cash_session_id": str(cash_id),
        "lines": [
            {"capture_mode": "CLASS_CAPTURE", "product_class_id": str(class_id), "quantity": "1"},
            {"capture_mode": "PRODUCT_DIRECT", "product_id": str(product_id), "quantity": "1"},
        ],
        "payments": [{"payment_method_code": "CASH", "tendered_amount": "50.00"}],
    }


def _submit(client: TestClient, headers: dict[str, str], body: dict[str, Any], key: str) -> Any:
    return client.post(ENDPOINT, headers={**headers, "Idempotency-Key": key}, json=body)


def _recover(client: TestClient, headers: dict[str, str], body: dict[str, Any], key: str) -> Any:
    return client.get(
        f"/v1/sales/confirmations/{key}",
        headers=headers,
        params={name: body[name] for name in ("workstation_code", "cash_session_id")},
    )


def _counts() -> dict[str, int]:
    with SessionLocal() as session:
        result = {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (
                Sale,
                SaleLine,
                SalePayment,
                CashMovement,
                InventoryMovement,
                FinancialOperation,
                FinancialEntry,
            )
        }
        for model, predicate in (
            (AuditLog, AuditLog.action == "sale.confirmed"),
            (OutboxEvent, OutboxEvent.event_name == "sale.confirmed.v1"),
            (IdempotencyRecord, IdempotencyRecord.operation_code == "sale.confirm"),
        ):
            result[model.__tablename__] = session.scalar(
                select(func.count()).select_from(model).where(predicate)
            )
        return result


@pytest.mark.parametrize("payment", ["CASH", "CARD", "MIXED"])
def test_retries_recover_exact_sale_and_ticket_without_repeating_effects(
    client: TestClient, payment: str
) -> None:
    headers, body = _setup(client)
    if payment == "CARD":
        body["payments"] = [{"payment_method_code": "CARD", "tendered_amount": "30.00"}]
    elif payment == "MIXED":
        body["payments"] = [
            {"payment_method_code": "CARD", "tendered_amount": "15.00"},
            {"payment_method_code": "CASH", "tendered_amount": "20.00"},
        ]
    before, key = _counts(), new_idempotency_key()
    first = _submit(
        client, {**headers, "X-Request-ID": "f8e0d861-8e1f-5a9e-8729-03d09d465bce"}, body, key
    )
    assert first.status_code == 201
    assert first.headers["Idempotency-Replayed"] == "false"
    after = _counts()
    expected = {
        "sales": 1,
        "sale_lines": 2,
        "sale_payments": len(body["payments"]),
        "cash_movements": 0,
        "financial_operations": 1,
        "financial_entries": len(body["payments"]),
        "inventory_movements": 0,
        "audit_log": 1,
        "outbox_events": 1,
        "idempotency_records": 1,
    }
    assert {table: after[table] - count for table, count in before.items()} == expected
    for attempt in range(3):
        replay = _submit(client, {**headers, "X-Request-ID": f"retry-{attempt}"}, body, key)
        assert replay.status_code == 201
        assert replay.headers["Idempotency-Replayed"] == "true"
        assert replay.headers["Cache-Control"] == "no-store"
        assert replay.json() == first.json()
    recovered = _recover(client, headers, body, key)
    assert recovered.status_code == 200
    assert recovered.json() == first.json()
    assert "operator_email" not in first.json()
    assert "operator_full_name" not in first.json()
    ticket = client.get(
        f"/v1/tickets/{first.json()['id']}",
        headers=headers,
        params={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert ticket.status_code == 200
    assert _counts() == after
    with SessionLocal() as session:
        record = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        ).one()
        audit = session.scalars(select(AuditLog).where(AuditLog.action == "sale.confirmed")).one()
        event = session.scalars(
            select(OutboxEvent).where(OutboxEvent.event_name == "sale.confirmed.v1")
        ).one()
        assert record.resource_id == first.json()["id"]
        assert record.first_request_id == "f8e0d861-8e1f-5a9e-8729-03d09d465bce"
        assert record.response_payload == first.json()
        for metadata in (audit.metadata_, event.headers):
            assert metadata["idempotency_key"] == key
            assert metadata["operation_id"] == str(record.id)


def test_identical_cart_with_new_key_is_a_new_sale(client: TestClient) -> None:
    headers, body = _setup(client)
    first = _submit(client, headers, body, new_idempotency_key())
    second = _submit(client, headers, body, new_idempotency_key())
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert _counts()["sales"] == _counts()["idempotency_records"] == 2


@pytest.mark.parametrize("change", ["quantity", "payment", "cash_session", "line_order"])
def test_reused_key_with_different_intention_is_rejected(client: TestClient, change: str) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    assert _submit(client, headers, body, key).status_code == 201
    before = _counts()
    changed = deepcopy(body)
    if change == "quantity":
        changed["lines"][0]["quantity"] = "2"
    elif change == "payment":
        changed["payments"][0]["tendered_amount"] = "100"
    elif change == "cash_session":
        changed["cash_session_id"] = str(uuid4())
    else:
        changed["lines"].reverse()
    response = _submit(client, headers, changed, key)
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _counts() == before


def test_equivalent_validated_payload_is_a_replay(client: TestClient) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    first = _submit(client, headers, body, key)
    body["lines"][0].update(quantity="1.000", product_id=None)
    body["payments"][0].update(payment_method_code=" cash ", tendered_amount="50")
    second = _submit(client, headers, body, key)
    assert first.status_code == second.status_code == 201
    assert second.headers["Idempotency-Replayed"] == "true"
    assert first.json() == second.json()


@pytest.mark.parametrize("key_kind", ["absent", "malformed", "uuid4", "duplicate"])
def test_invalid_key_never_admits_a_sale(client: TestClient, key_kind: str) -> None:
    headers, body = _setup(client)
    pairs = list(headers.items())
    if key_kind != "absent":
        value = {"malformed": "invalid", "uuid4": str(uuid4())}.get(key_kind, new_idempotency_key())
        pairs.append(("Idempotency-Key", value))
        if key_kind == "duplicate":
            pairs.append(("Idempotency-Key", value))
    before = _counts()
    assert client.post(ENDPOINT, headers=pairs, json=body).status_code == 422
    assert _counts() == before


@pytest.mark.parametrize("invalid", ["empty_cart", "payment", "cash_session", "missing_cash"])
def test_pre_admission_rejection_leaves_key_available(client: TestClient, invalid: str) -> None:
    headers, body = _setup(client)
    key, changed = new_idempotency_key(), deepcopy(body)
    if invalid == "empty_cart":
        changed["lines"] = []
    elif invalid == "payment":
        changed["payments"][0]["tendered_amount"] = "1"
    elif invalid == "cash_session":
        changed["cash_session_id"] = str(uuid4())
    else:
        del changed["cash_session_id"]
    before = _counts()
    assert _submit(client, headers, changed, key).status_code in {400, 409, 422}
    assert _counts() == before
    assert _submit(client, headers, body, key).status_code == 201


def test_replay_after_close_and_new_login_skips_pricing_and_keeps_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    first = _submit(client, headers, body, key)
    assert first.status_code == 201
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(body["cash_session_id"]))
        cash.status, cash.closed_at = "CLOSED", datetime.now(UTC)
        product = session.scalars(
            select(Product).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
        ).one()
        product.name = "Changed after confirmation"
        branch = session.get(Branch, cash.branch_id)
        branch.name = "Changed branch presentation"
        session.commit()

    def unexpected_pricing(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Completed replay must not invoke pricing")

    monkeypatch.setattr(SaleCommandService, "_price_lines", unexpected_pricing)
    fresh_headers = _login(client)
    before = _counts()
    replay = _submit(client, fresh_headers, body, key)
    recovered = _recover(client, fresh_headers, body, key)
    assert replay.status_code == 201
    assert recovered.status_code == 200
    assert replay.json() == recovered.json() == first.json()
    assert _counts() == before
    assert _submit(client, fresh_headers, body, new_idempotency_key()).status_code == 409


def test_response_loss_after_commit_recovers_sale(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.sales.presentation import router

    headers, body = _setup(client)
    key = new_idempotency_key()

    def lose_response(*args: Any, **kwargs: Any) -> Any:
        raise ConnectionError("Simulated loss after the database committed")

    with monkeypatch.context() as patch:
        patch.setattr(router, "idempotency_response", lose_response)
        with pytest.raises(ConnectionError):
            _submit(client, headers, body, key)
    before = _counts()
    assert before["sales"] == 1
    replay = _submit(client, headers, body, key)
    recovery = _recover(client, headers, body, key)
    assert replay.status_code == 201
    assert recovery.status_code == 200
    assert replay.json() == recovery.json()
    assert _counts() == before


def test_failure_after_flushed_sale_and_outbox_rolls_back_every_effect(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client)
    key, before = new_idempotency_key(), _counts()
    original = OutboxWriter.append

    def fail_after_write(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        session.flush()
        if kwargs["event_name"] == "sale.confirmed.v1":
            raise RuntimeError("Simulated failure before commit")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail_after_write)
        with pytest.raises(RuntimeError, match="Simulated failure"):
            _submit(client, headers, body, key)
    assert _counts() == before
    unknown = _recover(client, headers, body, key)
    assert unknown.status_code == 409
    assert unknown.json()["code"] == "IDEMPOTENCY_RESULT_UNKNOWN"
    assert _counts() == before
    assert _submit(client, headers, body, key).status_code == 201


def test_recovery_requires_current_authority_and_original_station(client: TestClient) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    assert _submit(client, headers, body, key).status_code == 201
    before = _counts()
    wrong_cash = _recover(client, headers, {**body, "cash_session_id": str(uuid4())}, key)
    assert wrong_cash.status_code == 409
    assert wrong_cash.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    other_headers = _login(client, SEED_DESTINATION_WORKSTATION_CODE)
    other_body = {**body, "workstation_code": SEED_DESTINATION_WORKSTATION_CODE}
    mismatch = _recover(client, other_headers, other_body, key)
    assert mismatch.status_code in {403, 409}
    assert "id" not in mismatch.json()
    assert _submit(client, other_headers, other_body, key).status_code in {403, 409}
    with SessionLocal() as session:
        actor = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        assignments = session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == actor.id)
        ).all()
        for assignment in assignments:
            assignment.is_active = False
        session.commit()
    for response in (_recover(client, headers, body, key), _submit(client, headers, body, key)):
        assert response.status_code == 401
        assert response.json()["code"] == "SESSION_REVOKED"
    assert _counts() == before


def test_another_authorized_cashier_cannot_recover_or_replay_the_sale(client: TestClient) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    assert _submit(client, headers, body, key).status_code == 201
    before = _counts()
    with SessionLocal() as session:
        original = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        actor = User(
            email="other.cashier@validation.invalid",
            full_name="Other validation cashier",
            password_hash=original.password_hash,
            allowed_surfaces=["POS"],
            default_surface="POS",
        )
        session.add(actor)
        session.flush()
        for membership in session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == original.id)
        ).all():
            session.add(UserBranchAssignment(user_id=actor.id, branch_id=membership.branch_id))
        for original_grant in session.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id == original.id)
        ).all():
            grant = UserRoleAssignment(
                user_id=actor.id,
                role_id=original_grant.role_id,
                scope_type=original_grant.scope_type,
            )
            session.add(grant)
            session.flush()
            for branch_id in session.scalars(
                select(UserRoleAssignmentBranchScope.branch_id).where(
                    UserRoleAssignmentBranchScope.assignment_id == original_grant.id
                )
            ).all():
                session.add(
                    UserRoleAssignmentBranchScope(assignment_id=grant.id, branch_id=branch_id)
                )
        session.commit()
    other = login_headers(
        client,
        email="other.cashier@validation.invalid",
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    for response in (_recover(client, other, body, key), _submit(client, other, body, key)):
        assert response.status_code == 409
        assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
        assert "id" not in response.json()
    assert _counts() == before


def _domain_confirmation(
    headers: dict[str, str], body: dict[str, Any], key: str, *, recover: bool = False
) -> IdempotencyResult:
    """Exercise sale/executor concurrency with real authority, excluding HTTP session locks."""
    cookies = SimpleCookie()
    cookies.load(headers["Cookie"])
    credential = cookies["__Host-zm-pos-session"].value
    with SessionLocal() as session:
        record = session.scalars(
            select(AuthSession).where(
                AuthSession.credential_hash == secret_hash(credential),
                AuthSession.audience == "POS",
                AuthSession.status == "ACTIVE",
            )
        ).one()
        actor = session.get(User, record.user_id)
        assert actor is not None
        user = resolve_authorization(session, actor, surface="POS")
        session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("pos.operate",),
            mutation=not recover,
            surface="POS",
        )
        service = SaleConfirmationService()
        if recover:
            return service.recover(
                session,
                current_user=user,
                key=UUID(key),
                workstation_code=body["workstation_code"],
                cash_session_id=UUID(body["cash_session_id"]),
            )
        return service.confirm(
            session,
            current_user=user,
            command=ConfirmSaleRequest.model_validate(body),
            key=UUID(key),
            request_id="domain-concurrency-probe",
        )


def test_concurrent_retries_and_recovery_while_uncommitted_converge(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The domain boundary bounds same-key contention independently of session authentication."""
    headers, body = _setup(client)
    key = new_idempotency_key()
    admitted, release = Event(), Event()
    original = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == "sale.confirmed.v1":
            admitted.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=1) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        future = pool.submit(_domain_confirmation, headers, body, key)
        try:
            assert admitted.wait(timeout=15)
            with pytest.raises(IdempotencyResultUnknown) as unknown:
                _domain_confirmation(headers, body, key, recover=True)
            assert unknown.value.code == "IDEMPOTENCY_RESULT_UNKNOWN"
            with pytest.raises(IdempotencyInProgress) as contender:
                _domain_confirmation(headers, body, key)
            assert contender.value.status_code == 409
            assert contender.value.code == "IDEMPOTENCY_IN_PROGRESS"
        finally:
            release.set()
        winner = future.result(timeout=15)
    assert winner.status_code == 201 and not winner.replayed
    replay = _domain_confirmation(headers, body, key)
    assert replay.replayed and replay.payload == winner.payload
    assert _counts()["sales"] == _counts()["idempotency_records"] == 1


def test_distinct_cash_sessions_execute_concurrently(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The boundary is per shift; independent operators and cash sessions do not share it."""
    contexts = [
        _setup(client, station)
        for station in (SEED_WORKSTATION_CODE, SEED_DESTINATION_WORKSTATION_CODE)
    ]
    barrier = Barrier(2)
    original = OutboxWriter.append

    def meet(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == "sale.confirmed.v1":
            barrier.wait(timeout=15)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", meet)
        calls = [
            pool.submit(_domain_confirmation, headers, body, new_idempotency_key())
            for headers, body in contexts
        ]
        results = [call.result(timeout=25) for call in calls]
    assert all(result.status_code == 201 and not result.replayed for result in results)
    assert len({result.payload["id"] for result in results}) == 2
    assert _counts()["sales"] == _counts()["idempotency_records"] == 2


def test_concurrent_http_retries_share_one_cookie_and_return_one_sale(client: TestClient) -> None:
    """Real HTTP retries converge even when existing authentication locks serialize requests."""
    headers, body = _setup(client)
    key = new_idempotency_key()
    barrier = Barrier(4)

    def submit() -> Any:
        with TestClient(create_app(), base_url="https://testserver") as concurrent_client:
            barrier.wait(timeout=15)
            return _submit(concurrent_client, headers, body, key)

    with ThreadPoolExecutor(max_workers=4) as pool:
        calls = [pool.submit(submit) for _ in range(4)]
        responses = [call.result(timeout=30) for call in calls]
    assert all(response.status_code == 201 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    assert sum(response.headers["Idempotency-Replayed"] == "false" for response in responses) == 1
    assert _counts()["sales"] == _counts()["idempotency_records"] == 1


def test_new_and_replayed_sale_latency_is_recorded_without_an_invented_sla(
    client: TestClient, record_testsuite_property: Any
) -> None:
    headers, body = _setup(client)
    samples: dict[str, list[float]] = {"new": [], "replay": []}
    for _ in range(5):
        key = new_idempotency_key()
        snapshots = []
        for mode in samples:
            started = perf_counter()
            response = _submit(client, headers, body, key)
            samples[mode].append((perf_counter() - started) * 1000)
            assert response.status_code == 201
            snapshots.append(response.json())
        assert snapshots[0] == snapshots[1]
    record_testsuite_property(
        "sale_latency_environment",
        "TestClient / guarded disposable PostgreSQL / two-line mixed-capture sale",
    )
    record_testsuite_property("sale_latency_samples_per_path", 5)
    for mode, values in samples.items():
        record_testsuite_property(f"sale_latency_{mode}_median_ms", round(median(values), 3))
    assert _counts()["sales"] == _counts()["idempotency_records"] == 5
