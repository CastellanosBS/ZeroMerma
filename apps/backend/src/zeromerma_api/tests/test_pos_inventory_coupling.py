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
    s.execute(text("TRUNCATE TABLE payment RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE sale_item RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE sale RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE cash_session RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE inventory_movement RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE inventory_balance RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE product RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE user_account RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE role RESTART IDENTITY CASCADE;"))
    s.execute(text("TRUNCATE TABLE branch RESTART IDENTITY CASCADE;"))
    s.commit()


def seed_core(s: Session) -> tuple[int, int, int]:
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
    Seed BOTH:
      1) inventory_movement ledger (audit)
      2) inventory_balance snapshot (operational)

    This avoids calling bootstrap inside tests and keeps tests deterministic.
    """
    # Ledger entry (audit)
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

    # Snapshot row (operational truth)
    s.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :qty, 0, now(), now())
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET on_hand = EXCLUDED.on_hand, updated_at = now()
            """
        ),
        {"branch_id": branch_id, "product_id": product_id, "qty": qty},
    )

    s.commit()


def snapshot_on_hand(s: Session, *, branch_id: int, product_id: int) -> float:
    val = s.execute(
        text(
            """
            SELECT COALESCE(on_hand, 0)
            FROM inventory_balance
            WHERE branch_id = :branch_id AND product_id = :product_id
            """
        ),
        {"branch_id": branch_id, "product_id": product_id},
    ).scalar_one_or_none()
    return float(val or 0)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping inventory coupling tests",
)
def test_sale_creates_negative_inventory_movements_and_decrements_snapshot():
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

        assert (
            abs(snapshot_on_hand(s, branch_id=branch_id, product_id=product_id) - 10.0)
            < 1e-6
        )
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

    # Create sale that consumes 3
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
    sale_id = sale_resp.json()["id"]

    # Verify ledger movement exists and is linked to sale
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

        # Snapshot must decrement from 10 -> 7
        assert (
            abs(snapshot_on_hand(s2, branch_id=branch_id, product_id=product_id) - 7.0)
            < 1e-6
        )
    finally:
        s2.close()


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping inventory coupling tests",
)
def test_oversell_is_blocked_with_409_and_snapshot_not_modified():
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
        assert (
            abs(snapshot_on_hand(s, branch_id=branch_id, product_id=product_id) - 5.0)
            < 1e-6
        )
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

    # Sell 6 with only 5 in snapshot -> 409
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

    # Verify rollback: no sale created, no SALE movement created, snapshot unchanged
    s2: Session = SessionLocal()
    try:
        sale_count = s2.execute(text("SELECT COUNT(*) FROM sale")).scalar_one()
        sale_mov_count = s2.execute(
            text("SELECT COUNT(*) FROM inventory_movement WHERE reason='SALE'")
        ).scalar_one()
        assert int(sale_count) == 0
        assert int(sale_mov_count) == 0
        assert (
            abs(snapshot_on_hand(s2, branch_id=branch_id, product_id=product_id) - 5.0)
            < 1e-6
        )
    finally:
        s2.close()
