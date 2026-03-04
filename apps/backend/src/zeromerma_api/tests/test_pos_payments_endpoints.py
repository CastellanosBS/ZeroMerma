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
    Tests live at:
      .../apps/backend/src/zeromerma_api/tests/test_pos_payments_endpoints.py

    So:
      parents[0]=tests
      parents[1]=zeromerma_api
      parents[2]=src
      parents[3]=backend ✅
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


def reset_tables(s: Session) -> None:
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

    # Snapshot row for inventory_balance so sales can decrement safely
    s.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b, :p, 100.000, 0.000, now(), now())
            """
        ),
        {"b": branch_id, "p": product_id},
    )

    s.commit()
    return int(branch_id), int(user_id), int(product_id)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS payments tests",
)
def test_payments_flow_and_balance_and_overpay():
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

    # Create sale total=75 (3 items at 25)
    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "created_by_id": user_id,
            "items": [
                {"product_id": product_id, "qty": 2, "unit_price": 25.00},
                {"product_id": product_id, "qty": 1, "unit_price": 25.00},
            ],
        },
    )
    assert sale_resp.status_code == 200, sale_resp.text
    sale_id = sale_resp.json()["id"]

    # First payment: 50
    p1 = client.post(
        f"/pos/sales/{sale_id}/payments", json={"method": "CASH", "amount": 50.00}
    )
    assert p1.status_code == 200, p1.text

    # Sale detail should show paid=50, balance=25
    d1 = client.get(f"/pos/sales/{sale_id}")
    assert d1.status_code == 200, d1.text
    detail = d1.json()
    assert abs(detail["paid_amount"] - 50.00) < 1e-6
    assert abs(detail["balance_due"] - 25.00) < 1e-6
    assert len(detail["payments"]) == 1

    # Second payment: 25 completes
    p2 = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CARD", "amount": 25.00, "reference": "AUTH123"},
    )
    assert p2.status_code == 200, p2.text

    d2 = client.get(f"/pos/sales/{sale_id}")
    assert d2.status_code == 200, d2.text
    detail2 = d2.json()
    assert abs(detail2["paid_amount"] - 75.00) < 1e-6
    assert abs(detail2["balance_due"] - 0.00) < 1e-6
    assert len(detail2["payments"]) == 2

    # Overpay rejected
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

    open_resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opened_by_id": user_id, "opening_amount": 0.00},
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

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

    close_resp = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closed_by_id": user_id, "closing_amount": 0.00},
    )
    assert close_resp.status_code == 200, close_resp.text

    # Force sale status out of OPEN to test rejection
    s2: Session = SessionLocal()
    try:
        s2.execute(
            text("UPDATE sale SET status='CANCELED' WHERE id=:id"), {"id": sale_id}
        )
        s2.commit()
    finally:
        s2.close()

    p = client.post(
        f"/pos/sales/{sale_id}/payments", json={"method": "CASH", "amount": 5.00}
    )
    assert p.status_code == 409, p.text
