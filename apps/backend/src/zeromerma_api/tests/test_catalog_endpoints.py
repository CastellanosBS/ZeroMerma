from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app


def make_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    if os.getenv("DATABASE_URL"):
        cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    return cfg


def alembic_upgrade_head() -> None:
    cfg = make_alembic_config()
    command.upgrade(cfg, "head")


def auth_headers(*, user_id: int, role_code: str, branch_id: int) -> dict[str, str]:
    token = create_access_token(
        subject=str(user_id),
        extra_claims={"role_code": role_code, "branch_id": int(branch_id)},
    )
    return {"Authorization": f"Bearer {token}"}


def reset_db_for_catalog(s: Session) -> None:
    """
    Reset DB state for deterministic catalog tests.

    Why TRUNCATE instead of DELETE:
      - We now have more tables with FK dependencies (e.g., production_run -> user_account).
      - TRUNCATE ... CASCADE avoids FK ordering problems.
      - RESTART IDENTITY keeps IDs predictable across repeated runs.

    Note:
      - This is an integration test suite that shares a real Postgres DB.
      - A "hard reset" is the simplest way to guarantee isolation.
    """
    s.execute(
        text(
            """
            TRUNCATE TABLE
                payment,
                sale_item,
                sale,
                inventory_movement,
                inventory_balance,
                cash_session,
                production_run,
                product,
                product_category,
                user_account,
                role,
                branch
            RESTART IDENTITY CASCADE
            """
        )
    )
    s.commit()


def seed_minimal_users(s: Session) -> dict[str, int]:
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES ('MAIN', 'Main Branch', true, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    admin_role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('ADMIN', 'Admin', now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    cashier_role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('CASHIER', 'Cashier', now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    admin_user_id = s.execute(
        text(
            """
            INSERT INTO user_account (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES (:b, :r, 'admin@example.com', 'Admin User', NULL, true, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "r": int(admin_role_id)},
    ).scalar_one()

    cashier_user_id = s.execute(
        text(
            """
            INSERT INTO user_account (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES (:b, :r, 'cashier@example.com', 'Cashier User', NULL, true, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "r": int(cashier_role_id)},
    ).scalar_one()

    s.commit()

    return {
        "branch_id": int(branch_id),
        "admin_user_id": int(admin_user_id),
        "cashier_user_id": int(cashier_user_id),
    }


def discover_catalog_prefix(app) -> str:
    """
    Discover the base prefix where catalog routes are mounted
    by scanning the OpenAPI path map.

    We look for a path that ends with '/catalog/categories' or '/catalog/products'
    or a shorter '/categories' under a 'catalog' tag. But we keep it pragmatic:
    find any path containing 'catalog' and 'categories' together.
    """
    paths = app.openapi().get("paths", {})
    for p in paths.keys():
        if "catalog" in p and "categories" in p:
            # Example: "/catalog/categories" OR "/api/catalog/categories"
            return p.rsplit("/categories", 1)[0]
    # If not found, return default so the assertion error is informative.
    return "/catalog"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping catalog tests",
)
def test_catalog_get_and_admin_write_permissions():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db_for_catalog(s)
        ids = seed_minimal_users(s)
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    catalog_prefix = discover_catalog_prefix(app)

    admin_h = auth_headers(
        user_id=ids["admin_user_id"], role_code="ADMIN", branch_id=ids["branch_id"]
    )
    cashier_h = auth_headers(
        user_id=ids["cashier_user_id"], role_code="CASHIER", branch_id=ids["branch_id"]
    )

    # Sanity check: the route must exist.
    # If it fails, it almost certainly means the router wasn't included in main.py.
    cats_probe = client.get(f"{catalog_prefix}/categories", headers=admin_h)
    assert cats_probe.status_code != 404, (
        f"Catalog routes not found at '{catalog_prefix}'. "
        "Make sure you included catalog_router in main.py. "
        f"Got: {cats_probe.text}"
    )

    # ADMIN create category
    cat_resp = client.post(
        f"{catalog_prefix}/categories",
        json={"code": "DONUTS", "name": "Donuts", "is_active": True},
        headers=admin_h,
    )
    assert cat_resp.status_code == 200, cat_resp.text
    category = cat_resp.json()
    category_id = int(category["id"])
    assert category["code"] == "DONUTS"

    # ADMIN create product
    prod_resp = client.post(
        f"{catalog_prefix}/products",
        json={
            "sku": "DONUT-GLA",
            "name": "Donut Glazed",
            "category_id": category_id,
            "is_active": True,
        },
        headers=admin_h,
    )
    assert prod_resp.status_code == 200, prod_resp.text
    product = prod_resp.json()
    product_id = int(product["id"])
    assert product["sku"] == "DONUT-GLA"
    assert int(product["category_id"]) == category_id

    # Both can GET
    cats_admin = client.get(f"{catalog_prefix}/categories", headers=admin_h)
    assert cats_admin.status_code == 200, cats_admin.text
    assert any(c["code"] == "DONUTS" for c in cats_admin.json())

    cats_cashier = client.get(f"{catalog_prefix}/categories", headers=cashier_h)
    assert cats_cashier.status_code == 200, cats_cashier.text

    prods_cashier = client.get(f"{catalog_prefix}/products", headers=cashier_h)
    assert prods_cashier.status_code == 200, prods_cashier.text
    assert any(p["sku"] == "DONUT-GLA" for p in prods_cashier.json())

    # Cashier cannot create/update
    cat_create_cashier = client.post(
        f"{catalog_prefix}/categories",
        json={"code": "DRINKS", "name": "Drinks", "is_active": True},
        headers=cashier_h,
    )
    assert cat_create_cashier.status_code == 403, cat_create_cashier.text

    # Admin updates
    cat_upd = client.put(
        f"{catalog_prefix}/categories/{category_id}",
        json={"name": "Donuts & More"},
        headers=admin_h,
    )
    assert cat_upd.status_code == 200, cat_upd.text
    assert cat_upd.json()["name"] == "Donuts & More"

    prod_upd = client.put(
        f"{catalog_prefix}/products/{product_id}",
        json={"name": "Donut Glazed (Updated)"},
        headers=admin_h,
    )
    assert prod_upd.status_code == 200, prod_upd.text
    assert prod_upd.json()["name"] == "Donut Glazed (Updated)"
