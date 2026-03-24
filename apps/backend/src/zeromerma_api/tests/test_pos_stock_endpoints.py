from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.tests.auth_helpers import build_auth_headers
from zeromerma_api.tests.support.db import reset_pos_core_tables
from zeromerma_api.tests.support.seeders import (
    seed_branch,
    seed_category,
    seed_product,
    seed_role,
    seed_user,
)


def _read_on_hand(session: Session, *, branch_id: int, product_id: int) -> Decimal:
    value = session.execute(
        text(
            """
            SELECT on_hand
            FROM inventory_balance
            WHERE branch_id = :branch_id
              AND product_id = :product_id
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
        },
    ).scalar_one()
    return Decimal(str(value))


def _movement_count_for_reason(
    session: Session,
    *,
    branch_id: int,
    product_id: int,
    reason: str,
) -> int:
    value = session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM inventory_movement
            WHERE branch_id = :branch_id
              AND product_id = :product_id
              AND reason = :reason
            """
        ),
        {
            "branch_id": int(branch_id),
            "product_id": int(product_id),
            "reason": reason,
        },
    ).scalar_one()
    return int(value)


def test_admin_can_register_finished_goods_stock_and_make_it_immediately_sellable(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )

    category_id = seed_category(
        db_session,
        code="BREAD",
        name="Bread",
        quick_name="Bread",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("0.000"),
        sku="FG-001",
        name="Bolillo",
        sale_price=Decimal("8.00"),
        is_input=False,
        is_sellable_in_pos=True,
    )

    response = client.post(
        "/pos/stock/finished-goods",
        json={
            "branch_id": branch_id,
            "items": [{"product_id": product_id, "qty": "12.000"}],
            "note": "Fresh batch out of oven.",
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["branch_id"] == branch_id
    assert payload["applied_count"] == 1
    assert payload["audit_event_id"] > 0
    assert payload["note"] == "Fresh batch out of oven."
    assert len(payload["items"]) == 1
    assert payload["items"][0]["product_id"] == product_id
    assert Decimal(payload["items"][0]["qty_added"]) == Decimal("12.000")
    assert Decimal(payload["items"][0]["new_on_hand"]) == Decimal("12.000")

    assert _read_on_hand(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
    ) == Decimal("12.000")

    assert (
        _movement_count_for_reason(
            db_session,
            branch_id=branch_id,
            product_id=product_id,
            reason="POS_FINISHED_GOODS_STOCK_IN",
        )
        == 1
    )


def test_cashier_can_register_finished_goods_stock(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    cashier_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    category_id = seed_category(
        db_session,
        code="DONUTS",
        name="Donuts",
        quick_name="Donuts",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("3.000"),
        sku="FG-002",
        name="Glazed Donut",
        sale_price=Decimal("20.00"),
        is_input=False,
        is_sellable_in_pos=True,
    )

    response = client.post(
        "/pos/stock/finished-goods",
        json={
            "branch_id": branch_id,
            "items": [{"product_id": product_id, "qty": "5.000"}],
        },
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text

    assert _read_on_hand(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
    ) == Decimal("8.000")


def test_baker_cannot_register_finished_goods_stock(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    baker_role_id = seed_role(db_session, code="BAKER", name="Baker")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    baker_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=baker_role_id,
        email="baker@example.com",
        full_name="Baker User",
    )

    category_id = seed_category(
        db_session,
        code="BREAD",
        name="Bread",
        quick_name="Bread",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("0.000"),
        sku="FG-003",
        name="Telera",
        sale_price=Decimal("8.00"),
        is_input=False,
        is_sellable_in_pos=True,
    )

    response = client.post(
        "/pos/stock/finished-goods",
        json={
            "branch_id": branch_id,
            "items": [{"product_id": product_id, "qty": "2.000"}],
        },
        headers=build_auth_headers(
            user_id=baker_user_id,
            role_code="BAKER",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "DOMAIN_FORBIDDEN"


def test_pos_stock_rejects_inputs_and_non_sellable_products(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )

    category_id = seed_category(
        db_session,
        code="BASE",
        name="Base",
        quick_name="Base",
    )

    input_product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("5.000"),
        sku="INPUT-001",
        name="Harina",
        sale_price=None,
        is_input=True,
        is_sellable_in_pos=False,
    )

    hidden_product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("0.000"),
        sku="FG-HIDDEN-001",
        name="Hidden Product",
        sale_price=Decimal("10.00"),
        is_input=False,
        is_sellable_in_pos=False,
    )

    response = client.post(
        "/pos/stock/finished-goods",
        json={
            "branch_id": branch_id,
            "items": [
                {"product_id": input_product_id, "qty": "1.000"},
                {"product_id": hidden_product_id, "qty": "1.000"},
            ],
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 409, response.text
    payload = response.json()

    assert payload["error"]["code"] == "DOMAIN_CONFLICT"
    assert (
        payload["error"]["message"]
        == "Only active POS-sellable finished goods can be registered through the POS stock endpoint."
    )
