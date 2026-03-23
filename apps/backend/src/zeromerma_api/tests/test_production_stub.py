# apps/backend/src/zeromerma_api/tests/test_production_stub.py
# -----------------------------------------------------------------------------
# PURPOSE (TEST):
#   Validate the Phase 6.3-C Production workflow:
#     - Inputs consumption -> PRODUCTION_INPUT ledger rows + decrement snapshot
#     - Outputs creation   -> PRODUCTION_OUTPUT ledger rows + increment snapshot
#
# IMPORTANT:
#   The production endpoint is expected to be:
#       POST /production/runs
#   but the test discovers it from OpenAPI to avoid brittle hardcoding.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app


# -----------------------------------------------------------------------------
# Alembic helpers (self-contained)
# -----------------------------------------------------------------------------
def make_alembic_config() -> Config:
    """
    Build an Alembic Config that always points to:
      - apps/backend/alembic.ini
      - apps/backend/migrations

    __file__ = .../apps/backend/src/zeromerma_api/tests/test_production_stub.py
    parents[0]=tests, [1]=zeromerma_api, [2]=src, [3]=backend
    """
    backend_dir = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    if os.getenv("DATABASE_URL"):
        cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    return cfg


def alembic_upgrade_head() -> None:
    cfg = make_alembic_config()
    command.upgrade(cfg, "head")


# -----------------------------------------------------------------------------
# Auth helpers
# -----------------------------------------------------------------------------
def auth_headers(*, user_id: int, role_code: str, branch_id: int) -> dict[str, str]:
    """
    Create Authorization headers for Bearer auth.
    """
    token = create_access_token(
        subject=str(int(user_id)),
        extra_claims={"role_code": str(role_code), "branch_id": int(branch_id)},
    )
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# DB reset + seeding helpers
# -----------------------------------------------------------------------------
def reset_db(s: Session) -> None:
    """
    Reset database tables for deterministic test runs.
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


def seed_minimal_admin_state(s: Session) -> dict[str, int]:
    """
    Create:
      - branch MAIN
      - role ADMIN
      - user admin@example.com
    """
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
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:b, :r, 'admin@example.com', 'Admin User', NULL, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "r": int(role_id)},
    ).scalar_one()

    s.commit()
    return {"branch_id": int(branch_id), "role_id": int(role_id), "user_id": int(user_id)}


def seed_catalog_for_production(s: Session) -> dict[str, int]:
    """
    Create:
      - categories ING (inputs) and FIN (finished)
      - products:
          * FLOUR-001 (is_input=TRUE)
          * DONUT-001 (is_input=FALSE)
    """
    cat_ing_id = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES ('ING', 'Ingredients', TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    cat_fin_id = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES ('FIN', 'Finished Goods', TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    flour_id = s.execute(
        text(
            """
            INSERT INTO product (sku, name, category_id, is_input, is_active, created_at, updated_at)
            VALUES ('FLOUR-001', 'Flour', :c, TRUE, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"c": int(cat_ing_id)},
    ).scalar_one()

    donut_id = s.execute(
        text(
            """
            INSERT INTO product (sku, name, category_id, is_input, is_active, created_at, updated_at)
            VALUES ('DONUT-001', 'Donut', :c, FALSE, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"c": int(cat_fin_id)},
    ).scalar_one()

    s.commit()
    return {
        "category_ing_id": int(cat_ing_id),
        "category_fin_id": int(cat_fin_id),
        "flour_id": int(flour_id),
        "donut_id": int(donut_id),
    }


def seed_inventory_balance(s: Session, *, branch_id: int, product_id: int, on_hand: float) -> None:
    s.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b, :p, :oh, 0, now(), now())
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET
                on_hand = EXCLUDED.on_hand,
                reserved = EXCLUDED.reserved,
                updated_at = now()
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "oh": float(on_hand)},
    )
    s.commit()


def get_on_hand(s: Session, *, branch_id: int, product_id: int) -> float:
    val = s.execute(
        text(
            """
            SELECT COALESCE(on_hand, 0)
            FROM inventory_balance
            WHERE branch_id = :b AND product_id = :p
            """
        ),
        {"b": int(branch_id), "p": int(product_id)},
    ).scalar_one_or_none()
    return float(val or 0.0)


def count_movements(s: Session, *, branch_id: int, product_id: int, reason: str) -> int:
    n = s.execute(
        text(
            """
            SELECT COUNT(*)
            FROM inventory_movement
            WHERE branch_id = :b
              AND product_id = :p
              AND reason = :r
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "r": str(reason)},
    ).scalar_one()
    return int(n or 0)


