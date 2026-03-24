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


def test_checkout_and_cash_close_generate_audit_events(
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
        on_hand=Decimal("10.000"),
        sku="AUDIT-001",
        name="Audit Product",
        sale_price=Decimal("20.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=admin_user_id,
        role_code="ADMIN",
    )

    checkout_response = client.post(
        "/pos/checkout",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000"}],
            "payment": {
                "method": "CASH",
                "amount_tendered": "20.00",
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
    sale_id = int(checkout_response.json()["sale_id"])

    close_response = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "1020.00"},
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert close_response.status_code == 200, close_response.text

    audit_response = client.get(
        "/pos/audit-events",
        params={"branch_id": branch_id, "limit": 20},
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert audit_response.status_code == 200, audit_response.text
    events = audit_response.json()

    event_types = [event["event_type"] for event in events]
    assert "CASH_SESSION_OPENED" in event_types
    assert "SALE_CHECKOUT_COMPLETED" in event_types
    assert "CASH_SESSION_CLOSED" in event_types

    sale_events = [
        event
        for event in events
        if event["event_type"] == "SALE_CHECKOUT_COMPLETED"
        and event["entity_type"] == "SALE"
        and event["entity_id"] == sale_id
    ]
    assert len(sale_events) == 1
    assert sale_events[0]["payload"]["payment_method"] == "CASH"

    close_events = [
        event
        for event in events
        if event["event_type"] == "CASH_SESSION_CLOSED"
        and event["entity_type"] == "CASH_SESSION"
        and event["entity_id"] == cash_session_id
    ]
    assert len(close_events) == 1
    assert close_events[0]["payload"]["expected_cash"] == "1020.00"


def test_order_delivery_checkout_and_refund_generate_audit_events(
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
        sku="AUDIT-ORDER-001",
        name="Audit Order Product",
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

    deliver_response = client.post(
        f"/pos/orders/{order_id}/deliver-checkout",
        json={
            "cash_session_id": cash_session_id,
            "payment": {
                "method": "TRANSFER",
                "reference": "TRX-AUDIT-001",
            },
            "print_ticket": False,
        },
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert deliver_response.status_code == 200, deliver_response.text
    sale_id = int(deliver_response.json()["sale_id"])

    refund_response = client.post(
        f"/pos/sales/{sale_id}/refund",
        json={"reason": "Customer canceled after transfer verification issue."},
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert refund_response.status_code == 200, refund_response.text

    order_audit_response = client.get(
        "/pos/audit-events",
        params={
            "branch_id": branch_id,
            "entity_type": "CUSTOMER_ORDER",
            "entity_id": order_id,
            "limit": 20,
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert order_audit_response.status_code == 200, order_audit_response.text
    order_events = order_audit_response.json()

    assert len(order_events) == 1
    assert order_events[0]["event_type"] == "ORDER_DELIVERED_VIA_CHECKOUT"
    assert order_events[0]["payload"]["sale_id"] == sale_id

    sale_audit_response = client.get(
        "/pos/audit-events",
        params={
            "branch_id": branch_id,
            "entity_type": "SALE",
            "entity_id": sale_id,
            "limit": 20,
        },
        headers=build_auth_headers(
            user_id=admin_user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert sale_audit_response.status_code == 200, sale_audit_response.text
    sale_events = sale_audit_response.json()

    sale_event_types = [event["event_type"] for event in sale_events]
    assert "SALE_REFUNDED" in sale_event_types


def test_cashier_cannot_read_pos_audit_events(
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
    cashier_user_id = seed_user(
        db_session,
        branch_id=branch_id,
        role_id=cashier_role_id,
        email="cashier@example.com",
        full_name="Cashier User",
    )

    response = client.get(
        "/pos/audit-events",
        params={"branch_id": branch_id},
        headers=build_auth_headers(
            user_id=cashier_user_id,
            role_code="CASHIER",
            branch_id=branch_id,
        ),
    )
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "DOMAIN_FORBIDDEN"
