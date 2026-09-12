from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_DESTINATION_BRANCH_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryMovement,
)
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


def _get_branch_id(code: str) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _seed_origin_stock(client: TestClient, *, product_code: str, quantity: str = "20.000") -> None:
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers=_admin_headers(client),
        json={
            "adjustment_type": "INCREASE",
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "location_code": "BACKROOM",
            "product_id": _get_product_id(product_code),
            "quantity": quantity,
            "reason": "Transfer test stock",
        },
    )
    assert response.status_code == 201


def _create_transfer(client: TestClient, *, quantity: str = "5.000") -> dict[str, object]:
    response = client.post(
        "/v1/admin/transfers",
        headers=_admin_headers(client),
        json={
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": quantity,
                }
            ],
            "notes": "Admin transfer draft",
            "origin_branch_id": _get_branch_id(SEED_BRANCH_CODE),
        },
    )

    assert response.status_code == 201
    return dict(response.json())


def _dispatch_transfer(client: TestClient) -> dict[str, object]:
    _seed_origin_stock(client, product_code=SEED_PRODUCT_BOLILLO_STD_CODE)
    transfer = _create_transfer(client)
    transfer_id = str(transfer["overview"]["id"])
    response = client.post(
        f"/v1/admin/transfers/{transfer_id}/dispatch",
        headers={**_admin_headers(client), "X-Request-ID": "admin-transfer-dispatch"},
        json={"notes": "Dispatch from backoffice"},
    )
    assert response.status_code == 200
    return dict(response.json())


def test_admin_transfers_list_empty_and_rejects_pos_surface_user(client: TestClient) -> None:
    response = client.get("/v1/admin/transfers", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["total_transfers"] == 0
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["products"]
    assert payload["filter_options"]["statuses"]

    forbidden = client.get(
        "/v1/admin/transfers",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )

    assert forbidden.status_code == 403


def test_admin_transfer_create_update_filters_and_detail(client: TestClient) -> None:
    transfer = _create_transfer(client)
    transfer_id = transfer["overview"]["id"]

    update_response = client.patch(
        f"/v1/admin/transfers/{transfer_id}",
        headers=_admin_headers(client),
        json={
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "quantity": "6.000",
                }
            ],
            "notes": "Updated draft quantity",
        },
    )
    assert update_response.status_code == 200
    assert Decimal(str(update_response.json()["overview"]["sent_unit_count"])) == Decimal("6.000")

    status_response = client.get("/v1/admin/transfers?status=DRAFT", headers=_admin_headers(client))
    assert status_response.status_code == 200
    assert [item["id"] for item in status_response.json()["items"]] == [transfer_id]

    origin_response = client.get(
        f"/v1/admin/transfers?origin_branch_id={_get_branch_id(SEED_BRANCH_CODE)}",
        headers=_admin_headers(client),
    )
    assert origin_response.status_code == 200
    assert [item["folio"] for item in origin_response.json()["items"]][0].startswith("ENV-")

    product_response = client.get(
        f"/v1/admin/transfers?product_id={_get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE)}",
        headers=_admin_headers(client),
    )
    assert product_response.status_code == 200
    assert product_response.json()["total"] == 1

    detail_response = client.get(
        f"/v1/admin/transfers/{transfer_id}", headers=_admin_headers(client)
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["status"] == "DRAFT"
    assert detail["available_actions"]["can_dispatch"] is True
    assert detail["origin"]["branch_code"] == SEED_BRANCH_CODE
    assert detail["destination"]["branch_code"] == SEED_DESTINATION_BRANCH_CODE
    assert detail["lines"][0]["product_code"] == SEED_PRODUCT_BOLILLO_STD_CODE


def test_admin_transfer_validates_same_branch_empty_lines_and_stock(client: TestClient) -> None:
    headers = _admin_headers(client)
    branch_id = _get_branch_id(SEED_BRANCH_CODE)
    product_id = _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE)

    same_branch_response = client.post(
        "/v1/admin/transfers",
        headers=headers,
        json={
            "destination_branch_id": branch_id,
            "lines": [{"product_id": product_id, "quantity": "1.000"}],
            "origin_branch_id": branch_id,
        },
    )
    assert same_branch_response.status_code == 422

    empty_lines_response = client.post(
        "/v1/admin/transfers",
        headers=headers,
        json={
            "destination_branch_id": _get_branch_id(SEED_DESTINATION_BRANCH_CODE),
            "lines": [],
            "origin_branch_id": branch_id,
        },
    )
    assert empty_lines_response.status_code == 422

    transfer = _create_transfer(client)
    dispatch_without_stock = client.post(
        f"/v1/admin/transfers/{transfer['overview']['id']}/dispatch",
        headers=headers,
        json={},
    )
    assert dispatch_without_stock.status_code == 400
    assert "Origin stock is insufficient" in dispatch_without_stock.json()["message"]


