from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRAND_EL_MEJOR_PAN_CODE,
    SEED_PRODUCT_CLASS_BEBIDAS_CODE,
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Brand
from zeromerma_api.modules.catalog.infrastructure.models import ProductClass
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


def _admin_headers(client: TestClient) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login_admin(client)}"}


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


def test_admin_product_classes_list_returns_real_seeded_classes(client: TestClient) -> None:
    response = client.get("/v1/admin/product-classes", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {item["code"] for item in payload["items"]}
    assert SEED_PRODUCT_CLASS_PAN_DULCE_CODE in codes
    assert SEED_PRODUCT_CLASS_BEBIDAS_CODE in codes
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["total_classes"] >= len(codes)
    assert payload["metrics"]["class_capture"] >= 1
    assert payload["metrics"]["product_direct"] >= 1
    assert payload["filter_options"]["brands"]


def test_admin_product_classes_filters_search_capture_mode_product_presence_and_brand(
    client: TestClient,
) -> None:
    headers = _admin_headers(client)

    search_response = client.get(
        "/v1/admin/product-classes?search=bolillo",
        headers=headers,
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert [item["code"] for item in search_payload["items"]] == [SEED_PRODUCT_CLASS_BOLILLO_CODE]

    capture_response = client.get(
        "/v1/admin/product-classes?capture_mode=CLASS_CAPTURE",
        headers=headers,
    )
    assert capture_response.status_code == 200
    assert capture_response.json()["items"]
    assert all(
        item["capture_mode_default"] == "CLASS_CAPTURE"
        for item in capture_response.json()["items"]
    )

    presence_response = client.get(
        "/v1/admin/product-classes?product_presence=with_products",
        headers=headers,
    )
    assert presence_response.status_code == 200
    assert presence_response.json()["items"]
    assert all(item["product_count"] > 0 for item in presence_response.json()["items"])

    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    brand_response = client.get(
        f"/v1/admin/product-classes?brand_id={brand_id}",
        headers=headers,
    )
    assert brand_response.status_code == 200
    assert brand_response.json()["items"]
    assert all(item["brand_id"] == brand_id for item in brand_response.json()["items"])


def test_admin_product_class_detail_returns_relationship_and_warnings(
    client: TestClient,
) -> None:
    class_id = _get_product_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
    response = client.get(f"/v1/admin/product-classes/{class_id}", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == class_id
    assert payload["capture_mode_default"] == "CLASS_CAPTURE"
    assert Decimal(str(payload["class_capture_unit_price"])) == Decimal("12.00")
    assert payload["product_count"] >= 1
    assert payload["linked_products"]
    assert payload["warnings"]["codes"] == []
    assert payload["readiness"] == "ready"


def test_admin_product_class_create_product_direct_persists_and_audits(
    client: TestClient,
) -> None:
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    response = client.post(
        "/v1/admin/product-classes",
        headers={**_admin_headers(client), "X-Request-ID": "admin-class-direct-create-test"},
        json={
            "brand_id": brand_id,
            "code": "ADMIN-DIRECT-TEST",
            "name": "Admin Direct Test",
            "quick_name": "Direct",
            "search_aliases": "admin direct",
            "capture_mode_default": "PRODUCT_DIRECT",
            "class_capture_unit_price": None,
            "currency_code": "MXN",
            "display_order": 900,
            "status": "active",
            "is_sellable": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["code"] == "ADMIN-DIRECT-TEST"
    assert payload["class_capture_unit_price"] is None

    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == "ADMIN-DIRECT-TEST")
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(product_class.id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(product_class.id))
        ).scalar_one()

    assert audit_record.action == "admin.product_class.created"
    assert audit_record.request_id == "admin-class-direct-create-test"
    assert outbox_event.event_name == "admin.product_class.created.v1"


def test_admin_product_class_create_class_capture_requires_price(
    client: TestClient,
) -> None:
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)

    missing_price_response = client.post(
        "/v1/admin/product-classes",
        headers=_admin_headers(client),
        json={
            "brand_id": brand_id,
            "code": "ADMIN-CLASS-MISSING-PRICE",
            "name": "Admin Class Missing Price",
            "capture_mode_default": "CLASS_CAPTURE",
            "class_capture_unit_price": None,
            "currency_code": "MXN",
            "display_order": 901,
            "status": "active",
            "is_sellable": True,
        },
    )

    assert missing_price_response.status_code == 409
    assert "require" in missing_price_response.json()["detail"].lower()

    valid_response = client.post(
        "/v1/admin/product-classes",
        headers=_admin_headers(client),
        json={
            "brand_id": brand_id,
            "code": "ADMIN-CLASS-PRICE",
            "name": "Admin Class Price",
            "capture_mode_default": "CLASS_CAPTURE",
            "class_capture_unit_price": "8.50",
            "currency_code": "MXN",
            "display_order": 902,
            "status": "active",
            "is_sellable": True,
        },
    )

    assert valid_response.status_code == 201
    assert Decimal(str(valid_response.json()["class_capture_unit_price"])) == Decimal("8.50")


def test_admin_product_class_rejects_product_direct_with_class_price(
    client: TestClient,
) -> None:
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    response = client.post(
        "/v1/admin/product-classes",
        headers=_admin_headers(client),
        json={
            "brand_id": brand_id,
            "code": "ADMIN-DIRECT-WITH-PRICE",
            "name": "Admin Direct With Price",
            "capture_mode_default": "PRODUCT_DIRECT",
            "class_capture_unit_price": "10.00",
            "currency_code": "MXN",
            "display_order": 903,
            "status": "active",
            "is_sellable": True,
        },
    )

    assert response.status_code == 409
    assert "cannot" in response.json()["detail"].lower()


def test_admin_product_class_create_rejects_duplicate_code(client: TestClient) -> None:
    brand_id = _get_brand_id(SEED_BRAND_EL_MEJOR_PAN_CODE)
    response = client.post(
        "/v1/admin/product-classes",
        headers=_admin_headers(client),
        json={
            "brand_id": brand_id,
            "code": SEED_PRODUCT_CLASS_BEBIDAS_CODE,
            "name": "Duplicate Beverages",
            "capture_mode_default": "PRODUCT_DIRECT",
            "class_capture_unit_price": None,
            "currency_code": "MXN",
            "display_order": 904,
            "status": "active",
            "is_sellable": True,
        },
    )

    assert response.status_code == 409
    assert "unique" in response.json()["detail"].lower()


def test_admin_product_class_patch_updates_status_order_and_audit(
    client: TestClient,
) -> None:
    class_id = _get_product_class_id(SEED_PRODUCT_CLASS_BEBIDAS_CODE)
    response = client.patch(
        f"/v1/admin/product-classes/{class_id}",
        headers={**_admin_headers(client), "X-Request-ID": "admin-class-update-test"},
        json={
            "display_order": 777,
            "status": "inactive",
            "is_sellable": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_order"] == 777
    assert payload["status"] == "inactive"
    assert payload["is_sellable"] is False

    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.id == class_id)
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(product_class.id),
                AuditLog.action == "admin.product_class.updated",
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(product_class.id),
                OutboxEvent.event_name == "admin.product_class.updated.v1",
            )
        ).scalar_one()

    assert product_class.display_order == 777
    assert product_class.is_active is False
    assert audit_record.request_id == "admin-class-update-test"
    assert outbox_event.aggregate_id == str(product_class.id)
