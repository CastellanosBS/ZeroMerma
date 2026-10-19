"""Order receipts reconcile across the real POS close and Backoffice projections."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_cash_concurrency import _baseline
from test_cash_concurrency import _setup as setup_concurrent_order
from test_financial_ledger import _reader
from test_financial_ledger import entry as make_entry
from test_financial_ledger import operation as make_operation

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.orders.application.financial_queries import read_order_financial_entries
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _post(client: TestClient, headers: dict[str, str], path: str, body: dict[str, Any]) -> Any:
    response = client.post(
        path, headers={**headers, "Idempotency-Key": new_idempotency_key()}, json=body
    )
    assert response.status_code in {200, 201}, response.json()
    return response.json()


def _setup(client: TestClient, opening: str = "500.00") -> tuple[dict[str, str], dict[str, str]]:
    headers = login_headers(
        client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS"
    )
    opened = _post(
        client,
        headers,
        "/v1/cash-sessions/open",
        {
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": opening,
        },
    )
    return headers, {"workstation_code": SEED_WORKSTATION_CODE, "cash_session_id": opened["id"]}


def _create(
    client: TestClient,
    headers: dict[str, str],
    context: dict[str, str],
    *,
    amount: str = "0.00",
    method: str | None = None,
    legs: list[dict[str, str]] | None = None,
    quantity: str = "2",
) -> Any:
    with SessionLocal() as session:
        product_id = session.scalar(
            select(Product.id).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        )
    return _post(
        client,
        headers,
        "/v1/orders",
        {
            **context,
            "customer_name": "Financial acceptance fixture",
            "requested_for_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "items": [{"product_id": str(product_id), "quantity": quantity}],
            "advance_amount": amount,
            "advance_payment_method_code": method,
            "advance_payments": legs or [],
        },
    )


def _summary(client: TestClient, headers: dict[str, str]) -> Any:
    response = client.get(
        "/v1/cash-close/summary",
        headers=headers,
        params={"workstation_code": SEED_WORKSTATION_CODE},
    )
    assert response.status_code == 200
    return response.json()


def _close(
    client: TestClient, headers: dict[str, str], context: dict[str, str], amount: str
) -> Any:
    return _post(
        client,
        headers,
        "/v1/cash-close/commit",
        {
            **context,
            "close_mode": "WITH_COUNT",
            "counter_empty_confirmed": True,
            "counted_payment_methods": [{"payment_method_code": "CASH", "counted_amount": amount}],
        },
    )


def test_audited_missing_six_pesos_reconciles_to_527_in_pos_and_backoffice(
    client: TestClient,
) -> None:
    headers, context = _setup(client)
    _, class_id = _baseline(context["cash_session_id"], SEED_PRODUCT_BOLILLO_STD_CODE, 7)
    sale = _post(
        client,
        headers,
        "/v1/sales/confirm",
        {
            **context,
            "lines": [
                {"capture_mode": "CLASS_CAPTURE", "product_class_id": class_id, "quantity": "7"}
            ],
            "payments": [{"payment_method_code": "CASH", "tendered_amount": "21.00"}],
        },
    )
    assert sale["total_amount"] == "21.00"
    order = _create(client, headers, context)
    _post(client, headers, f"/v1/orders/{order['id']}/mark-ready", context)
    payment_body = {
        **context,
        "settlement_amount": "6.00",
        "settlement_payment_method_code": "CASH",
    }
    key = new_idempotency_key()
    paid = client.post(
        f"/v1/orders/{order['id']}/deliver",
        json=payment_body,
        headers={**headers, "Idempotency-Key": key},
    )
    assert paid.status_code == 200
    replay = client.post(
        f"/v1/orders/{order['id']}/deliver",
        json=payment_body,
        headers={**headers, "Idempotency-Key": key},
    )
    assert replay.status_code == 200 and replay.json() == paid.json()
    summary = _summary(client, headers)
    assert summary["opening_amount"] == "500.00"
    assert summary["total_cash_in"] == "27.00"
    assert summary["expected_cash_amount"] == "527.00"
    closed = _close(client, headers, context, "527.00")
    assert closed["expected_cash_amount"] == "527.00"
    assert closed["cash_variance_amount"] == "0.00"
    with SessionLocal() as session:
        operation = session.scalars(select(FinancialOperation)).one()
        entry = session.scalars(select(FinancialEntry)).one()
        assert operation.subject_id == UUID(order["id"])
        assert str(operation.source_id) == paid.json()["payments"][0]["id"]
        assert entry.financial_operation_id == operation.id
        assert str(entry.cash_session_id) == context["cash_session_id"]
        assert entry.amount == Decimal("6.00")
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 1
        assert session.scalar(select(func.count()).select_from(Sale)) == 1
    admin = owner_headers()
    cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=admin)
    assert cut.status_code == 200
    assert cut.json()["expected_vs_counted"]["expected_cash_amount"] == "527.00"
    assert cut.json()["expected_vs_counted"]["difference_amount"] == "0.00"
    flow = client.get("/v1/admin/cash-flow", headers=admin)
    assert flow.status_code == 200
    assert flow.json()["summary"]["inflows_total"] == "27.00"
    assert flow.json()["summary"]["cash_total"] == "27.00"
    assert flow.json()["summary"]["order_collections_total"] == "6.00"
    order_rows = [row for row in flow.json()["items"] if row["source_type"] == "ORDER_PAYMENT"]
    assert len(order_rows) == 1
    row = order_rows[0]
    assert row["financial_entry_id"] == str(entry.id)
    assert row["financial_operation_id"] == str(operation.id)
    detail = client.get(f"/v1/admin/cash-flow/{row['id']}", headers=admin)
    assert detail.status_code == 200
    assert detail.json()["source_document_context"]["cash_session_id"] == context["cash_session_id"]
    assert detail.json()["source_document_context"]["order_id"] == order["id"]
    assert cut.json()["expected_vs_counted"]["cash_sales_amount"] == "21.00"
    assert cut.json()["expected_vs_counted"]["cash_order_collections_amount"] == "6.00"
    assert len(cut.json()["order_payments"]) == 1


@pytest.mark.parametrize(
    ("method", "cash_amount", "card_amount"),
    [("CASH", "6.00", "0.00"), ("CARD", "0.00", "6.00"), ("MIXED", "2.00", "4.00")],
)
def test_order_advance_and_refund_use_real_methods_once_without_becoming_sales(
    client: TestClient, method: str, cash_amount: str, card_amount: str
) -> None:
    headers, context = _setup(client)
    legs = (
        [
            {"payment_method_code": "CASH", "amount": cash_amount},
            {"payment_method_code": "CARD", "amount": card_amount},
        ]
        if method == "MIXED"
        else None
    )
    order = _create(client, headers, context, amount="6.00", method=method, legs=legs)
    expected = Decimal("500.00") + Decimal(cash_amount)
    summary = _summary(client, headers)
    assert Decimal(summary["expected_cash_amount"]) == expected
    admin = owner_headers()
    flow = client.get("/v1/admin/cash-flow", headers=admin, params={"source_type": "ORDER_PAYMENT"})
    assert flow.status_code == 200
    assert flow.json()["total"] == (2 if method == "MIXED" else 1)
    assert flow.json()["summary"]["cash_total"] == cash_amount
    assert flow.json()["summary"]["card_total"] == card_amount
    for filter_method, expected_count in (
        ("CASH", int(Decimal(cash_amount) > 0)),
        ("CARD", int(Decimal(card_amount) > 0)),
    ):
        filtered = client.get(
            "/v1/admin/cash-cuts",
            headers=admin,
            params={"payment_method": filter_method, "has_refunds": "false"},
        )
        assert filtered.status_code == 200
        assert filtered.json()["total"] == expected_count
    if Decimal(card_amount):
        card = next(row for row in flow.json()["items"] if row["payment_method"] == "CARD")
        detail = client.get(f"/v1/admin/cash-flow/{card['id']}", headers=admin)
        assert detail.status_code == 200
        classification = detail.json()["financial_classification"]
        assert classification["affects_cash_drawer"] is False
        assert classification["affects_bank_settlement"] is False
    _post(
        client,
        headers,
        f"/v1/orders/{order['id']}/cancel",
        {
            **context,
            "cancellation_reason": "Customer requested a confirmed refund",
        },
    )
    summary = _summary(client, headers)
    assert summary["total_cash_in"] == cash_amount
    assert summary["total_cash_out"] == cash_amount
    assert summary["expected_cash_amount"] == "500.00"
    closed = _close(client, headers, context, "500.00")
    assert closed["cash_variance_amount"] == "0.00"
    cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=admin)
    assert cut.status_code == 200
    assert cut.json()["included_tickets"] == []
    assert cut.json()["returns_refunds"] == []
    for row in cut.json()["payment_breakdown"]:
        amount = {"CASH": cash_amount, "CARD": card_amount}.get(row["payment_method_code"], "0.00")
        assert row["order_advance_amount"] == amount
        assert row["order_refund_amount"] == amount
        assert row["sales_amount"] == "0.00"
    assert len(cut.json()["order_payments"]) == (4 if method == "MIXED" else 2)
    refunded = client.get(
        "/v1/admin/cash-cuts",
        headers=admin,
        params={"payment_method": "CARD" if method == "CARD" else "CASH", "has_refunds": "true"},
    )
    assert refunded.status_code == 200 and refunded.json()["total"] == 1
    assert refunded.json()["items"][0]["has_refunds"] is True
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0
        assert session.scalar(select(func.count()).select_from(Sale)) == 0


@pytest.mark.parametrize("action", ["deliver", "cancel"])
def test_later_order_payment_belongs_to_its_actual_turn_and_preserves_old_close(
    client: TestClient, action: str
) -> None:
    headers, first = _setup(client)
    order = _create(client, headers, first, amount="3.00", method="CASH")
    first_close = _close(client, headers, first, "503.00")
    headers = login_headers(
        client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS"
    )
    opened = _post(
        client,
        headers,
        "/v1/cash-sessions/open",
        {
            "workstation_code": SEED_WORKSTATION_CODE,
            "opening_amount": "100.00",
        },
    )
    second = {"workstation_code": SEED_WORKSTATION_CODE, "cash_session_id": opened["id"]}
    if action == "deliver":
        _post(client, headers, f"/v1/orders/{order['id']}/mark-ready", second)
        body = {**second, "settlement_amount": "3.00", "settlement_payment_method_code": "CASH"}
        expected = "103.00"
    else:
        body = {**second, "cancellation_reason": "Refund performed in a later turn"}
        expected = "97.00"
    _post(client, headers, f"/v1/orders/{order['id']}/{action}", body)
    assert _summary(client, headers)["expected_cash_amount"] == expected
    closed = _close(client, headers, second, expected)
    assert closed["cash_variance_amount"] == "0.00"
    admin = owner_headers()
    for context, expected_amount in [(first, "503.00"), (second, expected)]:
        cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=admin)
        assert cut.status_code == 200
        assert cut.json()["expected_vs_counted"]["expected_cash_amount"] == expected_amount
        assert len(cut.json()["order_payments"]) == 1
    assert first_close["expected_cash_amount"] == "503.00"


def _financial_context(original: FinancialEntry) -> dict[str, Any]:
    return {
        name: getattr(original, name)
        for name in (
            "branch_id",
            "workstation_id",
            "cash_session_id",
            "actor_id",
            "currency_code",
            "context_version",
            "source_app",
            "actor_type",
            "operation_id",
            "correlation_id",
            "related_branch_ids",
            "occurred_at",
        )
    }


@pytest.mark.parametrize("state", ["PENDING", "PROCESSING", "UNKNOWN", "REJECTED", "CANCELLED"])
def test_unconfirmed_order_entries_are_excluded_from_all_cash_consumers(
    client: TestClient, state: str
) -> None:
    headers, context = _setup(client)
    order = _create(client, headers, context, amount="3.00", method="CASH")
    # Diagnostic fixture models an unresolved future payment, never an HTTP-confirmed receipt.
    with SessionLocal() as session:
        original = session.scalars(select(FinancialEntry)).one()
        trace = _financial_context(original)
        payment = CustomerOrderPayment(
            id=uuid4(),
            customer_order_id=UUID(order["id"]),
            sequence=2,
            payment_type="SETTLEMENT",
            payment_method_code="CASH",
            amount=Decimal("3.00"),
            currency_code="MXN",
            cash_session_id=original.cash_session_id,
            workstation_id=original.workstation_id,
            recorded_by_user_id=original.actor_id,
            recorded_at_utc=datetime.now(UTC),
        )
        session.add(payment)
        session.flush()
        operation = make_operation(
            trace,
            kind="ORDER_SETTLEMENT",
            effect_code="ORDER_SETTLEMENT",
            source_type="ORDER_PAYMENT",
            source_id=payment.id,
            subject_type="ORDER",
            subject_id=UUID(order["id"]),
            amount_due=Decimal("3.00"),
        )
        session.add(operation)
        session.flush()
        session.add(
            make_entry(
                trace,
                operation,
                amount=Decimal("3.00"),
                tendered_amount=Decimal("3.00"),
                state=state,
                confirmed_at=None,
                resolution_kind=None,
            )
        )
        session.commit()
    assert _summary(client, headers)["expected_cash_amount"] == "503.00"
    admin = owner_headers()
    cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=admin)
    assert cut.status_code == 200
    assert cut.json()["expected_vs_counted"]["expected_cash_amount"] == "503.00"
    assert len(cut.json()["order_payments"]) == 1
    flow = client.get("/v1/admin/cash-flow", headers=admin, params={"source_type": "ORDER_PAYMENT"})
    assert flow.status_code == 200
    assert flow.json()["total"] == 1
    assert flow.json()["summary"]["cash_total"] == "3.00"


def test_confirmed_order_compensation_is_included_once_and_keeps_its_original(
    client: TestClient,
) -> None:
    headers, context = _setup(client)
    order = _create(client, headers, context, amount="6.00", method="CASH")
    # There is deliberately no new public reversal endpoint in 042.
    with SessionLocal() as session:
        original = session.scalars(select(FinancialEntry)).one()
        trace = _financial_context(original)
        reversal = make_operation(
            trace,
            kind="TECHNICAL_REVERSAL",
            effect_code="TECHNICAL_REVERSAL",
            source_type="FINANCIAL_ENTRY",
            source_id=original.id,
            subject_type="ORDER",
            subject_id=UUID(order["id"]),
            amount_due=original.amount,
            related_operation_id=original.financial_operation_id,
            relation_kind="REVERSAL_OF",
        )
        session.add(reversal)
        session.flush()
        session.add(
            make_entry(
                trace,
                reversal,
                direction="OUT",
                amount=original.amount,
                tendered_amount=None,
                reverses_entry_id=original.id,
            )
        )
        session.commit()
    summary = _summary(client, headers)
    assert summary["expected_cash_amount"] == "500.00"
    assert summary["cash_order_collections_amount"] == "6.00"
    assert summary["cash_order_refunds_amount"] == "0.00"
    assert summary["cash_order_technical_reversal_amount"] == "-6.00"
    admin = owner_headers()
    cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=admin)
    assert cut.status_code == 200
    assert len(cut.json()["order_payments"]) == 2
    assert cut.json()["expected_vs_counted"]["cash_order_technical_reversal_amount"] == "-6.00"
    flow = client.get("/v1/admin/cash-flow", headers=admin, params={"source_type": "ORDER_PAYMENT"})
    assert flow.status_code == 200
    assert flow.json()["total"] == 2
    assert flow.json()["summary"]["order_collections_total"] == "6.00"
    assert flow.json()["summary"]["order_refunds_total"] == "0.00"
    assert flow.json()["summary"]["order_technical_reversal_total"] == "-6.00"
    assert flow.json()["summary"]["cash_total"] == "0.00"


def test_order_financial_query_requires_scope_and_excludes_another_branch(
    client: TestClient,
) -> None:
    from fastapi import HTTPException

    headers, context = _setup(client)
    order = _create(client, headers, context, amount="6.00", method="CASH")
    foreign, _close = setup_concurrent_order(client, "create", SEED_DESTINATION_WORKSTATION_CODE)
    other_order = _post(client, foreign.headers, "/v1/orders", foreign.body)
    assert other_order["branch_id"] != order["branch_id"]
    with SessionLocal() as session:
        actor = _reader(session, UUID(order["branch_id"]))
        with pytest.raises(HTTPException) as failure:
            read_order_financial_entries(session)
        assert failure.value.status_code == 403
        bind_authorization_scope(
            session,
            user=actor,
            capabilities=("cash_finance.view",),
            surface="BACKOFFICE",
            mutation=False,
        )
        visible = read_order_financial_entries(session)
        assert len(visible) == 1 and visible[0].order_id == UUID(order["id"])
        assert (
            read_order_financial_entries(
                session, cash_session_ids=(UUID(foreign.body["cash_session_id"]),)
            )
            == []
        )