def test_admin_transfer_dispatch_writes_inventory_movements_audit_and_outbox(
    client: TestClient,
) -> None:
    transfer = _dispatch_transfer(client)
    transfer_id = transfer["overview"]["id"]

    assert transfer["overview"]["status"] == "IN_TRANSIT"
    assert transfer["available_actions"]["can_receive"] is True
    assert len(transfer["inventory_impact"]["movements"]) == 2

    with SessionLocal() as session:
        movements = (
            session.execute(
                select(InventoryMovement).where(
                    InventoryMovement.source_document_id == UUID(transfer_id)
                ),
            )
            .scalars()
            .all()
        )
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "transfer.dispatched",
                AuditLog.resource_id == transfer_id,
            ),
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.event_name == "transfer.dispatched.v1",
                OutboxEvent.aggregate_id == transfer_id,
            ),
        ).scalar_one()

    assert {movement.movement_type for movement in movements} == {"TRANSFER_DISPATCH"}
    assert {movement.direction for movement in movements} == {"IN", "OUT"}
    assert audit_record.request_id == "admin-transfer-dispatch"
    assert outbox_event.aggregate_id == transfer_id


def test_admin_transfer_receive_full_transfer_and_prevents_double_receipt(
    client: TestClient,
) -> None:
    dispatched = _dispatch_transfer(client)
    transfer_id = dispatched["overview"]["id"]
    receipt_lines = [
        {
            "received_quantity": line["sent_quantity"],
            "shipment_line_id": line["shipment_line_id"],
        }
        for line in dispatched["lines"]
    ]

    receive_response = client.post(
        f"/v1/admin/transfers/{transfer_id}/receive",
        headers={**_admin_headers(client), "X-Request-ID": "admin-transfer-receive"},
        json={"lines": receipt_lines, "notes": "Received complete"},
    )
    assert receive_response.status_code == 200
    received = receive_response.json()
    assert received["overview"]["status"] == "RECEIVED"
    assert received["receipt"]["has_discrepancy"] is False
    assert received["available_actions"]["can_receive"] is False
    assert len(received["inventory_impact"]["movements"]) == 4

    duplicate_response = client.post(
        f"/v1/admin/transfers/{transfer_id}/receive",
        headers=_admin_headers(client),
        json={"lines": receipt_lines},
    )
    assert duplicate_response.status_code == 409


def test_admin_transfer_receive_requires_discrepancy_reason_and_records_variance(
    client: TestClient,
) -> None:
    dispatched = _dispatch_transfer(client)
    transfer_id = dispatched["overview"]["id"]
    shipment_line_id = dispatched["lines"][0]["shipment_line_id"]

    missing_reason_response = client.post(
        f"/v1/admin/transfers/{transfer_id}/receive",
        headers=_admin_headers(client),
        json={"lines": [{"received_quantity": "3.000", "shipment_line_id": shipment_line_id}]},
    )
    assert missing_reason_response.status_code == 400
    assert "Variance reason is required" in missing_reason_response.json()["message"]

    receive_response = client.post(
        f"/v1/admin/transfers/{transfer_id}/receive",
        headers=_admin_headers(client),
        json={
            "lines": [
                {
                    "received_quantity": "3.000",
                    "shipment_line_id": shipment_line_id,
                    "variance_reason": "Missing package",
                }
            ],
        },
    )
    assert receive_response.status_code == 200
    payload = receive_response.json()
    assert payload["overview"]["status"] == "RECEIVED_WITH_VARIANCE"
    assert payload["receipt"]["has_discrepancy"] is True
    assert payload["warnings"][0]["code"] == "quantity_discrepancy"


def test_admin_transfer_cancel_draft(client: TestClient) -> None:
    transfer = _create_transfer(client)
    transfer_id = transfer["overview"]["id"]

    cancel_response = client.post(
        f"/v1/admin/transfers/{transfer_id}/cancel",
        headers=_admin_headers(client),
        json={"reason": "No longer needed"},
    )

    assert cancel_response.status_code == 200
    payload = cancel_response.json()
    assert payload["overview"]["status"] == "CANCELLED"
    assert payload["available_actions"]["can_dispatch"] is False

    dispatch_response = client.post(
        f"/v1/admin/transfers/{transfer_id}/dispatch",
        headers=_admin_headers(client),
        json={},
    )
    assert dispatch_response.status_code == 400
