# apps/backend/tests/test_pos_payments_endpoints.py
# PURPOSE:
#   End-to-end tests for POS Payments:
#     - POST /pos/sales/{sale_id}/payments
#     - GET  /pos/sales/{sale_id}
#
# Validates:
#   - Payments can be added to OPEN sales
#   - paid_amount and balance_due are computed correctly
#   - Overpay is rejected (409)
#   - Payments are rejected if sale not OPEN (409)

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
    Ensure schema exists at HEAD. Uses alembic.ini in apps/backend/.
    """
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def reset_tables(s: Session) -> None:
    """
    Reset DB state so tests are deterministic.
    Order: leaf tables first, then parents.
    """
    # Payments depend on sale; sale_items depend on sale; sessions depend on users/branch.
    s.execute(text("TRUNCATE TABLE payment RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE sale_item RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE sale RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE cash_session RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE inventory_movement RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE product RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE user_account RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE role RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE branch RESTART IDENTITY CASCADE;"))
    s.commit()


def seed_core(s: Session) -> tuple[int, int, int]:
    """
    Create minimal entities:
      - branch MAIN
      - role ADMIN
      - user admin@example.com
      - product DONUT-GLA

    Returns: (branch_id, user_id, product_id)
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
    reason="DATABASE_URL not set; skipping POS payments tests",
)
def test_payments_flow_and_balance_and_overpay():
    # 1) Ensure schema up to date
    alembic_upgrade_head()

    # 2) Clean state + seed core
    s: Session = SessionLocal()
    try:
        reset_tables(s)
        branch_id, user_id, product_id = seed_core(s)
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    # 3) Open cash session (required for sale creation in your flow)
    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

    # 4) Create a sale total=75.00
    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [
                {"product_id": product_id, "qty": 2, "unit_price": 25.00},  # 50
                {"product_id": product_id, "qty": 1, "unit_price": 25.00},  # 25
            ],
        },
    )
    assert sale_resp.status_code == 200, sale_resp.text
    sale_id = sale_resp.json()["id"]
    assert abs(sale_resp.json()["total"] - 75.00) < 1e-6

    # 5) Add first payment: 50.00
    p1 = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CASH", "amount": 50.00, "reference": None},
    )
    assert p1.status_code == 200, p1.text
    assert abs(p1.json()["amount"] - 50.00) < 1e-6
    assert p1.json()["method"] == "CASH"
    assert p1.json()["sale_id"] == sale_id

    # 6) Sale detail should show paid=50, balance=25, payments length=1
    d1 = client.get(f"/pos/sales/{sale_id}")
    assert d1.status_code == 200, d1.text
    detail = d1.json()
    assert abs(detail["paid_amount"] - 50.00) < 1e-6
    assert abs(detail["balance_due"] - 25.00) < 1e-6
    assert len(detail["payments"]) == 1

    # 7) Add second payment: 25.00 (exactly completes sale)
    p2 = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CARD", "amount": 25.00, "reference": "AUTH123"},
    )
    assert p2.status_code == 200, p2.text

    # 8) Sale detail should show paid=75, balance=0, payments length=2
    d2 = client.get(f"/pos/sales/{sale_id}")
    assert d2.status_code == 200, d2.text
    detail2 = d2.json()
    assert abs(detail2["paid_amount"] - 75.00) < 1e-6
    assert abs(detail2["balance_due"] - 0.00) < 1e-6
    assert len(detail2["payments"]) == 2

    # 9) Overpay should be rejected (409)
    over = client.post(
        f"/pos/sales/{sale_id}/payments", json={"method": "CASH", "amount": 0.01}
    )
    assert over.status_code == 409, over.text


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS payments tests",
)
def test_payments_rejected_when_sale_not_open():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_tables(s)
        branch_id, user_id, product_id = seed_core(s)
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    # Open cash session
    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

    # Create sale
    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [{"product_id": product_id, "qty": 1, "unit_price": 10.00}],
        },
    )
    assert sale_resp.status_code == 200, sale_resp.text
    sale_id = sale_resp.json()["id"]

    # Close cash session (this does NOT close the sale, but in real life you might close session after sales)
    close_resp = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closed_by_id": user_id, "closing_amount": 0.00},
    )
    assert close_resp.status_code == 200, close_resp.text

    # Now we need a non-OPEN sale status to test payment rejection.
    # MVP: you don't yet have a cancel endpoint, so we simulate by directly updating the DB.
    s2: Session = SessionLocal()
    try:
        s2.execute(
            text("UPDATE sale SET status='CANCELED' WHERE id=:id"), {"id": sale_id}
        )
        s2.commit()
    finally:
        s2.close()

    # Try to pay a CANCELED sale -> 409
    p = client.post(
        f"/pos/sales/{sale_id}/payments", json={"method": "CASH", "amount": 5.00}
    )
    assert p.status_code == 409, p.text
