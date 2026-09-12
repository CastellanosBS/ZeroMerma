from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRAND_EL_MEJOR_PAN_CODE,
    SEED_BRAND_MERENNA_CODE,
    SEED_PRODUCT_CLASS_BEBIDAS_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_PRODUCT_REBANADA_TRES_LECHES_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Brand
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def _login_admin(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_ADMIN_EMAIL, "password": SEED_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == SEED_ADMIN_EMAIL
    return str(payload["access_token"])


def _login_cashier(client: TestClient) -> str:
    response = client.post(
        "/v1/auth/login",
        json={"email": SEED_USER_EMAIL, "password": SEED_USER_PASSWORD},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == SEED_USER_EMAIL
    return str(payload["access_token"])


def _admin_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login_admin(client)}"}


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _get_product_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
        return str(product_class.id)


def _get_brand_id(code: str) -> str:
    with SessionLocal() as session:
        brand = session.execute(select(Brand).where(Brand.code == code)).scalar_one()
        return str(brand.id)


def test_admin_products_list_returns_seeded_catalog_data(client: TestClient) -> None:
    response = client.get("/v1/admin/products", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["items"]}
    assert SEED_PRODUCT_CONCHA_VAN_CODE in codes
    assert payload["total"] >= len(codes)
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["active_products"] >= len(codes)
    assert payload["filter_options"]["classes"]
    assert payload["filter_options"]["branches"]
    brand_labels = {option["label"] for option in payload["filter_options"]["brands"]}
    assert {"El Mejor Pan", "Merenna"}.issubset(brand_labels)
    assert all(item["brand_name"] == "El Mejor Pan" for item in payload["items"])


def test_admin_products_reject_pos_surface_user(client: TestClient) -> None:
    cashier_token = _login_cashier(client)
    response = client.get(
        "/v1/admin/products",
        headers={"Authorization": f"Bearer {cashier_token}"},
    )

    assert response.status_code == 403


def test_admin_products_search_capture_mode_class_and_pagination_filters(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)

    search_response = client.get(
        "/v1/admin/products?search=coca",
        headers=headers,
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert [item["code"] for item in search_payload["items"]] == [SEED_PRODUCT_COCA_355_CODE]

    direct_response = client.get(
        "/v1/admin/products?capture_mode=PRODUCT_DIRECT",
        headers=headers,
    )
    assert direct_response.status_code == 200
    assert all(item["capture_mode"] == "PRODUCT_DIRECT" for item in direct_response.json()["items"])

    pan_dulce_class_id = _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
    class_response = client.get(
        f"/v1/admin/products?class_id={pan_dulce_class_id}",
        headers=headers,
    )
    assert class_response.status_code == 200
    assert all(item["class_id"] == pan_dulce_class_id for item in class_response.json()["items"])

    page_response = client.get(
        "/v1/admin/products?page=1&page_size=2",
        headers=headers,
    )
    assert page_response.status_code == 200
    page_payload = page_response.json()
    assert page_payload["page"] == 1
    assert page_payload["page_size"] == 2
    assert len(page_payload["items"]) == 2
    assert page_payload["total"] > 2

    el_mejor_pan_brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    brand_response = client.get(
        f"/v1/admin/products?brand_id={el_mejor_pan_brand_id}",
        headers=headers,
    )
    assert brand_response.status_code == 200
    brand_payload = brand_response.json()
    assert brand_payload["items"]
    assert all(item["brand_id"] == el_mejor_pan_brand_id for item in brand_payload["items"])
    assert all(
        "El Mejor Pan" in option["label"] for option in brand_payload["filter_options"]["branches"]
    )

    merenna_brand_id = _get_brand_id(SEED_BRAND_MERENNA_CODE)
    merenna_response = client.get(
        f"/v1/admin/products?brand_id={merenna_brand_id}",
        headers=headers,
    )
    assert merenna_response.status_code == 200
    merenna_payload = merenna_response.json()
    assert merenna_payload["items"] == []
    assert [option["label"] for option in merenna_payload["filter_options"]["branches"]] == [
        "North Branch - Merenna"
    ]
    assert merenna_payload["filter_options"]["classes"] == []


def test_admin_product_detail_returns_real_catalog_row(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_REBANADA_TRES_LECHES_CODE)
    response = client.get(f"/v1/admin/products/{product_id}", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == product_id
    assert payload["code"] == SEED_PRODUCT_REBANADA_TRES_LECHES_CODE
    assert payload["class_name"]
    assert payload["availability"]["state"] == "unknown"
    assert payload["readiness"]["related"]["branch_availability"] == "pending_integration"


def test_admin_product_create_persists_product_and_writes_audit_and_outbox(
    client: TestClient,
) -> None:
    class_id = _get_product_class_id(SEED_PRODUCT_CLASS_BEBIDAS_CODE)
    response = client.post(
        "/v1/admin/products",
        headers={**_admin_headers(client), "X-Request-ID": "admin-product-create-test"},
        json={
            "code": "AGUA-500",
            "name": "Agua 500 ml",
            "product_class_id": class_id,
            "unit_price": "14.00",
            "quick_name": "Agua",
            "search_aliases": "agua botella",
            "status": "active",
            "capture_mode": "PRODUCT_DIRECT",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == "AGUA-500"
    assert Decimal(str(payload["unit_price"])) == Decimal("14.00")

    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == "AGUA-500")).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(product.id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(product.id))
        ).scalar_one()

    assert audit_record.action == "admin.product.created"
    assert audit_record.request_id == "admin-product-create-test"
    assert outbox_event.event_name == "admin.product.created.v1"


def test_admin_product_create_rejects_duplicate_code(client: TestClient) -> None:
    class_id = _get_product_class_id(SEED_PRODUCT_CLASS_BEBIDAS_CODE)
    response = client.post(
        "/v1/admin/products",
        headers=_admin_headers(client),
        json={
            "code": SEED_PRODUCT_COCA_355_CODE,
            "name": "Duplicate Coca",
            "product_class_id": class_id,
            "unit_price": "14.00",
            "status": "active",
        },
    )

    assert response.status_code == 409
    assert "unique" in response.json()["message"].lower()


def test_admin_product_patch_updates_supported_fields(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_COCA_355_CODE)
    response = client.patch(
        f"/v1/admin/products/{product_id}",
        headers={**_admin_headers(client), "X-Request-ID": "admin-product-update-test"},
        json={
            "name": "Coca-Cola 355 ml retornable",
            "unit_price": "19.00",
            "status": "inactive",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Coca-Cola 355 ml retornable"
    assert payload["status"] == "inactive"
    assert Decimal(str(payload["unit_price"])) == Decimal("19.00")

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == product_id,
                AuditLog.action == "admin.product.updated",
            )
        ).scalar_one()

    assert audit_record.request_id == "admin-product-update-test"


def test_admin_product_availability_reports_pending_schema(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_COCA_355_CODE)
    response = client.post(
        f"/v1/admin/products/{product_id}/availability",
        headers={
            **_admin_headers(client),
            "X-Request-ID": "admin-product-availability-pending",
        },
        json={"branch_ids": [], "visible_in_pos": True},
    )

    assert response.status_code == 501
    assert response.json() == {
        "code": "REQUEST_FAILED",
        "message": "An unexpected error occurred.",
        "details": None,
        "request_id": "admin-product-availability-pending",
        "field_errors": None,
    }
    assert "availability schema" not in response.text
