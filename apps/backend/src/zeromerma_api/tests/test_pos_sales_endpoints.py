from __future__ import annotations

import os
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.core.security import create_access_token
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head


def auth_headers(user_id: int) -> dict[str, str]:
    """
    Build Authorization headers for protected endpoints.
    """
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def reset_tables(s: Session) -> None:
    """
    Hard reset only the tables needed by this test module.

    Important:
    - product_price must be cleared before branch/product due to FK references.
    - production_run must be cleared before user_account because it references
      user_account.created_by_id.
    """
    s.execute(text("DELETE FROM product_price"))
    s.execute(text("DELETE FROM payment"))
    s.execute(text("DELETE FROM sale_item"))
    s.execute(text("DELETE FROM sale"))
    s.execute(text("DELETE FROM inventory_movement"))
    s.execute(text("DELETE FROM inventory_balance"))
    s.execute(text("DELETE FROM production_run"))
    s.execute(text("DELETE FROM cash_session"))
    s.execute(text("DELETE FROM user_account"))
    s.execute(text("DELETE FROM role"))
    s.execute(text("DELETE FROM branch"))
    s.execute(text("DELETE FROM product"))
    s.execute(text("DELETE FROM product_category"))
    s.commit()


def seed_core(s: Session) -> tuple[int, int, int]:
    """
    Seed:
      - one branch
      - one ADMIN role
      - one active user
      - one finished product
      - one inventory_balance row with ample stock
    """
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                ('FINISHED', 'Finished Goods', 'Finished', TRUE, 10, TRUE, now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

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
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:branch_id, :role_id, 'admin@example.com', 'Admin User', NULL, true, now(), now())
            RETURNING id
            """
        ),
        {"branch_id": branch_id, "role_id": role_id},
    ).scalar_one()

    product_id = s.execute(
        text(
            """
            INSERT INTO product
                (
                    sku,
                    name,
                    quick_name,
                    category_id,
                    uom,
                    is_input,
                    show_in_pos,
                    is_sellable_in_pos,
                    default_pos_order,
                    is_active,
                    created_at,
                    updated_at
                )
            VALUES
                (
                    'SKU-001',
                    'Test Product',
                    'Test',
                    :category_id,
                    'PCS',
                    false,
                    true,
                    true,
                    10,
                    true,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {"category_id": category_id},
    ).scalar_one()

    s.execute(
        text(
            """
            INSERT INTO inventory_balance (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES (:b, :p, 999.000, 0.000, now(), now())
            """
        ),
        {"b": branch_id, "p": product_id},
    )

    s.commit()
    return int(branch_id), int(user_id), int(product_id)


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS sales tests",
)
def test_pos_sales_create_and_list_and_errors():
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
        json={"branch_id": branch_id, "opening_amount": "0.00"},
        headers=auth_headers(user_id),
    )
    assert open_resp.status_code == 200, open_resp.text
    cash_session_id = open_resp.json()["id"]

    sale_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [
                {"product_id": product_id, "qty": "2.000", "unit_price": "25.00"},
                {"product_id": product_id, "qty": "1.000", "unit_price": "25.00"},
            ],
        },
        headers=auth_headers(user_id),
    )
    assert sale_resp.status_code == 200, sale_resp.text
    sale = sale_resp.json()

    assert sale["status"] == "OPEN"
    assert Decimal(sale["subtotal"]) == Decimal("75.00")
    assert Decimal(sale["tax"]) == Decimal("0.00")
    assert Decimal(sale["total"]) == Decimal("75.00")

    assert len(sale["items"]) == 2
    assert Decimal(sale["items"][0]["line_total"]) == Decimal("50.00")
    assert Decimal(sale["items"][1]["line_total"]) == Decimal("25.00")

    list_resp = client.get(
        "/pos/sales",
        params={"branch_id": branch_id, "limit": 50},
        headers=auth_headers(user_id),
    )
    assert list_resp.status_code == 200, list_resp.text
    sales = list_resp.json()
    assert isinstance(sales, list)
    assert any(x["id"] == sale["id"] for x in sales)

    missing_product_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": 999999, "qty": "1.000", "unit_price": "10.00"}],
        },
        headers=auth_headers(user_id),
    )
    assert missing_product_resp.status_code == 404, missing_product_resp.text

    close_resp = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "0.00"},
        headers=auth_headers(user_id),
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["status"] == "CLOSED"

    closed_session_resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000", "unit_price": "10.00"}],
        },
        headers=auth_headers(user_id),
    )
    assert closed_session_resp.status_code == 409, closed_session_resp.text
