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
    SEED_PRODUCT_CLASS_BOLILLO_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import (
    Product,
    ProductClass,
    Recipe,
    RecipeInput,
)
from zeromerma_api.modules.inventory.infrastructure.models import InventoryBalance
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.suppliers.infrastructure.models import SupplierProduct
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


def _product_class_id() -> str:
    with SessionLocal() as session:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.code == SEED_PRODUCT_CLASS_BOLILLO_CODE)
        ).scalar_one()
        return str(product_class.id)


def _branch_id() -> str:
    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        return str(branch.id)


def _create_supplier(client: TestClient, *, code: str = "SUP-INSUMOS") -> dict[str, object]:
    response = client.post(
        "/v1/admin/suppliers",
        headers={**_admin_headers(client), "X-Request-ID": "input-supply-supplier"},
        json={
            "branch_ids": [_branch_id()],
            "category": "RAW_MATERIALS",
            "code": code,
            "commercial_name": "Harinas Centro",
            "contacts": [
                {
                    "email": "compras@harinas.test",
                    "is_primary": True,
                    "name": "Compras Harinas",
                    "phone": "6621000000",
                }
            ],
            "credit_days": 7,
            "default_currency": "MXN",
            "lead_time_days": 2,
            "legal_name": "Harinas del Centro SA",
            "payment_terms_type": "CREDIT",
            "product_relations": [],
            "status": "ACTIVE",
            "tax_id": f"RFC{code[-4:]}",
        },
    )
    assert response.status_code == 201
    return dict(response.json())


def _input_payload(
    *,
    code: str = "HARINA-TRIGO",
    product_kind: str = "RAW_MATERIAL",
    supplier_id: str | None = None,
) -> dict[str, object]:
    supplier_relations: list[dict[str, object]] = []
    if supplier_id is not None:
        supplier_relations.append(
            {
                "conversion_factor": "44.000000",
                "currency": "MXN",
                "is_active": True,
                "last_known_price": "620.0000",
                "lead_time_days": 2,
                "minimum_order_qty": "1.000",
                "purchase_uom": "SACK",
                "supplier_id": supplier_id,
                "supplier_sku": "HARINA-SACK",
            }
        )
    return {
        "code": code,
        "is_active": True,
        "is_inventory_tracked": True,
        "is_purchasable": True,
        "minimum_stock": "5.000",
        "name": "Harina de trigo",
        "preferred_order_quantity": "10.000",
        "procurement_notes": "Saco de harina panadera.",
        "product_class_id": _product_class_id(),
        "product_kind": product_kind,
        "purchase_conversion_factor": "44.000000",
        "purchase_uom": "SACK",
        "reorder_point": "8.000",
        "standard_cost": "14.0909",
        "supplier_relations": supplier_relations,
        "unit_of_measure": "KG",
        "usage_type": "RECIPE_INPUT",
    }


def _create_input(client: TestClient, *, code: str = "HARINA-TRIGO") -> dict[str, object]:
    supplier = _create_supplier(client, code=f"SUP-{uuid.uuid4().hex[:6].upper()}")
    supplier_id = str(supplier["overview"]["id"])
    response = client.post(
        "/v1/admin/inputs-supplies",
        headers={**_admin_headers(client), "X-Request-ID": "input-supply-create"},
        json=_input_payload(code=code, supplier_id=supplier_id),
    )
    assert response.status_code == 201
    return dict(response.json())


def test_admin_inputs_supplies_list_empty_and_rejects_pos_user(client: TestClient) -> None:
    response = client.get("/v1/admin/inputs-supplies", headers=_admin_headers(client))

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == []
    assert payload["total"] == 0
    assert payload["is_backend_connected"] is True
    assert payload["backend_contract"]["create_endpoint"] == "POST /v1/admin/inputs-supplies"
    assert payload["filter_options"]["product_kinds"]
    assert payload["filter_options"]["classes"]

    forbidden_response = client.get(
        "/v1/admin/inputs-supplies",
        headers={"Authorization": f"Bearer {_login_cashier(client)}"},
    )
    assert forbidden_response.status_code == 403


