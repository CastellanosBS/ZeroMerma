"""Return/refund acceptance against guarded, disposable PostgreSQL."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from http.cookies import SimpleCookie
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
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
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
from zeromerma_api.modules.inventory.infrastructure.models import InventoryMovement
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.returns.application.idempotency import ReturnCommitService
from zeromerma_api.modules.returns.application.schemas import ReturnCommitRequest
from zeromerma_api.modules.returns.domain.exceptions import SaleReturnConflictError
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.infrastructure.models import Sale, SaleLine
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.concurrency import transaction_probe, wait_until_blocked
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email

ENDPOINT = "/v1/returns/commit"
DISPOSITIONS = ["RESTOCK_COUNTER", "RESTOCK_BACKROOM", "SEND_TO_WASTE"]


def _login(client: TestClient, workstation: str = SEED_WORKSTATION_CODE) -> dict[str, str]:
    return login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )


def _sale(
    client: TestClient,
    headers: dict[str, str],
    cash_id: str,
    *,
    payment: str = "CASH",
    workstation: str = SEED_WORKSTATION_CODE,
) -> dict[str, Any]:
    with SessionLocal() as session:
        product = session.scalar(
            select(Product.id).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
        )
        product_class = session.scalar(
            select(ProductClass.id).where(ProductClass.code == SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
        )
    payments = [{"payment_method_code": payment, "tendered_amount": "96.00"}]
    if payment == "MIXED":
        payments = [
            {"payment_method_code": "CARD", "tendered_amount": "20.00"},
            {"payment_method_code": "CASH", "tendered_amount": "100.00"},
        ]
    response = client.post(
        "/v1/sales/confirm",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": workstation,
            "cash_session_id": cash_id,
            "lines": [
                {"capture_mode": "PRODUCT_DIRECT", "product_id": str(product), "quantity": "4"},
                {
                    "capture_mode": "CLASS_CAPTURE",
                    "product_class_id": str(product_class),
                    "quantity": "2",
                },
            ],
            "payments": payments,
        },
    )
    assert response.status_code == 201
    detail = client.get(
        f"/v1/returns/sales/{response.json()['id']}",
        headers=headers,
        params={"workstation_code": workstation},
    )
    assert detail.status_code == 200
    return detail.json()


def _setup(
    client: TestClient,
    *,
    workstation: str = SEED_WORKSTATION_CODE,
    capture: str = "PRODUCT_DIRECT",
    payment: str = "CASH",
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    headers = login_headers(
        client,
        email=transfer_cashier_email(workstation),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )
    opening = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": workstation, "opening_amount": "200.00"},
    )
    assert opening.status_code == 201
    sale = _sale(client, headers, opening.json()["id"], payment=payment, workstation=workstation)
    line = next(item for item in sale["lines"] if item["capture_mode"] == capture)
    with SessionLocal() as session:
        product = session.scalar(
            select(Product.id).where(Product.code == SEED_PRODUCT_CONCHA_VAN_CODE)
        )
    return (
        headers,
        {
            "workstation_code": workstation,
            "cash_session_id": opening.json()["id"],
            "original_sale_id": sale["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "notes": "Private return instructions",
            "lines": [
                {
                    "original_sale_line_id": line["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_COUNTER",
                    "exact_product_id": str(product) if capture == "CLASS_CAPTURE" else None,
                }
            ],
        },
        sale,
    )


def _post(client: TestClient, headers: dict[str, str], body: dict[str, Any], key: str) -> Any:
    return client.post(ENDPOINT, headers={**headers, "Idempotency-Key": key}, json=body)


def _recover(client: TestClient, headers: dict[str, str], body: dict[str, Any], key: str) -> Any:
    return client.get(
        f"/v1/returns/confirmations/{key}",
        headers=headers,
        params={name: body[name] for name in ("workstation_code", "cash_session_id")},
    )


def _counts() -> dict[str, int]:
    with SessionLocal() as session:
        result = {
            model.__tablename__: session.scalar(select(func.count()).select_from(model))
            for model in (SaleReturn, SaleReturnLine, InventoryMovement)
        }
        for model, predicate in (
            (
                FinancialEntry,
                FinancialEntry.financial_operation_id.in_(
                    select(FinancialOperation.id).where(FinancialOperation.kind == "SALE_REFUND")
                ),
            ),
            (AuditLog, AuditLog.action.like("sale_return.%")),
            (OutboxEvent, OutboxEvent.event_name.like("sale_return.%")),
            (IdempotencyRecord, IdempotencyRecord.operation_code == "return.commit"),
        ):
            result[model.__tablename__] = session.scalar(
                select(func.count()).select_from(model).where(predicate)
            )
        return result


def _state() -> tuple[Any, ...]:
    with SessionLocal() as session:
        returns = session.execute(
            select(SaleReturn.id, SaleReturn.total_refund_amount).order_by(SaleReturn.id)
        ).all()
        lines = session.execute(
            select(
                SaleReturnLine.id,
                SaleReturnLine.returned_quantity,
                SaleReturnLine.refund_line_total_amount,
            ).order_by(SaleReturnLine.id)
        ).all()
        movements = session.execute(
            select(FinancialEntry.id, FinancialEntry.amount)
            .where(
                FinancialEntry.financial_operation_id.in_(
                    select(FinancialOperation.id).where(FinancialOperation.kind == "SALE_REFUND")
                )
            )
            .order_by(FinancialEntry.id)
        ).all()
    return _counts(), returns, lines, movements


@pytest.mark.parametrize("capture", ["PRODUCT_DIRECT", "CLASS_CAPTURE"])
@pytest.mark.parametrize("disposition", DISPOSITIONS)
@pytest.mark.parametrize("full", [False, True])
def test_replay_preserves_return_refund_and_disposition_without_repeating_effects(
    client: TestClient,
    capture: str,
    disposition: str,
    full: bool,
) -> None:
    headers, body, sale = _setup(client, capture=capture)
    original = next(
        item for item in sale["lines"] if item["id"] == body["lines"][0]["original_sale_line_id"]
    )
    body["lines"][0]["disposition_code"] = disposition
    if full:
        body["lines"][0]["returned_quantity"] = original["quantity"]
    key, before = new_idempotency_key(), _counts()
    first = _post(
        client, {**headers, "X-Request-ID": "81c07ab4-e624-5fce-81dc-4793d455993f"}, body, key
    )
    assert first.status_code == 201
    assert first.headers["Idempotency-Replayed"] == "false"
    receipt, committed = first.json(), _state()
    assert receipt["status"] == "COMMITTED"
    assert receipt["refund_method_code"] == "CASH"
    assert receipt["original_sale_id"] == sale["id"]
    assert receipt["lines"][0]["disposition_code"] == disposition
    assert (
        not {"notes", "created_by", "operator_email", "operator_full_name", "audit_summary"}
        & receipt.keys()
    )
    second = _post(
        client, {**headers, "X-Request-ID": "972dfdc1-1db0-5f31-a1ea-8b7bd668a356"}, body, key
    )
    recovered = _recover(client, headers, body, key)
    assert second.status_code == 201 and recovered.status_code == 200
    assert second.json() == recovered.json() == receipt
    assert (
        second.headers["Idempotency-Replayed"]
        == recovered.headers["Idempotency-Replayed"]
        == "true"
    )
    assert _state() == committed
    after = _counts()
    for table in (
        "sale_returns",
        "sale_return_lines",
        "financial_entries",
        "audit_log",
        "outbox_events",
        "idempotency_records",
    ):
        assert after[table] == before[table] + 1
    # Dispositions are durable declarations; canonical physical materialization remains 051.
    assert after["inventory_movements"] == before["inventory_movements"]
    with SessionLocal() as session:
        movement = session.get(
            FinancialEntry, UUID(receipt["financial_refund"]["entries"][0]["id"])
        )
        assert movement.direction == "OUT"
        assert session.get(FinancialOperation, movement.financial_operation_id).subject_id == UUID(
            sale["id"]
        )
        assert movement.cash_session_id == UUID(body["cash_session_id"])
        assert movement.amount == Decimal(receipt["total_refund_amount"])
        record = session.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        )
        assert record.response_payload == receipt
        assert "Private return instructions" not in str(record.response_payload)
        audit = session.scalar(select(AuditLog).where(AuditLog.resource_id == receipt["id"]))
        event = session.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == receipt["id"]))
        for metadata in (audit.metadata_, event.payload):
            assert metadata["refund_cash_movement_id"] == receipt["refund_cash_movement_id"]
        assert audit.metadata_["idempotency_key"] == key
        assert event.headers["idempotency_key"] == key


@pytest.mark.parametrize("payment", ["CASH", "CARD", "MIXED"])
def test_distinct_partial_returns_keep_exact_admin_cash_links(
    client: TestClient,
    payment: str,
) -> None:
    headers, body, _ = _setup(client, payment=payment)
    receipts = [_post(client, headers, body, new_idempotency_key()) for _ in range(2)]
    assert all(result.status_code == 201 for result in receipts)
    payloads = [result.json() for result in receipts]
    assert payloads[0]["total_refund_amount"] == payloads[1]["total_refund_amount"]
    assert (
        payloads[0]["financial_refund"]["financial_operation_id"]
        != payloads[1]["financial_refund"]["financial_operation_id"]
    )
    admin = owner_headers()
    for receipt in payloads:
        detail = client.get(
            f"/v1/admin/returns-corrections/returns/{receipt['id']}",
            headers=admin,
        )
        assert detail.status_code == 200
        assert (
            detail.json()["refund_impact"]["linked_cash_movement_id"]
            == receipt["refund_cash_movement_id"]
        )
    listing = client.get("/v1/admin/returns-corrections/returns", headers=admin)
    assert listing.status_code == 200 and listing.json()["total"] == 2


@pytest.mark.parametrize("change", ["quantity", "notes", "reason", "disposition", "sale", "cash"])
def test_changed_payload_cannot_reuse_an_identity(client: TestClient, change: str) -> None:
    headers, body, _ = _setup(client)
    key = new_idempotency_key()
    assert _post(client, headers, body, key).status_code == 201
    before, changed = _state(), deepcopy(body)
    if change == "quantity":
        changed["lines"][0]["returned_quantity"] = "2.000"
    elif change == "disposition":
        changed["lines"][0]["disposition_code"] = "SEND_TO_WASTE"
    else:
        field, value = {
            "notes": ("notes", "Changed instructions"),
            "reason": ("reason_code", "CUSTOMER_REGRET"),
            "sale": ("original_sale_id", str(uuid4())),
            "cash": ("cash_session_id", str(uuid4())),
        }[change]
        changed[field] = value
    response = _post(client, headers, changed, key)
    assert response.status_code == 409 and response.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _state() == before


@pytest.mark.parametrize("kind", ["missing", "uuid4", "malformed", "duplicate"])
def test_invalid_keys_never_reserve_an_identity(client: TestClient, kind: str) -> None:
    headers, body, _ = _setup(client)
    request_headers: Any = dict(headers)
    if kind == "duplicate":
        request_headers = [
            *headers.items(),
            ("Idempotency-Key", new_idempotency_key()),
            ("Idempotency-Key", new_idempotency_key()),
        ]
    elif kind != "missing":
        request_headers["Idempotency-Key"] = str(uuid4()) if kind == "uuid4" else "invalid"
    before = _state()
    response = client.post(ENDPOINT, headers=request_headers, json=body)
    assert response.status_code == 422
    assert _state() == before


@pytest.mark.parametrize("invalid", ["CARD", "MIXED", "PROVIDER_PENDING"])
def test_unavailable_external_refunds_never_become_successful_effects(
    client: TestClient,
    invalid: str,
) -> None:
    headers, body, _ = _setup(client)
    body["refund_method_code"] = invalid
    key, before = new_idempotency_key(), _state()
    rejected = _post(client, headers, body, key)
    assert rejected.status_code in {400, 422}
    assert _recover(client, headers, body, key).status_code == 409
    assert _state() == before
    body["refund_method_code"] = "CASH"
    assert _post(client, headers, body, key).status_code == 201


def test_invalid_request_and_unknown_sale_do_not_consume_key(client: TestClient) -> None:
    headers, body, _ = _setup(client)
    key, before = new_idempotency_key(), _state()
    missing_cash = {name: value for name, value in body.items() if name != "cash_session_id"}
    assert _post(client, headers, missing_cash, key).status_code == 422
    unknown = {**body, "original_sale_id": str(uuid4())}
    assert _post(client, headers, unknown, key).status_code == 404
    duplicate = {**body, "lines": [body["lines"][0], body["lines"][0]]}
    assert _post(client, headers, duplicate, key).status_code in {400, 422}
    assert _state() == before
    assert _post(client, headers, body, key).status_code == 201


def test_fractional_returns_conserve_net_cents_and_last_residual(client: TestClient) -> None:
    headers, body, sale = _setup(client)
    # A controlled historical net line of one cent over three milliunits exposes
    # per-request HALF_UP over-refunds without relying on current catalog prices.
    with SessionLocal() as session:
        line = session.get(SaleLine, UUID(body["lines"][0]["original_sale_line_id"]))
        line.quantity, line.unit_price, line.line_total_amount = (
            Decimal("0.003"),
            Decimal("3.33"),
            Decimal("0.01"),
        )
        session.commit()
    body["lines"][0]["returned_quantity"] = "0.001"
    results = [_post(client, headers, body, new_idempotency_key()) for _ in range(3)]
    assert all(result.status_code == 201 for result in results)
    amounts = [Decimal(result.json()["total_refund_amount"]) for result in results]
    assert amounts == [Decimal("0.00"), Decimal("0.01"), Decimal("0.00")]
    before = _state()
    assert _post(client, headers, body, new_idempotency_key()).status_code == 409
    assert _state() == before
    detail = client.get(
        f"/v1/returns/sales/{sale['id']}",
        headers=headers,
        params={"workstation_code": SEED_WORKSTATION_CODE},
    )
    returned = next(
        item
        for item in detail.json()["lines"]
        if item["id"] == body["lines"][0]["original_sale_line_id"]
    )
    assert Decimal(returned["already_refunded_amount"]) == Decimal("0.01")
    assert Decimal(returned["remaining_refundable_amount"]) == Decimal("0.00")


def test_net_line_amount_controls_refund_and_final_partial_exhausts_budget(
    client: TestClient,
) -> None:
    headers, body, _ = _setup(client)
    with SessionLocal() as session:
        line = session.get(SaleLine, UUID(body["lines"][0]["original_sale_line_id"]))
        line.quantity, line.unit_price, line.line_total_amount = (
            Decimal("3.000"),
            Decimal("18.00"),
            Decimal("10.00"),
        )
        session.commit()
    receipts = [_post(client, headers, body, new_idempotency_key()) for _ in range(3)]
    assert all(result.status_code == 201 for result in receipts)
    assert [Decimal(result.json()["total_refund_amount"]) for result in receipts] == [
        Decimal("3.33"),
        Decimal("3.34"),
        Decimal("3.33"),
    ]


@pytest.mark.parametrize("inconsistency", ["line", "sale"])
def test_inconsistent_historical_refund_budget_is_rejected_without_new_effect(
    client: TestClient,
    inconsistency: str,
) -> None:
    headers, body, sale = _setup(client)
    assert _post(client, headers, body, new_idempotency_key()).status_code == 201
    with SessionLocal() as session:
        if inconsistency == "line":
            line = session.get(SaleLine, UUID(body["lines"][0]["original_sale_line_id"]))
            line.line_total_amount = Decimal("1.00")
        else:
            session.get(Sale, UUID(sale["id"])).total_amount = Decimal("1.00")
        session.commit()
    before = _state()
    assert _post(client, headers, body, new_idempotency_key()).status_code == 409
    assert _state() == before


@pytest.mark.parametrize("high_risk", [False, True])
def test_failure_after_real_effect_flush_rolls_back_the_entire_command(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    high_risk: bool,
) -> None:
    headers, body, sale = _setup(client)
    if high_risk:
        with SessionLocal() as session:
            session.get(Sale, UUID(sale["id"])).confirmed_at = datetime.now(UTC) - timedelta(
                days=365
            )
            session.commit()
        body["high_risk_acknowledged"] = True
    key, before, append = new_idempotency_key(), _state(), OutboxWriter.append
    target = (
        "sale_return.backoffice_review_requested.v1" if high_risk else "sale_return.committed.v1"
    )

    def fail(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == target:
            session.flush()
            assert session.scalar(select(func.count()).select_from(SaleReturn)) == 1
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(FinancialEntry)
                    .where(
                        FinancialEntry.financial_operation_id.in_(
                            select(FinancialOperation.id).where(
                                FinancialOperation.kind == "SALE_REFUND"
                            )
                        )
                    )
                )
                == 1
            )
            raise RuntimeError("Injected return failure after actual flush")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail)
        with pytest.raises(RuntimeError, match="Injected return failure"):
            _post(client, headers, body, key)
    assert _state() == before
    assert _post(client, headers, body, key).status_code == 201
    assert _counts()["outbox_events"] == before[0]["outbox_events"] + (2 if high_risk else 1)


def test_response_lost_after_commit_recovers_without_another_refund(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from zeromerma_api.modules.returns.presentation import router

    headers, body, _ = _setup(client)
    key = new_idempotency_key()

    def lost(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("Lost return acknowledgement after commit")

    with monkeypatch.context() as patch:
        patch.setattr(router, "idempotency_response", lost)
        with pytest.raises(RuntimeError, match="Lost return acknowledgement"):
            _post(client, headers, body, key)
    committed = _state()
    assert committed[0]["sale_returns"] == committed[0]["financial_entries"] == 1
    recovered = _recover(client, headers, body, key)
    replay = _post(client, headers, body, key)
    assert recovered.status_code == 200 and replay.status_code == 201
    assert recovered.json() == replay.json()
    assert _state() == committed


def test_replay_survives_later_returns_closed_cash_and_session_rotation(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from zeromerma_api.modules.returns.application.services import ReturnsCommandService

    headers, body, _ = _setup(client)
    key = new_idempotency_key()
    original = _post(client, headers, body, key)
    assert original.status_code == 201
    assert _post(client, headers, body, new_idempotency_key()).status_code == 201
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(body["cash_session_id"]))
        cash.status, cash.closed_at = "CLOSED", datetime.now(UTC)
        session.commit()
    fresh = _login(client)
    before = _state()

    def unexpected(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("A return replay must not execute the domain command again")

    with monkeypatch.context() as patch:
        patch.setattr(ReturnsCommandService, "commit_return", unexpected)
        assert _post(client, fresh, body, key).json() == original.json()
        assert _recover(client, fresh, body, key).json() == original.json()
    assert _state() == before
    assert _post(client, fresh, body, new_idempotency_key()).status_code == 409
    opening = client.post(
        "/v1/cash-sessions/open",
        headers={**fresh, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "100.00"},
    )
    assert opening.status_code == 201
    current = {**body, "cash_session_id": opening.json()["id"]}
    result = _post(client, fresh, current, new_idempotency_key())
    assert result.status_code == 201
    assert result.json()["cash_session_id"] != body["cash_session_id"]


def test_recovery_reauthorizes_actor_surface_station_cash_and_scope(client: TestClient) -> None:
    headers, body, _ = _setup(client)
    key = new_idempotency_key()
    assert _post(client, headers, body, key).status_code == 201
    before = _state()
    assert (
        _recover(client, headers, {**body, "cash_session_id": str(uuid4())}, key).status_code == 409
    )
    assert _recover(client, owner_headers(), body, key).status_code in {401, 403}
    other_station = _login(client, SEED_DESTINATION_WORKSTATION_CODE)
    changed = {**body, "workstation_code": SEED_DESTINATION_WORKSTATION_CODE}
    assert _recover(client, other_station, changed, key).status_code == 409
    fresh = _login(client)
    assert _recover(client, fresh, body, key).status_code == 200
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        for grant in session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == user.id)
        ):
            grant.is_active = False
        session.commit()
    denied = _recover(client, fresh, body, key)
    assert denied.status_code == 401 and denied.json()["code"] == "SESSION_REVOKED"
    assert _state() == before


def test_other_authorized_pos_actor_cannot_recover_another_operators_refund(
    client: TestClient,
) -> None:
    headers, body, sale = _setup(client)
    key = new_idempotency_key()
    assert _post(client, headers, body, key).status_code == 201
    with SessionLocal() as session:
        source = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        actor = User(
            email="return.other@validation.invalid",
            full_name="Other return operator",
            password_hash=source.password_hash,
            allowed_surfaces=["POS"],
            default_surface="POS",
        )
        session.add(actor)
        session.flush()
        session.add(
            UserBranchAssignment(
                user_id=actor.id, branch_id=UUID(sale["branch"]["id"]), is_default=True
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
        email="return.other@validation.invalid",
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    before = _state()
    assert _recover(client, other, body, key).status_code == 409
    assert _state() == before


@pytest.mark.parametrize("link", ["missing", "other_refund", "malformed", "nonexistent"])
def test_backoffice_never_guesses_a_refund_link_for_unlinked_history(
    client: TestClient, link: str
) -> None:
    headers, body, _ = _setup(client)
    receipt = _post(client, headers, body, new_idempotency_key()).json()
    other_receipt = _post(client, headers, body, new_idempotency_key()).json()
    with SessionLocal() as session:
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "sale_return.committed", AuditLog.resource_id == receipt["id"]
            )
        )
        metadata = dict(audit.metadata_)
        metadata.pop("refund_cash_movement_id")
        if link != "missing":
            metadata["refund_cash_movement_id"] = {
                "other_refund": other_receipt["refund_cash_movement_id"],
                "malformed": "not-a-uuid",
                "nonexistent": str(uuid4()),
            }[link]
        audit.metadata_ = metadata
        session.commit()
    detail = client.get(
        f"/v1/admin/returns-corrections/returns/{receipt['id']}", headers=owner_headers()
    )
    assert detail.status_code == 200
    assert detail.json()["refund_impact"]["linked_cash_movement_id"] is None


def _domain(
    headers: dict[str, str],
    body: dict[str, Any],
    key: str,
    *,
    recover: bool = False,
    backend_pid: dict[str, int] | None = None,
    entered: Event | None = None,
) -> IdempotencyResult:
    """Use real authority without HTTP identity locks masking sale-row contention."""
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
        actor = session.get(User, record.user_id)
        user = resolve_authorization(session, actor, surface="POS")
        session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("returns_corrections.manage",),
            mutation=not recover,
            surface="POS",
        )
        if entered is not None:
            entered.set()
        service = ReturnCommitService()
        if recover:
            return service.recover(
                session,
                current_user=user,
                key=UUID(key),
                workstation_code=body["workstation_code"],
                cash_session_id=UUID(body["cash_session_id"]),
            )
        return service.commit(
            session,
            current_user=user,
            command=ReturnCommitRequest.model_validate(body),
            key=UUID(key),
            request_id="return-concurrency-probe",
        )


def test_same_key_contention_is_bounded_and_uncommitted_result_stays_unknown(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, body, _ = _setup(client)
    held, release, key = Event(), Event(), new_idempotency_key()
    append = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == "sale_return.committed.v1" and not held.is_set():
            held.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(_domain, headers, body, key)
        try:
            assert held.wait(timeout=15)
            started = monotonic()
            with pytest.raises(IdempotencyInProgress):
                _domain(headers, body, key)
            assert monotonic() - started < 5
            with pytest.raises(IdempotencyResultUnknown):
                _domain(headers, body, key, recover=True)
        finally:
            release.set()
        result = first.result(timeout=15)
    replay = _domain(headers, body, key)
    assert replay.replayed and replay.payload == result.payload
    assert _counts()["sale_returns"] == _counts()["financial_entries"] == 1


@pytest.mark.parametrize("quantity", ["1.000", "3.000"])
def test_competing_partial_returns_recalculate_remaining_right_under_real_postgres_lock(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    quantity: str,
) -> None:
    """Separate cash rows leave the shared sale entitlement as the contested boundary."""
    headers, body, _ = _setup(client)
    body["lines"][0]["returned_quantity"] = quantity
    rival_station = "POS-RETURN-RACE-02"
    with SessionLocal() as session:
        first_cash = session.get(CashSession, UUID(body["cash_session_id"]))
        assert first_cash is not None
        session.add(
            Workstation(
                branch_id=first_cash.branch_id,
                code=rival_station,
                name="Concurrent return workstation",
            )
        )
        session.commit()
    rival_headers = login_headers(
        client,
        email=transfer_cashier_email(rival_station),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=rival_station,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**rival_headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": rival_station, "opening_amount": "200.00"},
    )
    assert opened.status_code == 201
    rival_body = {
        **deepcopy(body),
        "workstation_code": rival_station,
        "cash_session_id": opened.json()["id"],
    }
    with SessionLocal() as session:
        first_cash = session.get(CashSession, UUID(body["cash_session_id"]))
        rival_cash = session.get(CashSession, UUID(rival_body["cash_session_id"]))
        assert first_cash is not None and rival_cash is not None
        assert first_cash.branch_id == rival_cash.branch_id
        assert first_cash.id != rival_cash.id
        assert first_cash.workstation_id != rival_cash.workstation_id
        assert first_cash.user_id != rival_cash.user_id
    held, release, entered, pid = Event(), Event(), Event(), {}
    blocker_pid: dict[str, int] = {}
    append = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == "sale_return.committed.v1" and not held.is_set():
            blocker_pid["pid"] = transaction_probe(session).backend_pid
            held.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(_domain, headers, body, new_idempotency_key())
        try:
            assert held.wait(timeout=15)
            second = pool.submit(
                _domain,
                rival_headers,
                rival_body,
                new_idempotency_key(),
                backend_pid=pid,
                entered=entered,
            )
            assert entered.wait(timeout=10)
            wait_until_blocked(pid["pid"], blocker_pid["pid"])
        finally:
            release.set()
        assert first.result(timeout=15).status_code == 201
        if quantity == "3.000":
            with pytest.raises(SaleReturnConflictError):
                second.result(timeout=15)
        else:
            assert second.result(timeout=15).status_code == 201
    expected = 1 if quantity == "3.000" else 2
    counts = _counts()
    assert (
        counts["sale_returns"]
        == counts["financial_entries"]
        == counts["idempotency_records"]
        == expected
    )
    assert counts["audit_log"] == counts["outbox_events"] == expected


def test_unrelated_sales_can_refund_without_a_global_command_lock(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contexts = [
        _setup(client, workstation=station)
        for station in (SEED_WORKSTATION_CODE, SEED_DESTINATION_WORKSTATION_CODE)
    ]
    barrier, append = Barrier(2), OutboxWriter.append

    def meet(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = append(self, session, **kwargs)
        if kwargs["event_name"] == "sale_return.committed.v1":
            barrier.wait(timeout=15)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", meet)
        futures = [
            pool.submit(_domain, headers, payload, new_idempotency_key())
            for headers, payload, _sale_detail in contexts
        ]
        results = [future.result(timeout=25) for future in futures]
    assert all(result.status_code == 201 and not result.replayed for result in results)


def test_two_http_clients_replay_one_refund(client: TestClient) -> None:
    headers, body, _ = _setup(client)
    key, barrier = new_idempotency_key(), Barrier(2)

    def submit() -> Any:
        with TestClient(create_app(), base_url="https://testserver") as other:
            barrier.wait(timeout=15)
            return _post(other, headers, body, key)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        responses = [future.result(timeout=30) for future in futures]
    assert all(response.status_code == 201 for response in responses)
    assert responses[0].json() == responses[1].json()
    assert sorted(response.headers["Idempotency-Replayed"] for response in responses) == [
        "false",
        "true",
    ]
    assert _counts()["sale_returns"] == _counts()["financial_entries"] == 1


def test_return_latency_is_observed_without_a_production_sla(
    client: TestClient,
    record_testsuite_property: Any,
) -> None:
    headers, body, _ = _setup(client)
    body["lines"][0]["returned_quantity"] = "0.100"
    timings: dict[str, list[float]] = {"new": [], "replay": []}
    for _ in range(5):
        key = new_idempotency_key()
        for kind in timings:
            started = perf_counter()
            assert _post(client, headers, body, key).status_code == 201
            timings[kind].append((perf_counter() - started) * 1000)
    record_testsuite_property(
        "return_latency_environment", "TestClient / disposable PostgreSQL / partial CASH refund"
    )
    record_testsuite_property("return_latency_samples_per_path", 5)
    for kind, samples in timings.items():
        record_testsuite_property(f"return_latency_{kind}_median_ms", round(median(samples), 3))
