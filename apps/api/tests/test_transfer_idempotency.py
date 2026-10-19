from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from http.cookies import SimpleCookie
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    COOKIE_NAMES,
    SessionAuthentication,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.transfers.application import physical_workflow
from zeromerma_api.modules.transfers.application.admin_schemas import AdminTransferReceiveRequest
from zeromerma_api.modules.transfers.application.idempotency import TransferCommandServiceWrapper
from zeromerma_api.modules.transfers.domain.exceptions import TransferValidationError
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.inventory import seed_test_inventory
from zeromerma_api.testing.sessions import login_headers


def _setup() -> tuple[dict[str, str], dict[str, Any]]:
    headers = owner_headers()
    with SessionLocal() as session:
        origin = session.scalar(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE))
        destination = session.scalar(
            select(Branch.id).where(Branch.code == SEED_DESTINATION_BRANCH_CODE)
        )
        product = session.scalar(
            select(Product.id).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        )
        actor = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert origin is not None and destination is not None and product is not None
        assert actor is not None
        seed_test_inventory(
            session,
            branch_id=origin,
            actor_user_id=actor,
            product_quantities={product: Decimal(100)},
            location_code="BACKROOM",
            fixture_reference="Transfer idempotency explicit origin stock",
        )
    return headers, {
        "origin_branch_id": str(origin),
        "destination_branch_id": str(destination),
        "notes": "Private transfer note",
        "lines": [{"product_id": str(product), "quantity": "5.000"}],
    }


def _send(
    client: TestClient,
    headers: dict[str, str],
    code: str,
    body: dict[str, Any],
    *,
    transfer_id: str | None = None,
    key: str | None = None,
) -> Any:
    path = "/v1/admin/transfers" + (f"/{transfer_id}" if transfer_id else "")
    if code not in {"create", "update"}:
        path += f"/{code}"
    return client.request(
        "PATCH" if code == "update" else "POST",
        path,
        headers={**headers, "Idempotency-Key": key or new_idempotency_key()},
        json=body,
    )


def _state() -> tuple[int, ...]:
    with SessionLocal() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                OperationDocument,
                InventoryMovement,
                AuditLog,
                OutboxEvent,
                IdempotencyRecord,
            )
        )


def _created(client: TestClient) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    headers, body = _setup()
    response = _send(client, headers, "create", body)
    assert response.status_code == 201, response.text
    return headers, body, response.json()


@pytest.mark.parametrize("code", ["create", "update", "dispatch", "receive", "cancel"])
def test_admin_transfer_command_replay_and_recovery_preserve_effects(
    client: TestClient, code: str
) -> None:
    headers, create, result = _created(client)
    transfer_id = result["id"]
    body: dict[str, Any] = {}
    if code == "create":
        body, transfer_id = create, None
    elif code == "update":
        body = {"notes": "Changed private note"}
    elif code == "receive":
        assert _send(client, headers, "dispatch", {}, transfer_id=transfer_id).status_code == 200
        body = {
            "lines": [
                {
                    "shipment_line_id": result["lines"][0]["shipment_line_id"],
                    "received_quantity": "5.000",
                }
            ]
        }
    key = new_idempotency_key()
    response = _send(client, headers, code, body, transfer_id=transfer_id, key=key)
    assert response.status_code == (201 if code == "create" else 200), response.text
    expected, before = response.json(), _state()
    replay = _send(client, headers, code, body, transfer_id=transfer_id, key=key)
    assert replay.status_code == response.status_code and replay.json() == expected
    assert replay.headers["Idempotency-Replayed"] == "true"
    recovered = client.get(
        f"/v1/admin/transfers/commands/{code}/confirmations/{key}",
        headers=headers,
        params={"branch_id": create["origin_branch_id"]},
    )
    assert recovered.status_code == 200 and recovered.json() == expected, recovered.text
    assert _state() == before
    assert not {"notes", "created_by_user_name", "created_by_user_email"}.intersection(expected)