def test_admin_inputs_supplies_create_detail_audit_and_supplier_relation(
    client: TestClient,
) -> None:
    payload = _create_input(client)
    product_id = payload["overview"]["id"]

    assert payload["overview"]["product_kind"] == "RAW_MATERIAL"
    assert payload["overview"]["is_purchasable"] is True
    assert payload["overview"]["is_inventory_tracked"] is True
    assert payload["units_conversion"]["purchase_uom"] == "SACK"
    assert payload["units_conversion"]["conversion_factor"] == "44.000000"
    assert payload["suppliers"][0]["last_known_price"] == "620.0000"
    assert payload["inventory_status"]["integration_available"] is False
    assert payload["related_documents"][0]["document_type"] == "SUPPLIER_PRODUCT"

    with SessionLocal() as session:
        product = session.get(Product, product_id)
        relation = session.execute(
            select(SupplierProduct).where(SupplierProduct.product_id == product_id)
        ).scalar_one()
        audit_record = session.execute(
            select(AuditLog).where(AuditLog.resource_id == str(product_id))
        ).scalar_one()
        outbox_event = session.execute(
            select(OutboxEvent).where(OutboxEvent.aggregate_id == str(product_id))
        ).scalar_one()

    assert product is not None
    assert product.is_sellable is False
    assert product.purchase_unit_of_measure == "SACK"
    assert relation.conversion_factor == Decimal("44.000000")
    assert audit_record.action == "admin.input_supply.created"
    assert audit_record.request_id == "input-supply-create"
    assert outbox_event.event_name == "admin.input_supply.created.v1"