def sum_movement_qty(s: Session, *, branch_id: int, product_id: int, reason: str) -> float:
    q = s.execute(
        text(
            """
            SELECT COALESCE(SUM(qty), 0)
            FROM inventory_movement
            WHERE branch_id = :b
              AND product_id = :p
              AND reason = :r
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "r": str(reason)},
    ).scalar_one()
    return float(q or 0.0)


# -----------------------------------------------------------------------------
# Endpoint discovery (OpenAPI-based)
# -----------------------------------------------------------------------------
def discover_production_post_path(app: FastAPI) -> str:
    """
    Discover the production POST endpoint using OpenAPI.
    Prefers paths containing '/production' + '/runs'.

    If none found, falls back to '/production/runs'.

    If still 404, it strongly suggests you did NOT include production_router in main.py.
    """
    openapi = app.openapi()
    paths = openapi.get("paths", {})

    # Prefer /production/.../runs with POST
    for path, ops in paths.items():
        if "/production" in path and "/runs" in path and "post" in ops:
            return path

    # Otherwise: any /production path with POST
    for path, ops in paths.items():
        if "/production" in path and "post" in ops:
            return path

    return "/production/runs"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping production tests",
)
def test_production_stub_creates_input_output_movements_and_updates_snapshot():
    """
    Scenario:
      - Flour (input) starts at 10.0
      - Donut (finished) starts at 0.0
      - Production: consume 2.0 flour -> produce 5.0 donuts

    Expect:
      - snapshot flour: 8.0
      - snapshot donut: 5.0
      - ledger:
          * flour PRODUCTION_INPUT sum(qty) == -2.0
          * donut PRODUCTION_OUTPUT sum(qty) == +5.0
    """
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        ids = seed_minimal_admin_state(s)
        cat = seed_catalog_for_production(s)

        branch_id = ids["branch_id"]
        user_id = ids["user_id"]
        flour_id = cat["flour_id"]
        donut_id = cat["donut_id"]

        seed_inventory_balance(s, branch_id=branch_id, product_id=flour_id, on_hand=10.0)
        seed_inventory_balance(s, branch_id=branch_id, product_id=donut_id, on_hand=0.0)

        assert get_on_hand(s, branch_id=branch_id, product_id=flour_id) == pytest.approx(10.0)
        assert get_on_hand(s, branch_id=branch_id, product_id=donut_id) == pytest.approx(0.0)
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    post_path = discover_production_post_path(app)
    headers = auth_headers(user_id=user_id, role_code="ADMIN", branch_id=branch_id)

    resp = client.post(
        post_path,
        json={
            "branch_id": branch_id,
            "inputs": [{"product_id": flour_id, "qty": 2.0}],
            "outputs": [{"product_id": donut_id, "qty": 5.0}],
            "note": "test production run",
        },
        headers=headers,
    )

    # If we still get 404, production_router is not mounted.
    assert resp.status_code != 404, (
        f"Production POST endpoint not found. Tried path='{post_path}'. "
        "Make sure you included production_router in main.py (app.include_router(...)). "
        f"Response: {resp.text}"
    )

    assert resp.status_code == 200, resp.text

    s2: Session = SessionLocal()
    try:
        flour_after = get_on_hand(s2, branch_id=branch_id, product_id=flour_id)
        donut_after = get_on_hand(s2, branch_id=branch_id, product_id=donut_id)

        assert flour_after == pytest.approx(8.0)
        assert donut_after == pytest.approx(5.0)

        assert (
            count_movements(s2, branch_id=branch_id, product_id=flour_id, reason="PRODUCTION_INPUT")
            >= 1
        )
        assert (
            count_movements(
                s2, branch_id=branch_id, product_id=donut_id, reason="PRODUCTION_OUTPUT"
            )
            >= 1
        )

        assert sum_movement_qty(
            s2, branch_id=branch_id, product_id=flour_id, reason="PRODUCTION_INPUT"
        ) == pytest.approx(-2.0)
        assert sum_movement_qty(
            s2, branch_id=branch_id, product_id=donut_id, reason="PRODUCTION_OUTPUT"
        ) == pytest.approx(+5.0)
    finally:
        s2.close()
