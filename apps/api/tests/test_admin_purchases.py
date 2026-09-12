from __future__ import annotations

import uuid
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
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.suppliers.infrastructure.models import Supplier, SupplierProduct


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


def _supplier_payload(
    *, code: str = "SUP-COMPRA", tax_id: str = "CMP010101000"
) -> dict[str, object]:
    return {
        "branch_ids": [_get_branch_id()],
        "category": "RAW_MATERIALS",
        "code": code,
        "commercial_name": "Proveedor Compras",
        "contacts": [
            {
                "email": "compras@proveedor.test",
                "is_primary": True,
                "name": "Contacto Compras",
                "phone": "6621000000",
            }
        ],
        "credit_days": 7,
        "default_currency": "MXN",
        "lead_time_days": 2,
        "legal_name": "Proveedor Compras SA de CV",
        "payment_terms_type": "CREDIT",
        "product_relations": [
            {
                "currency": "MXN",
                "is_active": True,
                "last_known_price": "10.0000",
                "lead_time_days": 2,
                "minimum_order_qty": "1.000",
                "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                "purchase_uom": "PCS",
                "supplier_sku": "CONCHA-SUP",
            }
        ],
        "status": "ACTIVE",
        "tax_id": tax_id,
    }


def _create_supplier(
    client: TestClient, *, code: str = "SUP-COMPRA", tax_id: str = "CMP010101000"
) -> dict[str, object]:
    response = client.post(
        "/v1/admin/suppliers",
        headers={**_admin_headers(client), "X-Request-ID": "admin-purchase-supplier"},
        json=_supplier_payload(code=code, tax_id=tax_id),
    )
    assert response.status_code == 201
    return dict(response.json())


def _purchase_payload(
    *,
    branch_id: str | None = None,
    confirm_now: bool = False,
    product_id: str | None = None,
    quantity: str = "5.000",
    supplier_id: str | None = None,
    unit_cost: str = "12.5000",
) -> dict[str, object]:
    supplier = supplier_id or str(_create_supplier_id_fallback())
    return {
        "branch_id": branch_id or _get_branch_id(),
        "confirm_now": confirm_now,
        "external_document_number": "REM-100",
        "external_document_type": "REMISSION",
        "lines": [
            {
                "ordered_quantity": quantity,
                "product_id": product_id or _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                "unit_cost": unit_cost,
            }
        ],
        "notes": "Entrada de prueba",
        "supplier_id": supplier,
    }


def _create_supplier_id_fallback() -> uuid.UUID:
    with SessionLocal() as session:
        supplier = session.execute(
            select(Supplier).where(Supplier.code == "SUP-COMPRA")
        ).scalar_one()
        return supplier.id


