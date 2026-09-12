from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_BRANCH_CODE,
    SEED_PRODUCT_CLASS_BEBIDAS_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.domain.constants import CATALOG_PRODUCT_KIND_RAW_MATERIAL
from zeromerma_api.modules.catalog.infrastructure.models import (
    Product,
    ProductClass,
    Recipe,
    RecipeInput,
)
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.production.infrastructure.models import ProductionBatch


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


def _create_raw_material(code: str, *, standard_cost: Decimal | None = Decimal("20.00")) -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == SEED_PRODUCT_CLASS_BEBIDAS_CODE),
        ).scalar_one()
        product = Product(
            code=code,
            currency_code="MXN",
            display_order=900,
            is_active=True,
            is_sellable=False,
            name=f"Raw {code}",
            product_class_id=product_class.id,
            product_kind=CATALOG_PRODUCT_KIND_RAW_MATERIAL,
            quick_name=code,
            search_aliases=code,
            standard_cost=standard_cost,
            unit_of_measure="kg",
            unit_price=Decimal("0.00"),
        )
        session.add(product)
        session.commit()
        return str(product.id)


def _create_active_recipe(
    *,
    input_qty: str = "2.000",
    output_code: str = SEED_PRODUCT_CONCHA_VAN_CODE,
    raw_material_id: str,
    version_name: str = "Production base",
    yield_qty: str = "10.000",
) -> str:
    with SessionLocal() as session:
        product = session.execute(select(Product).where(Product.code == output_code)).scalar_one()
        session.query(Recipe).filter(
            Recipe.product_id == product.id, Recipe.is_active.is_(True)
        ).update(
            {Recipe.is_active: False},
            synchronize_session=False,
        )
        recipe = Recipe(
            is_active=True,
            product_id=product.id,
            version_name=version_name,
            yield_qty=Decimal(yield_qty),
            yield_uom=product.unit_of_measure,
        )
        session.add(recipe)
        session.flush()
        session.add(
            RecipeInput(
                display_order=10,
                input_product_id=UUID(raw_material_id),
                quantity=Decimal(input_qty),
                recipe_id=recipe.id,
            ),
        )
        session.commit()
        return str(recipe.id)


def _create_production(
    client: TestClient,
    *,
    planned_output_qty: str = "20.000",
    product_code: str = SEED_PRODUCT_CONCHA_VAN_CODE,
    recipe_id: str,
) -> dict[str, object]:
    response = client.post(
        "/v1/admin/production",
        headers={**_admin_headers(client), "X-Request-ID": "admin-production-create"},
        json={
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "notes": "Backoffice production draft",
            "planned_output_qty": planned_output_qty,
            "product_id": _get_product_id(product_code),
            "recipe_id": recipe_id,
        },
    )

    assert response.status_code == 201
    return dict(response.json())


def _seed_raw_stock(client: TestClient, *, product_id: str, quantity: str = "10.000") -> None:
    response = client.post(
        "/v1/admin/inventory/adjustments",
        headers=_admin_headers(client),
        json={
            "adjustment_type": "INCREASE",
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "location_code": "BACKROOM",
            "product_id": product_id,
            "quantity": quantity,
            "reason": "Production material stock",
        },
    )
    assert response.status_code == 201


def _create_started_production(
    client: TestClient, *, actual_stock: str = "10.000"
) -> dict[str, object]:
    raw_material_id = _create_raw_material("RAW-PROD-FLOUR")
    recipe_id = _create_active_recipe(raw_material_id=raw_material_id)
    _seed_raw_stock(client, product_id=raw_material_id, quantity=actual_stock)
    production = _create_production(client, recipe_id=recipe_id)
    production_id = str(production["overview"]["id"])

    start_response = client.post(
        f"/v1/admin/production/{production_id}/start",
        headers={**_admin_headers(client), "X-Request-ID": "admin-production-start"},
        json={"notes": "Start batch"},
    )

    assert start_response.status_code == 200
    return dict(start_response.json())


