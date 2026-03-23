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
    Hard reset all tables touched by reprint tests.

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


def seed_roles(s: Session) -> dict[str, int]:
    """
    Seed ADMIN and CASHIER roles.
    """
    admin_role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('ADMIN', 'Administrator', now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    cashier_role_id = s.execute(
        text(
            """
            INSERT INTO role (code, name, created_at, updated_at)
            VALUES ('CASHIER', 'Cashier', now(), now())
            RETURNING id
            """
        )
    ).scalar_one()

    s.commit()
    return {
        "admin_role_id": int(admin_role_id),
        "cashier_role_id": int(cashier_role_id),
    }


def seed_branch(
    s: Session,
    *,
    code: str,
    name: str,
) -> int:
    """
    Seed one active branch.
    """
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
    """
    Seed one active user.
    """
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
    is_active: bool = True,
) -> int:
    """
    Seed one POS-visible category.
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
    on_hand_branch_id: int,
    on_hand: Decimal,
    is_input: bool = False,
    show_in_pos: bool = True,
    is_sellable_in_pos: bool = True,
    default_pos_order: int = 10,
    is_active: bool = True,
    uom: str = "PCS",
) -> int:
    """
    Seed one product and one inventory_balance row for one branch.
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


def create_checkout_sale(
    client: TestClient,
    *,
    branch_id: int,
    cash_session_id: int,
    user_id: int,
    product_id: int,
    qty: str,
    method: str,
    amount_tendered: str | None = None,
    reference: str | None = None,
    external_auth_code: str | None = None,
    print_ticket: bool = True,
) -> dict[str, Any]:
    """
    Create one sale through POST /pos/checkout and return the response payload.
    """
    resp = client.post(
        "/pos/checkout",
        json=build_checkout_payload(
            branch_id=branch_id,
            cash_session_id=cash_session_id,
            product_id=product_id,
            qty=qty,
            method=method,
            amount_tendered=amount_tendered,
            reference=reference,
            external_auth_code=external_auth_code,
            print_ticket=print_ticket,
        ),
        headers=auth_headers(user_id),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS reprint tests",
)
def test_reprint_uses_snapshot_when_present():
    """
    When checkout persisted a receipt_snapshot, reprint must return source=SNAPSHOT.
    """
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        roles = seed_roles(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=roles["admin_role_id"],
            email="admin@example.com",
            full_name="Admin User",
        )
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
            on_hand_branch_id=branch_id,
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=admin_user_id,
    )

    checkout = create_checkout_sale(
        client,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        user_id=admin_user_id,
        product_id=product_id,
        qty="2.000",
        method="CASH",
        amount_tendered="36.00",
        reference="CASH-REPRINT-SNAPSHOT",
    )
    sale_id = int(checkout["sale_id"])

    resp = client.post(
        f"/pos/sales/{sale_id}/reprint",
        headers=auth_headers(admin_user_id),
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert payload["sale_id"] == sale_id
    assert payload["source"] == "SNAPSHOT"
    assert payload["reprint_count"] == 1

    receipt = payload["receipt"]
    assert receipt["sale_id"] == sale_id
    assert receipt["payment_method"] == "CASH"
    assert Decimal(receipt["amount_tendered"]) == Decimal("36.00")
    assert Decimal(receipt["change_due"]) == Decimal("0.00")
    assert Decimal(receipt["subtotal"]) == Decimal("36.00")
    assert Decimal(receipt["tax"]) == Decimal("0.00")
    assert Decimal(receipt["total"]) == Decimal("36.00")

    assert len(receipt["items"]) == 1
    line = receipt["items"][0]
    assert line["sku"] == "DONUT-GLA"
    assert line["name"] == "Donut Glazed"
    assert line["quick_name"] == "Glazed"
    assert Decimal(line["qty"]) == Decimal("2.000")
    assert Decimal(line["unit_price"]) == Decimal("18.00")
    assert Decimal(line["line_total"]) == Decimal("36.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS reprint tests",
)
def test_reprint_falls_back_to_reconstructed_when_snapshot_missing():
    """
    When receipt_snapshot is NULL, reprint must reconstruct a valid payload.
    """
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        roles = seed_roles(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=roles["admin_role_id"],
            email="admin@example.com",
            full_name="Admin User",
        )
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
            on_hand_branch_id=branch_id,
            on_hand=Decimal("30.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=admin_user_id,
    )

    checkout = create_checkout_sale(
        client,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        user_id=admin_user_id,
        product_id=product_id,
        qty="1.000",
        method="CARD",
        reference="CARD-REPRINT-FALLBACK",
        external_auth_code="AUTH-REPRINT",
        print_ticket=False,
    )
    sale_id = int(checkout["sale_id"])

    s2: Session = SessionLocal()
    try:
        s2.execute(
            text(
                """
                UPDATE sale
                SET receipt_snapshot = NULL,
                    updated_at = now()
                WHERE id = :sale_id
                """
            ),
            {"sale_id": sale_id},
        )
        s2.commit()
    finally:
        s2.close()

    resp = client.post(
        f"/pos/sales/{sale_id}/reprint",
        headers=auth_headers(admin_user_id),
    )
    assert resp.status_code == 200, resp.text

    payload = resp.json()
    assert payload["sale_id"] == sale_id
    assert payload["source"] == "RECONSTRUCTED"
    assert payload["reprint_count"] == 1

    receipt = payload["receipt"]
    assert receipt["sale_id"] == sale_id
    assert receipt["payment_method"] == "CARD"
    assert receipt["amount_tendered"] is None
    assert Decimal(receipt["change_due"]) == Decimal("0.00")
    assert Decimal(receipt["subtotal"]) == Decimal("35.00")
    assert Decimal(receipt["tax"]) == Decimal("0.00")
    assert Decimal(receipt["total"]) == Decimal("35.00")

    assert len(receipt["items"]) == 1
    line = receipt["items"][0]
    assert line["sku"] == "COFFEE-AM"
    assert line["name"] == "Coffee Americano"
    assert line["quick_name"] == "Americano"
    assert Decimal(line["qty"]) == Decimal("1.000")
    assert Decimal(line["unit_price"]) == Decimal("35.00")
    assert Decimal(line["line_total"]) == Decimal("35.00")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS reprint tests",
)
def test_reprint_enforces_sale_branch_scope_for_non_admin_user():
    """
    A non-admin user from another branch must not be allowed to reprint the sale.
    """
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        roles = seed_roles(s)

        branch_1_id = seed_branch(s, code="MAIN", name="Main Branch")
        branch_2_id = seed_branch(s, code="AUX", name="Aux Branch")

        admin_user_id = seed_user(
            s,
            branch_id=branch_1_id,
            role_id=roles["admin_role_id"],
            email="admin@example.com",
            full_name="Admin User",
        )
        cashier_other_branch_id = seed_user(
            s,
            branch_id=branch_2_id,
            role_id=roles["cashier_role_id"],
            email="cashier.other@example.com",
            full_name="Other Branch Cashier",
        )

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
            on_hand_branch_id=branch_1_id,
            on_hand=Decimal("50.000"),
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_1_id,
        user_id=admin_user_id,
    )

    checkout = create_checkout_sale(
        client,
        branch_id=branch_1_id,
        cash_session_id=cash_session_id,
        user_id=admin_user_id,
        product_id=product_id,
        qty="1.000",
        method="CASH",
        amount_tendered="18.00",
    )
    sale_id = int(checkout["sale_id"])

    resp = client.post(
        f"/pos/sales/{sale_id}/reprint",
        headers=auth_headers(cashier_other_branch_id),
    )
    assert resp.status_code == 403, resp.text

    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_FORBIDDEN"


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping POS reprint tests",
)
def test_reprint_sale_not_found_returns_404():
    """
    Reprinting a missing sale must return 404.
    """
    alembic_upgrade_head()

    s: Session = SessionLocal()
    try:
        reset_db(s)

        roles = seed_roles(s)
        branch_id = seed_branch(s, code="MAIN", name="Main Branch")
        admin_user_id = seed_user(
            s,
            branch_id=branch_id,
            role_id=roles["admin_role_id"],
            email="admin@example.com",
            full_name="Admin User",
        )
    finally:
        s.close()

    app = create_app()
    client = TestClient(app)

    resp = client.post(
        "/pos/sales/999999/reprint",
        headers=auth_headers(admin_user_id),
    )
    assert resp.status_code == 404, resp.text

    payload = resp.json()
    assert payload["error"]["code"] == "DOMAIN_NOT_FOUND"
