# apps/backend/tests/test_pos_inventory_coupling.py
# PURPOSE:
#   End-to-end tests for B3.4 inventory coupling:
#     - When a sale is created, inventory_movement rows are written (reason='SALE')
#     - Stock (on-hand) is computed from ledger and oversell is blocked
#
# Verifies:
#   1) Seed opening stock with OPENING_BALANCE movement.
#   2) Create a sale that consumes stock -> OK + movement rows created.
#   3) Attempt a sale that would oversell -> 409.
#   4) Confirm ledger sums match expected on-hand.

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
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")


def reset_tables(s: Session) -> None:
    """
    Reset state in dependency-safe order.
    """
    # Payments and sale items depend on sale; movements depend on branch/product/user.
    # If payment table exists but you haven't created it yet, TRUNCATE will fail.
    # In your project B3.3 is already done, so payment exists.
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
    Minimal core entities.
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


def seed_opening_stock(
    s: Session, *, branch_id: int, product_id: int, qty: float, created_by_id: int
) -> None:
    """
    Insert opening stock directly into the inventory ledger.
    We do this at DB level because your API for stock seeding isn't built yet.
    """
    s.execute(
        text(
            """
            INSERT INTO inventory_movement
                (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :qty, 'OPENING_BALANCE', NULL, NULL, 'seed opening stock', :created_by_id, now(), now())
            """
        ),
        {
            "branch_id": branch_id,
            "product_id": product_id,
            "qty": qty,
            "created_by_id": created_by_id,
        },
    )
    s.commit()


def on_hand(s: Session, *, branch_id: int, product_id: int) -> float:
    """
    Compute on-hand from ledger directly in SQL for assertion.
    """
    val = s.execute(
        text(
            """
            SELECT COALESCE(SUM(qty), 0)
            FROM inventory_movement
            WHERE branch_id = :branch_id AND product_id = :product_id
            """
        ),
        {"branch_id": branch_id, "product_id": product_id},
    ).scalar_one()
    return float(val)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping inventory coupling tests",
)
def test_sale_creates_negative_inventory_movements_and_updates_on_hand():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_tables(s)
        branch_id, user_id, product_id = seed_core(s)
        seed_opening_stock(
            s,
            branch_id=branch_id,
            product_id=product_id,
            qty=10.0,
            created_by_id=user_id,
        )

        # Sanity: on hand should be 10
        assert abs(on_hand(s, branch_id=branch_id, product_id=product_id) - 10.0) < 1e-6
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

    # Create sale that consumes 3 units
    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [{"product_id": product_id, "qty": 3.0, "unit_price": 25.00}],
        },
    )
    assert sale_resp.status_code == 200, sale_resp.text
    sale = sale_resp.json()
    sale_id = sale["id"]

    # Verify ledger: there must be one SALE movement with qty=-3 and ref_id=sale_id
    s2: Session = SessionLocal()
    try:
        rows = s2.execute(
            text(
                """
                SELECT qty, reason, ref_type, ref_id
                FROM inventory_movement
                WHERE branch_id = :branch_id AND product_id = :product_id AND reason = 'SALE'
                ORDER BY id ASC
                """
            ),
            {"branch_id": branch_id, "product_id": product_id},
        ).fetchall()

        assert len(rows) == 1
        qty_val, reason, ref_type, ref_id = rows[0]
        assert float(qty_val) == -3.0
        assert reason == "SALE"
        assert ref_type == "SALE"
        assert int(ref_id) == int(sale_id)

        # On hand should now be 7
        assert abs(on_hand(s2, branch_id=branch_id, product_id=product_id) - 7.0) < 1e-6
    finally:
        s2.close()


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping inventory coupling tests",
)
def test_oversell_is_blocked_with_409_and_no_sale_is_created():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_tables(s)
        branch_id, user_id, product_id = seed_core(s)
        seed_opening_stock(
            s,
            branch_id=branch_id,
            product_id=product_id,
            qty=5.0,
            created_by_id=user_id,
        )
        assert abs(on_hand(s, branch_id=branch_id, product_id=product_id) - 5.0) < 1e-6
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

    # Try to sell 6 units when only 5 on hand -> expect 409
    resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [{"product_id": product_id, "qty": 6.0, "unit_price": 10.00}],
        },
    )
    assert resp.status_code == 409, resp.text

    # Confirm no sale row exists and no SALE movement row exists
    s2: Session = SessionLocal()
    try:
        sale_count = s2.execute(text("SELECT COUNT(*) FROM sale")).scalar_one()
        sale_mov_count = s2.execute(
            text("SELECT COUNT(*) FROM inventory_movement WHERE reason='SALE'")
        ).scalar_one()

        assert int(sale_count) == 0
        assert int(sale_mov_count) == 0

        # Stock should still be 5
        assert abs(on_hand(s2, branch_id=branch_id, product_id=product_id) - 5.0) < 1e-6
    finally:
        s2.close()
