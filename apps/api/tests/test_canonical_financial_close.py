"""Actual-method cash equations and historical count snapshots agree across surfaces."""

from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_cash_concurrency import _baseline
from test_financial_ledger import entry as make_entry
from test_financial_ledger import operation as make_operation
from test_financial_producers import _setup
from test_order_cash_flow import _financial_context, _post, _summary

from zeromerma_api.bootstrap.seed_local import SEED_PRODUCT_COCA_355_CODE, SEED_WORKSTATION_CODE
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key


@pytest.mark.parametrize("card_count", [None, "0.00", "-10.00"])
def test_card_only_outflow_reconciles_signed_count_and_preserves_absent_count(
    client: TestClient, card_count: str | None
) -> None:
    headers, body = _setup(client, "payment")
    body["payment_method_code"] = "CARD"
    _post(client, headers, "/v1/payments", body)
    context = {key: body[key] for key in ("workstation_code", "cash_session_id")}
    counts = [{"payment_method_code": "CASH", "counted_amount": "100.00"}]
    if card_count is not None:
        counts.append({"payment_method_code": "CARD", "counted_amount": card_count})
    command = {**context, "counter_empty_confirmed": True, "counted_payment_methods": counts}
    preview = _post(client, headers, "/v1/cash-close/preview", command)
    card = next(
        row for row in preview["payment_method_rows"] if row["payment_method_code"] == "CARD"
    )
    assert card["expected_amount"] == "-10.00"
    assert card["counted_amount"] == card_count
    variance = None if card_count is None else "10.00" if card_count == "0.00" else "0.00"
    assert card["variance_amount"] == variance
    closed = _post(client, headers, "/v1/cash-close/commit", command)
    assert closed["expected_cash_amount"] == "100.00"
    assert closed["cash_variance_amount"] == "0.00"
    cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=owner_headers())
    assert cut.status_code == 200
    card = next(
        row for row in cut.json()["payment_breakdown"] if row["payment_method_code"] == "CARD"
    )
    assert card["expected_amount"] == "-10.00"
    assert card["counted_amount"] == card_count
    assert card["variance_amount"] == variance


@pytest.mark.parametrize("action", ["preview", "commit"])
def test_negative_cash_count_is_rejected_even_when_card_accepts_a_sign(
    client: TestClient, action: str
) -> None:
    headers, body = _setup(client, "payment")
    response = client.post(
        f"/v1/cash-close/{action}",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": body["workstation_code"],
            "cash_session_id": body["cash_session_id"],
            "counter_empty_confirmed": True,
            "counted_payment_methods": [
                {"payment_method_code": "cash", "counted_amount": "-10.00"},
                {"payment_method_code": "CARD", "counted_amount": "-10.00"},
            ],
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize("card_count", [None, "0.00", "16.00"])
def test_mixed_sale_operating_receipt_and_payment_reconcile_once(
    client: TestClient,
    card_count: str | None,
) -> None:
    headers, body = _setup(client, "sale")
    context = {key: body[key] for key in ("workstation_code", "cash_session_id")}
    _baseline(context["cash_session_id"], SEED_PRODUCT_COCA_355_CODE, 2)
    body["payments"] = [
        {"payment_method_code": "CARD", "tendered_amount": "16.00"},
        {"payment_method_code": "CASH", "tendered_amount": "30.00"},
    ]
    sale = _post(client, headers, "/v1/sales/confirm", body)
    assert sale["change_amount"] == "10.00"
    _post(
        client,
        headers,
        "/v1/discounts",
        {
            **context,
            "subject_name": "Fixture",
            "concept": "Receipt",
            "payment_method_code": "CASH",
            "total_amount": "10.00",
        },
    )
    _post(
        client,
        headers,
        "/v1/payments",
        {
            **context,
            "payee_name": "Fixture",
            "concept": "Outflow",
            "payment_method_code": "CASH",
            "total_amount": "5.00",
        },
    )
    summary = _summary(client, headers)
    assert summary["total_cash_in"] == "30.00"
    assert summary["total_cash_out"] == "5.00"
    assert summary["expected_cash_amount"] == "125.00"
    counts = [{"payment_method_code": "CASH", "counted_amount": "125.00"}]
    if card_count is not None:
        counts.append({"payment_method_code": "CARD", "counted_amount": card_count})
    command: dict[str, Any] = {
        **context,
        "counter_empty_confirmed": True,
        "counted_payment_methods": counts,
    }
    preview = _post(client, headers, "/v1/cash-close/preview", command)
    rows = {row["payment_method_code"]: row for row in preview["payment_method_rows"]}
    assert set(rows) == {"CASH", "CARD"}
    assert rows["CASH"]["variance_amount"] == "0.00"
    assert rows["CARD"]["expected_amount"] == "16.00"
    assert rows["CARD"]["counted_amount"] == card_count
    assert rows["CARD"]["variance_amount"] == (
        None if card_count is None else "-16.00" if card_count == "0.00" else "0.00"
    )
    _post(client, headers, "/v1/cash-close/commit", command)
    admin = owner_headers()
    cut = client.get(f"/v1/admin/cash-cuts/{context['cash_session_id']}", headers=admin)
    assert cut.status_code == 200
    cash = cut.json()["expected_vs_counted"]
    assert cash["expected_cash_amount"] == "125.00" and cash["difference_amount"] == "0.00"
    methods = {row["payment_method_code"]: row for row in cut.json()["payment_breakdown"]}
    assert methods["CASH"]["net_amount"] == "25.00"
    assert methods["CARD"]["counted_amount"] == card_count
    assert methods["CARD"]["expected_amount"] == "16.00"
    flow = client.get("/v1/admin/cash-flow", headers=admin)
    assert flow.status_code == 200
    assert flow.json()["summary"]["cash_total"] == "25.00"
    assert flow.json()["summary"]["card_total"] == "16.00"
    charge = next(
        row for row in flow.json()["items"] if row["source_type"] == "OPERATIONAL_DISCOUNT"
    )
    assert charge["direction"] == "INFLOW" and charge["financial_entry_id"]
    card = next(row for row in flow.json()["items"] if row["payment_method"] == "CARD")
    detail = client.get(f"/v1/admin/cash-flow/{card['id']}", headers=admin)
    assert detail.json()["financial_classification"]["affects_bank_settlement"] is False


def test_card_count_never_substitutes_missing_cash_and_mixed_is_not_a_count_method(
    client: TestClient,
) -> None:
    headers, body = _setup(client, "sale")
    context = {key: body[key] for key in ("workstation_code", "cash_session_id")}
    preview = _post(
        client,
        headers,
        "/v1/cash-close/preview",
        {
            **context,
            "counter_empty_confirmed": True,
            "counted_payment_methods": [{"payment_method_code": "CARD", "counted_amount": "0.00"}],
        },
    )
    assert preview["counted_cash_amount"] is None
    assert not preview["can_start_close"]
    assert any(row["code"] == "MISSING_COUNTED_PAYMENT_TOTALS" for row in preview["blockers"])
    rejected = client.post(
        "/v1/cash-close/preview",
        headers=headers,
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "counter_empty_confirmed": True,
            "counted_payment_methods": [
                {"payment_method_code": "MIXED", "counted_amount": "100.00"}
            ],
        },
    )
    assert rejected.status_code == 400


