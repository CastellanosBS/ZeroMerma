from __future__ import annotations

import os
from datetime import datetime, timezone
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
    token = create_access_token(subject=str(user_id))
    return {"Authorization": f"Bearer {token}"}


def reset_db(s: Session) -> None:
    s.execute(
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
    s.commit()


def seed_role(s: Session, code: str, name: str) -> int:
    role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES (:code, :name, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(role_id)


def seed_branch(s: Session, code: str, name: str) -> int:
    branch_id = s.execute(
        text(
            """
            INSERT INTO branch (code, name, is_active, created_at, updated_at)
            VALUES (:code, :name, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name},
    ).scalar_one()
    s.commit()
    return int(branch_id)


def seed_user(
    s: Session,
    *,
    branch_id: int,
    role_id: int,
    email: str,
    full_name: str,
) -> int:
    user_id = s.execute(
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
    s.commit()
    return int(user_id)


def seed_category(
    s: Session,
    *,
    code: str,
    name: str,
    quick_name: str,
) -> int:
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :quick_name, TRUE, 10, TRUE, now(), now())
            RETURNING id
            """
        ),
        {"code": code, "name": name, "quick_name": quick_name},
    ).scalar_one()
    s.commit()
    return int(category_id)


def seed_product(
    s: Session,
    *,
    category_id: int,
    branch_id: int,
    sku: str,
    name: str,
    quick_name: str,
    sale_price: Decimal,
) -> int:
    product_id = s.execute(
        text(
            """
            INSERT INTO product
                (
                    sku, name, quick_name, category_id, uom, is_input,
                    show_in_pos, is_sellable_in_pos, default_pos_order,
                    sale_price, is_active, created_at, updated_at
                )
            VALUES
                (
                    :sku, :name, :quick_name, :category_id, 'PCS', FALSE,
                    TRUE, TRUE, 10,
                    :sale_price, TRUE, now(), now()
                )
            RETURNING id
            """
        ),
        {
            "sku": sku,
            "name": name,
            "quick_name": quick_name,
            "category_id": int(category_id),
            "sale_price": sale_price,
        },
    ).scalar_one()

    s.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, 100.000, 0.000, now(), now())
            """
        ),
        {"branch_id": int(branch_id), "product_id": int(product_id)},
    )
    s.commit()
    return int(product_id)


def seed_price_override(
    s: Session,
    *,
    branch_id: int,
    product_id: int,
    price: Decimal,
    created_by_id: int,
) -> int:
    override_id = s.execute(
        text(
            """
            INSERT INTO product_price
                (branch_id, product_id, price, currency, created_by_id, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :price, 'MXN', :created_by_id, now(), now())
            RETURNING id
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
            "price": price,
            "created_by_id": int(created_by_id),
        },
    ).scalar_one()
    s.commit()
    return int(override_id)


def open_cash_session(client: TestClient, *, branch_id: int, user_id: int) -> int:
    resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": "1000.00"},
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


