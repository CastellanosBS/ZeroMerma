from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_PRODUCT_CLASS_BEBIDAS_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_PRODUCT_KIND_RAW_MATERIAL,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass, Recipe
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


def _get_product_id(code: str) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == code)).scalar_one()
        return str(product.id)


def _create_raw_material(code: str, *, standard_cost: Decimal | None = Decimal("20.00")) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == SEED_PRODUCT_CLASS_BEBIDAS_CODE)
        ).scalar_one()
        product = Product(
            product_class_id=product_class.id,
            code=code,
            name=f"Raw {code}",
            quick_name=code,
            search_aliases=code,
            display_order=900,
            product_kind=CATALOG_PRODUCT_KIND_RAW_MATERIAL,
            unit_of_measure="kg",
            unit_price=Decimal("0.00"),
            standard_cost=standard_cost,
            currency_code="MXN",
            is_active=True,
            is_sellable=False,
        )
        session.add(product)
        session.commit()
        return str(product.id)


def test_admin_recipe_costs_list_returns_finished_products_without_fake_data(
    client: TestClient,
) -> None:
    response = client.get("/v1/admin/recipes-costs/products", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    codes = {item["product_code"] for item in payload["items"]}
    assert SEED_PRODUCT_CONCHA_VAN_CODE in codes
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["without_recipe"] >= 1
    assert payload["filter_options"]["classes"]
    assert payload["filter_options"]["raw_materials"] == []


def test_admin_recipe_create_calculates_cost_and_writes_audit(
    client: TestClient,
) -> None:
    product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)
    raw_material_id = _create_raw_material("RAW-FLOUR")

    response = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers={**_admin_headers(client), "X-Request-ID": "admin-recipe-create-test"},
        json={
            "product_id": product_id,
            "version_name": "Base",
            "yield_qty": "10.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [{"input_product_id": raw_material_id, "quantity": "2.000"}],
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["product"]["active_recipe_id"]
    assert Decimal(str(payload["active_recipe"]["total_batch_cost"])) == Decimal("40.00000")
    assert Decimal(str(payload["active_recipe"]["calculated_unit_cost"])) == Decimal("4.00000")

    with SessionLocal() as session:
        recipe = session.execute(
            select(Recipe).where(Recipe.product_id == uuid.UUID(product_id), Recipe.is_active.is_(True))
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(recipe.id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(recipe.id))
        ).scalar_one()

    assert audit_record.action == "admin.recipe.created"
    assert audit_record.request_id == "admin-recipe-create-test"
    assert outbox_event.event_name == "admin.recipe.created.v1"


def test_admin_recipe_rejects_non_finished_good_target(client: TestClient) -> None:
    raw_target_id = _create_raw_material("RAW-TARGET")
    raw_input_id = _create_raw_material("RAW-INPUT")

    response = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=_admin_headers(client),
        json={
            "product_id": raw_target_id,
            "version_name": "Invalid",
            "yield_qty": "1.000",
            "yield_uom": "kg",
            "activate": True,
            "inputs": [{"input_product_id": raw_input_id, "quantity": "1.000"}],
        },
    )

    assert response.status_code == 409
    assert "finished goods" in response.json()["detail"]


def test_admin_recipe_rejects_non_raw_material_input(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)
    finished_input_id = _get_product_id(SEED_PRODUCT_COCA_355_CODE)

    response = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=_admin_headers(client),
        json={
            "product_id": product_id,
            "version_name": "Invalid input",
            "yield_qty": "1.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [{"input_product_id": finished_input_id, "quantity": "1.000"}],
        },
    )

    assert response.status_code == 409
    assert "RAW_MATERIAL" in response.json()["detail"]


def test_admin_recipe_rejects_duplicate_inputs_and_invalid_shape(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)
    raw_input_id = _create_raw_material("RAW-SUGAR")

    duplicate_response = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=_admin_headers(client),
        json={
            "product_id": product_id,
            "version_name": "Duplicates",
            "yield_qty": "1.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [
                {"input_product_id": raw_input_id, "quantity": "1.000"},
                {"input_product_id": raw_input_id, "quantity": "2.000"},
            ],
        },
    )

    assert duplicate_response.status_code == 409
    assert "duplicate" in duplicate_response.json()["detail"].lower()

    missing_inputs_response = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=_admin_headers(client),
        json={
            "product_id": product_id,
            "version_name": "Missing inputs",
            "yield_qty": "1.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [],
        },
    )
    assert missing_inputs_response.status_code == 422

    invalid_yield_response = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=_admin_headers(client),
        json={
            "product_id": product_id,
            "version_name": "Invalid yield",
            "yield_qty": "0",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [{"input_product_id": raw_input_id, "quantity": "1.000"}],
        },
    )
    assert invalid_yield_response.status_code == 422


def test_admin_recipe_activation_deactivates_previous_active_version(
    client: TestClient,
) -> None:
    product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)
    raw_input_id = _create_raw_material("RAW-BUTTER")
    headers = _admin_headers(client)

    first = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=headers,
        json={
            "product_id": product_id,
            "version_name": "First",
            "yield_qty": "10.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [{"input_product_id": raw_input_id, "quantity": "1.000"}],
        },
    )
    assert first.status_code == 201
    first_recipe_id = first.json()["active_recipe"]["id"]

    second = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=headers,
        json={
            "product_id": product_id,
            "version_name": "Second",
            "yield_qty": "5.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [{"input_product_id": raw_input_id, "quantity": "1.000"}],
        },
    )
    assert second.status_code == 201
    second_recipe_id = second.json()["active_recipe"]["id"]
    assert second_recipe_id != first_recipe_id

    with SessionLocal() as session:
        active_recipes = session.execute(
            select(Recipe).where(Recipe.product_id == uuid.UUID(product_id), Recipe.is_active.is_(True))
        ).scalars().all()
        first_recipe = session.execute(select(Recipe).where(Recipe.id == uuid.UUID(first_recipe_id))).scalar_one()

    assert len(active_recipes) == 1
    assert str(active_recipes[0].id) == second_recipe_id
    assert first_recipe.is_active is False


def test_admin_recipe_apply_standard_cost_updates_product(client: TestClient) -> None:
    product_id = _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE)
    raw_input_id = _create_raw_material("RAW-MILK", standard_cost=Decimal("15.00"))
    headers = _admin_headers(client)
    created = client.post(
        "/v1/admin/recipes-costs/recipes",
        headers=headers,
        json={
            "product_id": product_id,
            "version_name": "Cost update",
            "yield_qty": "3.000",
            "yield_uom": "piece",
            "activate": True,
            "inputs": [{"input_product_id": raw_input_id, "quantity": "2.000"}],
        },
    )
    assert created.status_code == 201
    recipe_id = created.json()["active_recipe"]["id"]

    response = client.post(
        f"/v1/admin/recipes-costs/recipes/{recipe_id}/apply-standard-cost",
        headers={**headers, "X-Request-ID": "admin-standard-cost-test"},
    )

    assert response.status_code == 200
    assert Decimal(str(response.json()["product"]["product_standard_cost"])) == Decimal("10.0000")

    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.id == uuid.UUID(product_id))).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.resource_id == str(product.id),
                AuditLog.action == "admin.product.standard_cost_updated",
            )
        ).scalar_one()

    assert product.standard_cost == Decimal("10.0000")
    assert audit_record.request_id == "admin-standard-cost-test"
