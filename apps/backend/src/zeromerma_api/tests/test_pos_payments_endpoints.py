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
    Hard reset all tables touched by POS payment tests.

    Important:
    - product_price must be cleared before branch/product due to FK references.
    - production_run must be cleared before user_account due to FK references.
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
      - one category
      - one branch
      - one ADMIN role
      - one active user
      - one finished product with stock
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
                (:branch_id, :role_id, 'admin@example.com', 'Admin User', NULL, TRUE, now(), now())
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
                    sale_price,
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
                    FALSE,
                    TRUE,
                    TRUE,
                    10,
                    25.00,
                    TRUE,
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
            VALUES (:branch_id, :product_id, 999.000, 0.000, now(), now())
            """
        ),
        {"branch_id": branch_id, "product_id": product_id},
    )

    s.commit()
    return int(branch_id), int(user_id), int(product_id)


def open_cash_session(client: TestClient, *, branch_id: int, user_id: int) -> int:
    resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": "0.00"},
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


def create_sale(
    client: TestClient,
    *,
    branch_id: int,
    cash_session_id: int,
    user_id: int,
    product_id: int,
    qty: str,
    unit_price: str,
) -> dict:
    resp = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [
                {
                    "product_id": product_id,
                    "qty": qty,
                    "unit_price": unit_price,
                }
            ],
        },
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


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

    cash_session_id = open_cash_session(client, branch_id=branch_id, user_id=user_id)

    sale = create_sale(
        client,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        user_id=user_id,
        product_id=product_id,
        qty="3.000",
        unit_price="25.00",
    )
    sale_id = int(sale["id"])

    payment_1 = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CASH", "amount": "50.00", "reference": "CASH-1"},
        headers=auth_headers(user_id),
    )
    assert payment_1.status_code == 200, payment_1.text
    payment_1_json = payment_1.json()
    assert payment_1_json["sale_id"] == sale_id
    assert payment_1_json["method"] == "CASH"
    assert Decimal(payment_1_json["amount"]) == Decimal("50.00")
    assert payment_1_json["reference"] == "CASH-1"

    detail_1 = client.get(
        f"/pos/sales/{sale_id}",
        headers=auth_headers(user_id),
    )
    assert detail_1.status_code == 200, detail_1.text
    detail_1_json = detail_1.json()
    assert Decimal(detail_1_json["total"]) == Decimal("75.00")
    assert Decimal(detail_1_json["paid_amount"]) == Decimal("50.00")
    assert Decimal(detail_1_json["balance_due"]) == Decimal("25.00")
    assert len(detail_1_json["payments"]) == 1

    payment_2 = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CARD", "amount": "25.00", "reference": "CARD-1"},
        headers=auth_headers(user_id),
    )
    assert payment_2.status_code == 200, payment_2.text
    payment_2_json = payment_2.json()
    assert payment_2_json["method"] == "CARD"
    assert Decimal(payment_2_json["amount"]) == Decimal("25.00")

    detail_2 = client.get(
        f"/pos/sales/{sale_id}",
        headers=auth_headers(user_id),
    )
    assert detail_2.status_code == 200, detail_2.text
    detail_2_json = detail_2.json()
    assert Decimal(detail_2_json["total"]) == Decimal("75.00")
    assert Decimal(detail_2_json["paid_amount"]) == Decimal("75.00")
    assert Decimal(detail_2_json["balance_due"]) == Decimal("0.00")
    assert len(detail_2_json["payments"]) == 2

    overpay = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CASH", "amount": "1.00", "reference": "OVERPAY"},
        headers=auth_headers(user_id),
    )
    assert overpay.status_code == 409, overpay.text


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

    cash_session_id = open_cash_session(client, branch_id=branch_id, user_id=user_id)

    sale = create_sale(
        client,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        user_id=user_id,
        product_id=product_id,
        qty="1.000",
        unit_price="25.00",
    )
    sale_id = int(sale["id"])

    close_resp = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "0.00"},
        headers=auth_headers(user_id),
    )
    assert close_resp.status_code == 200, close_resp.text

    s2: Session = SessionLocal()
    try:
        s2.execute(
            text(
                """
                UPDATE sale
                SET status = 'VOIDED',
                    updated_at = now()
                WHERE id = :sale_id
                """
            ),
            {"sale_id": sale_id},
        )
        s2.commit()
    finally:
        s2.close()

    payment_resp = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "CASH", "amount": "25.00", "reference": "CASH-CLOSED"},
        headers=auth_headers(user_id),
    )
    assert payment_resp.status_code == 409, payment_resp.text
