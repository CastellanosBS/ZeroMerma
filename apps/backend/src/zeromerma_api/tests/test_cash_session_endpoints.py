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


def test_cash_session_open_close_flow_persists_empty_reconciliation(
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

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=user_id,
        role_code="ADMIN",
    )

    current_response = client.get(
        "/pos/cash-sessions/current",
        params={"branch_id": branch_id},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert current_response.status_code == 200, current_response.text
    current_payload = current_response.json()

    assert current_payload["id"] == cash_session_id
    assert current_payload["status"] == "OPEN"
    assert current_payload["expected_cash"] is None
    assert current_payload["reconciliation_snapshot"] is None

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

    assert closed["status"] == "CLOSED"
    assert closed["closed_by_id"] == user_id
    assert Decimal(closed["opening_amount"]) == Decimal("1000.00")
    assert Decimal(closed["closing_amount"]) == Decimal("1000.00")
    assert Decimal(closed["expected_cash"]) == Decimal("1000.00")

    snapshot = closed["reconciliation_snapshot"]
    assert snapshot is not None
    assert Decimal(snapshot["expected_cash"]) == Decimal("1000.00")
    assert Decimal(snapshot["counted_cash"]) == Decimal("1000.00")
    assert Decimal(snapshot["cash_difference"]) == Decimal("0.00")
    assert Decimal(snapshot["total_expected_non_cash"]) == Decimal("0.00")
    assert Decimal(snapshot["total_counted_non_cash"]) == Decimal("0.00")
    assert Decimal(snapshot["total_difference"]) == Decimal("0.00")
    assert snapshot["assumed_counted_non_cash_methods"] == []
    assert snapshot["note"] is None

    assert snapshot["expected_payment_totals_by_method"] == {
        "cash": "0.00",
        "card": "0.00",
        "transfer": "0.00",
        "other": "0.00",
    }

    reopen_response = client.post(
        "/pos/cash-sessions/open",
        json={"branch_id": branch_id, "opening_amount": "0.00"},
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert reopen_response.status_code == 200, reopen_response.text
    assert reopen_response.json()["status"] == "OPEN"


def test_cash_session_close_reconciles_cash_and_card_payments(
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
        code="DONUTS",
        name="Donuts",
        quick_name="Donuts",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("25.000"),
        sku="DONUT-GLA",
        name="Glazed Donut",
        sale_price=Decimal("20.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=user_id,
        role_code="ADMIN",
    )

    cash_checkout_response = client.post(
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
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert cash_checkout_response.status_code == 200, cash_checkout_response.text

    card_checkout_response = client.post(
        "/pos/checkout",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000"}],
            "payment": {
                "method": "CARD",
                "reference": "AUTH-001",
            },
            "print_ticket": False,
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert card_checkout_response.status_code == 200, card_checkout_response.text

    close_response = client.post(
        f"/pos/cash-sessions/{cash_session_id}/close",
        json={
            "closing_amount": "1020.00",
            "counted_card_total": "20.00",
            "note": "Shift close matched card voucher total.",
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert close_response.status_code == 200, close_response.text
    closed = close_response.json()

    assert closed["status"] == "CLOSED"
    assert Decimal(closed["expected_cash"]) == Decimal("1020.00")
    assert Decimal(closed["closing_amount"]) == Decimal("1020.00")

    snapshot = closed["reconciliation_snapshot"]
    assert snapshot is not None

    assert snapshot["expected_payment_totals_by_method"] == {
        "cash": "20.00",
        "card": "20.00",
        "transfer": "0.00",
        "other": "0.00",
    }

    assert snapshot["expected_non_cash_totals_by_method"] == {
        "card": "20.00",
        "transfer": "0.00",
        "other": "0.00",
    }

    assert snapshot["counted_non_cash_totals_by_method"] == {
        "card": "20.00",
        "transfer": "0.00",
        "other": "0.00",
    }

    assert snapshot["non_cash_differences_by_method"] == {
        "card": "0.00",
        "transfer": "0.00",
        "other": "0.00",
    }

    assert Decimal(snapshot["expected_cash"]) == Decimal("1020.00")
    assert Decimal(snapshot["counted_cash"]) == Decimal("1020.00")
    assert Decimal(snapshot["cash_difference"]) == Decimal("0.00")
    assert Decimal(snapshot["total_expected_non_cash"]) == Decimal("20.00")
    assert Decimal(snapshot["total_counted_non_cash"]) == Decimal("20.00")
    assert Decimal(snapshot["total_difference"]) == Decimal("0.00")
    assert snapshot["assumed_counted_non_cash_methods"] == []
    assert snapshot["note"] == "Shift close matched card voucher total."


def test_cash_session_close_can_assume_non_cash_totals_when_omitted(
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
        code="DRINKS",
        name="Drinks",
        quick_name="Drinks",
    )
    product_id = seed_product(
        db_session,
        category_id=category_id,
        branch_id=branch_id,
        on_hand=Decimal("10.000"),
        sku="COFFEE-AM",
        name="Americano",
        sale_price=Decimal("30.00"),
    )

    cash_session_id = open_cash_session(
        client,
        branch_id=branch_id,
        user_id=user_id,
        role_code="ADMIN",
    )

    transfer_checkout_response = client.post(
        "/pos/checkout",
        json={
            "branch_id": branch_id,
            "cash_session_id": cash_session_id,
            "items": [{"product_id": product_id, "qty": "1.000"}],
            "payment": {
                "method": "TRANSFER",
                "reference": "TRX-001",
            },
            "print_ticket": False,
        },
        headers=build_auth_headers(
            user_id=user_id,
            role_code="ADMIN",
            branch_id=branch_id,
        ),
    )
    assert transfer_checkout_response.status_code == 200, transfer_checkout_response.text

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
    assert snapshot is not None
    assert Decimal(closed["expected_cash"]) == Decimal("1000.00")
    assert snapshot["assumed_counted_non_cash_methods"] == ["TRANSFER"]
    assert snapshot["counted_non_cash_totals_by_method"] == {
        "card": "0.00",
        "transfer": "30.00",
        "other": "0.00",
    }
    assert Decimal(snapshot["total_difference"]) == Decimal("0.00")