def _create_purchase(client: TestClient, *, confirm_now: bool = False) -> dict[str, object]:
    suffix = uuid.uuid4().hex[:8].upper()
    supplier = _create_supplier(client, code=f"SUP-{suffix}", tax_id=f"CMP{suffix}")
    response = client.post(
        "/v1/admin/purchases",
        headers={**_admin_headers(client), "X-Request-ID": "admin-purchase-create"},
        json=_purchase_payload(
            confirm_now=confirm_now, supplier_id=str(supplier["overview"]["id"])
        ),
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_purchases_list_empty_and_rejects_pos_surface_user(client: TestClient) -> None:
    response = client.get("/v1/admin/purchases", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert (
        payload["backend_contract"]["create_direct_entry_endpoint"]
        == "POST /v1/admin/purchases/direct-entry"
    )
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["operators"]
    assert payload["filter_options"]["products"]
    assert payload["filter_options"]["suppliers"] == []

    forbidden_response = client.get(
        "/v1/admin/purchases",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_purchases_create_draft_detail_audit_and_no_inventory_movement(
    client: TestClient,
) -> None:
    payload = _create_purchase(client)
    purchase_id = payload["overview"]["id"]

    assert payload["overview"]["status"] == "DRAFT"
    assert payload["overview"]["document_type"] == "PURCHASE"
    assert payload["supplier_context"]["supplier_name"] == "Proveedor Compras SA de CV"
    assert payload["receiving_branch"]["branch_code"] == SEED_BRANCH_CODE
    assert payload["lines"][0]["product_code"] == SEED_PRODUCT_CONCHA_VAN_CODE
    assert payload["inventory_impact"]["movements"] == []
    assert payload["available_actions"]["can_edit"] is True
    assert payload["available_actions"]["can_receive"] is True

    with SessionLocal() as session:
        movement_count = session.execute(select(InventoryMovement)).scalars().all()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(purchase_id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(purchase_id))
        ).scalar_one()

    assert movement_count == []
    assert audit_record.action == "admin.purchase.created"
    assert audit_record.request_id == "admin-purchase-create"
    assert outbox_event.event_name == "admin.purchase.created.v1"


def test_admin_purchases_filters_by_status_supplier_branch_product_kind_and_amount(
    client: TestClient,
) -> None:
    payload = _create_purchase(client, confirm_now=True)
    purchase_id = payload["overview"]["id"]
    supplier_id = payload["overview"]["supplier_id"]
    branch_id = payload["overview"]["branch_id"]
    product_id = payload["lines"][0]["product_id"]

    paths = [
        "/v1/admin/purchases?search=REM-100",
        "/v1/admin/purchases?status=ORDERED",
        f"/v1/admin/purchases?supplier_id={supplier_id}",
        f"/v1/admin/purchases?branch_id={branch_id}",
        f"/v1/admin/purchases?product_id={product_id}",
        "/v1/admin/purchases?product_kind=FINISHED_GOOD",
        "/v1/admin/purchases?amount_min=1&amount_max=1000",
        "/v1/admin/purchases?warning_state=warning",
    ]
    for path in paths:
        response = client.get(path, headers=_admin_headers(client))
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [purchase_id]


def test_admin_purchases_validates_required_fields_and_invalid_values(client: TestClient) -> None:
    supplier = _create_supplier(client)
    headers = _admin_headers(client)

    missing_supplier_response = client.post(
        "/v1/admin/purchases",
        headers=headers,
        json={
            **_purchase_payload(supplier_id=str(supplier["overview"]["id"])),
            "supplier_id": str(uuid.uuid4()),
        },
    )
    assert missing_supplier_response.status_code == 404

    empty_lines_response = client.post(
        "/v1/admin/purchases",
        headers=headers,
        json={**_purchase_payload(supplier_id=str(supplier["overview"]["id"])), "lines": []},
    )
    assert empty_lines_response.status_code == 422

    invalid_quantity_response = client.post(
        "/v1/admin/purchases",
        headers=headers,
        json={
            **_purchase_payload(supplier_id=str(supplier["overview"]["id"])),
            "lines": [
                {
                    "ordered_quantity": "0.000",
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                    "unit_cost": "1.0000",
                }
            ],
        },
    )
    assert invalid_quantity_response.status_code == 422

    invalid_cost_response = client.post(
        "/v1/admin/purchases",
        headers=headers,
        json={
            **_purchase_payload(supplier_id=str(supplier["overview"]["id"])),
            "lines": [
                {
                    "ordered_quantity": "1.000",
                    "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
                    "unit_cost": "-1.0000",
                }
            ],
        },
    )
    assert invalid_cost_response.status_code == 422


def test_admin_purchases_confirm_and_receive_full_purchase_creates_inventory_movement(
    client: TestClient,
) -> None:
    payload = _create_purchase(client)
    purchase_id = payload["overview"]["id"]
    line_id = payload["lines"][0]["purchase_line_id"]

    confirm_response = client.post(
        f"/v1/admin/purchases/{purchase_id}/confirm", headers=_admin_headers(client)
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["overview"]["status"] == "ORDERED"

    receive_response = client.post(
        f"/v1/admin/purchases/{purchase_id}/receive",
        headers={**_admin_headers(client), "X-Request-ID": "admin-purchase-receive"},
        json={
            "lines": [
                {
                    "purchase_line_id": line_id,
                    "received_quantity": "5.000",
                    "unit_cost": "13.7500",
                }
            ],
            "notes": "Recibido completo",
        },
    )

    assert receive_response.status_code == 200
    received = receive_response.json()
    assert received["overview"]["status"] == "RECEIVED"
    assert Decimal(str(received["receipt"]["received_quantity"])) == Decimal("5.000")
    assert received["inventory_impact"]["integration_available"] is True
    assert received["inventory_impact"]["movements"][0]["movement_type"] == "PURCHASE_RECEIPT"

    with SessionLocal() as session:
        balance = session.execute(select(InventoryBalance)).scalar_one()
        movement = session.execute(select(InventoryMovement)).scalar_one()
        supplier_product = session.execute(select(SupplierProduct)).scalars().first()
        receipt_audit = session.execute(
            select(AuditLog).where(AuditLog.action == "admin.purchase.received"),
        ).scalar_one()
        receipt_outbox = session.execute(
            select(OutboxEvent).where(OutboxEvent.event_name == "admin.purchase.received.v1"),
        ).scalar_one()

    assert balance.quantity_on_hand == Decimal("5.000")
    assert movement.direction == "IN"
    assert movement.source_document_type == "PURCHASE_RECEIPT"
    assert supplier_product is not None
    assert supplier_product.last_known_price == Decimal("13.7500")
    assert receipt_audit.request_id == "admin-purchase-receive"
    assert receipt_outbox.event_name == "admin.purchase.received.v1"


def test_admin_purchases_partial_receipt_requires_reason_and_prevents_over_receipt(
    client: TestClient,
) -> None:
    payload = _create_purchase(client, confirm_now=True)
    purchase_id = payload["overview"]["id"]
    line_id = payload["lines"][0]["purchase_line_id"]
    headers = _admin_headers(client)

    missing_reason_response = client.post(
        f"/v1/admin/purchases/{purchase_id}/receive",
        headers=headers,
        json={"lines": [{"purchase_line_id": line_id, "received_quantity": "2.000"}]},
    )
    assert missing_reason_response.status_code == 409
    assert (
        missing_reason_response.json()["message"]
        == "Discrepancy reason is required when received quantity differs from pending quantity."
    )

    partial_response = client.post(
        f"/v1/admin/purchases/{purchase_id}/receive",
        headers=headers,
        json={
            "lines": [
                {
                    "discrepancy_reason": "Proveedor entrego menos piezas",
                    "purchase_line_id": line_id,
                    "received_quantity": "2.000",
                }
            ]
        },
    )
    assert partial_response.status_code == 200
    assert partial_response.json()["overview"]["status"] == "PARTIALLY_RECEIVED"
    assert partial_response.json()["overview"]["has_discrepancy"] is True

    over_response = client.post(
        f"/v1/admin/purchases/{purchase_id}/receive",
        headers=headers,
        json={
            "lines": [
                {
                    "discrepancy_reason": "Intento de sobre recepcion",
                    "purchase_line_id": line_id,
                    "received_quantity": "4.000",
                }
            ]
        },
    )
    assert over_response.status_code == 409
    assert over_response.json()["message"] == "Received quantity cannot exceed pending quantity."


def test_admin_purchases_direct_entry_creates_received_document_and_inventory(
    client: TestClient,
) -> None:
    supplier = _create_supplier(client)
    response = client.post(
        "/v1/admin/purchases/direct-entry",
        headers={**_admin_headers(client), "X-Request-ID": "admin-direct-entry"},
        json={
            "branch_id": _get_branch_id(),
            "external_document_number": "FAC-200",
            "external_document_type": "INVOICE",
            "lines": [
                {
                    "product_id": _get_product_id(SEED_PRODUCT_BOLILLO_STD_CODE),
                    "received_quantity": "3.000",
                    "unit_cost": "9.2500",
                }
            ],
            "notes": "Entrada directa con factura",
            "supplier_id": supplier["overview"]["id"],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["overview"]["document_type"] == "DIRECT_ENTRY"
    assert payload["overview"]["status"] == "RECEIVED"
    assert payload["receipt"]["receipt_count"] == 1
    assert payload["inventory_impact"]["movements"][0]["quantity"] == "3.000"

    with SessionLocal() as session:
        movement = session.execute(select(InventoryMovement)).scalar_one()

    assert movement.movement_type == "PURCHASE_RECEIPT"


def test_admin_purchases_cancel_draft_and_block_cancel_after_receipt(client: TestClient) -> None:
    draft = _create_purchase(client)
    draft_id = draft["overview"]["id"]
    cancel_response = client.post(
        f"/v1/admin/purchases/{draft_id}/cancel",
        headers=_admin_headers(client),
        json={"reason": "Orden duplicada"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["overview"]["status"] == "CANCELLED"

    received = _create_purchase(client, confirm_now=True)
    received_id = received["overview"]["id"]
    line_id = received["lines"][0]["purchase_line_id"]
    receive_response = client.post(
        f"/v1/admin/purchases/{received_id}/receive",
        headers=_admin_headers(client),
        json={"lines": [{"purchase_line_id": line_id, "received_quantity": "5.000"}]},
    )
    assert receive_response.status_code == 200

    cancel_received_response = client.post(
        f"/v1/admin/purchases/{received_id}/cancel",
        headers=_admin_headers(client),
        json={"reason": "No se puede cancelar"},
    )
    assert cancel_received_response.status_code == 409
