from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRAND_EL_MEJOR_PAN_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Brand
from zeromerma_api.modules.catalog.domain.constants import CATALOG_CAPTURE_MODE_CLASS_CAPTURE
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass


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


def _get_product(code: str) -> Product:
    with SessionLocal() as session:
        return session.execute(select(Product).where(Product.code == code)).scalar_one()


def _get_product_class(code: str) -> ProductClass:
    with SessionLocal() as session:
        return session.execute(select(ProductClass).where(ProductClass.code == code)).scalar_one()


def _create_zero_price_class() -> str:
    with SessionLocal() as session:
        brand = session.execute(
            select(Brand).where(Brand.code == SEED_BRAND_EL_MEJOR_PAN_CODE)
        ).scalar_one()
        product_class = ProductClass(
            brand_id=brand.id,
            code="PRICE-ZERO-CLASS",
            name="Price Zero Class",
            quick_name="Zero",
            search_aliases="price zero",
            display_order=999,
            capture_mode_default=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
            class_capture_unit_price=Decimal("0.00"),
            currency_code="MXN",
            is_active=True,
            is_sellable=True,
        )
        session.add(product_class)
        session.commit()
        return str(product_class.id)


def test_admin_prices_list_builds_unified_product_and_class_rows(client: TestClient) -> None:
    response = client.get("/v1/admin/prices", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_backend_connected"] is True
    assert payload["items"]
    assert payload["metrics"]["total_entities"] == payload["total"]
    assert payload["metrics"]["product_direct"] >= 1
    assert payload["metrics"]["class_capture"] >= 1
    assert payload["filter_options"]["brands"]
    assert payload["filter_options"]["classes"]

    owners = {item["price_owner"] for item in payload["items"]}
    assert "product_unit_price" in owners
    assert "class_capture_unit_price" in owners


def test_admin_prices_filters_search_capture_mode_and_health(client: TestClient) -> None:
    headers = _admin_headers(client)
    zero_class_id = _create_zero_price_class()

    search_response = client.get("/v1/admin/prices?search=coca", headers=headers)
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert [item["entity_code"] for item in search_payload["items"]] == [SEED_PRODUCT_COCA_355_CODE]
    assert search_payload["items"][0]["entity_type"] == "product"
    assert search_payload["items"][0]["capture_mode"] == "PRODUCT_DIRECT"

    class_capture_response = client.get(
        "/v1/admin/prices?capture_mode=CLASS_CAPTURE",
        headers=headers,
    )
    assert class_capture_response.status_code == 200
    assert class_capture_response.json()["items"]
    assert all(item["entity_type"] == "class" for item in class_capture_response.json()["items"])

    missing_response = client.get("/v1/admin/prices?price_health=missing_price", headers=headers)
    assert missing_response.status_code == 200
    assert any(item["entity_id"] == zero_class_id for item in missing_response.json()["items"])


def test_admin_prices_detail_exposes_price_owner_and_cost_comparison(client: TestClient) -> None:
    product = _get_product(SEED_PRODUCT_COCA_355_CODE)
    with SessionLocal() as session:
        product_record = session.execute(
            select(Product).where(Product.id == product.id)
        ).scalar_one()
        product_record.standard_cost = Decimal("10.00")
        session.commit()

    response = client.get(f"/v1/admin/prices/product/{product.id}", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["price"]["entity_type"] == "product"
    assert payload["price"]["price_owner"] == "product_unit_price"
    assert Decimal(str(payload["price"]["standard_cost"])) == Decimal("10.0000")
    assert payload["history_note"]


def test_admin_prices_update_product_direct_writes_product_owner_and_audits(
    client: TestClient,
) -> None:
    product = _get_product(SEED_PRODUCT_COCA_355_CODE)
    response = client.patch(
        f"/v1/admin/prices/product/{product.id}",
        headers={**_admin_headers(client), "X-Request-ID": "admin-price-product-update"},
        json={"price": "19.50"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert Decimal(str(payload["price"]["current_price"])) == Decimal("19.50")
    assert payload["price"]["price_owner"] == "product_unit_price"

    with SessionLocal() as session:
        updated_product = session.execute(
            select(Product).where(Product.id == product.id)
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(product.id),
                AuditLog.request_id == "admin-price-product-update",
            )
        ).scalar_one()

    assert updated_product.unit_price == Decimal("19.50")
    assert audit_record.action == "admin.product.updated"


def test_admin_prices_update_class_capture_writes_class_owner_and_audits(
    client: TestClient,
) -> None:
    product_class = _get_product_class(SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
    response = client.patch(
        f"/v1/admin/prices/class/{product_class.id}",
        headers={**_admin_headers(client), "X-Request-ID": "admin-price-class-update"},
        json={"price": "13.50"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert Decimal(str(payload["price"]["current_price"])) == Decimal("13.50")
    assert payload["price"]["price_owner"] == "class_capture_unit_price"

    with SessionLocal() as session:
        updated_class = session.execute(
            select(ProductClass).where(ProductClass.id == product_class.id)
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(product_class.id),
                AuditLog.request_id == "admin-price-class-update",
            )
        ).scalar_one()

    assert updated_class.class_capture_unit_price == Decimal("13.50")
    assert audit_record.action == "admin.product_class.updated"


def test_admin_prices_reject_negative_price(client: TestClient) -> None:
    product = _get_product(SEED_PRODUCT_COCA_355_CODE)
    response = client.patch(
        f"/v1/admin/prices/product/{product.id}",
        headers=_admin_headers(client),
        json={"price": "-1.00"},
    )

    assert response.status_code == 422
