from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_BRANCH_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _login_cashier(client: TestClient) -> dict[str, str]:
    return login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS")


def _admin_headers(client: TestClient) -> dict[str, str]:
    return owner_headers()


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _create_adjustment(
    client: TestClient,
    *,
    adjustment_type: str = "INCREASE",
    quantity: str = "12.000",
    reason: str = "Initial physical count",
    allow_negative: bool = False,
) -> dict[str, object]:
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={
            **{**_admin_headers(client), "X-Request-ID": "23792e65-ef7f-5c69-8511-2c6e8833986b"},
            "Idempotency-Key": new_idempotency_key(),
        },
        json={
            "adjustment_type": adjustment_type,
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "location_code": "BACKROOM",
            "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
            "quantity": quantity,
            "reason": reason,
            "allow_negative": allow_negative,
        },
    )

    assert response.status_code == 201
    return dict(response.json())


def test_admin_inventory_list_empty_until_adjustments_exist(client: TestClient) -> None:
    response = client.get("/v1/admin/inventory", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["total_records"] == 0
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["classes"]
    assert payload["filter_options"]["locations"]
    assert payload["filter_options"]["products"]
    assert payload["filter_options"]["product_kinds"]


def test_admin_inventory_rejects_pos_surface_user(client: TestClient) -> None:
    response = client.get(
        "/v1/admin/inventory",
        headers=_login_cashier(client),
    )

    assert response.status_code == 403


def test_admin_inventory_adjustment_persists_balance_movement_audit_and_outbox(
    client: TestClient,
) -> None:
    payload = _create_adjustment(client)

    assert Decimal(str(payload["previous_quantity"])) == Decimal("0.000")
    assert Decimal(str(payload["new_quantity"])) == Decimal("12.000")

    with SessionLocal() as session:
        balance = session.execute(
            select(InventoryBalance).where(InventoryBalance.id == payload["balance_id"]),
        ).scalar_one()
        movement = session.execute(
            select(InventoryMovement).where(InventoryMovement.source_document_id == payload["id"]),
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(balance.id)),
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(balance.id)),
        ).scalar_one()

    assert balance.quantity_on_hand == Decimal("12.000")
    assert movement.direction == "IN"
    assert movement.balance_after == Decimal("12.000")
    assert audit_record.action == "admin.inventory.adjustment.created"
    assert audit_record.request_id == "23792e65-ef7f-5c69-8511-2c6e8833986b"
    assert outbox_event.event_name == "admin.inventory_adjustment.created.v1"


