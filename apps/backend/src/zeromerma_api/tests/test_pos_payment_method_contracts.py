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
    Build Authorization headers for protected POS endpoints.
    """
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def reset_db(session: Session) -> None:
    """
    Hard reset the tables touched by the payment-method contract tests.
    """
    session.execute(
        text(
            """
            TRUNCATE TABLE
                customer_order_item,
                customer_order,
                product_price,
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
    session.commit()


def seed_role(session: Session, *, code: str, name: str) -> int:
    role_id = session.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    session.commit()
    return int(role_id)


def seed_branch(session: Session, *, code: str = "MAIN", name: str = "Main Branch") -> int:
    branch_id = session.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    session.commit()
    return int(branch_id)


def seed_user(
    session: Session,
    *,
    branch_id: int,
    role_id: int,
    email: str,
    full_name: str,
) -> int:
    user_id = session.execute(
        text(
            """
            INSERT INTO user_account
                (branch_id, role_id, email, full_name, password_hash, is_active, created_at, updated_at)
            VALUES
                (:branch_id, :role_id, :email, :full_name, NULL, TRUE, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "role_id": int(role_id),
            "email": email,
            "full_name": full_name,
        },
    ).scalar_one()
    session.commit()
    return int(user_id)


def seed_category(session: Session) -> int:
    category_id = session.execute(
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
    session.commit()
    return int(category_id)


def seed_product(
    session: Session,
    *,
    branch_id: int,
    category_id: int,
    sku: str,
    name: str,
    sale_price: Decimal,
    on_hand: Decimal,
) -> int:
    product_id = session.execute(
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
                    :sku,
                    :name,
                    :name,
                    :category_id,
                    'PCS',
                    FALSE,
                    TRUE,
                    TRUE,
                    10,
                    :sale_price,
                    TRUE,
                    now(),
                    now()
                )
            RETURNING id
            """
        ),
        {
            "sku": sku,
            "name": name,
            "category_id": int(category_id),
            "sale_price": sale_price,
        },
    ).scalar_one()

    session.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :on_hand, 0.000, now(), now())
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
            "on_hand": on_hand,
        },
    )
    session.commit()
    return int(product_id)


def open_cash_session(client: TestClient, *, branch_id: int, user_id: int) -> int:
    response = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": "1000.00"},
        headers=auth_headers(user_id),
    )
    assert response.status_code == 200, response.text
    return int(response.json()["id"])