def create_order(
    client: TestClient,
    *,
    branch_id: int,
    user_id: int,
    product_id: int,
    qty: str,
    customer_name: str,
    requested_for_at: str | None,
) -> int:
    resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "customer_name": customer_name,
            "requested_for_at": requested_for_at,
            "items": [{"product_id": product_id, "qty": qty}],
        },
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order checkout tests",
)
def test_order_checkout_preview_uses_frozen_order_snapshots():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        baker_role_id = seed_role(s, "BAKER", "Baker")

        branch_id = seed_branch(s, "MAIN", "Main Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
        baker_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=baker_role_id,
            email="baker@example.com",
            full_name="Baker User",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            branch_id=branch_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
        )
        seed_price_override(
            s,
            branch_id=branch_id,
            product_id=product_id,
            price=Decimal("9.50"),
            created_by_id=admin_user_id,
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="3.000",
        customer_name="Juan Perez",
        requested_for_at=datetime(2026, 3, 25, 8, 30, tzinfo=timezone.utc).isoformat(),
    )

    s2 = SessionLocal()
    try:
        s2.execute(
            text(
                """
                UPDATE product_price
                SET price = 12.00,
                    updated_at = now()
                WHERE branch_id = :branch_id
                  AND product_id = :product_id
                """
            ),
            {"branch_id": branch_id, "product_id": product_id},
        )
        s2.commit()
    finally:
        s2.close()

    send_resp = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    assert send_resp.status_code == 200, send_resp.text

    ready_resp = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=auth_headers(baker_user_id),
    )
    assert ready_resp.status_code == 200, ready_resp.text

    resp = client.get(
        f"/pos/orders/{order_id}/checkout-preview",
        headers=auth_headers(cashier_user_id),
    )
    assert resp.status_code == 200, resp.text
    preview = resp.json()

    assert preview["order_id"] == order_id
    assert preview["status"] == "READY"
    assert preview["customer_name"] == "Juan Perez"
    assert Decimal(preview["subtotal"]) == Decimal("28.50")
    assert Decimal(preview["tax"]) == Decimal("0.00")
    assert Decimal(preview["total"]) == Decimal("28.50")
    assert len(preview["items"]) == 1
    assert preview["items"][0]["sku"] == "BREAD-BOL"
    assert Decimal(preview["items"][0]["qty"]) == Decimal("3.000")
    assert Decimal(preview["items"][0]["unit_price_snapshot"]) == Decimal("9.50")
    assert Decimal(preview["items"][0]["line_total_snapshot"]) == Decimal("28.50")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order checkout tests",
)
def test_deliver_order_via_checkout_links_sale_and_marks_delivered():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        baker_role_id = seed_role(s, "BAKER", "Baker")

        branch_id = seed_branch(s, "MAIN", "Main Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
        baker_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=baker_role_id,
            email="baker@example.com",
            full_name="Baker User",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            branch_id=branch_id,
            sku="BREAD-BAG",
            name="Baguette",
            quick_name="Baguette",
            sale_price=Decimal("25.00"),
        )
        seed_price_override(
            s,
            branch_id=branch_id,
            product_id=product_id,
            price=Decimal("27.00"),
            created_by_id=admin_user_id,
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="2.000",
        customer_name="Maria",
        requested_for_at=None,
    )

    send_resp = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    assert send_resp.status_code == 200, send_resp.text

    ready_resp = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=auth_headers(baker_user_id),
    )
    assert ready_resp.status_code == 200, ready_resp.text

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
    )

    resp = client.post(
        f"/pos/orders/{order_id}/deliver-checkout",
        json={
            "cash_session_id": cash_session_id,
            "payment": {
                "method": "CASH",
                "amount_tendered": "54.00",
                "reference": "ORDER-CASH-001",
            },
            "print_ticket": True,
        },
        headers=auth_headers(cashier_user_id),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["order_id"] == order_id
    assert payload["order_status"] == "DELIVERED"
    assert payload["sale_status"] == "PAID"
    assert payload["payment_status"] == "AUTHORIZED"
    assert Decimal(payload["subtotal"]) == Decimal("54.00")
    assert Decimal(payload["tax"]) == Decimal("0.00")
    assert Decimal(payload["total"]) == Decimal("54.00")
    assert Decimal(payload["paid_amount"]) == Decimal("54.00")
    assert Decimal(payload["change_due"]) == Decimal("0.00")
    assert Decimal(payload["balance_due"]) == Decimal("0.00")
    assert payload["print_ticket"] is True

    receipt = payload["receipt"]
    assert receipt["payment_method"] == "CASH"
    assert Decimal(receipt["amount_tendered"]) == Decimal("54.00")
    assert Decimal(receipt["total"]) == Decimal("54.00")
    assert len(receipt["items"]) == 1
    assert receipt["items"][0]["sku"] == "BREAD-BAG"
    assert Decimal(receipt["items"][0]["unit_price"]) == Decimal("27.00")
    assert Decimal(receipt["items"][0]["line_total"]) == Decimal("54.00")

    detail_resp = client.get(
        f"/pos/orders/{order_id}",
        headers=auth_headers(cashier_user_id),
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()

    assert detail["status"] == "DELIVERED"
    assert detail["delivered_by_id"] == cashier_user_id
    assert detail["delivered_at"] is not None
    assert detail["delivered_sale_id"] == payload["sale_id"]


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order checkout tests",
)
def test_deliver_order_via_checkout_rejects_non_ready_order():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")

        branch_id = seed_branch(s, "MAIN", "Main Branch")

        seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            branch_id=branch_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="2.000",
        customer_name="Juan",
        requested_for_at=None,
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
    )

    resp = client.post(
        f"/pos/orders/{order_id}/deliver-checkout",
        json={
            "cash_session_id": cash_session_id,
            "payment": {
                "method": "CASH",
                "amount_tendered": "16.00",
            },
            "print_ticket": True,
        },
        headers=auth_headers(cashier_user_id),
    )
    assert resp.status_code == 409, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_CONFLICT"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order checkout tests",
)
def test_deliver_order_via_checkout_cannot_run_twice():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")
        baker_role_id = seed_role(s, "BAKER", "Baker")

        branch_id = seed_branch(s, "MAIN", "Main Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=cashier_role_id,
            email="cashier@example.com",
            full_name="Cashier User",
        )
        baker_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=baker_role_id,
            email="baker@example.com",
            full_name="Baker User",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            branch_id=branch_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    order_id = create_order(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        product_id=product_id,
        qty="2.000",
        customer_name="Juan",
        requested_for_at=None,
    )

    send_resp = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    assert send_resp.status_code == 200, send_resp.text

    ready_resp = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=auth_headers(baker_user_id),
    )
    assert ready_resp.status_code == 200, ready_resp.text

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
    )

    first_resp = client.post(
        f"/pos/orders/{order_id}/deliver-checkout",
        json={
            "cash_session_id": cash_session_id,
            "payment": {
                "method": "CASH",
                "amount_tendered": "16.00",
            },
            "print_ticket": True,
        },
        headers=auth_headers(cashier_user_id),
    )
    assert first_resp.status_code == 200, first_resp.text

    second_resp = client.post(
        f"/pos/orders/{order_id}/deliver-checkout",
        json={
            "cash_session_id": cash_session_id,
            "payment": {
                "method": "CASH",
                "amount_tendered": "16.00",
            },
            "print_ticket": True,
        },
        headers=auth_headers(cashier_user_id),
    )
    assert second_resp.status_code == 409, second_resp.text
    payload = second_resp.json()
    assert payload["error"]["code"] == "DOMAIN_CONFLICT"