def test_admin_inventory_filters_search_stock_state_and_detail(client: TestClient) -> None:
    adjustment = _create_adjustment(client)
    balance_id = str(adjustment["balance_id"])
    branch_id = _get_branch_id(SEED_BRANCH_CODE)

    search_response = client.get(
        "/v1/admin/inventory?search=concha", headers=_admin_headers(client)
    )
    assert search_response.status_code == 200
    assert [item["balance_id"] for item in search_response.json()["items"]] == [balance_id]

    branch_response = client.get(
        f"/v1/admin/inventory?branch_id={branch_id}", headers=_admin_headers(client)
    )
    assert branch_response.status_code == 200
    assert [item["balance_id"] for item in branch_response.json()["items"]] == [balance_id]

    kind_response = client.get(
        "/v1/admin/inventory?product_kind=FINISHED_GOOD", headers=_admin_headers(client)
    )
    assert kind_response.status_code == 200
    assert [item["balance_id"] for item in kind_response.json()["items"]] == [balance_id]

    stock_state_response = client.get(
        "/v1/admin/inventory?stock_state=in_stock", headers=_admin_headers(client)
    )
    assert stock_state_response.status_code == 200
    assert [item["stock_state"] for item in stock_state_response.json()["items"]] == ["in_stock"]

    detail_response = client.get(
        f"/v1/admin/inventory/{balance_id}", headers=_admin_headers(client)
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["balance_id"] == balance_id
    assert detail_payload["product"]["code"] == SEED_PRODUCT_CONCHA_VAN_CODE
    assert detail_payload["stock_breakdown"]["quantity_on_hand"] == "12.000"
    assert detail_payload["related_actions"]["can_create_adjustment"] is True
    assert detail_payload["related_actions"]["count_endpoint_available"] is False


def test_admin_inventory_negative_stock_warning_and_movements(client: TestClient) -> None:
    _create_adjustment(client, quantity="2.000")
    adjustment = _create_adjustment(
        client,
        adjustment_type="DECREASE",
        quantity="5.000",
        reason="Count correction",
        allow_negative=True,
    )
    balance_id = str(adjustment["balance_id"])

    response = client.get(
        "/v1/admin/inventory?stock_state=negative_stock", headers=_admin_headers(client)
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["balance_id"] for item in payload["items"]] == [balance_id]
    assert payload["items"][0]["warning_state"] == "critical"
    assert payload["items"][0]["warnings"][0]["code"] == "negative_stock"

    movements_response = client.get(
        f"/v1/admin/inventory/{balance_id}/movements",
        headers=_admin_headers(client),
    )
    assert movements_response.status_code == 200
    movements_payload = movements_response.json()
    assert movements_payload["total"] == 2
    assert movements_payload["items"][0]["direction"] == "OUT"
    assert movements_payload["items"][0]["movement_type"] == "MANUAL_ADJUSTMENT"


def test_admin_inventory_adjustment_validates_reason_quantity_product_and_branch(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    base_payload = {
        "adjustment_type": "INCREASE",
        "branch_id": _get_branch_id(SEED_BRANCH_CODE),
        "location_code": "BACKROOM",
        "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
        "quantity": "1.000",
        "reason": "Physical count",
    }

    reason_response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**base_payload, "reason": " "},
    )
    assert reason_response.status_code == 422

    quantity_response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**base_payload, "quantity": "0"},
    )
    assert quantity_response.status_code == 422

    product_response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**base_payload, "product_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert product_response.status_code == 404

    branch_response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**base_payload, "branch_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert branch_response.status_code == 404


def test_controlled_adjustment_requires_lot_and_zero_count_targets_only_selected_lot(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
    product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)
    with SessionLocal() as session:
        product = session.get(Product, product_id)
        assert product is not None
        product.lot_tracking_enabled = True
        product.expiry_required = True
        session.commit()
    body = {
        "branch_id": branch_id,
        "product_id": product_id,
        "location_code": "BACKROOM",
        "adjustment_type": "INCREASE",
        "quantity": "3",
        "reason": "Physical lot count",
    }
    missing = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json=body,
    )
    assert missing.status_code == 400
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            **body,
            "lot_code": "ACTUAL-COUNT-1",
            "expires_at": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
            "unit_cost": "2.00000000",
            "cost_evidence_reference": "synthetic-invoice-1",
        },
    )
    assert response.status_code == 201, response.text
    balance_id = response.json()["balance_id"]
    detail = client.get(f"/v1/admin/inventory/{balance_id}", headers=headers).json()
    assert detail["product"]["lot_tracking_enabled"] and detail["product"]["expiry_required"]
    assert Decimal(detail["stock_breakdown"]["estimated_value"]) == 6
    lot_id = detail["lots"][0]["id"]
    assert detail["lots"][0]["lot_code"] == "ACTUAL-COUNT-1"
    zero = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={**body, "adjustment_type": "SET_COUNTED", "quantity": "0", "lot_id": lot_id},
    )
    assert zero.status_code == 201, zero.text
    assert Decimal(zero.json()["new_quantity"]) == 0
    detail = client.get(f"/v1/admin/inventory/{balance_id}", headers=headers).json()
    assert Decimal(detail["lots"][0]["quantity_on_hand"]) == 0
    assert Decimal(detail["stock_breakdown"]["estimated_value"]) == 0


def test_negative_adjustment_requires_explicit_opt_in(client: TestClient) -> None:
    headers = _admin_headers(client)
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
            "location_code": "BACKROOM",
            "adjustment_type": "DECREASE",
            "quantity": "1",
            "reason": "Negative stock needs explicit evidence",
        },
    )
    assert response.status_code == 400
    with SessionLocal() as session:
        assert session.scalar(select(InventoryMovement.id)) is None