def create_ready_order(
    client: TestClient,
    *,
    branch_id: int,
    admin_user_id: int,
    cashier_user_id: int,
    product_id: int,
) -> int:
    create_response = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "customer_name": "Transfer Customer",
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=auth_headers(cashier_user_id),
    )
    assert create_response.status_code == 200, create_response.text
    order_id = int(create_response.json()["id"])

    send_response = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    assert send_response.status_code == 200, send_response.text

    ready_response = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=auth_headers(admin_user_id),
    )
    assert ready_response.status_code == 200, ready_response.text

    return order_id


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping payment-method contract tests",
)
def test_checkout_accepts_transfer_payment():
    alembic_upgrade_head()

    session: Session = SessionLocal()
    try:
        reset_db(session)

        admin_role_id = seed_role(session, code="ADMIN", name="Administrator")
        branch_id = seed_branch(session)
        admin_user_id = seed_user(
            session,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        category_id = seed_category(session)
        product_id = seed_product(
            session,
            branch_id=branch_id,
            category_id=category_id,
            sku="SKU-TR-CHECKOUT",
            name="Transfer Checkout Product",
            sale_price=Decimal("40.00"),
            on_hand=Decimal("25.000"),
        )
    finally:
        session.close()

    client = TestClient(create_app())
    cash_session_id = open_cash_session(client, branch_id=branch_id, user_id=admin_user_id)

    response = client.post(
        "/pos/checkout",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000"}],
            "payment": {
                "method": "TRANSFER",
                "reference": "TRX-CHK-001",
                "external_auth_code": "AUTH-TR-001",
            },
            "print_ticket": False,
        },
        headers=auth_headers(admin_user_id),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["sale_status"] == "PAID"
    assert payload["payment_status"] == "AUTHORIZED"
    assert Decimal(payload["total"]) == Decimal("40.00")
    assert Decimal(payload["paid_amount"]) == Decimal("40.00")
    assert Decimal(payload["change_due"]) == Decimal("0.00")
    assert payload["receipt"]["payment_method"] == "TRANSFER"
    assert payload["receipt"]["amount_tendered"] is None
    assert payload["print_ticket"] is False

    sale_detail = client.get(
        f"/pos/sales/{payload['sale_id']}",
        headers=auth_headers(admin_user_id),
    )
    assert sale_detail.status_code == 200, sale_detail.text
    detail_payload = sale_detail.json()
    assert detail_payload["payments"][0]["method"] == "TRANSFER"
    assert detail_payload["payments"][0]["reference"] == "TRX-CHK-001"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping payment-method contract tests",
)
def test_add_payment_accepts_transfer_method():
    alembic_upgrade_head()

    session: Session = SessionLocal()
    try:
        reset_db(session)

        admin_role_id = seed_role(session, code="ADMIN", name="Administrator")
        branch_id = seed_branch(session)
        admin_user_id = seed_user(
            session,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        category_id = seed_category(session)
        product_id = seed_product(
            session,
            branch_id=branch_id,
            category_id=category_id,
            sku="SKU-TR-PAYMENT",
            name="Transfer Payment Product",
            sale_price=Decimal("25.00"),
            on_hand=Decimal("25.000"),
        )
    finally:
        session.close()

    client = TestClient(create_app())
    cash_session_id = open_cash_session(client, branch_id=branch_id, user_id=admin_user_id)

    sale_response = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000", "unit_price": "25.00"}],
        },
        headers=auth_headers(admin_user_id),
    )
    assert sale_response.status_code == 200, sale_response.text
    sale_id = int(sale_response.json()["id"])

    payment_response = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "TRANSFER", "amount": "25.00", "reference": "TRX-SALE-001"},
        headers=auth_headers(admin_user_id),
    )
    assert payment_response.status_code == 200, payment_response.text
    payment_payload = payment_response.json()

    assert payment_payload["method"] == "TRANSFER"
    assert Decimal(payment_payload["amount"]) == Decimal("25.00")
    assert payment_payload["reference"] == "TRX-SALE-001"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping payment-method contract tests",
)
def test_order_delivery_checkout_accepts_transfer_payment():
    alembic_upgrade_head()

    session: Session = SessionLocal()
    try:
        reset_db(session)

        admin_role_id = seed_role(session, code="ADMIN", name="Administrator")
        cashier_role_id = seed_role(session, code="CASHIER", name="Cashier")
        branch_id = seed_branch(session)

        admin_user_id = seed_user(
            session,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_user_id = seed_user(
            session,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )

        category_id = seed_category(session)
        product_id = seed_product(
            session,
            branch_id=branch_id,
            category_id=category_id,
            sku="SKU-TR-ORDER",
            name="Transfer Order Product",
            sale_price=Decimal("27.00"),
            on_hand=Decimal("25.000"),
        )
    finally:
        session.close()

    client = TestClient(create_app())

    order_id = create_ready_order(
        client,
        branch_id=branch_id,
        admin_user_id=admin_user_id,
        cashier_user_id=cashier_user_id,
        product_id=product_id,
    )
    cash_session_id = open_cash_session(client, branch_id=branch_id, user_id=cashier_user_id)

    response = client.post(
        f"/pos/orders/{order_id}/deliver-checkout",
        json={
            "cash_session_id": cash_session_id,
            "payment": {
                "method": "TRANSFER",
                "reference": "TRX-ORDER-001",
                "external_auth_code": "AUTH-ORDER-001",
            },
            "print_ticket": True,
        },
        headers=auth_headers(cashier_user_id),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["order_status"] == "DELIVERED"
    assert payload["sale_status"] == "PAID"
    assert payload["payment_status"] == "AUTHORIZED"
    assert Decimal(payload["paid_amount"]) == Decimal("54.00")
    assert Decimal(payload["change_due"]) == Decimal("0.00")
    assert payload["receipt"]["payment_method"] == "TRANSFER"
    assert payload["receipt"]["amount_tendered"] is None

    order_detail = client.get(
        f"/pos/orders/{order_id}",
        headers=auth_headers(cashier_user_id),
    )
    assert order_detail.status_code == 200, order_detail.text
    assert order_detail.json()["delivered_sale_id"] == payload["sale_id"]

    sale_detail = client.get(
        f"/pos/sales/{payload['sale_id']}",
        headers=auth_headers(cashier_user_id),
    )
    assert sale_detail.status_code == 200, sale_detail.text
    assert sale_detail.json()["payments"][0]["method"] == "TRANSFER"