def test_admin_inputs_supplies_filters_and_inventory_recipe_context(client: TestClient) -> None:
    payload = _create_input(client, code="HARINA-CONTEXTO")
    product_id = payload["overview"]["id"]

    with SessionLocal() as session:
        branch = session.execute(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).scalar_one()
        finished_product = session.execute(
            select(Product).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        ).scalar_one()
        recipe = Recipe(
            created_by_user_id=None,
            is_active=True,
            product_id=finished_product.id,
            version_name="Masa base",
            yield_qty=Decimal("100.000"),
            yield_uom="PCS",
        )
        session.add(recipe)
        session.flush()
        session.add(
            RecipeInput(
                input_product_id=uuid.UUID(product_id),
                quantity=Decimal("12.500"),
                recipe_id=recipe.id,
            )
        )
        session.add(
            InventoryBalance(
                branch_id=branch.id,
                location_code="BACKROOM",
                product_id=uuid.UUID(product_id),
                quantity_on_hand=Decimal("6.000"),
            )
        )
        session.commit()

    response = client.get(
        "/v1/admin/inputs-supplies",
        headers=_admin_headers(client),
        params={
            "product_kind": "RAW_MATERIAL",
            "recipe_usage": "used",
            "stock_state": "low_stock",
            "supplier_id": payload["suppliers"][0]["supplier_id"],
        },
    )
    assert response.status_code == 200
    list_payload = response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["stock_state"] == "low_stock"
    assert list_payload["items"][0]["recipe_usage_count"] == 1
    assert list_payload["metrics"]["used_in_recipes"] == 1

    no_supplier_response = client.post(
        "/v1/admin/inputs-supplies",
        headers=_admin_headers(client),
        json=_input_payload(code="HARINA-SIN-PROVEEDOR"),
    )
    assert no_supplier_response.status_code == 201
    without_supplier_response = client.get(
        "/v1/admin/inputs-supplies",
        headers=_admin_headers(client),
        params={"without_supplier": True},
    )
    assert without_supplier_response.status_code == 200
    without_supplier_payload = without_supplier_response.json()
    assert without_supplier_payload["total"] == 1
    assert without_supplier_payload["items"][0]["code"] == "HARINA-SIN-PROVEEDOR"
    assert without_supplier_payload["metrics"]["without_supplier"] == 1

    detail_response = client.get(
        f"/v1/admin/inputs-supplies/{product_id}", headers=_admin_headers(client)
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["inventory_status"]["stock_by_branch"][0]["quantity_on_hand"] == "6.000"
    assert detail["recipe_usage"][0]["finished_product_code"] == SEED_PRODUCT_BOLILLO_STD_CODE
    assert any(warning["code"] == "low_stock" for warning in detail["procurement_warnings"])


def test_admin_inputs_supplies_validation_update_status_and_supplier_relation(
    client: TestClient,
) -> None:
    supplier = _create_supplier(client, code="SUP-VALIDA")
    supplier_id = str(supplier["overview"]["id"])

    invalid_response = client.post(
        "/v1/admin/inputs-supplies",
        headers=_admin_headers(client),
        json=_input_payload(code="VENTA-NO-VALIDA", product_kind="FINISHED_GOOD"),
    )
    assert invalid_response.status_code == 422

    missing_response = client.post(
        "/v1/admin/inputs-supplies",
        headers=_admin_headers(client),
        json={"code": "SIN-NOMBRE"},
    )
    assert missing_response.status_code == 422

    created = _create_input(client, code="HARINA-VALIDA")
    product_id = created["overview"]["id"]
    duplicate_response = client.post(
        "/v1/admin/inputs-supplies",
        headers=_admin_headers(client),
        json=_input_payload(code="HARINA-VALIDA", supplier_id=supplier_id),
    )
    assert duplicate_response.status_code == 409

    updated_payload = _input_payload(code="HARINA-EDITADA", supplier_id=supplier_id)
    updated_payload["name"] = "Harina editada"
    updated_payload["product_kind"] = "CONSUMABLE"
    update_response = client.patch(
        f"/v1/admin/inputs-supplies/{product_id}",
        headers=_admin_headers(client),
        json=updated_payload,
    )
    assert update_response.status_code == 200
    assert update_response.json()["overview"]["name"] == "Harina editada"
    assert update_response.json()["overview"]["product_kind"] == "CONSUMABLE"

    status_response = client.post(
        f"/v1/admin/inputs-supplies/{product_id}/status",
        headers=_admin_headers(client),
        json={"is_active": False, "notes": "Pausado para compras."},
    )
    assert status_response.status_code == 200
    assert status_response.json()["overview"]["is_active"] is False

    relation_response = client.post(
        f"/v1/admin/inputs-supplies/{product_id}/suppliers",
        headers=_admin_headers(client),
        json={
            "conversion_factor": "1.000000",
            "currency": "MXN",
            "is_active": True,
            "last_known_price": "15.0000",
            "lead_time_days": 3,
            "minimum_order_qty": "2.000",
            "purchase_uom": "KG",
            "supplier_id": supplier_id,
            "supplier_sku": "KG-HARINA",
        },
    )
    assert relation_response.status_code == 201
    relation = relation_response.json()["suppliers"][0]
    assert relation["supplier_id"] == supplier_id
    assert relation["conversion_factor"] == "1.000000"

    relation_id = relation["id"]
    relation_update = client.patch(
        f"/v1/admin/inputs-supplies/{product_id}/suppliers/{relation_id}",
        headers=_admin_headers(client),
        json={
            "conversion_factor": "2.000000",
            "currency": "MXN",
            "is_active": False,
            "last_known_price": "16.0000",
            "lead_time_days": 4,
            "minimum_order_qty": "3.000",
            "purchase_uom": "BAG",
            "supplier_id": supplier_id,
            "supplier_sku": "BAG-HARINA",
        },
    )
    assert relation_update.status_code == 200
    assert relation_update.json()["suppliers"][0]["is_active"] is False
    assert any(
        warning["code"] == "missing_supplier"
        for warning in relation_update.json()["procurement_warnings"]
    )