@pytest.mark.parametrize(
    "payments,mixed",
    [
        ([("CARD", "36.00"), ("CASH", "10.00")], False),
        ([("CARD", "10.00"), ("CARD", "6.00"), ("CASH", "20.00")], True),
        ([("CASH", "10.00"), ("CASH", "26.00")], False),
    ],
)
def test_mixed_classification_uses_distinct_positive_methods(
    client: TestClient,
    payments: list[tuple[str, str]],
    mixed: bool,
) -> None:
    headers, body = _setup(client, "sale")
    body["payments"] = [
        {"payment_method_code": method, "tendered_amount": amount} for method, amount in payments
    ]
    sale = _post(client, headers, "/v1/sales/confirm", body)
    response = client.get(
        "/v1/admin/sales/tickets", headers=owner_headers(), params={"payment_method": "MIXED"}
    )
    assert response.status_code == 200
    ids = [row["id"] for row in response.json()["items"]]
    assert (sale["id"] in ids) is mixed
    cut = client.get(
        "/v1/admin/cash-cuts", headers=owner_headers(), params={"payment_method": "MIXED"}
    )
    assert cut.status_code == 200
    assert (cut.json()["total"] == 1) is mixed


def test_sale_compensation_preserves_original_and_reconciles_actual_cash_once(
    client: TestClient,
) -> None:
    headers, body = _setup(client, "sale")
    body["payments"] = [
        {"payment_method_code": "CASH", "tendered_amount": "35.99"},
        {"payment_method_code": "CASH", "tendered_amount": "0.01"},
    ]
    sale = _post(client, headers, "/v1/sales/confirm", body)
    with SessionLocal() as session:
        original = session.scalar(
            select(FinancialEntry)
            .join(FinancialOperation)
            .where(
                FinancialOperation.source_id == UUID(sale["id"]),
                FinancialEntry.amount == Decimal("0.01"),
            )
        )
        assert original is not None
        trace = _financial_context(original)
        reversal = make_operation(
            trace,
            kind="TECHNICAL_REVERSAL",
            effect_code="TECHNICAL_REVERSAL",
            source_type="FINANCIAL_ENTRY",
            source_id=original.id,
            subject_type="SALE",
            subject_id=UUID(sale["id"]),
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
                amount=Decimal("0.01"),
                tendered_amount=None,
                reverses_entry_id=original.id,
            )
        )
        session.commit()
        assert original.amount == Decimal("0.01")
    assert _summary(client, headers)["expected_cash_amount"] == "135.99"
    admin = owner_headers()
    cut = client.get(f"/v1/admin/cash-cuts/{body['cash_session_id']}", headers=admin)
    assert cut.status_code == 200
    assert cut.json()["expected_vs_counted"]["expected_cash_amount"] == "135.99"
    assert cut.json()["expected_vs_counted"]["cash_adjustments_amount"] == "-0.01"
    flow = client.get("/v1/admin/cash-flow", headers=admin)
    assert flow.json()["summary"]["cash_total"] == "35.99"
    compensation = [
        row for row in flow.json()["items"] if row["source_type"] == "FINANCIAL_COMPENSATION"
    ]
    assert len(compensation) == 1
    assert compensation[0]["direction"] == "OUTFLOW"
    assert compensation[0]["amount"] == "0.01"
