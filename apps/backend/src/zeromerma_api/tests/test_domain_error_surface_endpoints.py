from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from zeromerma_api.tests.auth_helpers import build_auth_headers
from zeromerma_api.tests.support.db import reset_pos_core_tables
from zeromerma_api.tests.support.seeders import (
    seed_branch,
    seed_category,
    seed_product,
    seed_role,
    seed_user,
)


def discover_catalog_prefix(app: FastAPI) -> str:
    """
    Resolve the catalog router prefix from OpenAPI for resilience.
    """
    paths = app.openapi().get("paths", {})
    for path in paths:
        if "catalog" in path and "categories" in path:
            return path.rsplit("/categories", 1)[0]
    return "/catalog"


def discover_production_post_path(app: FastAPI) -> str:
    """
    Resolve the production run POST path from OpenAPI for resilience.
    """
    paths = app.openapi().get("paths", {})
    for path, ops in paths.items():
        if "/production" in path and "/runs" in path and "post" in ops:
            return path
    return "/production/runs"


def test_pricing_missing_product_returns_domain_not_found(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )

    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    response = client.get(
        f"/pricing/branches/{branch_id}/products/999999",
        headers=headers,
    )
    assert response.status_code == 404, response.text

    payload = response.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
    assert payload["error"]["message"] == "Product 999999 not found."


def test_catalog_duplicate_category_returns_domain_conflict(
    db_session: Session,
    app: FastAPI,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )

    catalog_prefix = discover_catalog_prefix(app)
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    first_response = client.post(
        f"{catalog_prefix}/categories",
        json={"code": "DONUTS", "name": "Donuts", "is_active": True},
        headers=headers,
    )
    assert first_response.status_code == 200, first_response.text

    second_response = client.post(
        f"{catalog_prefix}/categories",
        json={"code": "DONUTS", "name": "Duplicate Donuts", "is_active": True},
        headers=headers,
    )
    assert second_response.status_code == 409, second_response.text

    payload = second_response.json()
    assert payload["error"]["code"] == "DOMAIN_CONFLICT"
    assert payload["error"]["message"] == "Category already exists (duplicate code)."


def test_catalog_missing_category_reference_returns_domain_not_found(
    db_session: Session,
    app: FastAPI,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )

    catalog_prefix = discover_catalog_prefix(app)
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    response = client.post(
        f"{catalog_prefix}/products",
        json={
            "sku": "MISSING-CAT",
            "name": "Missing Category Product",
            "category_id": 999999,
            "uom": "PCS",
            "is_input": False,
            "sale_price": 10.0,
            "is_active": True,
        },
        headers=headers,
    )
    assert response.status_code == 404, response.text

    payload = response.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
    assert payload["error"]["message"] == "Category 999999 not found."


def test_production_missing_product_returns_domain_not_found(
    db_session: Session,
    app: FastAPI,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )
    finished_category_id = seed_category(
        db_session,
        code="FIN",
        name="Finished",
    )
    seed_product(
        db_session,
        category_id=finished_category_id,
        sku="DONUT",
        name="Donut",
        sale_price=Decimal(12.0),
        is_input=False,
    )

    production_path = discover_production_post_path(app)
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    response = client.post(
        production_path,
        json={
            "branch_id": branch_id,
            "inputs": [{"product_id": 999999, "qty": 1.0}],
            "outputs": [{"product_id": 1, "qty": 1.0}],
            "note": "missing product",
        },
        headers=headers,
    )
    assert response.status_code == 404, response.text

    payload = response.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
    assert payload["error"]["message"] == "Some products do not exist."
