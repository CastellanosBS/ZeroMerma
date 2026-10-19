"""Order command acceptance against guarded, disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
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
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product
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
    COOKIE_NAMES,
    SessionAuthentication,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.orders.application.idempotency import OrdersIdempotencyService
from zeromerma_api.modules.orders.application.schemas import (
    CancelCustomerOrderRequest,
    CreateCustomerOrderRequest,
    DeliverCustomerOrderRequest,
    OrderActionRequest,
)
from zeromerma_api.modules.orders.domain.exceptions import OrderStateConflictError
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrder,
    CustomerOrderItem,
    CustomerOrderPayment,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.concurrency import transaction_probe, wait_until_blocked
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email

COMMANDS = [
    ("POS", "create"),
    ("POS", "mark-ready"),
    ("POS", "deliver"),
    ("POS", "cancel"),
    ("BACKOFFICE", "mark-ready"),
    ("BACKOFFICE", "deliver"),
    ("BACKOFFICE", "cancel"),
]
EVENTS = {"create": "created", "mark-ready": "ready", "deliver": "delivered", "cancel": "canceled"}


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
        products = dict(session.execute(select(Product.code, Product.id)).all())
    return headers, {
        "workstation_code": workstation,
        "cash_session_id": str(cash_id),
        "customer_name": "Private order customer",
        "customer_phone": "6621234567",
        "notes": "Private order instructions",
        "requested_for_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        "items": [
            {"product_id": str(products[SEED_PRODUCT_BOLILLO_STD_CODE]), "quantity": "4"},
            {"product_id": str(products[SEED_PRODUCT_CAFE_AMERICANO_CODE]), "quantity": "1"},
        ],
        "advance_amount": "20.00",
        "advance_payment_method_code": "CASH",
    }


def _path(surface: str, action: str, order_id: str | None = None) -> str:
    prefix = "/v1/orders" if surface == "POS" else "/v1/admin/orders"
    return prefix if action == "create" else f"{prefix}/{order_id}/{action}"


def _post(
    client: TestClient,
    headers: dict[str, str],
    action: str,
    body: dict[str, Any],
    key: str,
    order_id: str | None = None,
    surface: str = "POS",
) -> Any:
    return client.post(
        _path(surface, action, order_id),
        headers={**headers, "Idempotency-Key": key},
        json=body,
    )


def _context(body: dict[str, Any]) -> dict[str, str]:
    return {name: body[name] for name in ("workstation_code", "cash_session_id")}


def _recover(
    client: TestClient,
    headers: dict[str, str],
    action: str,
    body: dict[str, Any],
    key: str,
    *,
    surface: str = "POS",
    branch_id: str | None = None,
) -> Any:
    prefix = "/v1/orders" if surface == "POS" else "/v1/admin/orders"
    params = _context(body) if surface == "POS" else {"branch_id": branch_id}
    return client.get(f"{prefix}/commands/{action}/{key}", headers=headers, params=params)


def _prepare(
    client: TestClient, surface: str, action: str
) -> tuple[dict[str, str], dict[str, Any], str | None, str]:
    headers, create = _setup(client)
    with SessionLocal() as session:
        branch_id = str(session.get(CashSession, UUID(create["cash_session_id"])).branch_id)
    if action == "create":
        return headers, create, None, branch_id
    if surface == "BACKOFFICE":
        create["advance_amount"] = "34.00" if action == "deliver" else "0.00"
        if action != "deliver":
            create["advance_payment_method_code"] = None
    created = _post(client, headers, "create", create, new_idempotency_key())
    assert created.status_code == 201
    order_id = created.json()["id"]
    body: dict[str, Any] = _context(create)
    if action == "deliver":
        ready = _post(client, headers, "mark-ready", body, new_idempotency_key(), order_id)
        assert ready.status_code == 200
        if surface == "POS":
            body.update(settlement_amount="14.00", settlement_payment_method_code="CASH")
    elif action == "cancel":
        body["cancellation_reason"] = "Customer requested cancellation"
    if surface == "BACKOFFICE":
        return owner_headers(), {}, order_id, branch_id
    return headers, body, order_id, branch_id


def _counts() -> dict[str, int]:
    with SessionLocal() as session:
        result = {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (
                CustomerOrder,
                CustomerOrderItem,
                CustomerOrderPayment,
                CashMovement,
                InventoryMovement,
            )
        }
        for model, predicate in (
            (AuditLog, AuditLog.action.like("order.%")),
            (OutboxEvent, OutboxEvent.event_name.like("order.%")),
            (IdempotencyRecord, IdempotencyRecord.operation_code.like("order.%")),
        ):
            result[model.__tablename__] = session.scalar(
                select(func.count()).select_from(model).where(predicate)
            )
        return result


def _state() -> tuple[Any, ...]:
    with SessionLocal() as session:
        orders = session.execute(
            select(
                CustomerOrder.id,
                CustomerOrder.status,
                CustomerOrder.advance_amount,
                CustomerOrder.remaining_balance_amount,
                CustomerOrder.updated_at_utc,
            ).order_by(CustomerOrder.id)
        ).all()
        payments = session.execute(
            select(
                CustomerOrderPayment.id, CustomerOrderPayment.sequence, CustomerOrderPayment.amount
            ).order_by(CustomerOrderPayment.id)
        ).all()
        return _counts(), orders, payments


@pytest.mark.parametrize(("surface", "action"), COMMANDS)
def test_every_order_command_replays_its_original_result_without_effects(
    client: TestClient, surface: str, action: str
) -> None:
    headers, body, order_id, branch_id = _prepare(client, surface, action)
    key, before = new_idempotency_key(), _counts()
    first = _post(
        client,
        {**headers, "X-Request-ID": "8fe29116-b257-58eb-b17c-6f1d72a9b68a"},
        action,
        body,
        key,
        order_id,
        surface,
    )
    assert first.status_code == (201 if action == "create" else 200)
    assert first.headers["Idempotency-Replayed"] == "false"
    after = _state()
    for attempt in range(2):
        replay = _post(
            client,
            {**headers, "X-Request-ID": f"retry-{attempt}"},
            action,
            body,
            key,
            order_id,
            surface,
        )
        assert replay.status_code == first.status_code
        assert replay.headers["Idempotency-Replayed"] == "true"
        assert replay.headers["Cache-Control"] == "no-store"
        assert replay.json() == first.json()
    recovered = _recover(client, headers, action, body, key, surface=surface, branch_id=branch_id)
    assert recovered.status_code == 200
    assert recovered.json() == first.json()
    assert _state() == after
    assert after[0]["idempotency_records"] == before["idempotency_records"] + 1
    assert after[0]["audit_log"] == before["audit_log"] + 1
    assert after[0]["outbox_events"] == before["outbox_events"] + 1
    # Existing orders only write their own payment records; ledger adoption is a later task.
    assert after[0]["cash_movements"] == before["cash_movements"]
    assert after[0]["inventory_movements"] == before["inventory_movements"]
    if surface == "POS" and action in {"create", "deliver", "cancel"}:
        assert after[0]["customer_order_payments"] == before["customer_order_payments"] + 1
    with SessionLocal() as session:
        record = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        ).one()
        assert record.response_payload == first.json()
        assert record.resource_id == first.json()["id"]
        assert record.first_request_id == "8fe29116-b257-58eb-b17c-6f1d72a9b68a"
        audits = session.scalars(
            select(AuditLog).where(AuditLog.action == f"order.{EVENTS[action]}")
        ).all()
        events = session.scalars(
            select(OutboxEvent).where(OutboxEvent.event_name == f"order.{EVENTS[action]}.v1")
        ).all()
        for metadata in (audits[-1].metadata_, events[-1].headers):
            assert metadata["idempotency_key"] == key
            assert metadata["operation_id"] == str(record.id)
            assert metadata["operation_code"] == record.operation_code
        encoded = str(record.response_payload)
        for private in (
            "Private order",
            "6621234567",
            "customer_phone",
            "full_name",
            "email",
            "cancellation_reason",
        ):
            assert private not in encoded


@pytest.mark.parametrize("payment", ["CASH", "CARD", "MIXED"])
def test_advance_settlement_and_refund_legs_are_not_duplicated(
    client: TestClient, payment: str
) -> None:
    headers, body = _setup(client)
    body["advance_payment_method_code"] = payment
    if payment == "MIXED":
        body["advance_payments"] = [
            {"payment_method_code": "CASH", "amount": "10.00"},
            {"payment_method_code": "CARD", "amount": "10.00"},
        ]
    context, legs = _context(body), 2 if payment == "MIXED" else 1
    for final_action in ("deliver", "cancel"):
        key = new_idempotency_key()
        created = _post(client, headers, "create", body, key)
        assert created.status_code == 201
        assert _post(client, headers, "create", body, key).json() == created.json()
        order_id = created.json()["id"]
        payload: dict[str, Any] = dict(context)
        if final_action == "deliver":
            assert (
                _post(
                    client, headers, "mark-ready", context, new_idempotency_key(), order_id
                ).status_code
                == 200
            )
            payload.update(settlement_amount="14.00", settlement_payment_method_code=payment)
            if payment == "MIXED":
                payload["settlement_payments"] = [
                    {"payment_method_code": "CASH", "amount": "7.00"},
                    {"payment_method_code": "CARD", "amount": "7.00"},
                ]
        else:
            payload["cancellation_reason"] = "Requested refund before cutoff"
        key = new_idempotency_key()
        result = _post(client, headers, final_action, payload, key, order_id)
        assert result.status_code == 200
        stable = _state()
        assert _post(client, headers, final_action, payload, key, order_id).json() == result.json()
        assert _state() == stable
        assert len(result.json()["payments"]) == legs * 2
        assert Decimal(result.json()["remaining_balance_amount"]) == 0
        assert len({payment_row["id"] for payment_row in result.json()["payments"]}) == legs * 2


def test_identical_create_payload_with_distinct_keys_is_two_intentions(client: TestClient) -> None:
    headers, body = _setup(client)
    first = _post(client, headers, "create", body, new_idempotency_key())
    second = _post(client, headers, "create", body, new_idempotency_key())
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert _counts()["customer_orders"] == _counts()["idempotency_records"] == 2


@pytest.mark.parametrize("change", ["customer", "quantity", "payment", "cash_session"])
def test_reused_create_key_with_different_payload_is_conflict(
    client: TestClient, change: str
) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    assert _post(client, headers, "create", body, key).status_code == 201
    modified = deepcopy(body)
    if change == "customer":
        modified["customer_name"] = "Another customer"
    elif change == "quantity":
        modified["items"][0]["quantity"] = "5"
    elif change == "payment":
        modified["advance_amount"] = "10.00"
    else:
        modified["cash_session_id"] = str(uuid4())
    before = _state()
    response = _post(client, headers, "create", modified, key)
    assert response.status_code == 409
    assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _state() == before


def test_order_target_and_command_have_independent_identities(client: TestClient) -> None:
    headers, body = _setup(client)
    first = _post(client, headers, "create", body, new_idempotency_key()).json()
    second = _post(client, headers, "create", body, new_idempotency_key()).json()
    key, action = new_idempotency_key(), _context(body)
    assert _post(client, headers, "mark-ready", action, key, first["id"]).status_code == 200
    before = _state()
    wrong_target = _post(client, headers, "mark-ready", action, key, second["id"])
    wrong_command = _post(
        client,
        headers,
        "cancel",
        {**action, "cancellation_reason": "Cancellation requested"},
        key,
        first["id"],
    )
    for response in (wrong_target, wrong_command):
        assert response.status_code == 409
        assert response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _state() == before


@pytest.mark.parametrize("key_kind", ["absent", "invalid", "uuid4", "duplicate"])
def test_invalid_key_does_not_admit_order(client: TestClient, key_kind: str) -> None:
    headers, body = _setup(client)
    pairs = list(headers.items())
    if key_kind != "absent":
        value = {"invalid": "bad-key", "uuid4": str(uuid4())}.get(key_kind, new_idempotency_key())
        pairs.append(("Idempotency-Key", value))
        if key_kind == "duplicate":
            pairs.append(("Idempotency-Key", value))
    before = _state()
    assert client.post("/v1/orders", headers=pairs, json=body).status_code == 422
    assert _state() == before


def test_invalid_input_and_unavailable_transition_leave_identity_unused(client: TestClient) -> None:
    headers, body = _setup(client)
    key, before = new_idempotency_key(), _state()
    invalid = {**body, "advance_amount": "999.00"}
    assert _post(client, headers, "create", invalid, key).status_code == 400
    assert _state() == before
    created = _post(client, headers, "create", body, key)
    assert created.status_code == 201
    order_id, key = created.json()["id"], new_idempotency_key()
    deliver = {
        **_context(body),
        "settlement_amount": "14.00",
        "settlement_payment_method_code": "CASH",
    }
    before = _state()
    assert _post(client, headers, "deliver", deliver, key, order_id).status_code == 409
    assert _state() == before
    assert (
        _post(
            client, headers, "mark-ready", _context(body), new_idempotency_key(), order_id
        ).status_code
        == 200
    )
    assert _post(client, headers, "deliver", deliver, key, order_id).status_code == 200


@pytest.mark.parametrize(("surface", "action"), COMMANDS[1:])
def test_new_key_cannot_repeat_an_already_reached_transition(
    client: TestClient, surface: str, action: str
) -> None:
    headers, body, order_id, _ = _prepare(client, surface, action)
    assert (
        _post(client, headers, action, body, new_idempotency_key(), order_id, surface).status_code
        == 200
    )
    before = _state()
    response = _post(client, headers, action, body, new_idempotency_key(), order_id, surface)
    assert response.status_code == 409
    assert _state() == before


@pytest.mark.parametrize(("surface", "action"), COMMANDS)
def test_precommit_failure_rolls_back_command_payments_trace_and_identity(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, surface: str, action: str
) -> None:
    headers, body, order_id, branch_id = _prepare(client, surface, action)
    key, before = new_idempotency_key(), _state()
    original = OutboxWriter.append

    def fail_after_flush(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        session.flush()
        if kwargs["event_name"] == f"order.{EVENTS[action]}.v1":
            raise RuntimeError("Simulated order failure before commit")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail_after_flush)
        with pytest.raises(RuntimeError, match="Simulated order failure"):
            _post(client, headers, action, body, key, order_id, surface)
    assert _state() == before
    unknown = _recover(client, headers, action, body, key, surface=surface, branch_id=branch_id)
    assert unknown.status_code == 409
    assert unknown.json()["code"] == "IDEMPOTENCY_RESULT_UNKNOWN"
    assert _state() == before
    assert _post(client, headers, action, body, key, order_id, surface).status_code == (
        201 if action == "create" else 200
    )


@pytest.mark.parametrize(("surface", "action"), [("POS", "deliver"), ("BACKOFFICE", "cancel")])
def test_postcommit_response_loss_is_recovered_without_another_effect(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, surface: str, action: str
) -> None:
    from zeromerma_api.modules.orders.presentation import router

    headers, body, order_id, branch_id = _prepare(client, surface, action)
    key = new_idempotency_key()

    def lose_response(*args: Any, **kwargs: Any) -> Any:
        raise ConnectionError("Lost order response after commit")

    with monkeypatch.context() as patch:
        patch.setattr(router, "idempotency_response", lose_response)
        with pytest.raises(ConnectionError):
            _post(client, headers, action, body, key, order_id, surface)
    before = _state()
    replay = _post(client, headers, action, body, key, order_id, surface)
    recovery = _recover(client, headers, action, body, key, surface=surface, branch_id=branch_id)
    assert replay.status_code == recovery.status_code == 200
    assert replay.json() == recovery.json()
    assert _state() == before


def test_replay_keeps_historical_state_after_later_transitions_close_and_login(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.orders.application import services

    headers, body = _setup(client)
    create_key, ready_key = new_idempotency_key(), new_idempotency_key()
    created = _post(client, headers, "create", body, create_key)
    assert created.status_code == 201
    order_id, context = created.json()["id"], _context(body)
    ready = _post(client, headers, "mark-ready", context, ready_key, order_id)
    assert ready.status_code == 200
    assert (
        _post(
            client,
            headers,
            "deliver",
            {**context, "settlement_amount": "14.00", "settlement_payment_method_code": "CARD"},
            new_idempotency_key(),
            order_id,
        ).status_code
        == 200
    )
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(body["cash_session_id"]))
        cash.status, cash.closed_at = "CLOSED", datetime.now(UTC)
        order = session.get(CustomerOrder, UUID(order_id))
        order.customer_name = "Changed personal details"
        session.commit()

    def unexpected_pricing(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("Replay must not price an existing order again")

    monkeypatch.setattr(services, "_prepare_order_items", unexpected_pricing)
    fresh = _login(client)
    before = _state()
    assert _post(client, fresh, "create", body, create_key).json() == created.json()
    assert _post(client, fresh, "mark-ready", context, ready_key, order_id).json() == ready.json()
    assert _recover(client, fresh, "mark-ready", context, ready_key).json() == ready.json()
    assert _state() == before
    assert _post(client, fresh, "create", body, new_idempotency_key()).status_code == 409


def test_admin_replay_returns_ready_snapshot_after_delivery(client: TestClient) -> None:
    headers, body = _setup(client)
    body["advance_amount"] = "34.00"
    created = _post(client, headers, "create", body, new_idempotency_key()).json()
    admin, key = owner_headers(), new_idempotency_key()
    ready = _post(client, admin, "mark-ready", {}, key, created["id"], "BACKOFFICE")
    assert ready.status_code == 200
    assert (
        _post(
            client, admin, "deliver", {}, new_idempotency_key(), created["id"], "BACKOFFICE"
        ).status_code
        == 200
    )
    before = _state()
    assert (
        _post(client, admin, "mark-ready", {}, key, created["id"], "BACKOFFICE").json()
        == ready.json()
    )
    assert (
        _recover(
            client,
            admin,
            "mark-ready",
            {},
            key,
            surface="BACKOFFICE",
            branch_id=created["branch_id"],
        ).json()
        == ready.json()
    )
    wrong_branch = _recover(
        client, admin, "mark-ready", {}, key, surface="BACKOFFICE", branch_id=str(uuid4())
    )
    assert wrong_branch.status_code == 409
    assert "id" not in wrong_branch.json()
    assert _state() == before


def test_recovery_checks_actor_surface_station_cash_and_current_authority(
    client: TestClient,
) -> None:
    headers, body = _setup(client)
    key = new_idempotency_key()
    created = _post(client, headers, "create", body, key)
    assert created.status_code == 201
    before = _state()
    wrong_cash = _recover(client, headers, "create", {**body, "cash_session_id": str(uuid4())}, key)
    assert wrong_cash.status_code == 409
    other_station = _login(client, SEED_DESTINATION_WORKSTATION_CODE)
    changed = {**body, "workstation_code": SEED_DESTINATION_WORKSTATION_CODE}
    for response in (
        _recover(client, other_station, "create", changed, key),
        _post(client, other_station, "create", changed, key),
        _post(client, owner_headers(), "mark-ready", {}, key, created.json()["id"], "BACKOFFICE"),
    ):
        assert response.status_code in {403, 409}
        assert "id" not in response.json()
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        for grant in session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == user.id)
        ):
            grant.is_active = False
        session.commit()
    for response in (
        _recover(client, headers, "create", body, key),
        _post(client, headers, "create", body, key),
    ):
        assert response.status_code == 401
        assert response.json()["code"] == "SESSION_REVOKED"
    assert _state() == before


def test_cancel_only_operator_can_recover_without_manage_or_view(client: TestClient) -> None:
    headers, body = _setup(client)
    body.update(advance_amount="0.00", advance_payment_method_code=None)
    created = _post(client, headers, "create", body, new_idempotency_key()).json()
    with SessionLocal() as session:
        original = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        actor = User(
            email="order.cancel.only@validation.invalid",
            full_name="Cancellation operator",
            password_hash=original.password_hash,
            allowed_surfaces=["BACKOFFICE"],
            default_surface="BACKOFFICE",
        )
        role = Role(
            code="ORDER_CANCEL_ONLY_TEST", name="Order cancellation test", surfaces=["BACKOFFICE"]
        )
        session.add_all([actor, role])
        session.flush()
        capability = session.scalars(
            select(Permission).where(Permission.code == "orders.cancel")
        ).one()
        session.add(RolePermission(role_id=role.id, permission_id=capability.id))
        session.add(
            UserBranchAssignment(
                user_id=actor.id, branch_id=UUID(created["branch_id"]), is_default=True
            )
        )
        assignment = UserRoleAssignment(user_id=actor.id, role_id=role.id, scope_type="BRANCH_SET")
        session.add(assignment)
        session.flush()
        session.add(
            UserRoleAssignmentBranchScope(
                assignment_id=assignment.id, branch_id=UUID(created["branch_id"])
            )
        )
        session.commit()
    limited = login_headers(
        client,
        email="order.cancel.only@validation.invalid",
        password=SEED_USER_PASSWORD,
        audience="BACKOFFICE",
    )
    key = new_idempotency_key()
    canceled = _post(client, limited, "cancel", {}, key, created["id"], "BACKOFFICE")
    assert canceled.status_code == 200
    assert (
        _recover(
            client, limited, "cancel", {}, key, surface="BACKOFFICE", branch_id=created["branch_id"]
        ).json()
        == canceled.json()
    )
    assert client.get(f"/v1/admin/orders/{created['id']}", headers=limited).status_code == 403
    assert (
        _post(
            client, limited, "mark-ready", {}, new_idempotency_key(), created["id"], "BACKOFFICE"
        ).status_code
        == 403
    )
    # Another authorized actor still cannot use this operator's durable identity.
    assert (
        _recover(
            client,
            owner_headers(),
            "cancel",
            {},
            key,
            surface="BACKOFFICE",
            branch_id=created["branch_id"],
        ).status_code
        == 409
    )


def test_backoffice_body_correlation_key_is_not_a_compatibility_bypass(client: TestClient) -> None:
    headers, _, order_id, _ = _prepare(client, "BACKOFFICE", "mark-ready")
    before = _state()
    assert (
        client.post(
            _path("BACKOFFICE", "mark-ready", order_id),
            headers=headers,
            json={"idempotency_key": new_idempotency_key()},
        ).status_code
        == 422
    )
    assert (
        _post(
            client,
            headers,
            "mark-ready",
            {"idempotency_key": "old-correlation"},
            new_idempotency_key(),
            order_id,
            "BACKOFFICE",
        ).status_code
        == 422
    )
    assert _state() == before


def _domain_command(
    headers: dict[str, str],
    action: str,
    body: dict[str, Any],
    key: str,
    order_id: str | None = None,
    surface: str = "POS",
    *,
    recover: bool = False,
    backend_pid: dict[str, int] | None = None,
    entered: Event | None = None,
) -> IdempotencyResult:
    """Use real authority without HTTP user/session locks masking order concurrency."""
    cookies = SimpleCookie()
    cookies.load(headers["Cookie"])
    credential = cookies[COOKIE_NAMES[surface]].value
    with SessionLocal() as session:
        if backend_pid is not None:
            backend_pid["pid"] = session.scalar(select(func.pg_backend_pid()))
        record = session.scalars(
            select(AuthSession).where(
                AuthSession.credential_hash == secret_hash(credential),
                AuthSession.audience == surface,
                AuthSession.status == "ACTIVE",
            )
        ).one()
        actor = session.get(User, record.user_id)
        assert actor is not None
        user = resolve_authorization(session, actor, surface=surface)
        session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("orders.cancel" if action == "cancel" else "orders.manage",),
            mutation=not recover,
            surface=surface,
        )
        if entered is not None:
            entered.set()
        service = OrdersIdempotencyService()
        if surface == "BACKOFFICE":
            assert order_id is not None
            return service.execute_admin(
                session,
                current_user=user,
                command_code=action,
                order_id=UUID(order_id),
                key=UUID(key),
                request_id="order-concurrency-probe",
            )
        if recover:
            return service.recover_pos(
                session,
                current_user=user,
                command_code=action,
                key=UUID(key),
                workstation_code=body["workstation_code"],
                cash_session_id=UUID(body["cash_session_id"]),
            )
        schema = {
            "create": CreateCustomerOrderRequest,
            "mark-ready": OrderActionRequest,
            "deliver": DeliverCustomerOrderRequest,
            "cancel": CancelCustomerOrderRequest,
        }[action]
        return service.execute_pos(
            session,
            current_user=user,
            command_code=action,
            command=schema.model_validate(body),
            key=UUID(key),
            request_id="order-concurrency-probe",
            order_id=UUID(order_id) if order_id else None,
        )


def test_same_key_contention_and_uncommitted_recovery_are_bounded(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body = _setup(client)
    key, admitted, release = new_idempotency_key(), Event(), Event()
    original = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == "order.created.v1":
            admitted.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=1) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        future = pool.submit(_domain_command, headers, "create", body, key)
        try:
            assert admitted.wait(timeout=15)
            with pytest.raises(IdempotencyResultUnknown):
                _domain_command(headers, "create", body, key, recover=True)
            with pytest.raises(IdempotencyInProgress):
                _domain_command(headers, "create", body, key)
        finally:
            release.set()
        first = future.result(timeout=15)
    replay = _domain_command(headers, "create", body, key)
    assert not first.replayed and replay.replayed
    assert replay.payload == first.payload
    assert _counts()["customer_orders"] == _counts()["idempotency_records"] == 1


@pytest.mark.parametrize(
    ("winner", "rival", "rival_surface"),
    [
        ("deliver", "deliver", "POS"),
        ("deliver", "cancel", "POS"),
        ("cancel", "deliver", "POS"),
        ("deliver", "deliver", "BACKOFFICE"),
    ],
)
def test_order_lock_serializes_competing_payments_and_cross_surface_transitions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, winner: str, rival: str, rival_surface: str
) -> None:
    """Distinct POS cash rows cannot substitute for the shared customer-order lock."""
    headers, create = _setup(client)
    if rival_surface == "BACKOFFICE":
        create["advance_amount"] = "34.00"
    created = _post(client, headers, "create", create, new_idempotency_key()).json()
    order_id, context = created["id"], _context(create)
    assert (
        _post(client, headers, "mark-ready", context, new_idempotency_key(), order_id).status_code
        == 200
    )
    deliver = (
        {**context, "settlement_amount": "14.00", "settlement_payment_method_code": "CASH"}
        if rival_surface == "POS"
        else dict(context)
    )
    cancel = {**context, "cancellation_reason": "Concurrent cancellation requested"}
    winner_body = deliver if winner == "deliver" else cancel
    if rival_surface == "POS":
        rival_station = "POS-ORDER-RACE-02"
        with SessionLocal() as session:
            first_cash = session.get(CashSession, UUID(create["cash_session_id"]))
            assert first_cash is not None
            session.add(
                Workstation(
                    branch_id=first_cash.branch_id,
                    code=rival_station,
                    name="Concurrent order workstation",
                )
            )
            session.commit()
        rival_headers, rival_create = _setup(client, rival_station)
        rival_body = {
            **(deliver if rival == "deliver" else cancel),
            **_context(rival_create),
        }
        with SessionLocal() as session:
            first_cash = session.get(CashSession, UUID(create["cash_session_id"]))
            rival_cash = session.get(CashSession, UUID(rival_create["cash_session_id"]))
            assert first_cash is not None and rival_cash is not None
            assert first_cash.branch_id == rival_cash.branch_id
            assert first_cash.id != rival_cash.id
            assert first_cash.workstation_id != rival_cash.workstation_id
            assert first_cash.user_id != rival_cash.user_id
    else:
        rival_headers, rival_body = owner_headers(), {}
    held, release, entered = Event(), Event(), Event()
    rival_pid: dict[str, int] = {}
    blocker_pid: dict[str, int] = {}
    before, original = _counts(), OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == f"order.{EVENTS[winner]}.v1" and not held.is_set():
            blocker_pid["pid"] = transaction_probe(session).backend_pid
            held.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(
            _domain_command, headers, winner, winner_body, new_idempotency_key(), order_id
        )
        try:
            assert held.wait(timeout=15)
            second = pool.submit(
                _domain_command,
                rival_headers,
                rival,
                rival_body,
                new_idempotency_key(),
                order_id,
                rival_surface,
                backend_pid=rival_pid,
                entered=entered,
            )
            assert entered.wait(timeout=10)
            wait_until_blocked(rival_pid["pid"], blocker_pid["pid"])
        finally:
            release.set()
        assert first.result(timeout=15).status_code == 200
        with pytest.raises(OrderStateConflictError):
            second.result(timeout=15)
    after = _counts()
    assert after["audit_log"] == before["audit_log"] + 1
    assert after["outbox_events"] == before["outbox_events"] + 1
    assert after["idempotency_records"] == before["idempotency_records"] + 1
    assert after["customer_order_payments"] == before["customer_order_payments"] + int(
        rival_surface == "POS"
    )
    with SessionLocal() as session:
        assert session.get(CustomerOrder, UUID(order_id)).status == (
            "DELIVERED" if winner == "deliver" else "CANCELED"
        )


def test_unrelated_orders_do_not_share_a_command_lock(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    contexts = [
        _setup(client, station)
        for station in (SEED_WORKSTATION_CODE, SEED_DESTINATION_WORKSTATION_CODE)
    ]
    ids = [
        _post(client, headers, "create", create, new_idempotency_key()).json()["id"]
        for headers, create in contexts
    ]
    barrier, original = Barrier(2), OutboxWriter.append

    def meet(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == "order.ready.v1":
            barrier.wait(timeout=15)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", meet)
        futures = [
            pool.submit(
                _domain_command,
                headers,
                "mark-ready",
                _context(create),
                new_idempotency_key(),
                order_id,
            )
            for (headers, create), order_id in zip(contexts, ids, strict=True)
        ]
        results = [future.result(timeout=25) for future in futures]
    assert all(result.status_code == 200 and not result.replayed for result in results)
    assert {result.payload["id"] for result in results} == set(ids)


def test_simultaneous_http_retries_return_one_order_and_payment(client: TestClient) -> None:
    headers, body = _setup(client)
    key, barrier = new_idempotency_key(), Barrier(3)

    def submit() -> Any:
        with TestClient(create_app(), base_url="https://testserver") as other:
            barrier.wait(timeout=15)
            return _post(other, headers, "create", body, key)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(submit) for _ in range(3)]
        responses = [future.result(timeout=30) for future in futures]
    assert all(response.status_code == 201 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    assert sum(response.headers["Idempotency-Replayed"] == "false" for response in responses) == 1
    assert (
        _counts()["customer_orders"]
        == _counts()["customer_order_payments"]
        == _counts()["idempotency_records"]
        == 1
    )


def test_order_command_latency_is_observed_without_a_production_sla(
    client: TestClient, record_testsuite_property: Any
) -> None:
    headers, body = _setup(client)
    timings: dict[str, list[float]] = {"new": [], "replay": []}
    for _ in range(5):
        key, snapshots = new_idempotency_key(), []
        for kind in timings:
            started = perf_counter()
            response = _post(client, headers, "create", body, key)
            timings[kind].append((perf_counter() - started) * 1000)
            assert response.status_code == 201
            snapshots.append(response.json())
        assert snapshots[0] == snapshots[1]
    record_testsuite_property(
        "order_latency_environment",
        "TestClient / guarded disposable PostgreSQL / two-line order with advance",
    )
    record_testsuite_property("order_latency_samples_per_path", 5)
    for kind, samples in timings.items():
        record_testsuite_property(f"order_latency_{kind}_median_ms", round(median(samples), 3))
