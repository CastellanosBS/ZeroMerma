from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.discounts.infrastructure.models import CommercialDiscount
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers


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
    return owner_headers()


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _get_class_id(code: str) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == code)
        ).scalar_one()
        return str(product_class.id)


def test_admin_discounts_create_percentage_and_list_filters(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_COCA_355_CODE)
    response = client.post(
        "/v1/admin/discounts",
        headers={**_admin_headers(client), "X-Request-ID": "admin-discount-create-product"},
        json={
            "code": "DISC-COCA-10",
            "name": "Coca 10 percent",
            "description": "Commercial governance discount",
            "discount_type": "PERCENTAGE",
            "target_scope": "PRODUCT",
            "target_id": product_id,
            "value": "10.00",
            "currency_code": "MXN",
            "status": "ACTIVE",
            "priority": 25,
            "is_pos_eligible": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["target_scope"] == "PRODUCT"
    assert payload["target_id"] == product_id
    assert payload["base_price"] is not None
    assert payload["preview_price"] is not None
    assert payload["health"] == "healthy"

    list_response = client.get("/v1/admin/discounts?search=coca", headers=_admin_headers(client))

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["is_backend_connected"] is True
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["code"] == "DISC-COCA-10"
    assert list_payload["metrics"]["active_discounts"] == 1
    assert list_payload["filter_options"]["products"]

    with SessionLocal() as session:
        discount = session.execute(
            select(CommercialDiscount).where(CommercialDiscount.code == "DISC-COCA-10")
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(discount.id),
                AuditLog.request_id == "admin-discount-create-product",
            )
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(discount.id))
        ).scalar_one()

    assert audit_record.action == "admin.commercial_discount.created"
    assert outbox_event.event_name == "admin.commercial_discount.created.v1"


def test_admin_discounts_create_fixed_class_discount_and_detail(client: TestClient) -> None:
    class_id = _get_class_id(SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
    response = client.post(
        "/v1/admin/discounts",
        headers=_admin_headers(client),
        json={
            "code": "DISC-PAN-2",
            "name": "Pan dulce menos dos",
            "discount_type": "FIXED_AMOUNT",
            "target_scope": "CLASS",
            "target_id": class_id,
            "value": "2.00",
            "currency_code": "MXN",
            "status": "INACTIVE",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["target_scope"] == "CLASS"
    assert payload["target_id"] == class_id
    assert Decimal(str(payload["base_price"])) == Decimal("12.00")
    assert Decimal(str(payload["preview_price"])) == Decimal("10.00")

    detail_response = client.get(
        f"/v1/admin/discounts/{payload['id']}", headers=_admin_headers(client)
    )

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == payload["id"]
    assert detail_payload["target_name"]
    assert detail_payload["warnings"]["codes"] == []


def test_admin_discounts_reject_invalid_values_and_missing_target(client: TestClient) -> None:
    headers = _admin_headers(client)
    invalid_percentage = client.post(
        "/v1/admin/discounts",
        headers=headers,
        json={
            "name": "Invalid percent",
            "discount_type": "PERCENTAGE",
            "target_scope": "GLOBAL",
            "value": "101.00",
            "currency_code": "MXN",
        },
    )
    invalid_fixed = client.post(
        "/v1/admin/discounts",
        headers=headers,
        json={
            "name": "Invalid fixed",
            "discount_type": "FIXED_AMOUNT",
            "target_scope": "GLOBAL",
            "value": "0.00",
            "currency_code": "MXN",
        },
    )
    missing_target = client.post(
        "/v1/admin/discounts",
        headers=headers,
        json={
            "name": "Missing target",
            "discount_type": "PERCENTAGE",
            "target_scope": "PRODUCT",
            "value": "5.00",
            "currency_code": "MXN",
        },
    )

    assert invalid_percentage.status_code == 422
    assert invalid_fixed.status_code == 422
    assert missing_target.status_code == 422


def test_admin_discounts_update_status_and_duplicate(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_COCA_355_CODE)
    create_response = client.post(
        "/v1/admin/discounts",
        headers=_admin_headers(client),
        json={
            "code": "DISC-TOGGLE",
            "name": "Toggle discount",
            "discount_type": "PERCENTAGE",
            "target_scope": "PRODUCT",
            "target_id": product_id,
            "value": "5.00",
            "currency_code": "MXN",
            "status": "INACTIVE",
        },
    )
    discount_id = create_response.json()["id"]

    update_response = client.patch(
        f"/v1/admin/discounts/{discount_id}",
        headers={**_admin_headers(client), "X-Request-ID": "admin-discount-update"},
        json={"status": "ACTIVE", "value": "7.50"},
    )
    duplicate_response = client.post(
        f"/v1/admin/discounts/{discount_id}/duplicate",
        headers=_admin_headers(client),
        json={"code": "DISC-TOGGLE-COPY", "name": "Toggle discount copy"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["status"] == "ACTIVE"
    assert Decimal(str(update_response.json()["value"])) == Decimal("7.5000")
    assert duplicate_response.status_code == 200
    assert duplicate_response.json()["status"] == "INACTIVE"
    assert duplicate_response.json()["code"] == "DISC-TOGGLE-COPY"

    with SessionLocal() as session:
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == discount_id,
                AuditLog.request_id == "admin-discount-update",
            )
        ).scalar_one()

    assert audit_record.action == "admin.commercial_discount.updated"


def test_admin_discounts_warn_for_expired_active_discount(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_COCA_355_CODE)
    expired_at = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()
    response = client.post(
        "/v1/admin/discounts",
        headers=_admin_headers(client),
        json={
            "code": "DISC-EXPIRED",
            "name": "Expired active discount",
            "discount_type": "PERCENTAGE",
            "target_scope": "PRODUCT",
            "target_id": product_id,
            "value": "5.00",
            "currency_code": "MXN",
            "valid_to_utc": expired_at,
            "status": "ACTIVE",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["validity_status"] == "expired"
    assert "active_expired" in payload["warnings"]["codes"]
    assert payload["health"] == "expired"
