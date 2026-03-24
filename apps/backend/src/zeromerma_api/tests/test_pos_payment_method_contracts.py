from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from zeromerma_api.tests.auth_helpers import build_auth_headers
from zeromerma_api.tests.support.db import reset_pos_core_tables
from zeromerma_api.tests.support.seeders import (
    create_ready_order,
    open_cash_session,
    seed_branch,
    seed_category,
    seed_price_override,
    seed_product,
    seed_role,
    seed_user,
)


def test_checkout_accepts_transfer_payment(
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
        code="FINISHED",
        name="Finished Goods",
        quick_name="Finished",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("25.000"),
        sku="SKU-TR-CHECKOUT",
        name="Transfer Checkout Product",
        sale_price=Decimal("40.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=admin_user_id,
        role_code="ADMIN",
    )

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
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
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
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert sale_detail.status_code == 200, sale_detail.text
    detail_payload = sale_detail.json()
    assert detail_payload["payments"][0]["method"] == "TRANSFER"
    assert detail_payload["payments"][0]["reference"] == "TRX-CHK-001"


def test_add_payment_accepts_transfer_method(
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
        code="FINISHED",
        name="Finished Goods",
        quick_name="Finished",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("25.000"),
        sku="SKU-TR-PAYMENT",
        name="Transfer Payment Product",
        sale_price=Decimal("25.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=admin_user_id,
        role_code="ADMIN",
    )

    sale_response = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000", "unit_price": "25.00"}],
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert sale_response.status_code == 200, sale_response.text
    sale_id = int(sale_response.json()["id"])

    payment_response = client.post(
        f"/pos/sales/{sale_id}/payments",
        json={"method": "TRANSFER", "amount": "25.00", "reference": "TRX-SALE-001"},
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert payment_response.status_code == 200, payment_response.text
    payment_payload = payment_response.json()

    assert payment_payload["method"] == "TRANSFER"
    assert Decimal(payment_payload["amount"]) == Decimal("25.00")
    assert payment_payload["reference"] == "TRX-SALE-001"


def test_order_delivery_checkout_accepts_transfer_payment(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")

    admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )
    cashier_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    category_id = seed_category(
        db_session,
        code="FINISHED",
        name="Finished Goods",
        quick_name="Finished",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("25.000"),
        sku="SKU-TR-ORDER",
        name="Transfer Order Product",
        sale_price=Decimal("20.00"),
    )
    seed_price_override(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
        price=Decimal("27.00"),
        created_by_id=admin_user_id,
    )

    order_id = create_ready_order(
        client,
        branch_id=branch_id,
        admin_user_id=admin_user_id,
        cashier_user_id=cashier_user_id,
        product_id=product_id,
    )
    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_user_id,
        role_code="CASHIER",
    )

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
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
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
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert order_detail.status_code == 200, order_detail.text
    assert order_detail.json()["delivered_sale_id"] == payload["sale_id"]

    sale_detail = client.get(
        f"/pos/sales/{payload['sale_id']}",
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert sale_detail.status_code == 200, sale_detail.text
    assert sale_detail.json()["payments"][0]["method"] == "TRANSFER"
