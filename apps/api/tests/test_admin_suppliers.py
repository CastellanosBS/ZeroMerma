from __future__ import annotations

import uuid

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
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.suppliers.infrastructure.models import Supplier, SupplierProduct
from zeromerma_api.testing.authorization import owner_headers


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
    return owner_headers()


def _get_branch_id(code: str = SEED_BRANCH_CODE) -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == code)).scalar_one()
        return str(branch.id)


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _supplier_payload(
    *,
    code: str = "SUP-TRIGO",
    product_code: str = SEED_PRODUCT_CONCHA_VAN_CODE,
    tax_id: str = "XAXX010101000",
) -> dict[str, object]:
    return {
        "branch_ids": [_get_branch_id()],
        "category": "RAW_MATERIALS",
        "code": code,
        "commercial_name": "Harinas del Trigo",
        "contacts": [
            {
                "email": "ventas@trigo.test",
                "is_primary": True,
                "name": "Laura Compras",
                "phone": "6621000000",
                "role": "Ventas",
            }
        ],
        "credit_days": 15,
        "default_currency": "MXN",
        "delivery_notes": "Entrega matutina",
        "fiscal_address": "Calle Fiscal 123",
        "lead_time_days": 2,
        "legal_name": "Harinas del Trigo SA de CV",
        "minimum_order_amount": "500.00",
        "payment_fiscal_email": "facturas@trigo.test",
        "payment_terms_type": "CREDIT",
        "product_relations": [
            {
                "currency": "MXN",
                "is_active": True,
                "last_known_price": "18.2500",
                "lead_time_days": 2,
                "minimum_order_qty": "1.000",
                "product_id": _get_product_id(product_code),
                "purchase_uom": "KG",
                "supplier_sku": "TRIGO-001",
            }
        ],
        "purchase_notes": "Revisar precio semanalmente",
        "status": "ACTIVE",
        "tax_id": tax_id,
    }


