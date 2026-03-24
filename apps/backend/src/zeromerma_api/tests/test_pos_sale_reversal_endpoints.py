from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import text
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
        {"branch_id": int(branch_id), "product_id": int(product_id)},
    ).scalar_one()
    return Decimal(str(value))


def test_void_open_unpaid_sale_restores_inventory_and_marks_voided(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    user_id = seed_user(
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
        sku="VOID-001",
        name="Voidable Product",
        sale_price=Decimal("15.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=user_id,
        role_code="ADMIN",
    )

    create_response = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "2.000", "unit_price": "15.00"}],
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert create_response.status_code == 200, create_response.text
    sale_id = int(create_response.json()["id"])

    assert _read_on_hand(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
    ) == Decimal("8.000")

    void_response = client.post(
        f"/pos/sales/{sale_id}/void",
        json={"reason": "Operator canceled before collecting payment."},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert void_response.status_code == 200, void_response.text
    payload = void_response.json()

    assert payload["sale_id"] == sale_id
    assert payload["status"] == "VOIDED"
    assert payload["reversal_kind"] == "VOID"
    assert payload["voided_by_id"] == user_id
    assert payload["voided_at"] is not None
    assert payload["reversal_reason"] == "Operator canceled before collecting payment."
    assert payload["reversal_snapshot"]["payment_reversal"] == "NONE"

    assert _read_on_hand(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
    ) == Decimal("10.000")

    detail_response = client.get(
        f"/pos/sales/{sale_id}",
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert detail["status"] == "VOIDED"
    assert Decimal(detail["paid_amount"]) == Decimal("0.00")
    assert Decimal(detail["balance_due"]) == Decimal("0.00")


def test_refund_paid_sale_creates_negative_payments_restores_inventory_and_nets_cash_session(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    user_id = seed_user(
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
        sku="REFUND-001",
        name="Refundable Product",
        sale_price=Decimal("20.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=user_id,
        role_code="ADMIN",
    )

    checkout_response = client.post(
        "/pos/checkout",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000"}],
            "payment": {
                "method": "CARD",
                "reference": "AUTH-REFUND-001",
            },
            "print_ticket": False,
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert checkout_response.status_code == 200, checkout_response.text
    sale_id = int(checkout_response.json()["sale_id"])

    assert _read_on_hand(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
    ) == Decimal("9.000")

    refund_response = client.post(
        f"/pos/sales/{sale_id}/refund",
        json={"reason": "Customer returned item same day."},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert refund_response.status_code == 200, refund_response.text
    payload = refund_response.json()

    assert payload["sale_id"] == sale_id
    assert payload["status"] == "REFUNDED"
    assert payload["reversal_kind"] == "REFUND"
    assert payload["refunded_by_id"] == user_id
    assert payload["refunded_at"] is not None
    assert payload["reversal_reason"] == "Customer returned item same day."
    assert len(payload["reversal_snapshot"]["mirrored_refund_payments"]) == 1

    assert _read_on_hand(
        db_session,
        branch_id=branch_id,
        product_id=product_id,
    ) == Decimal("10.000")

    detail_response = client.get(
        f"/pos/sales/{sale_id}",
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()

    assert detail["status"] == "REFUNDED"
    assert len(detail["payments"]) == 2
    assert Decimal(detail["payments"][0]["amount"]) == Decimal("20.00")
    assert Decimal(detail["payments"][1]["amount"]) == Decimal("-20.00")
    assert Decimal(detail["paid_amount"]) == Decimal("0.00")
    assert Decimal(detail["balance_due"]) == Decimal("0.00")

    close_response = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={"closing_amount": "1000.00"},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert close_response.status_code == 200, close_response.text
    closed = close_response.json()

    snapshot = closed["reconciliation_snapshot"]
    assert snapshot["expected_payment_totals_by_method"] == {
        "cash": "0.00",
        "card": "0.00",
        "transfer": "0.00",
        "other": "0.00",
    }
    assert Decimal(closed["expected_cash"]) == Decimal("1000.00")


def test_void_rejects_sale_with_payments_and_refund_rejects_non_paid_sale(
    db_session: Session,
    client: TestClient,
) -> None:
    reset_pos_core_tables(db_session)

    admin_role_id = seed_role(db_session, code="ADMIN", name="Administrator")
    branch_id = seed_branch(db_session, code="MAIN", name="Main Branch")
    user_id = seed_user(
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
        sku="BLOCK-001",
        name="Blocked Reversal Product",
        sale_price=Decimal("12.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=user_id,
        role_code="ADMIN",
    )

    open_sale_response = client.post(
        "/pos/sales",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000", "unit_price": "12.00"}],
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert open_sale_response.status_code == 200, open_sale_response.text
    open_sale_id = int(open_sale_response.json()["id"])

    add_payment_response = client.post(
        f"/pos/sales/{open_sale_id}/payments",
        json={"method": "CASH", "amount": "5.00", "reference": "PARTIAL-001"},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert add_payment_response.status_code == 200, add_payment_response.text

    void_response = client.post(
        f"/pos/sales/{open_sale_id}/void",
        json={"reason": "Should fail because payment exists."},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert void_response.status_code == 409, void_response.text
    assert void_response.json()["error"]["code"] == "DOMAIN_CONFLICT"

    refund_response = client.post(
        f"/pos/sales/{open_sale_id}/refund",
        json={"reason": "Should fail because sale is not PAID."},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert refund_response.status_code == 409, refund_response.text
    assert refund_response.json()["error"]["code"] == "DOMAIN_CONFLICT"
