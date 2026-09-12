from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
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
from zeromerma_api.modules.operations.infrastructure.models import OperationDocument
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_ADMIN_EMAIL, "password": SEED_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    return str(response.json()["access_token"])


def _login_cashier(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )

    assert response.status_code == 200
    return str(response.json()["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login_admin(client)}"}


def _get_branch_id(code: str = SEED_BRANCH_CODE) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _create_stock(
    client: TestClient, *, product_code: str, quantity: str = "20.000"
) -> dict[str, object]:
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers=_admin_headers(client),
        json={
            "adjustment_type": "INCREASE",
            "branch_id": _get_branch_id(),
            "location_code": "BACKROOM",
            "product_id": _get_product_id(product_code),
            "quantity": quantity,
            "reason": "Initial stock for waste test",
        },
    )
    assert response.status_code == 201
    return dict(response.json())


def _create_waste(
    client: TestClient,
    *,
    product_code: str = SEED_PRODUCT_CONCHA_VAN_CODE,
    quantity: str = "2.000",
    reason_code: str = "DAMAGED",
    notes: str | None = "Tray damage",
) -> dict[str, object]:
    response = client.post(
        "/v1/admin/waste",
        headers={**_admin_headers(client), "X-Request-ID": "admin-waste-test"},
        json={
            "branch_id": _get_branch_id(),
            "location_code": "BACKROOM",
            "notes": notes,
            "product_id": _get_product_id(product_code),
            "quantity": quantity,
            "reason_code": reason_code,
        },
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_waste_list_empty_and_rejects_pos_surface_user(client: TestClient) -> None:
    response = client.get("/v1/admin/waste", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert payload["filter_options"]["reasons"]
    assert payload["backend_contract"]["create_endpoint"] == "POST /v1/admin/waste"

    forbidden_response = client.get(
        "/v1/admin/waste",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_waste_create_confirms_document_inventory_movement_audit_and_outbox(
    client: TestClient,
) -> None:
    _create_stock(client, product_code=SEED_PRODUCT_CONCHA_VAN_CODE, quantity="20.000")

    payload = _create_waste(client, quantity="3.000")
    waste_id = payload["overview"]["id"]

    assert payload["overview"]["folio"].startswith("WST-")
    assert payload["overview"]["status"] == "COMMITTED"
    assert payload["overview"]["location_code"] == "BACKROOM"
    assert payload["overview"]["reason_code"] == "DAMAGED"
    assert Decimal(str(payload["overview"]["quantity"])) == Decimal("3.000")
    assert payload["inventory_impact"]["integration_available"] is True
    assert payload["inventory_impact"]["movements"][0]["movement_type"] == "WASTE_RECORD"
    assert payload["product_inventory_context"]["stock_before"] == "20.000"
    assert payload["product_inventory_context"]["stock_after"] == "17.000"

    with SessionLocal() as session:
        document = session.execute(
            select(OperationDocument).where(OperationDocument.id == waste_id)
        ).scalar_one()
        balance = session.execute(
            select(InventoryBalance).where(
                InventoryBalance.product_id == _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                InventoryBalance.branch_id == _get_branch_id(),
                InventoryBalance.location_code == "BACKROOM",
            ),
        ).scalar_one()
        movement = session.execute(
            select(InventoryMovement).where(InventoryMovement.source_document_id == waste_id),
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(waste_id)),
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(waste_id)),
        ).scalar_one()

    assert document.document_type == "WASTE_RECORD"
    assert movement.direction == "OUT"
    assert movement.balance_after == Decimal("17.000")
    assert balance.quantity_on_hand == Decimal("17.000")
    assert audit_record.action == "admin.waste.confirmed"
    assert audit_record.request_id == "admin-waste-test"
    assert outbox_event.event_name == "waste_record.committed.v1"


def test_admin_waste_filters_search_reason_branch_and_product(client: TestClient) -> None:
    _create_stock(client, product_code=SEED_PRODUCT_BOLILLO_STD_CODE, quantity="10.000")
    created = _create_waste(
        client,
        product_code=SEED_PRODUCT_BOLILLO_STD_CODE,
        quantity="1.000",
        reason_code="EXPIRED",
        notes=None,
    )
    waste_id = created["overview"]["id"]

    branch_response = client.get(
        f"/v1/admin/waste?branch_id={_get_branch_id()}", headers=_admin_headers(client)
    )
    assert branch_response.status_code == 200
    assert [item["id"] for item in branch_response.json()["items"]] == [waste_id]

    reason_response = client.get(
        "/v1/admin/waste?reason_code=EXPIRED", headers=_admin_headers(client)
    )
    assert reason_response.status_code == 200
    assert [item["id"] for item in reason_response.json()["items"]] == [waste_id]

    product_response = client.get(
        f"/v1/admin/waste?product_id={_get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE)}",
        headers=_admin_headers(client),
    )
    assert product_response.status_code == 200
    assert [item["id"] for item in product_response.json()["items"]] == [waste_id]

    product_kind_response = client.get(
        "/v1/admin/waste?product_kind=FINISHED_GOOD", headers=_admin_headers(client)
    )
    assert product_kind_response.status_code == 200
    assert [item["id"] for item in product_kind_response.json()["items"]] == [waste_id]

    evidence_response = client.get(
        "/v1/admin/waste?evidence_state=without_evidence", headers=_admin_headers(client)
    )
    assert evidence_response.status_code == 200
    assert [item["id"] for item in evidence_response.json()["items"]] == [waste_id]

    with_evidence_response = client.get(
        "/v1/admin/waste?evidence_state=with_evidence", headers=_admin_headers(client)
    )
    assert with_evidence_response.status_code == 200
    assert with_evidence_response.json()["items"] == []

    search_response = client.get("/v1/admin/waste?search=bolillo", headers=_admin_headers(client))
    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()["items"]] == [waste_id]
    assert search_response.json()["metrics"]["expired_records"] == 1


