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
    show_in_pos: bool,
    default_pos_order: int,
) -> int:
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :quick_name, :show_in_pos, :default_pos_order, TRUE, now(), now())
            RETURNING id
            """
        ),
        {
            "code": code,
            "name": name,
            "quick_name": quick_name,
            "show_in_pos": bool(show_in_pos),
            "default_pos_order": int(default_pos_order),
        },
    ).scalar_one()
    s.commit()
    return int(category_id)


def seed_product(
    s: Session,
    *,
    category_id: int,
    sku: str,
    name: str,
    quick_name: str,
    sale_price: Decimal | None,
    on_hand_branch_id: int,
    on_hand: Decimal,
    is_input: bool = False,
    show_in_pos: bool = True,
    is_sellable_in_pos: bool = True,
) -> int:
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
                    :sku,
                    :name,
                    :quick_name,
                    :category_id,
                    'PCS',
                    :is_input,
                    :show_in_pos,
                    :is_sellable_in_pos,
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
            "quick_name": quick_name,
            "category_id": int(category_id),
            "is_input": bool(is_input),
            "show_in_pos": bool(show_in_pos),
            "is_sellable_in_pos": bool(is_sellable_in_pos),
            "sale_price": sale_price,
        },
    ).scalar_one()

    s.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (:branch_id, :product_id, :on_hand, 0.000, now(), now())
            """
        ),
        {
            "branch_id": int(on_hand_branch_id),
            "product_id": int(product_id),
            "on_hand": on_hand,
        },
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


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order tests",
)
def test_create_list_detail_order_freezes_price_and_does_not_touch_inventory():
    alembic_upgrade_head()

    s = SessionLocal()
    try:
        reset_db(s)
        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")

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

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
            on_hand_branch_id=branch_id,
            on_hand=Decimal("100.000"),
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

    requested_for = datetime(2026, 3, 25, 8, 30, tzinfo=timezone.utc).isoformat()

    create_resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "customer_name": "Juan Perez",
            "customer_phone": "6620000000",
            "note": "Pedido de mostrador",
            "requested_for_at": requested_for,
            "items": [
                {"product_id": product_id, "qty": "3.000"},
            ],
        },
        headers=auth_headers(cashier_user_id),
    )
    assert create_resp.status_code == 200, create_resp.text
    order = create_resp.json()

    assert order["status"] == "CREATED"
    assert order["branch_id"] == branch_id
    assert order["created_by_id"] == cashier_user_id
    assert order["customer_name"] == "Juan Perez"
    assert order["customer_phone"] == "6620000000"
    assert Decimal(order["subtotal"]) == Decimal("28.50")
    assert Decimal(order["tax"]) == Decimal("0.00")
    assert Decimal(order["total"]) == Decimal("28.50")
    assert order["delivered_sale_id"] is None
    assert len(order["items"]) == 1
    assert order["items"][0]["sku"] == "BREAD-BOL"
    assert order["items"][0]["name"] == "Bolillo"
    assert Decimal(order["items"][0]["qty"]) == Decimal("3.000")
    assert Decimal(order["items"][0]["unit_price_snapshot"]) == Decimal("9.50")
    assert Decimal(order["items"][0]["line_total_snapshot"]) == Decimal("28.50")

    s2 = SessionLocal()
    try:
        on_hand = s2.execute(
            text(
                """
                SELECT on_hand
                FROM inventory_balance
                WHERE branch_id = :branch_id
                  AND product_id = :product_id
                """
            ),
            {"branch_id": branch_id, "product_id": product_id},
        ).scalar_one()
        assert Decimal(str(on_hand)) == Decimal("100.000")
    finally:
        s2.close()

    list_resp = client.get(
        "/pos/orders",
        params={"branch_id": branch_id},
        headers=auth_headers(cashier_user_id),
    )
    assert list_resp.status_code == 200, list_resp.text
    orders = list_resp.json()
    assert len(orders) == 1
    assert orders[0]["status"] == "CREATED"
    assert Decimal(orders[0]["total"]) == Decimal("28.50")

    detail_resp = client.get(
        f"/pos/orders/{order['id']}",
        headers=auth_headers(cashier_user_id),
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail = detail_resp.json()
    assert detail["id"] == order["id"]
    assert len(detail["items"]) == 1
    assert detail["items"][0]["sku"] == "BREAD-BOL"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order tests",
)
def test_create_order_rejects_input_product():
    alembic_upgrade_head()

    s = SessionLocal()
    try:
        reset_db(s)
        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")

        branch_id = seed_branch(s, "MAIN", "Main Branch")
        _admin_user_id = seed_user(
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
            code="INGREDIENTS",
            name="Ingredients",
            quick_name="Ingredients",
            show_in_pos=True,
            default_pos_order=10,
        )
        input_product_id = seed_product(
            s,
            category_id=category_id,
            sku="FLOUR",
            name="Wheat Flour",
            quick_name="Flour",
            sale_price=None,
            on_hand_branch_id=branch_id,
            on_hand=Decimal("50.000"),
            is_input=True,
            show_in_pos=True,
            is_sellable_in_pos=True,
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "items": [
                {"product_id": input_product_id, "qty": "2.000"},
            ],
        },
        headers=auth_headers(cashier_user_id),
    )
    assert resp.status_code == 400, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_VALIDATION_ERROR"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order tests",
)
def test_order_lifecycle_send_ready_manual_deliver_is_admin_only():
    alembic_upgrade_head()

    s = SessionLocal()
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
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="BREAD-BAG",
            name="Baguette",
            quick_name="Baguette",
            sale_price=Decimal("25.00"),
            on_hand_branch_id=branch_id,
            on_hand=Decimal("20.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "customer_name": "Maria",
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=auth_headers(cashier_user_id),
    )
    assert create_resp.status_code == 200, create_resp.text
    order_id = create_resp.json()["id"]

    sent_resp = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    assert sent_resp.status_code == 200, sent_resp.text
    sent = sent_resp.json()
    assert sent["status"] == "SENT_TO_BAKERY"
    assert sent["sent_to_bakery_by_id"] == admin_user_id
    assert sent["sent_to_bakery_at"] is not None

    ready_resp = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=auth_headers(baker_user_id),
    )
    assert ready_resp.status_code == 200, ready_resp.text
    ready = ready_resp.json()
    assert ready["status"] == "READY"
    assert ready["ready_by_id"] == baker_user_id
    assert ready["ready_at"] is not None

    cashier_deliver_resp = client.post(
        f"/pos/orders/{order_id}/deliver",
        json={
            "confirm_without_sale": True,
            "reason": "Cashier should not use manual delivery route.",
        },
        headers=auth_headers(cashier_user_id),
    )
    assert cashier_deliver_resp.status_code == 403, cashier_deliver_resp.text

    admin_deliver_resp = client.post(
        f"/pos/orders/{order_id}/deliver",
        json={
            "confirm_without_sale": True,
            "reason": "Order settled outside POS under administrative approval.",
        },
        headers=auth_headers(admin_user_id),
    )
    assert admin_deliver_resp.status_code == 200, admin_deliver_resp.text
    delivered = admin_deliver_resp.json()

    assert delivered["status"] == "DELIVERED"
    assert delivered["delivered_by_id"] == admin_user_id
    assert delivered["delivered_at"] is not None
    assert delivered["delivered_sale_id"] is None
    assert delivered["note"] is not None
    assert "[MANUAL_DELIVERY_WITHOUT_SALE]" in delivered["note"]


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order tests",
)
def test_manual_deliver_requires_explicit_acknowledgement_payload():
    alembic_upgrade_head()

    s = SessionLocal()
    try:
        reset_db(s)
        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        baker_role_id = seed_role(s, "BAKER", "Baker")

        branch_id = seed_branch(s, "MAIN", "Main Branch")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
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
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
            on_hand_branch_id=branch_id,
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=auth_headers(admin_user_id),
    )
    assert create_resp.status_code == 200, create_resp.text
    order_id = create_resp.json()["id"]

    sent_resp = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(admin_user_id),
    )
    assert sent_resp.status_code == 200, sent_resp.text

    ready_resp = client.post(
        f"/pos/orders/{order_id}/ready",
        headers=auth_headers(baker_user_id),
    )
    assert ready_resp.status_code == 200, ready_resp.text

    invalid_resp = client.post(
        f"/pos/orders/{order_id}/deliver",
        json={
            "confirm_without_sale": False,
            "reason": "Invalid acknowledgement flag.",
        },
        headers=auth_headers(admin_user_id),
    )
    assert invalid_resp.status_code == 422, invalid_resp.text


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order tests",
)
def test_order_cancel_and_invalid_transition_after_cancel():
    alembic_upgrade_head()

    s = SessionLocal()
    try:
        reset_db(s)
        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")

        branch_id = seed_branch(s, "MAIN", "Main Branch")
        _admin_user_id = seed_user(
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
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
            on_hand_branch_id=branch_id,
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_id,
            "items": [{"product_id": product_id, "qty": "5.000"}],
        },
        headers=auth_headers(cashier_user_id),
    )
    assert create_resp.status_code == 200, create_resp.text
    order_id = create_resp.json()["id"]

    cancel_resp = client.post(
        f"/pos/orders/{order_id}/cancel",
        headers=auth_headers(cashier_user_id),
    )
    assert cancel_resp.status_code == 200, cancel_resp.text
    canceled = cancel_resp.json()
    assert canceled["status"] == "CANCELED"
    assert canceled["canceled_by_id"] == cashier_user_id
    assert canceled["canceled_at"] is not None

    invalid_resp = client.post(
        f"/pos/orders/{order_id}/send-to-bakery",
        headers=auth_headers(cashier_user_id),
    )
    assert invalid_resp.status_code == 403 or invalid_resp.status_code == 409
    if invalid_resp.status_code == 409:
        payload = invalid_resp.json()
        assert payload["error"]["code"] == "DOMAIN_CONFLICT"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS order tests",
)
def test_order_scope_blocks_other_branch_cashier():
    alembic_upgrade_head()

    s = SessionLocal()
    try:
        reset_db(s)
        admin_role_id = seed_role(s, "ADMIN", "Administrator")
        cashier_role_id = seed_role(s, "CASHIER", "Cashier")

        branch_1_id = seed_branch(s, "MAIN", "Main Branch")
        branch_2_id = seed_branch(s, "AUX", "Aux Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_1_id,
            role_id=admin_role_id,
            email="admin@example.com",
            full_name="Admin User",
        )
        other_branch_cashier_id = seed_user(
            s,
            branch_id=branch_2_id,
            role_id=cashier_role_id,
            email="cashier.other@example.com",
            full_name="Other Branch Cashier",
        )

        category_id = seed_category(
            s,
            code="BREAD",
            name="Bread",
            quick_name="Bread",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="BREAD-BOL",
            name="Bolillo",
            quick_name="Bolillo",
            sale_price=Decimal("8.00"),
            on_hand_branch_id=branch_1_id,
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    create_resp = client.post(
        "/pos/orders",
        json={
            "branch_id": branch_1_id,
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=auth_headers(admin_user_id),
    )
    assert create_resp.status_code == 200, create_resp.text
    order_id = create_resp.json()["id"]

    detail_resp = client.get(
        f"/pos/orders/{order_id}",
        headers=auth_headers(other_branch_cashier_id),
    )
    assert detail_resp.status_code == 403, detail_resp.text

    deliver_resp = client.post(
        f"/pos/orders/{order_id}/deliver",
        json={
            "confirm_without_sale": True,
            "reason": "Cross-branch cashier must not deliver manually.",
        },
        headers=auth_headers(other_branch_cashier_id),
    )
    assert deliver_resp.status_code == 403, deliver_resp.text
