# apps/backend/src/zeromerma_api/tests/test_production_validations.py
# PURPOSE:
#   Negative-path tests for production runs:
#     - Semantic validation: inputs must be is_input=true, outputs must be is_input=false
#     - Stock validation: insufficient input stock -> 409
#     - Rollback safety: on failure, NO production_run, NO movements, NO snapshot changes

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head


def auth_headers(*, user_id: int, role_code: str, branch_id: int) -> dict[str, str]:
    token = create_access_token(
        subject=str(int(user_id)),
        extra_claims={"role_code": str(role_code), "branch_id": int(branch_id)},
    )
    return {"Authorization": f"Bearer {token}"}


def reset_db(s: Session) -> None:
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


def seed_admin_branch(s: Session) -> dict[str, int]:
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES ('MAIN', 'Main Branch', TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('ADMIN', 'Admin', now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    user_id = s.execute(
        text(
            """
            INSERT INTO user_account (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES (:b, :r, 'admin@example.com', 'Admin User', NULL, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "r": int(role_id)},
    ).scalar_one()

    s.commit()
    return {"branch_id": int(branch_id), "user_id": int(user_id)}


def seed_products(s: Session) -> dict[str, int]:
    cat_ing = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES ('ING', 'Ingredients', TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()
    cat_fin = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES ('FIN', 'Finished', TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    # Input product
    flour_id = s.execute(
        text(
            """
            INSERT INTO product (sku, name, category_id, is_input, is_active, created_at, updated_at)
            VALUES ('FLOUR', 'Flour', :c, TRUE, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"c": int(cat_ing)},
    ).scalar_one()

    # Finished product
    donut_id = s.execute(
        text(
            """
            INSERT INTO product (sku, name, category_id, is_input, is_active, created_at, updated_at)
            VALUES ('DONUT', 'Donut', :c, FALSE, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"c": int(cat_fin)},
    ).scalar_one()

    s.commit()
    return {"flour_id": int(flour_id), "donut_id": int(donut_id)}


def seed_balance(s: Session, *, branch_id: int, product_id: int, on_hand: float) -> None:
    s.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b, :p, :oh, 0, now(), now())
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET on_hand = EXCLUDED.on_hand, updated_at = now()
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "oh": float(on_hand)},
    )
    s.commit()


def on_hand(s: Session, *, branch_id: int, product_id: int) -> float:
    v = s.execute(
        text(
            "SELECT COALESCE(on_hand,0) FROM inventory_balance WHERE branch_id=:b AND product_id=:p"
        ),
        {"b": int(branch_id), "p": int(product_id)},
    ).scalar_one_or_none()
    return float(v or 0.0)


def discover_production_post_path(app: FastAPI) -> str:
    openapi = app.openapi()
    paths = openapi.get("paths", {})
    for p, ops in paths.items():
        if "/production" in p and "/runs" in p and "post" in ops:
            return p
    for p, ops in paths.items():
        if "/production" in p and "post" in ops:
            return p
    return "/production/runs"


def count_rows(s: Session, table: str) -> int:
    return int(s.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
def test_rejects_output_that_is_input_and_rolls_back():
    alembic_upgrade_head()
    s = SessionLocal()
    try:
        reset_db(s)
        ids = seed_admin_branch(s)
        p = seed_products(s)
        seed_balance(s, branch_id=ids["branch_id"], product_id=p["flour_id"], on_hand=10.0)

        app = create_app()
        client = TestClient(app)
        path = discover_production_post_path(app)
        h = auth_headers(user_id=ids["user_id"], role_code="ADMIN", branch_id=ids["branch_id"])

        # BAD: output uses input product (flour)
        r = client.post(
            path,
            json={
                "branch_id": ids["branch_id"],
                "inputs": [{"product_id": p["flour_id"], "qty": 1.0}],
                "outputs": [{"product_id": p["flour_id"], "qty": 1.0}],
                "note": "bad output",
            },
            headers=h,
        )
        assert r.status_code == 409, r.text

        # Rollback invariants
        s2 = SessionLocal()
        try:
            assert count_rows(s2, "production_run") == 0
            assert count_rows(s2, "inventory_movement") == 0
            assert on_hand(
                s2, branch_id=ids["branch_id"], product_id=p["flour_id"]
            ) == pytest.approx(10.0)
        finally:
            s2.close()
    finally:
        s.close()


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
def test_rejects_input_that_is_finished_and_rolls_back():
    alembic_upgrade_head()
    s = SessionLocal()
    try:
        reset_db(s)
        ids = seed_admin_branch(s)
        p = seed_products(s)
        seed_balance(s, branch_id=ids["branch_id"], product_id=p["donut_id"], on_hand=5.0)

        app = create_app()
        client = TestClient(app)
        path = discover_production_post_path(app)
        h = auth_headers(user_id=ids["user_id"], role_code="ADMIN", branch_id=ids["branch_id"])

        # BAD: input uses finished product (donut)
        r = client.post(
            path,
            json={
                "branch_id": ids["branch_id"],
                "inputs": [{"product_id": p["donut_id"], "qty": 1.0}],
                "outputs": [{"product_id": p["donut_id"], "qty": 1.0}],
                "note": "bad input",
            },
            headers=h,
        )
        assert r.status_code == 409, r.text

        s2 = SessionLocal()
        try:
            assert count_rows(s2, "production_run") == 0
            assert count_rows(s2, "inventory_movement") == 0
            assert on_hand(
                s2, branch_id=ids["branch_id"], product_id=p["donut_id"]
            ) == pytest.approx(5.0)
        finally:
            s2.close()
    finally:
        s.close()


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="DATABASE_URL not set")
def test_insufficient_stock_rejected_and_rolls_back():
    alembic_upgrade_head()
    s = SessionLocal()
    try:
        reset_db(s)
        ids = seed_admin_branch(s)
        p = seed_products(s)
        seed_balance(s, branch_id=ids["branch_id"], product_id=p["flour_id"], on_hand=1.0)
        seed_balance(s, branch_id=ids["branch_id"], product_id=p["donut_id"], on_hand=0.0)

        app = create_app()
        client = TestClient(app)
        path = discover_production_post_path(app)
        h = auth_headers(user_id=ids["user_id"], role_code="ADMIN", branch_id=ids["branch_id"])

        # Consume 2 flour, but only 1 exists -> should fail
        r = client.post(
            path,
            json={
                "branch_id": ids["branch_id"],
                "inputs": [{"product_id": p["flour_id"], "qty": 2.0}],
                "outputs": [{"product_id": p["donut_id"], "qty": 5.0}],
                "note": "insufficient stock",
            },
            headers=h,
        )
        assert r.status_code == 409, r.text

        s2 = SessionLocal()
        try:
            assert count_rows(s2, "production_run") == 0
            assert count_rows(s2, "inventory_movement") == 0
            assert on_hand(
                s2, branch_id=ids["branch_id"], product_id=p["flour_id"]
            ) == pytest.approx(1.0)
            assert on_hand(
                s2, branch_id=ids["branch_id"], product_id=p["donut_id"]
            ) == pytest.approx(0.0)
        finally:
            s2.close()
    finally:
        s.close()
