from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head
from zeromerma_api.tests.auth_helpers import build_auth_headers


def reset_db(s: Session) -> None:
    s.execute(
        text(
            """
            TRUNCATE TABLE
                customer_order_item,
                customer_order,
                product_price,
                payment,
                sale_item,
                sale,
                inventory_movement,
                inventory_balance,
                cash_session,
                production_run,
                user_account,
                role,
                branch,
                product,
                product_category
            RESTART IDENTITY CASCADE
            """
        )
    )
    s.commit()


def seed_branch(s: Session, code: str, name: str) -> int:
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(branch_id)


def seed_role(s: Session, code: str, name: str) -> int:
    role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(role_id)


def seed_user(
    s: Session,
    *,
    branch_id: int,
    role_id: int,
    email: str,
    full_name: str,
) -> int:
    user_id = s.execute(
        text(
            """
            INSERT INTO user_account
                (
                    branch_id,
                    role_id,
                    email,
                    full_name,
                    password_hash,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :branch_id,
                    :role_id,
                    :email,
                    :full_name,
                    NULL,
                    TRUE,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "email": email,
            "full_name": full_name,
        },
    ).scalar_one()
    s.commit()
    return int(user_id)


def seed_category(s: Session, *, code: str, name: str) -> int:
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(category_id)


def seed_product(
    s: Session,
    *,
    sku: str,
    name: str,
    category_id: int,
    is_input: bool,
    sale_price: float | None = None,
) -> int:
    product_id = s.execute(
        text(
            """
            INSERT INTO product
                (
                    sku,
                    name,
                    category_id,
                    uom,
                    is_input,
                    sale_price,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    :sku,
                    :name,
                    :category_id,
                    'PCS',
                    :is_input,
                    :sale_price,
                    TRUE,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {
            "sku": sku,
            "name": name,
            "category_id": int(category_id),
            "is_input": bool(is_input),
            "sale_price": sale_price,
        },
    ).scalar_one()
    s.commit()
    return int(product_id)


def discover_catalog_prefix(app: FastAPI) -> str:
    paths = app.openapi().get("paths", {})
    for path in paths:
        if "catalog" in path and "categories" in path:
            return path.rsplit("/categories", 1)[0]
    return "/catalog"


def discover_production_post_path(app: FastAPI) -> str:
    paths = app.openapi().get("paths", {})
    for path, ops in paths.items():
        if "/production" in path and "/runs" in path and "post" in ops:
            return path
    return "/production/runs"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping domain error surface tests",
)
def test_pricing_missing_product_returns_domain_not_found():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_role_id = seed_role(s, code="ADMIN", name="Administrator")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
    finally:
        s.close()

    client = TestClient(create_app())
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    resp = client.get(
        f"/pricing/branches/{branch_id}/products/999999",
        headers=headers,
    )
    assert resp.status_code == 404, resp.text

    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
    assert payload["error"]["message"] == "Product 999999 not found."


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping domain error surface tests",
)
def test_catalog_duplicate_category_returns_domain_conflict():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_role_id = seed_role(s, code="ADMIN", name="Administrator")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    catalog_prefix = discover_catalog_prefix(app)
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    first_resp = client.post(
        f"{catalog_prefix}/categories",
        json={"code": "DONUTS", "name": "Donuts", "is_active": True},
        headers=headers,
    )
    assert first_resp.status_code == 200, first_resp.text

    second_resp = client.post(
        f"{catalog_prefix}/categories",
        json={"code": "DONUTS", "name": "Duplicate Donuts", "is_active": True},
        headers=headers,
    )
    assert second_resp.status_code == 409, second_resp.text

    payload = second_resp.json()
    assert payload["error"]["code"] == "DOMAIN_CONFLICT"
    assert payload["error"]["message"] == "Category already exists (duplicate code)."


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping domain error surface tests",
)
def test_catalog_missing_category_reference_returns_domain_not_found():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_role_id = seed_role(s, code="ADMIN", name="Administrator")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    catalog_prefix = discover_catalog_prefix(app)
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    resp = client.post(
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
    assert resp.status_code == 404, resp.text

    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
    assert payload["error"]["message"] == "Category 999999 not found."


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping domain error surface tests",
)
def test_production_missing_product_returns_domain_not_found():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_role_id = seed_role(s, code="ADMIN", name="Administrator")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        finished_category_id = seed_category(s, code="FIN", name="Finished")
        donut_id = seed_product(
            s,
            sku="DONUT",
            name="Donut",
            category_id=finished_category_id,
            is_input=False,
            sale_price=12.0,
        )
        _ = donut_id
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)
    production_path = discover_production_post_path(app)
    headers = build_auth_headers(
        user_id=admin_user_id,
        role_code="ADMIN",
        branch_id=branch_id,
    )

    resp = client.post(
        production_path,
        json={
            "branch_id": branch_id,
            "inputs": [{"product_id": 999999, "qty": 1.0}],
            "outputs": [{"product_id": 1, "qty": 1.0}],
            "note": "missing product",
        },
        headers=headers,
    )
    assert resp.status_code == 404, resp.text

    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
    assert payload["error"]["message"] == "Some products do not exist."