def test_admin_production_list_empty_and_rejects_pos_surface_user(client: TestClient) -> None:
    response = client.get("/v1/admin/production", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["is_backend_connected"] is True
    assert payload["metrics"]["total_batches"] == 0
    assert payload["filter_options"]["branches"]
    assert payload["filter_options"]["products"]
    assert payload["filter_options"]["statuses"]

    forbidden = client.get(
        "/v1/admin/production",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )

    assert forbidden.status_code == 403


def test_admin_production_create_filters_detail_and_shortage_warning(client: TestClient) -> None:
    raw_material_id = _create_raw_material("RAW-PROD-SHORTAGE")
    recipe_id = _create_active_recipe(raw_material_id=raw_material_id)
    production = _create_production(client, recipe_id=recipe_id)
    production_id = production["overview"]["id"]

    assert production["overview"]["status"] == "DRAFT"
    assert production["available_actions"]["can_start"] is True
    assert production["planned_inputs"][0]["input_product_name"] == "Raw RAW-PROD-SHORTAGE"
    assert Decimal(str(production["planned_inputs"][0]["required_qty"])) == Decimal("4.000")
    assert Decimal(str(production["planned_inputs"][0]["shortage_qty"])) == Decimal("4.000")
    assert production["planned_inputs"][0]["status"] == "unavailable"
    assert production["warnings"][0]["code"] == "raw_material_shortage"

    search_response = client.get(
        "/v1/admin/production?search=concha", headers=_admin_headers(client)
    )
    assert search_response.status_code == 200
    assert [item["id"] for item in search_response.json()["items"]] == [production_id]

    folio_response = client.get(
        f"/v1/admin/production?search={production['overview']['folio']}",
        headers=_admin_headers(client),
    )
    assert folio_response.status_code == 200
    assert [item["id"] for item in folio_response.json()["items"]] == [production_id]

    status_response = client.get(
        "/v1/admin/production?status=DRAFT", headers=_admin_headers(client)
    )
    assert status_response.status_code == 200
    assert status_response.json()["total"] == 1

    warning_response = client.get(
        "/v1/admin/production?warning_state=critical", headers=_admin_headers(client)
    )
    assert warning_response.status_code == 200
    assert [item["id"] for item in warning_response.json()["items"]] == [production_id]

    detail_response = client.get(
        f"/v1/admin/production/{production_id}", headers=_admin_headers(client)
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["overview"]["id"] == production_id
    assert detail["product_recipe"]["recipe_id"] == recipe_id
    assert detail["waste_scrap"]["integration_available"] is False


def test_admin_production_validates_target_recipe_and_quantity(client: TestClient) -> None:
    headers = _admin_headers(client)
    raw_target_id = _create_raw_material("RAW-PROD-TARGET")
    raw_material_id = _create_raw_material("RAW-PROD-INPUT")
    recipe_id = _create_active_recipe(raw_material_id=raw_material_id)

    raw_target_response = client.post(
        "/v1/admin/production",
        headers=headers,
        json={
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "planned_output_qty": "10.000",
            "product_id": raw_target_id,
            "recipe_id": recipe_id,
        },
    )
    assert raw_target_response.status_code == 409
    assert "FINISHED_GOOD" in raw_target_response.json()["message"]

    invalid_recipe_response = client.post(
        "/v1/admin/production",
        headers=headers,
        json={
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "planned_output_qty": "10.000",
            "product_id": _get_product_id(SEED_PRODUCT_COCA_355_CODE),
            "recipe_id": recipe_id,
        },
    )
    assert invalid_recipe_response.status_code == 409
    assert "does not belong" in invalid_recipe_response.json()["message"]

    quantity_response = client.post(
        "/v1/admin/production",
        headers=headers,
        json={
            "branch_id": _get_branch_id(SEED_BRANCH_CODE),
            "planned_output_qty": "0",
            "product_id": _get_product_id(SEED_PRODUCT_CONCHA_VAN_CODE),
            "recipe_id": recipe_id,
        },
    )
    assert quantity_response.status_code == 422


def test_admin_production_start_blocks_shortages_then_succeeds(client: TestClient) -> None:
    raw_material_id = _create_raw_material("RAW-PROD-START")
    recipe_id = _create_active_recipe(raw_material_id=raw_material_id)
    production = _create_production(client, recipe_id=recipe_id)
    production_id = str(production["overview"]["id"])

    blocked_response = client.post(
        f"/v1/admin/production/{production_id}/start",
        headers=_admin_headers(client),
        json={},
    )
    assert blocked_response.status_code == 409
    assert "shortages" in blocked_response.json()["message"]

    _seed_raw_stock(client, product_id=raw_material_id)
    start_response = client.post(
        f"/v1/admin/production/{production_id}/start",
        headers=_admin_headers(client),
        json={"notes": "Materials ready"},
    )

    assert start_response.status_code == 200
    payload = start_response.json()
    assert payload["overview"]["status"] == "IN_PROGRESS"
    assert payload["available_actions"]["can_complete"] is True
    assert payload["planned_inputs"][0]["status"] == "available"
    assert payload["warnings"] == []


def test_admin_production_complete_writes_inventory_movements_audit_and_outbox(
    client: TestClient,
) -> None:
    started = _create_started_production(client)
    production_id = str(started["overview"]["id"])

    complete_response = client.post(
        f"/v1/admin/production/{production_id}/complete",
        headers={**_admin_headers(client), "X-Request-ID": "admin-production-complete"},
        json={
            "actual_output_qty": "18.000",
            "notes": "Yield below plan after cooling",
            "variance_reason": "Shrinkage during bake",
        },
    )

    assert complete_response.status_code == 200
    payload = complete_response.json()
    assert payload["overview"]["status"] == "COMPLETED"
    assert Decimal(str(payload["output_yield"]["variance_qty"])) == Decimal("-2.000")
    assert Decimal(str(payload["output_yield"]["variance_percent"])) == Decimal("-10.0000")
    assert payload["warnings"][0]["code"] == "yield_variance"
    assert len(payload["inventory_impact"]["movements"]) == 2

    with SessionLocal() as session:
        batch = session.execute(
            select(ProductionBatch).where(ProductionBatch.id == UUID(production_id))
        ).scalar_one()
        movements = (
            session.execute(
                select(InventoryMovement).where(
                    InventoryMovement.source_document_id == UUID(production_id)
                ),
            )
            .scalars()
            .all()
        )
        output_balance = session.execute(
            select(InventoryBalance).where(
                InventoryBalance.branch_id == batch.branch_id,
                InventoryBalance.product_id == batch.product_id,
            ),
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(
                AuditLog.action == "admin.production.completed",
                AuditLog.resource_id == production_id,
            ),
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == production_id,
                OutboxEvent.event_name == "admin.production.completed.v1",
            ),
        ).scalar_one()

    assert {movement.movement_type for movement in movements} == {
        "PRODUCTION_CONSUMPTION",
        "PRODUCTION_OUTPUT",
    }
    assert {movement.direction for movement in movements} == {"IN", "OUT"}
    assert output_balance.quantity_on_hand == Decimal("18.000")
    assert audit_record.request_id == "admin-production-complete"
    assert outbox_event.aggregate_id == production_id


def test_admin_production_complete_validates_output_and_variance_reason(client: TestClient) -> None:
    started = _create_started_production(client)
    production_id = str(started["overview"]["id"])

    negative_response = client.post(
        f"/v1/admin/production/{production_id}/complete",
        headers=_admin_headers(client),
        json={"actual_output_qty": "-1.000"},
    )
    assert negative_response.status_code == 422

    missing_reason_response = client.post(
        f"/v1/admin/production/{production_id}/complete",
        headers=_admin_headers(client),
        json={"actual_output_qty": "18.000"},
    )
    assert missing_reason_response.status_code == 409
    assert "variance" in missing_reason_response.json()["message"].lower()

    zero_response = client.post(
        f"/v1/admin/production/{production_id}/complete",
        headers=_admin_headers(client),
        json={"actual_output_qty": "0.000"},
    )
    assert zero_response.status_code == 409
    assert "Zero output" in zero_response.json()["message"]


def test_admin_production_cancel_draft_and_blocks_completed_cancellation(
    client: TestClient,
) -> None:
    raw_material_id = _create_raw_material("RAW-PROD-CANCEL")
    recipe_id = _create_active_recipe(raw_material_id=raw_material_id)
    production = _create_production(client, recipe_id=recipe_id)
    production_id = str(production["overview"]["id"])

    cancel_response = client.post(
        f"/v1/admin/production/{production_id}/cancel",
        headers=_admin_headers(client),
        json={"reason": "No longer needed"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["overview"]["status"] == "CANCELLED"

    completed = _create_started_production(client, actual_stock="12.000")
    completed_id = str(completed["overview"]["id"])
    complete_response = client.post(
        f"/v1/admin/production/{completed_id}/complete",
        headers=_admin_headers(client),
        json={"actual_output_qty": "20.000"},
    )
    assert complete_response.status_code == 200

    blocked_cancel_response = client.post(
        f"/v1/admin/production/{completed_id}/cancel",
        headers=_admin_headers(client),
        json={"reason": "Mistake"},
    )
    assert blocked_cancel_response.status_code == 409