def _create_supplier(
    client: TestClient, *, code: str = "SUP-TRIGO", tax_id: str = "XAXX010101000"
) -> dict[str, object]:
    response = client.post(
        "/v1/admin/suppliers",
        headers={**_admin_headers(client), "X-Request-ID": "admin-supplier-test"},
        json=_supplier_payload(code=code, tax_id=tax_id),
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_suppliers_list_empty_and_rejects_pos_surface_user(client: TestClient) -> None:
    response = client.get("/v1/admin/suppliers", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert payload["backend_contract"]["create_endpoint"] == "POST /v1/admin/suppliers"
    assert payload["filter_options"]["categories"]

    forbidden_response = client.get(
        "/v1/admin/suppliers",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_suppliers_create_detail_audit_and_outbox(client: TestClient) -> None:
    payload = _create_supplier(client)
    supplier_id = payload["overview"]["id"]

    assert payload["overview"]["code"] == "SUP-TRIGO"
    assert payload["overview"]["status"] == "ACTIVE"
    assert payload["commercial_terms"]["payment_terms_type"] == "CREDIT"
    assert payload["contacts"][0]["is_primary"] is True
    assert payload["product_associations"][0]["product_code"] == SEED_PRODUCT_CONCHA_VAN_CODE
    assert payload["branch_applicability"][0]["branch_code"] == SEED_BRANCH_CODE
    assert payload["warnings"] == []

    with SessionLocal() as session:
        supplier = session.execute(
            select(Supplier).where(Supplier.id == uuid.UUID(str(supplier_id)))
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(supplier_id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(supplier_id))
        ).scalar_one()

    assert supplier.tax_id == "XAXX010101000"
    assert audit_record.action == "admin.supplier.created"
    assert audit_record.request_id == "admin-supplier-test"
    assert outbox_event.event_name == "admin.supplier.created.v1"


def test_admin_suppliers_filters_search_status_category_product_kind_and_branch(
    client: TestClient,
) -> None:
    created = _create_supplier(client)
    supplier_id = created["overview"]["id"]

    searches = [
        "/v1/admin/suppliers?search=trigo",
        "/v1/admin/suppliers?status=ACTIVE",
        "/v1/admin/suppliers?category=RAW_MATERIALS",
        "/v1/admin/suppliers?product_kind=FINISHED_GOOD",
        f"/v1/admin/suppliers?branch_id={_get_branch_id()}",
    ]
    for path in searches:
        response = client.get(path, headers=_admin_headers(client))
        assert response.status_code == 200
        assert [item["id"] for item in response.json()["items"]] == [supplier_id]

    warnings_response = client.get(
        "/v1/admin/suppliers?warning_state=without_warnings", headers=_admin_headers(client)
    )
    assert warnings_response.status_code == 200
    assert [item["id"] for item in warnings_response.json()["items"]] == [supplier_id]


def test_admin_suppliers_validates_required_fields_duplicates_and_contact_channel(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)
    missing_name_response = client.post(
        "/v1/admin/suppliers", headers=headers, json={**_supplier_payload(), "legal_name": ""}
    )
    assert missing_name_response.status_code == 422

    bad_contact_response = client.post(
        "/v1/admin/suppliers",
        headers=headers,
        json={
            **_supplier_payload(code="SUP-BAD", tax_id="BAD010101000"),
            "contacts": [{"name": "Sin contacto", "is_primary": True}],
        },
    )
    assert bad_contact_response.status_code == 409
    assert (
        bad_contact_response.json()["message"]
        == "Supplier contact needs at least one contact channel."
    )

    _create_supplier(client)
    duplicate_code_response = client.post(
        "/v1/admin/suppliers",
        headers=headers,
        json=_supplier_payload(code="SUP-TRIGO", tax_id="OTHER010101000"),
    )
    assert duplicate_code_response.status_code == 409

    duplicate_tax_response = client.post(
        "/v1/admin/suppliers",
        headers=headers,
        json=_supplier_payload(code="SUP-OTHER", tax_id="XAXX010101000"),
    )
    assert duplicate_tax_response.status_code == 409


def test_admin_suppliers_update_status_contact_product_and_branch_relations(
    client: TestClient,
) -> None:
    created = _create_supplier(client)
    supplier_id = created["overview"]["id"]
    headers = _admin_headers(client)

    updated_payload = _supplier_payload(
        code="SUP-TRIGO", product_code=SEED_PRODUCT_BOLILLO_STD_CODE
    )
    updated_payload["legal_name"] = "Harinas del Trigo Actualizado SA de CV"
    update_response = client.patch(
        f"/v1/admin/suppliers/{supplier_id}", headers=headers, json=updated_payload
    )
    assert update_response.status_code == 200
    assert (
        update_response.json()["overview"]["legal_name"] == "Harinas del Trigo Actualizado SA de CV"
    )

    status_response = client.post(
        f"/v1/admin/suppliers/{supplier_id}/status",
        headers=headers,
        json={"notes": "Incidencia de calidad", "status": "BLOCKED"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["overview"]["status"] == "BLOCKED"
    assert status_response.json()["warnings"][0]["code"] == "blocked_supplier"

    contact_response = client.post(
        f"/v1/admin/suppliers/{supplier_id}/contacts",
        headers=headers,
        json={"email": "compras2@trigo.test", "is_primary": True, "name": "Contacto alterno"},
    )
    assert contact_response.status_code == 201
    assert contact_response.json()["contacts"][0]["name"] == "Contacto alterno"

    product_response = client.post(
        f"/v1/admin/suppliers/{supplier_id}/products",
        headers=headers,
        json={
            "is_active": False,
            "lead_time_days": 5,
            "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
            "purchase_uom": "PCS",
        },
    )
    assert product_response.status_code == 201
    relation = next(
        item
        for item in product_response.json()["product_associations"]
        if item["product_code"] == SEED_PRODUCT_CONCHA_VAN_CODE
    )
    assert relation["is_active"] is False

    branch_response = client.post(
        f"/v1/admin/suppliers/{supplier_id}/branches",
        headers=headers,
        json={"branch_id": _get_branch_id(), "delivery_notes": "Solo lunes", "is_active": False},
    )
    assert branch_response.status_code == 201
    assert branch_response.json()["branch_applicability"][0]["is_active"] is False

    with SessionLocal() as session:
        actions = (
            session.execute(
                select(AuditLog.action)
                .where(AuditLog.resource_id == str(supplier_id))
                .order_by(AuditLog.occurred_at.asc()),
            )
            .scalars()
            .all()
        )
        inactive_relation = session.execute(
            select(SupplierProduct).where(
                SupplierProduct.supplier_id == uuid.UUID(str(supplier_id)),
                SupplierProduct.product_id == _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
            ),
        ).scalar_one()

    assert "admin.supplier.status_changed" in actions
    assert "admin.supplier.contact.created" in actions
    assert "admin.supplier.product.updated" in actions
    assert inactive_relation.is_active is False
