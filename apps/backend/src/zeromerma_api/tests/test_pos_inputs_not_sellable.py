# apps/backend/src/zeromerma_api/tests/test_pos_inputs_not_sellable.py
# PURPOSE:
#   Ensure POS rejects selling input products (ingredients/raw materials).
#
# IMPORTANT (Anti-impersonation contract):
#   - POS endpoints derive the acting user from the Authorization token.
#   - Therefore request payloads must NOT include opened_by_id / created_by_id.
#   - If we send those fields, Pydantic rejects them as extra_forbidden (422).
#
# EXPECTED BEHAVIOR:
#   - If product.is_input = TRUE, POST /pos/sales must return 409
#   - No sale is created
#   - No inventory movement (SALE) is created
#   - inventory_balance snapshot is unchanged

from __future__ import annotations

import os
from decimal import Decimal
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
    """
    Programmatic Alembic config:
      - backend/alembic.ini
      - backend/migrations

    __file__ = .../apps/backend/src/zeromerma_api/tests/test_pos_inputs_not_sellable.py
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


def auth_headers(*, user_id: int, role_code: str, branch_id: int) -> dict[str, str]:
    """
    Create a Bearer token consistent with the current auth/fast-path.
    """
    token = create_access_token(
        subject=str(user_id),
        extra_claims={"role_code": role_code, "branch_id": int(branch_id)},
    )
    return {"Authorization": f"Bearer {token}"}


def reset_tables(s: Session) -> None:
    """
    Reset what we need for deterministic POS tests.
    FK order matters.
    """
    s.execute(text("DELETE FROM payment"))
    s.execute(text("DELETE FROM sale_item"))
    s.execute(text("DELETE FROM sale"))
    s.execute(text("DELETE FROM cash_session"))
    s.execute(text("DELETE FROM inventory_movement"))
    s.execute(text("DELETE FROM inventory_balance"))
    s.execute(text("DELETE FROM product"))
    s.execute(text("DELETE FROM product_category"))
    s.execute(text("DELETE FROM user_account"))
    s.execute(text("DELETE FROM role"))
    s.execute(text("DELETE FROM branch"))
    s.commit()


def seed_base_state(s: Session) -> dict[str, int]:
    """
    Create:
      - branch MAIN
      - roles ADMIN
      - user admin@example.com
      - category INGREDIENTS
      - product FLOUR (is_input = true)
      - inventory_balance row with on_hand=100 (to avoid oversell logic interfering)

    Returns:
      {branch_id, user_id, product_id}
    """
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES ('MAIN', 'Main Branch', true, now(), now())
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
            VALUES (:b, :r, 'admin@example.com', 'Admin User', NULL, true, now(), now())
            RETURNING id
            """
        ),
        {"b": int(branch_id), "r": int(role_id)},
    ).scalar_one()

    cat_id = s.execute(
        text(
            """
            INSERT INTO product_category (code, name, is_active, created_at, updated_at)
            VALUES ('INGREDIENTS', 'Ingredients', true, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    product_id = s.execute(
        text(
            """
            INSERT INTO product (
                sku, name, category_id,
                uom, is_input,
                sale_price, standard_cost,
                is_active, created_at, updated_at
            )
            VALUES (
                'FLOUR', 'Wheat Flour', :cat_id,
                'KG', TRUE,
                NULL, 18.00,
                TRUE, now(), now()
            )
            RETURNING id
            """
        ),
        {"cat_id": int(cat_id)},
    ).scalar_one()

    # Snapshot row: 100 on hand
    s.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b, :p, :oh, 0, now(), now())
            """
        ),
        {"b": int(branch_id), "p": int(product_id), "oh": 100.0},
    )

    s.commit()

    return {
        "branch_id": int(branch_id),
        "user_id": int(user_id),
        "product_id": int(product_id),
    }


def get_on_hand(s: Session, *, branch_id: int, product_id: int) -> Decimal:
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
    return Decimal(str(val or 0))


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS guardrail tests",
)
def test_input_products_cannot_be_sold_via_pos():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_tables(s)
        ids = seed_base_state(s)
        before = get_on_hand(s, branch_id=ids["branch_id"], product_id=ids["product_id"])
        assert before == Decimal("100")
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    headers = auth_headers(user_id=ids["user_id"], role_code="ADMIN", branch_id=ids["branch_id"])

    # Open cash session (anti-impersonation: no opened_by_id in payload)
    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": ids["branch_id"], "opening_amount": 0.00},
        headers=headers,
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = int(open_resp.json()["id"])

    # Attempt sale of an input product -> must be rejected with 409
    # (anti-impersonation: no created_by_id in payload)
    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": ids["branch_id"],
            "cash_session_id": cash_session_id,
            "items": [{"product_id": ids["product_id"], "qty": 1.0, "unit_price": 10.00}],
        },
        headers=headers,
    )
    assert sale_resp.status_code == 400, sale_resp.text

    payload = sale_resp.json()
    assert payload["error"]["code"] == "DOMAIN_VALIDATION_ERROR"
    assert "Cannot sell input/ingredient products via POS." in payload["error"]["message"]

    # DB invariants: no sale, no SALE movements, snapshot unchanged
    s2: Session = SessionLocal()
    try:
        sale_count = s2.execute(text("SELECT COUNT(*) FROM sale")).scalar_one()
        sale_mov_count = s2.execute(
            text("SELECT COUNT(*) FROM inventory_movement WHERE reason = 'SALE'")
        ).scalar_one()
        after = get_on_hand(s2, branch_id=ids["branch_id"], product_id=ids["product_id"])

        assert int(sale_count) == 0
        assert int(sale_mov_count) == 0
        assert after == Decimal("100")
    finally:
        s2.close()
