from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from zeromerma_api.tests.auth_helpers import build_auth_headers
from zeromerma_api.tests.support.db import reset_pos_core_tables
from zeromerma_api.tests.support.seeders import (
    open_cash_session,
    seed_branch,
    seed_category,
    seed_product,
    seed_role,
    seed_user,
)


def test_cashier_cannot_close_another_cashiers_session(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")

    _admin_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=admin_role_id,
        email="admin@example.com",
        full_name="Admin User",
    )
    cashier_one_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier.one@example.com",
        full_name="Cashier One",
    )
    cashier_two_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier.two@example.com",
        full_name="Cashier Two",
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_one_id,
        role_code="CASHIER",
    )

    response = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "1000.00"},
        headers=build_auth_headers(
            user_id=cashier_two_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 403, response.text

    payload = response.json()
    assert payload["error"]["code"] == "DOMAIN_FORBIDDEN"
    assert payload["error"]["message"] == ("Cashier can only close the cash session they opened.")


def test_cashier_can_close_own_session(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    cashier_role_id = seed_role(db_session, code="CASHIER", name="Cashier")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    cashier_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_id,
        role_code="CASHIER",
    )

    response = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "1000.00"},
        headers=build_auth_headers(
            user_id=cashier_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["status"] == "CLOSED"
    assert payload["closed_by_id"] == cashier_id


def test_admin_can_close_cashier_session(
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
    cashier_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=cashier_id,
        role_code="CASHIER",
    )

    response = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "1000.00"},
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["status"] == "CLOSED"
    assert payload["closed_by_id"] == admin_user_id


def test_cashier_cannot_void_or_refund_sales(
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
        on_hand=Decimal("20.000"),
        sku="RBAC-001",
        name="RBAC Product",
        sale_price=Decimal("20.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=admin_user_id,
        role_code="ADMIN",
    )

    open_sale_response = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000", "unit_price": "20.00"}],
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert open_sale_response.status_code == 200, open_sale_response.text
    open_sale_id = int(open_sale_response.json()["id"])

    checkout_response = client.post(
        "/pos/checkout",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000"}],
            "payment": {
                "method": "CARD",
                "reference": "RBAC-CARD-001",
            },
            "print_ticket": False,
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert checkout_response.status_code == 200, checkout_response.text
    paid_sale_id = int(checkout_response.json()["sale_id"])

    void_response = client.post(
        f"/pos/sales/{open_sale_id}/void",
        json={"reason": "Cashier should not be able to void sales."},
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert void_response.status_code == 403, void_response.text
    assert void_response.json()["error"]["code"] == "DOMAIN_FORBIDDEN"

    refund_response = client.post(
        f"/pos/sales/{paid_sale_id}/refund",
        json={"reason": "Cashier should not be able to refund sales."},
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert refund_response.status_code == 403, refund_response.text
    assert refund_response.json()["error"]["code"] == "DOMAIN_FORBIDDEN"