def test_receipts_are_cumulative_and_preserve_transit_until_complete(client: TestClient) -> None:
    headers, create, result = _created(client)
    transfer_id, line_id = result["id"], result["lines"][0]["shipment_line_id"]
    assert _send(client, headers, "dispatch", {}, transfer_id=transfer_id).status_code == 200
    partial = _send(
        client,
        headers,
        "receive",
        {
            "lines": [
                {
                    "shipment_line_id": line_id,
                    "received_quantity": "2",
                    "variance_reason": "Remaining in transit",
                }
            ]
        },
        transfer_id=transfer_id,
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["status"] == "IN_TRANSIT"
    assert Decimal(partial.json()["lines"][0]["pending_quantity"]) == 3
    with SessionLocal() as session:
        transit = session.scalar(
            select(InventoryBalance.quantity_on_hand).where(
                InventoryBalance.branch_id == UUID(create["destination_branch_id"]),
                InventoryBalance.location_code == "IN_TRANSIT",
            )
        )
        assert transit == 3
    final = _send(
        client,
        headers,
        "receive",
        {"lines": [{"shipment_line_id": line_id, "received_quantity": "3"}]},
        transfer_id=transfer_id,
    )
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "RECEIVED"
    assert final.json()["receipt_id"] != partial.json()["receipt_id"]
    detail = client.get(f"/v1/admin/transfers/{transfer_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert Decimal(detail.json()["lines"][0]["received_quantity"]) == 5
    assert Decimal(detail.json()["lines"][0]["pending_quantity"]) == 0
    assert len(detail.json()["related_documents"]) == 3
    listing = client.get("/v1/admin/transfers", headers=headers)
    assert listing.status_code == 200 and listing.json()["total"] == 1


def test_duplicate_and_excess_receipt_lines_do_not_consume_identity(client: TestClient) -> None:
    headers, _, result = _created(client)
    transfer_id, line_id = result["id"], result["lines"][0]["shipment_line_id"]
    assert _send(client, headers, "dispatch", {}, transfer_id=transfer_id).status_code == 200
    before, key = _state(), new_idempotency_key()
    line = {"shipment_line_id": line_id, "received_quantity": "6", "variance_reason": "Excess"}
    assert (
        _send(
            client, headers, "receive", {"lines": [line, line]}, transfer_id=transfer_id, key=key
        ).status_code
        == 422
    )
    assert (
        _send(
            client, headers, "receive", {"lines": [line]}, transfer_id=transfer_id, key=key
        ).status_code
        == 400
    )
    assert _state() == before
    line["received_quantity"] = "5"
    assert (
        _send(
            client, headers, "receive", {"lines": [line]}, transfer_id=transfer_id, key=key
        ).status_code
        == 200
    )


def test_patch_omission_and_explicit_null_are_different_intentions(client: TestClient) -> None:
    headers, _, result = _created(client)
    key = new_idempotency_key()
    assert (
        _send(client, headers, "update", {}, transfer_id=result["id"], key=key).status_code == 200
    )
    before = _state()
    conflict = _send(client, headers, "update", {"notes": None}, transfer_id=result["id"], key=key)
    assert conflict.status_code == 409 and conflict.json()["code"] == "IDEMPOTENCY_KEY_REUSED"
    assert _state() == before


@pytest.mark.parametrize("code", ["dispatch", "receive"])
def test_pos_replay_and_recovery_use_original_closed_cash_context(
    client: TestClient, code: str
) -> None:
    admin, create, shipment = _created(client)
    station = SEED_WORKSTATION_CODE if code == "dispatch" else SEED_DESTINATION_WORKSTATION_CODE
    if code == "receive":
        assert _send(client, admin, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=station,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": station, "opening_amount": "0"},
    )
    assert opened.status_code == 201, opened.text
    cash = opened.json()["id"]
    body = {"workstation_code": station, "cash_session_id": cash}
    if code == "dispatch":
        body.update(
            {"destination_branch_id": create["destination_branch_id"], "lines": create["lines"]}
        )
        path = "/v1/transfers/dispatch/commit"
    else:
        body["lines"] = [
            {
                "shipment_line_id": shipment["lines"][0]["shipment_line_id"],
                "expected_quantity": "5",
                "received_quantity": "5",
            }
        ]
        path = f"/v1/transfers/{shipment['id']}/receive"
    key = new_idempotency_key()
    response = client.post(path, headers={**headers, "Idempotency-Key": key}, json=body)
    assert response.status_code == (201 if code == "dispatch" else 200), response.text
    result = response.json()
    closed = client.post(
        "/v1/cash-close/commit",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": station,
            "cash_session_id": cash,
            "close_mode": "WITH_COUNT",
            "counter_empty_confirmed": True,
            "counted_payment_methods": [{"payment_method_code": "CASH", "counted_amount": "0"}],
        },
    )
    assert closed.status_code == 200, closed.text
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=station,
    )
    before = _state()
    replay = client.post(path, headers={**headers, "Idempotency-Key": key}, json=body)
    assert replay.status_code == response.status_code and replay.json() == result, replay.text
    recovered = client.get(
        f"/v1/transfers/commands/{code}/confirmations/{key}",
        headers=headers,
        params={"workstation_code": station, "cash_session_id": cash},
    )
    assert recovered.status_code == 200 and recovered.json() == result, recovered.text
    assert _state() == before
    new = client.post(
        path, headers={**headers, "Idempotency-Key": new_idempotency_key()}, json=body
    )
    assert new.status_code == 409, new.text
    assert _state() == before