def test_admin_waste_validates_note_reason_stock_and_quantity(client: TestClient) -> None:
    _create_stock(client, product_code=SEED_PRODUCT_CONCHA_VAN_CODE, quantity="2.000")
    headers = _admin_headers(client)
    base_payload = {
        "branch_id": _get_branch_id(),
        "location_code": "BACKROOM",
        "notes": "Waste note",
        "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
        "quantity": "1.000",
        "reason_code": "DAMAGED",
    }

    quantity_response = client.post(
        "/v1/admin/waste", headers=headers, json={**base_payload, "quantity": "0"}
    )
    assert quantity_response.status_code == 422

    missing_note_response = client.post(
        "/v1/admin/waste", headers=headers, json={**base_payload, "notes": None}
    )
    assert missing_note_response.status_code == 409
    assert (
        missing_note_response.json()["message"]
        == "Notes are required for this waste reason or impact level."
    )

    other_note_response = client.post(
        "/v1/admin/waste",
        headers=headers,
        json={**base_payload, "reason_code": "OTHER", "notes": None},
    )
    assert other_note_response.status_code == 409

    missing_reason_response = client.post(
        "/v1/admin/waste", headers=headers, json={**base_payload, "reason_code": "NOPE"}
    )
    assert missing_reason_response.status_code == 404

    excess_response = client.post(
        "/v1/admin/waste", headers=headers, json={**base_payload, "quantity": "5.000"}
    )
    assert excess_response.status_code == 409
    assert (
        excess_response.json()["message"]
        == "Waste quantity exceeds available stock for selected branch and location."
    )


def test_admin_waste_high_impact_notifies_backoffice_without_supervisor_approval(
    client: TestClient,
) -> None:
    _create_stock(client, product_code=SEED_PRODUCT_CONCHA_VAN_CODE, quantity="20.000")

    payload = _create_waste(
        client,
        quantity="12.000",
        reason_code="EXPIRED",
        notes="Large batch expired overnight",
    )
    waste_id = payload["overview"]["id"]

    assert payload["overview"]["impact_level"] == "high"
    assert payload["warnings"][0]["code"] == "high_impact"

    with SessionLocal() as session:
        audit_actions = (
            session.execute(
                select(AuditLog.action)
                .where(AuditLog.resource_id == str(waste_id))
                .order_by(AuditLog.action.asc()),
            )
            .scalars()
            .all()
        )
        outbox_events = (
            session.execute(
                select(OutboxEvent.event_name)
                .where(OutboxEvent.aggregate_id == str(waste_id))
                .order_by(OutboxEvent.event_name.asc()),
            )
            .scalars()
            .all()
        )

    assert audit_actions == ["admin.waste.confirmed", "admin.waste.high_impact_notified"]
    assert outbox_events == ["waste_record.committed.v1", "waste_record.high_impact_alert.v1"]
