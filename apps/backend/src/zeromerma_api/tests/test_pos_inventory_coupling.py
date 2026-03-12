from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app


def make_alembic_config() -> Config:
    """
    Build an Alembic Config that is independent of the current working directory.

    File path:
      .../apps/backend/src/zeromerma_api/tests/test_xxx.py

    Parent chain:
      parents[0] = tests
      parents[1] = zeromerma_api
      parents[2] = src
      parents[3] = backend
    """
    backend_dir = Path(__file__).resolve().parents[3]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    # Optional but good: force the same DB the tests are using
    if os.getenv("DATABASE_URL"):
        cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    return cfg


def alembic_upgrade_head() -> None:
    """
    Apply migrations up to head using Alembic's programmatic API.
    """
    cfg = make_alembic_config()
    command.upgrade(cfg, "head")


def reset_tables(s: Session) -> None:
    """
    Keep deterministic test runs locally by clearing key tables.

    We delete in FK-safe order (children first, parents last).
    """
    s.execute(text("DELETE FROM payment"))
    s.execute(text("DELETE FROM sale_item"))
    s.execute(text("DELETE FROM sale"))
    s.execute(text("DELETE FROM inventory_movement"))
    s.execute(text("DELETE FROM inventory_balance"))
    s.execute(text("DELETE FROM cash_session"))
    s.execute(text("DELETE FROM user_account"))
    s.execute(text("DELETE FROM role"))
    s.execute(text("DELETE FROM branch"))
    s.execute(text("DELETE FROM product"))
    s.commit()


def seed_core(s: Session) -> tuple[int, int, int]:
    """
    Create minimal core data:

      - branch MAIN
      - role ADMIN
      - user admin@example.com
      - product SKU-001

    Returns:
      (branch_id, user_id, product_id)
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
            VALUES (:branch_id, :role_id, 'admin@example.com', 'Admin User', NULL, true, now(), now())
            RETURNING id
            """
        ),
        {"branch_id": branch_id, "role_id": role_id},
    ).scalar_one()

    product_id = s.execute(
        text(
            """
            INSERT INTO product (sku, name, is_active, created_at, updated_at)
            VALUES ('SKU-001', 'Test Product', true, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    s.commit()
    return int(branch_id), int(user_id), int(product_id)


def seed_stock_ledger_only(
    s: Session, *, branch_id: int, product_id: int, qty: float, created_by_id: int
) -> None:
    """
    Insert a single OPENING_BALANCE movement into the ledger.

    This is used to keep ledger and snapshot consistent for tests that
    validate both.
    """
    s.execute(
        text(
            """
            INSERT INTO inventory_movement
              (branch_id, product_id, qty, reason, ref_type, ref_id, note, created_by_id, created_at, updated_at)
            VALUES
              (:b, :p, :q, 'OPENING_BALANCE', NULL, NULL, 'seed', :u, now(), now())
            """
        ),
        {"b": branch_id, "p": product_id, "q": qty, "u": created_by_id},
    )
    s.commit()


def seed_stock_snapshot(
    s: Session, *, branch_id: int, product_id: int, on_hand: float
) -> None:
    """
    Upsert inventory snapshot row (inventory_balance).

    Why upsert:
    - Tests may run multiple times against the same DB.
    - We want deterministic behavior without UNIQUE constraint failures.

    Important:
    - inventory_balance has a non-negative check constraint for on_hand, so
      tests should only seed non-negative values here.
    """
    s.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:b, :p, :on_hand, 0, now(), now())
            ON CONFLICT (branch_id, product_id)
            DO UPDATE SET
                on_hand = EXCLUDED.on_hand,
                reserved = EXCLUDED.reserved,
                updated_at = now()
            """
        ),
        {"b": branch_id, "p": product_id, "on_hand": float(on_hand)},
    )
    s.commit()


def on_hand(s: Session, *, branch_id: int, product_id: int) -> float:
    """
    Read current snapshot on_hand for a given (branch, product).
    """
    val = s.execute(
        text(
            """
            SELECT COALESCE(on_hand, 0)
            FROM inventory_balance
            WHERE branch_id = :b AND product_id = :p
            """
        ),
        {"b": branch_id, "p": product_id},
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

        # Seed snapshot stock (operational truth for decrement)
        seed_stock_snapshot(s, branch_id=branch_id, product_id=product_id, on_hand=10.0)

        # Seed ledger too (audit truth)
        seed_stock_ledger_only(
            s,
            branch_id=branch_id,
            product_id=product_id,
            qty=10.0,
            created_by_id=user_id,
        )

        assert abs(on_hand(s, branch_id=branch_id, product_id=product_id) - 10.0) < 1e-6
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

    resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [{"product_id": product_id, "qty": 2.0, "unit_price": 10.00}],
        },
    )
    assert resp.status_code == 200, resp.text

    s2: Session = SessionLocal()
    try:
        mov_qty_sum = s2.execute(
            text(
                """
                SELECT COALESCE(SUM(qty), 0)
                FROM inventory_movement
                WHERE branch_id = :b AND product_id = :p
                """
            ),
            {"b": branch_id, "p": product_id},
        ).scalar_one()

        # Ledger should reflect -2 SALE (and +10 opening)
        assert float(mov_qty_sum) == pytest.approx(8.0, abs=1e-6)

        # Snapshot must reflect on_hand = 8
        assert abs(on_hand(s2, branch_id=branch_id, product_id=product_id) - 8.0) < 1e-6
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

        seed_stock_snapshot(s, branch_id=branch_id, product_id=product_id, on_hand=5.0)
        seed_stock_ledger_only(
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

    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

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

    s2: Session = SessionLocal()
    try:
        sale_count = s2.execute(text("SELECT COUNT(*) FROM sale")).scalar_one()
        sale_mov_count = s2.execute(
            text("SELECT COUNT(*) FROM inventory_movement WHERE reason='SALE'")
        ).scalar_one()

        assert int(sale_count) == 0
        assert int(sale_mov_count) == 0
        assert abs(on_hand(s2, branch_id=branch_id, product_id=product_id) - 5.0) < 1e-6
    finally:
        s2.close()
