# apps/backend/tests/test_pos_sales_endpoints.py
# PURPOSE:
#   End-to-end tests for POS Sales endpoints:
#     - POST /pos/sales (create)
#     - GET  /pos/sales (list)
#
# Strategy:
#   - Ensure migrations are applied (alembic upgrade head).
#   - Reset data with TRUNCATE for deterministic tests.
#   - Create minimal core entities (branch/role/user/product).
#   - Open a cash session.
#   - Create a sale and assert computed totals.
#   - Assert listing returns it.
#   - Assert errors for closed session and missing product.

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.product import Product
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount


def alembic_upgrade_head() -> None:
    """
    Apply all migrations to HEAD for the configured DATABASE_URL.
    This makes tests self-contained.
    """
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def reset_tables(s: Session) -> None:
    """
    Reset DB state for deterministic tests.
    TRUNCATE is fast and CASCADE removes dependent rows (sale_item depends on sale, etc.).

    NOTE: We truncate in dependency-safe order using CASCADE.
    """
    s.execute(text("TRUNCATE TABLE sale_item RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE sale RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE cash_session RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE inventory_movement RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE product RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE user_account RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE role RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE branch RESTART IDENTITY CASCADE;"))
    s.commit()


def ensure_core_entities(s: Session) -> tuple[int, int, int]:
    """
    Create minimal core entities needed by POS:
      - Branch MAIN
      - Role ADMIN
      - UserAccount admin@example.com
      - Product DONUT-GLA

    Returns:
      (branch_id, user_id, product_id)
    """
    b = Branch(code="MAIN", name="Main Branch")
    s.add(b)
    s.flush()

    r = Role(code="ADMIN", name="Admin")
    s.add(r)
    s.flush()

    u = UserAccount(
        branch_id=b.id,
        role_id=r.id,
        email="admin@example.com",
        full_name="Admin User",
        password_hash=None,
        is_active=True,
    )
    s.add(u)
    s.flush()

    p = Product(sku="DONUT-GLA", name="Donut Glazed")
    s.add(p)
    s.flush()

    s.commit()
    return b.id, u.id, p.id


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS sales tests",
)
def test_pos_sales_create_and_list_and_errors():
    # 1) Ensure schema exists
    alembic_upgrade_head()

    # 2) Reset DB state (deterministic test)
    s: Session = SessionLocal()
    try:
        reset_tables(s)
        branch_id, user_id, product_id = ensure_core_entities(s)
    finally:
        s.close()

    # 3) TestClient hits the real FastAPI router stack
    app = create_app()
    client = TestClient(app)

    # 4) Open a cash session (required for sales)
    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

    # 5) Create a sale (2 lines; totals must be computed by backend)
    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [
                {"product_id": product_id, "qty": 2, "unit_price": 25.00},  # 50.00
                {"product_id": product_id, "qty": 1, "unit_price": 25.00},  # 25.00
            ],
        },
    )
    assert sale_resp.status_code == 200, sale_resp.text
    sale = sale_resp.json()

    # Validate totals
    assert sale["status"] == "OPEN"
    assert abs(sale["subtotal"] - 75.00) < 1e-6
    assert abs(sale["tax"] - 0.00) < 1e-6
    assert abs(sale["total"] - 75.00) < 1e-6

    # Validate items exist and line totals are computed
    assert len(sale["items"]) == 2
    assert abs(sale["items"][0]["line_total"] - 50.00) < 1e-6
    assert abs(sale["items"][1]["line_total"] - 25.00) < 1e-6

    # 6) List sales should include it
    list_resp = client.get("/pos/sales", params={"branch_id": branch_id, "limit": 50})
    assert list_resp.status_code == 200, list_resp.text
    sales = list_resp.json()
    assert isinstance(sales, list)
    assert len(sales) >= 1
    assert any(x["id"] == sale["id"] for x in sales)

    # 7) Missing product should return 404
    missing_product_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [
                {"product_id": 999999, "qty": 1, "unit_price": 10.00},
            ],
        },
    )
    assert missing_product_resp.status_code == 404, missing_product_resp.text

    # 8) Close the cash session
    close_resp = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closed_by_id": user_id, "closing_amount": 0.00},
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["status"] == "CLOSED"

    # 9) Creating a sale on a CLOSED session should fail (409)
    closed_session_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [
                {"product_id": product_id, "qty": 1, "unit_price": 10.00},
            ],
        },
    )
    assert closed_session_resp.status_code == 409, closed_session_resp.text