def _domain_receive(headers: dict[str, str], shipment_id: str, line_id: str, quantity: str) -> Any:
    """Compete on the shipment after reservation without HTTP auth-row serialization."""
    cookies = SimpleCookie()
    cookies.load(headers["Cookie"])
    credential = cookies[COOKIE_NAMES["BACKOFFICE"]].value
    with SessionLocal() as session:
        record = session.scalars(
            select(AuthSession).where(AuthSession.credential_hash == secret_hash(credential))
        ).one()
        user = resolve_authorization(
            session, session.get(User, record.user_id), surface="BACKOFFICE"
        )
        session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("transfers.execute",),
            mutation=True,
            surface="BACKOFFICE",
        )
        return TransferCommandServiceWrapper().execute_admin(
            session,
            current_user=user,
            command_code="receive",
            command=AdminTransferReceiveRequest.model_validate(
                {
                    "lines": [
                        {
                            "shipment_line_id": line_id,
                            "received_quantity": quantity,
                            "variance_reason": "Partial arrival",
                        }
                    ]
                }
            ),
            key=UUID(new_idempotency_key()),
            request_id="transfer-concurrency",
            transfer_id=UUID(shipment_id),
        )


@pytest.mark.parametrize("quantity, accepted, pending", [("2", 2, "1.000"), ("3", 1, "2.000")])
def test_distinct_keys_serialize_cumulative_receipts_after_both_reservations(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, quantity: str, accepted: int, pending: str
) -> None:
    headers, _, shipment = _created(client)
    assert _send(client, headers, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    barrier = Barrier(2)
    original = physical_workflow.lock_shipment

    def synchronized(*args: Any, **kwargs: Any) -> Any:
        barrier.wait(timeout=15)
        return original(*args, **kwargs)

    monkeypatch.setattr(physical_workflow, "lock_shipment", synchronized)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(
                _domain_receive,
                headers,
                shipment["id"],
                shipment["lines"][0]["shipment_line_id"],
                quantity,
            )
            for _ in range(2)
        ]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=25))
            except TransferValidationError:
                outcomes.append(None)
    assert sum(result is not None for result in outcomes) == accepted
    detail = client.get(f"/v1/admin/transfers/{shipment['id']}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["lines"][0]["pending_quantity"] == pending
    assert len(detail.json()["related_documents"]) == accepted + 1


def test_transfer_outbox_failure_rolls_back_key_document_and_inventory(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.outbox.application.service import OutboxWriter

    headers, _, shipment = _created(client)
    before = _state()
    key = new_idempotency_key()
    original = OutboxWriter.append

    def failing(*args: Any, **kwargs: Any) -> Any:
        original(*args, **kwargs)
        raise RuntimeError("Injected outbox failure")

    monkeypatch.setattr(OutboxWriter, "append", failing)
    with pytest.raises(RuntimeError, match="Injected outbox"):
        _send(client, headers, "dispatch", {}, transfer_id=shipment["id"], key=key)
    assert _state() == before
    monkeypatch.setattr(OutboxWriter, "append", original)
    assert (
        _send(client, headers, "dispatch", {}, transfer_id=shipment["id"], key=key).status_code
        == 200
    )


def test_pos_and_backoffice_receivers_share_one_cumulative_shipment_lock(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from zeromerma_api.modules.transfers.application.schemas import TransferReceiveRequest

    admin, _, shipment = _created(client)
    assert _send(client, admin, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_DESTINATION_WORKSTATION_CODE,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE, "opening_amount": "0"},
    )
    assert opened.status_code == 201, opened.text
    barrier = Barrier(2)
    original = physical_workflow.lock_shipment

    def synchronized(*args: Any, **kwargs: Any) -> Any:
        barrier.wait(timeout=15)
        return original(*args, **kwargs)

    monkeypatch.setattr(physical_workflow, "lock_shipment", synchronized)

    def pos_receive() -> Any:
        cookies = SimpleCookie()
        cookies.load(headers["Cookie"])
        credential = cookies[COOKIE_NAMES["POS"]].value
        with SessionLocal() as session:
            record = session.scalars(
                select(AuthSession).where(AuthSession.credential_hash == secret_hash(credential))
            ).one()
            user = resolve_authorization(session, session.get(User, record.user_id), surface="POS")
            session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
            bind_authorization_scope(
                session,
                user=user,
                capabilities=("transfers.execute",),
                mutation=True,
                surface="POS",
            )
            return TransferCommandServiceWrapper().execute_pos(
                session,
                current_user=user,
                command_code="receive",
                key=UUID(new_idempotency_key()),
                request_id="cross-surface-receipt",
                transfer_id=UUID(shipment["id"]),
                command=TransferReceiveRequest.model_validate(
                    {
                        "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
                        "cash_session_id": opened.json()["id"],
                        "lines": [
                            {
                                "shipment_line_id": shipment["lines"][0]["shipment_line_id"],
                                "expected_quantity": "5",
                                "received_quantity": "3",
                                "variance_reason": "Partial arrival",
                            }
                        ],
                    }
                ),
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(pos_receive),
            pool.submit(
                _domain_receive,
                admin,
                shipment["id"],
                shipment["lines"][0]["shipment_line_id"],
                "3",
            ),
        ]
        outcomes = []
        for future in futures:
            try:
                outcomes.append(future.result(timeout=25))
            except TransferValidationError:
                outcomes.append(None)
    assert sum(result is not None for result in outcomes) == 1
    detail = client.get(f"/v1/admin/transfers/{shipment['id']}", headers=admin)
    assert detail.status_code == 200, detail.text
    assert detail.json()["lines"][0]["received_quantity"] == "3.000"
    assert detail.json()["lines"][0]["pending_quantity"] == "2.000"
    assert len(detail.json()["related_documents"]) == 2


@pytest.mark.parametrize("field", ["origin_branch_id", "destination_branch_id"])
def test_missing_transfer_branch_is_rejected_before_reservation(
    client: TestClient, field: str
) -> None:
    headers, create, shipment = _created(client)
    for code, body, transfer_id in [
        ("create", {**create, field: str(uuid4())}, None),
        ("update", {field: str(uuid4())}, shipment["id"]),
    ]:
        before = _state()
        response = _send(client, headers, code, body, transfer_id=transfer_id)
        assert response.status_code == 400, response.text
        assert _state() == before


def test_pos_partial_receipts_keep_original_station_and_complete_cumulatively(
    client: TestClient,
) -> None:
    admin, _, shipment = _created(client)
    assert _send(client, admin, "dispatch", {}, transfer_id=shipment["id"]).status_code == 200
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_DESTINATION_WORKSTATION_CODE,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE, "opening_amount": "0"},
    )
    assert opened.status_code == 201, opened.text
    receipt_ids = []
    for expected, quantity, status in [("5", "2", "IN_TRANSIT"), ("3", "3", "RECEIVED")]:
        response = client.post(
            f"/v1/transfers/{shipment['id']}/receive",
            headers={**headers, "Idempotency-Key": new_idempotency_key()},
            json={
                "workstation_code": SEED_DESTINATION_WORKSTATION_CODE,
                "cash_session_id": opened.json()["id"],
                "lines": [
                    {
                        "shipment_line_id": shipment["lines"][0]["shipment_line_id"],
                        "expected_quantity": expected,
                        "received_quantity": quantity,
                        "variance_reason": "Partial arrival",
                    }
                ],
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status
        receipt_ids.append(response.json()["receipt_id"])
        if status == "IN_TRANSIT":
            pending = client.get(
                "/v1/transfers/inbound/pending",
                headers=headers,
                params={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
            )
            assert pending.status_code == 200, pending.text
            assert pending.json()["transfers"][0]["expected_total_quantity"] == "3.000"
    assert len(set(receipt_ids)) == 2
    detail = client.get(
        f"/v1/transfers/{shipment['id']}",
        headers=headers,
        params={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
    )
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["receipts"]) == 2
    assert detail.json()["shipment"]["source_branch_id"] == shipment["origin_branch_id"]
    assert detail.json()["receipt_progress"][0]["pending_quantity"] == "0.000"
    history = client.get(
        "/v1/transfers/inbound/history",
        headers=headers,
        params={"workstation_code": SEED_DESTINATION_WORKSTATION_CODE},
    )
    assert history.status_code == 200, history.text
    assert {record["id"] for record in history.json()["records"]} == set(receipt_ids)
    assert {record["shipment_id"] for record in history.json()["records"]} == {shipment["id"]}
