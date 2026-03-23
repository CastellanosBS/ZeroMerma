from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

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


def reset_db(s: Session) -> None:
    """
    Hard reset all tables touched by checkout tests.

    The order matters due to FK dependencies.
    """
    s.execute(
        text(
            """
            TRUNCATE TABLE
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


def seed_branch_role_user(s: Session) -> dict[str, int]:
    """
    Create one branch, one ADMIN role, and one active admin user.
    """
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
            VALUES ('ADMIN', 'Administrator', now(), now())
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
        {"branch_id": int(branch_id), "role_id": int(role_id)},
    ).scalar_one()

    s.commit()

    return {
        "branch_id": int(branch_id),
        "role_id": int(role_id),
        "user_id": int(user_id),
    }


def seed_category(
    s: Session,
    *,
    code: str,
    name: str,
    quick_name: str,
    show_in_pos: bool,
    default_pos_order: int,
    is_active: bool = True,
) -> int:
    """
    Insert one product category with POS projection fields.
    """
    category_id = s.execute(
        text(
            """
            INSERT INTO product_category
                (code, name, quick_name, show_in_pos, default_pos_order, is_active, created_at, updated_at)
            VALUES
                (:code, :name, :quick_name, :show_in_pos, :default_pos_order, :is_active, now(), now())
            RETURNING id
            """
        ),
        {
            "code": code,
            "name": name,
            "quick_name": quick_name,
            "show_in_pos": bool(show_in_pos),
            "default_pos_order": int(default_pos_order),
            "is_active": bool(is_active),
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
    on_hand: Decimal,
    is_input: bool = False,
    show_in_pos: bool = True,
    is_sellable_in_pos: bool = True,
    default_pos_order: int = 10,
    is_active: bool = True,
    uom: str = "PCS",
) -> int:
    """
    Insert one product plus one inventory_balance row.
    """
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
                    :uom,
                    :is_input,
                    :show_in_pos,
                    :is_sellable_in_pos,
                    :default_pos_order,
                    :sale_price,
                    :is_active,
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
            "uom": uom,
            "is_input": bool(is_input),
            "show_in_pos": bool(show_in_pos),
            "is_sellable_in_pos": bool(is_sellable_in_pos),
            "default_pos_order": int(default_pos_order),
            "sale_price": sale_price,
            "is_active": bool(is_active),
        },
    ).scalar_one()

    s.execute(
        text(
            """
            INSERT INTO inventory_balance
                (branch_id, product_id, on_hand, reserved, created_at, updated_at)
            VALUES
                (1, :product_id, :on_hand, 0.000, now(), now())
            """
        ),
        {
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
    """
    Insert one branch-specific price override.
    """
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
    """
    Open one cash session through the public POS endpoint.
    """
    resp = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": "1000.00"},
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return int(resp.json()["id"])


def close_cash_session(
    client: TestClient,
    *,
    cash_session_id: int,
    user_id: int,
) -> None:
    """
    Close one cash session through the public POS endpoint.
    """
    resp = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "1000.00"},
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text


def build_checkout_payload(
    *,
    branch_id: int,
    cash_session_id: int,
    product_id: int,
    qty: str,
    method: str,
    amount_tendered: str | None = None,
    reference: str | None = None,
    external_auth_code: str | None = None,
    print_ticket: bool = True,
) -> dict[str, Any]:
    """
    Helper to build one checkout request payload.
    """
    payment: dict[str, Any] = {
        "method": method,
    }
    if amount_tendered is not None:
        payment["amount_tendered"] = amount_tendered
    if reference is not None:
        payment["reference"] = reference
    if external_auth_code is not None:
        payment["external_auth_code"] = external_auth_code

    return {
        "branch_id": branch_id,
        "cash_session_id": cash_session_id,
        "items": [{"product_id": product_id, "qty": qty}],
        "payment": payment,
        "print_ticket": print_ticket,
    }


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_cash_exact_amount():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
        category_id = seed_category(
            s,
            code="DONUTS",
            name="Donuts",
            quick_name="Donuts",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="DONUT-GLA",
            name="Donut Glazed",
            quick_name="Glazed",
            sale_price=Decimal("18.00"),
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="2.000",
            method="CASH",
            amount_tendered="36.00",
            reference="CASH-EXACT",
            print_ticket=True,
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["sale_status"] == "PAID"
    assert payload["payment_status"] == "AUTHORIZED"
    assert Decimal(payload["subtotal"]) == Decimal("36.00")
    assert Decimal(payload["tax"]) == Decimal("0.00")
    assert Decimal(payload["total"]) == Decimal("36.00")
    assert Decimal(payload["paid_amount"]) == Decimal("36.00")
    assert Decimal(payload["change_due"]) == Decimal("0.00")
    assert Decimal(payload["balance_due"]) == Decimal("0.00")
    assert payload["print_ticket"] is True

    receipt = payload["receipt"]
    assert receipt["payment_method"] == "CASH"
    assert Decimal(receipt["amount_tendered"]) == Decimal("36.00")
    assert Decimal(receipt["change_due"]) == Decimal("0.00")
    assert Decimal(receipt["total"]) == Decimal("36.00")
    assert len(receipt["items"]) == 1
    assert receipt["items"][0]["sku"] == "DONUT-GLA"
    assert Decimal(receipt["items"][0]["qty"]) == Decimal("2.000")
    assert Decimal(receipt["items"][0]["unit_price"]) == Decimal("18.00")
    assert Decimal(receipt["items"][0]["line_total"]) == Decimal("36.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_cash_with_change():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
        category_id = seed_category(
            s,
            code="DRINKS",
            name="Drinks",
            quick_name="Drinks",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="COFFEE-AM",
            name="Coffee Americano",
            quick_name="Americano",
            sale_price=Decimal("35.00"),
            on_hand=Decimal("30.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="1.000",
            method="CASH",
            amount_tendered="50.00",
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert Decimal(payload["total"]) == Decimal("35.00")
    assert Decimal(payload["paid_amount"]) == Decimal("35.00")
    assert Decimal(payload["change_due"]) == Decimal("15.00")
    assert Decimal(payload["balance_due"]) == Decimal("0.00")

    receipt = payload["receipt"]
    assert receipt["payment_method"] == "CASH"
    assert Decimal(receipt["amount_tendered"]) == Decimal("50.00")
    assert Decimal(receipt["change_due"]) == Decimal("15.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_card_authorized():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
        category_id = seed_category(
            s,
            code="DONUTS",
            name="Donuts",
            quick_name="Donuts",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="DONUT-CHO",
            name="Donut Chocolate",
            quick_name="Chocolate",
            sale_price=Decimal("20.00"),
            on_hand=Decimal("40.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="2.000",
            method="CARD",
            reference="CARD-001",
            external_auth_code="AUTH-XYZ",
            print_ticket=False,
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert payload["sale_status"] == "PAID"
    assert payload["payment_status"] == "AUTHORIZED"
    assert Decimal(payload["total"]) == Decimal("40.00")
    assert Decimal(payload["paid_amount"]) == Decimal("40.00")
    assert Decimal(payload["change_due"]) == Decimal("0.00")
    assert Decimal(payload["balance_due"]) == Decimal("0.00")
    assert payload["print_ticket"] is False

    receipt = payload["receipt"]
    assert receipt["payment_method"] == "CARD"
    assert receipt["amount_tendered"] is None
    assert Decimal(receipt["change_due"]) == Decimal("0.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_rejects_product_not_sellable_in_pos():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
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
            sku="BREAD-HIDDEN",
            name="Hidden Bread",
            quick_name="Hidden",
            sale_price=Decimal("15.00"),
            on_hand=Decimal("10.000"),
            is_sellable_in_pos=False,
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="1.000",
            method="CASH",
            amount_tendered="15.00",
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 400, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_VALIDATION_ERROR"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_rejects_closed_cash_session():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
        category_id = seed_category(
            s,
            code="DONUTS",
            name="Donuts",
            quick_name="Donuts",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="DONUT-GLA",
            name="Donut Glazed",
            quick_name="Glazed",
            sale_price=Decimal("18.00"),
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )
    close_cash_session(
        client,
        cash_session_id=cash_session_id,
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="1.000",
            method="CASH",
            amount_tendered="18.00",
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 409, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_CONFLICT"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_rejects_insufficient_stock():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
        category_id = seed_category(
            s,
            code="DRINKS",
            name="Drinks",
            quick_name="Drinks",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="COFFEE-AM",
            name="Coffee Americano",
            quick_name="Americano",
            sale_price=Decimal("35.00"),
            on_hand=Decimal("1.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="2.000",
            method="CASH",
            amount_tendered="70.00",
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 409, resp.text
    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_CONFLICT"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS checkout tests",
)
def test_checkout_uses_branch_override_price_over_base_price():
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)
        core = seed_branch_role_user(s)
        category_id = seed_category(
            s,
            code="DONUTS",
            name="Donuts",
            quick_name="Donuts",
            show_in_pos=True,
            default_pos_order=10,
        )
        product_id = seed_product(
            s,
            category_id=category_id,
            sku="DONUT-GLA",
            name="Donut Glazed",
            quick_name="Glazed",
            sale_price=Decimal("18.00"),
            on_hand=Decimal("50.000"),
        )
        seed_price_override(
            s,
            branch_id=core["branch_id"],
            product_id=product_id,
            price=Decimal("19.50"),
            created_by_id=core["user_id"],
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=core["branch_id"],
        user_id=core["user_id"],
    )

    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=core["branch_id"],
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty="2.000",
            method="CASH",
            amount_tendered="39.00",
        ),
        headers=auth_headers(core["user_id"]),
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()

    assert Decimal(payload["total"]) == Decimal("39.00")
    assert Decimal(payload["receipt"]["items"][0]["unit_price"]) == Decimal("19.50")
    assert Decimal(payload["receipt"]["items"][0]["line_total"]) == Decimal("39.00")
