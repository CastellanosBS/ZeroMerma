"""Actual sales, operating movements and opening funds are single financial facts."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_COCA_355_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.discounts.infrastructure.models import OperationalDiscount
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.payments.infrastructure.models import OperationalPayment
from zeromerma_api.modules.sales.infrastructure.models import (
    CashMovement,
    Sale,
    SaleLine,
    SalePayment,
)
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers

PATHS = {
    "opening": "/v1/cash-sessions/open",
    "sale": "/v1/sales/confirm",
    "payment": "/v1/payments",
    "charge": "/v1/discounts",
}
KINDS = {
    "opening": "CASH_OPENING",
    "sale": "SALE_COLLECTION",
    "payment": "OPERATIONAL_PAYMENT",
    "charge": "OPERATIONAL_CHARGE",
}
ACTIONS = {
    "opening": "cash_session.opened",
    "sale": "sale.confirmed",
    "payment": "operational_payment.committed",
    "charge": "operational_discount.committed",
}


def _post(
    client: TestClient, headers: dict[str, str], kind: str, body: dict[str, Any], key: str
) -> Any:
    return client.post(PATHS[kind], headers={**headers, "Idempotency-Key": key}, json=body)


def _setup(client: TestClient, kind: str) -> tuple[dict[str, str], dict[str, Any]]:
    headers = login_headers(
        client,
        email=SEED_USER_EMAIL,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    body: dict[str, Any] = {"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "100.00"}
    if kind == "opening":
        return headers, body
    opening = _post(client, headers, "opening", body, new_idempotency_key())
    assert opening.status_code == 201
    body = {"workstation_code": SEED_WORKSTATION_CODE, "cash_session_id": opening.json()["id"]}
    if kind == "sale":
        with SessionLocal() as session:
            product_id = session.scalar(
                select(Product.id).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
            )
        body.update(
            lines=[
                {"capture_mode": "PRODUCT_DIRECT", "product_id": str(product_id), "quantity": "2"}
            ],
            payments=[{"payment_method_code": "CASH", "tendered_amount": "50.00"}],
        )
    else:
        body.update(
            {"payee_name" if kind == "payment" else "subject_name": "Financial acceptance fixture"},
            concept="Actual operating movement",
            payment_method_code="CASH",
            total_amount="10.00",
        )
    return headers, body


def _state() -> tuple[int | None, ...]:
    with SessionLocal() as session:
        counts = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                CashSession,
                Sale,
                SaleLine,
                SalePayment,
                CashMovement,
                OperationalPayment,
                OperationalDiscount,
                FinancialOperation,
                FinancialEntry,
                IdempotencyRecord,
                OutboxEvent,
            )
        )
        return (
            *counts,
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action.in_(ACTIONS.values()))
            ),
        )


def _assert_trace(
    session: Any, key: str, operation: FinancialOperation, entries: list[FinancialEntry], kind: str
) -> None:
    record = session.scalars(
        select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
    ).one()
    audit = session.scalars(
        select(AuditLog).where(
            AuditLog.idempotency_key == UUID(key), AuditLog.action == ACTIONS[kind]
        )
    ).one()
    event = session.scalars(
        select(OutboxEvent).where(OutboxEvent.idempotency_key == UUID(key))
    ).one()
    expected = {
        "financial_operation_id": str(operation.id),
        "financial_entry_ids": [str(entry.id) for entry in entries],
    }
    for trace in (audit.metadata_, event.payload, event.headers):
        assert trace["financial_operation_id"] == expected["financial_operation_id"]
        assert sorted(trace["financial_entry_ids"]) == sorted(expected["financial_entry_ids"])
    for fact in (operation, *entries):
        assert fact.operation_id == record.id == audit.operation_id == event.operation_id
        assert fact.correlation_id == audit.correlation_id == event.correlation_id
        assert fact.branch_id == record.branch_id == audit.branch_id == event.branch_id
        assert fact.actor_id == record.actor_user_id == audit.actor_id
        assert fact.workstation_id == record.workstation_id
        assert fact.cash_session_id == audit.cash_session_id == event.cash_session_id
        assert fact.idempotency_key == UUID(key)
        assert fact.context_version == 1 and fact.source_app == "POS" and fact.actor_type == "USER"
        assert fact.recorded_at is not None
        if kind != "opening":
            assert fact.cash_session_id == record.cash_session_id
    assert record.response_schema_version is not None


@pytest.mark.parametrize("amount", ["0.00", "100.00"])
def test_opening_has_one_explicit_operation_and_no_zero_entry(
    client: TestClient, amount: str
) -> None:
    headers, body = _setup(client, "opening")
    body["opening_amount"] = amount
    key = new_idempotency_key()
    first = _post(client, headers, "opening", body, key)
    assert first.status_code == 201
    after = _state()
    replay = _post(client, headers, "opening", body, key)
    assert replay.status_code == 201 and replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == first.json() and _state() == after
    with SessionLocal() as session:
        operation = session.scalars(select(FinancialOperation)).one()
        entries = list(session.scalars(select(FinancialEntry)).all())
        assert operation.kind == "CASH_OPENING" and operation.source_type == "CASH_SESSION"
        assert operation.source_id == operation.subject_id == UUID(first.json()["id"])
        assert operation.amount_due == Decimal(amount)
        assert len(entries) == int(Decimal(amount) > 0)
        if entries:
            assert entries[0].direction == "IN" and entries[0].payment_method_code == "CASH"
            assert entries[0].amount == entries[0].tendered_amount == Decimal(amount)
            assert entries[0].change_amount == Decimal("0.00")
        _assert_trace(session, key, operation, entries, "opening")
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0


@pytest.mark.parametrize(
    "payments,expected",
    [
        ([("CASH", "36.00")], [("CASH", "36.00", "0.00")]),
        ([("CASH", "50.00")], [("CASH", "36.00", "14.00")]),
        ([("CARD", "36.00")], [("CARD", "36.00", "0.00")]),
        (
            [("CARD", "16.00"), ("CASH", "30.00")],
            [("CARD", "16.00", "0.00"), ("CASH", "20.00", "10.00")],
        ),
        ([("CARD", "36.00"), ("CASH", "10.00")], [("CARD", "36.00", "0.00")]),
    ],
)
def test_sale_records_only_applied_legs_and_preserves_tender_change_and_replay(
    client: TestClient, payments: list[tuple[str, str]], expected: list[tuple[str, str, str]]
) -> None:
    headers, body = _setup(client, "sale")
    body["payments"] = [
        {"payment_method_code": method, "tendered_amount": amount} for method, amount in payments
    ]
    key = new_idempotency_key()
    first = _post(client, headers, "sale", body, key)
    assert first.status_code == 201
    after = _state()
    replay = _post(client, headers, "sale", body, key)
    assert replay.status_code == 201 and replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == first.json() and _state() == after
    with SessionLocal() as session:
        operation = session.scalars(
            select(FinancialOperation).where(FinancialOperation.idempotency_key == UUID(key))
        ).one()
        entries = list(
            session.scalars(
                select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
            ).all()
        )
        assert operation.source_type == operation.subject_type == "SALE"
        assert operation.source_id == operation.subject_id == UUID(first.json()["id"])
        assert operation.kind == "SALE_COLLECTION" and operation.amount_due == Decimal("36.00")
        assert sorted(
            (entry.payment_method_code, entry.amount, entry.change_amount) for entry in entries
        ) == sorted(
            (method, Decimal(amount), Decimal(change)) for method, amount, change in expected
        )
        assert sum(entry.amount for entry in entries) == operation.amount_due
        receipts = list(
            session.scalars(
                select(SalePayment).where(SalePayment.sale_id == operation.source_id)
            ).all()
        )
        assert len(receipts) == len(payments)
        for entry in entries:
            receipt = next(item for item in receipts if str(item.id) == entry.leg_key)
            assert entry.direction == "IN" and entry.state == "CONFIRMED"
            assert (
                entry.amount == receipt.applied_amount
                and entry.tendered_amount == receipt.tendered_amount
            )
            if entry.payment_method_code == "CARD":
                assert (
                    entry.execution_mode == "ACCOUNTING_ONLY"
                    and entry.resolution_kind == "EXTERNAL_RECORDING"
                )
                assert entry.resolution_reference == receipt.id
            else:
                assert entry.tendered_amount == entry.amount + entry.change_amount
                assert entry.execution_mode == "LOCAL" and entry.resolution_kind == "LOCAL_CASH"
        _assert_trace(session, key, operation, entries, "sale")
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0


@pytest.mark.parametrize("kind", ["payment", "charge"])
@pytest.mark.parametrize("method", ["CASH", "CARD"])
def test_operating_movement_direction_and_cause_are_canonical_and_replayable(
    client: TestClient, kind: str, method: str
) -> None:
    headers, body = _setup(client, kind)
    body["payment_method_code"] = method
    key = new_idempotency_key()
    first = _post(client, headers, kind, body, key)
    assert first.status_code == 201
    assert first.json()["cash_movement_id"] is None
    after = _state()
    replay = _post(client, headers, kind, body, key)
    assert replay.status_code == 201 and replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == first.json() and _state() == after
    with SessionLocal() as session:
        operation = session.scalars(
            select(FinancialOperation).where(FinancialOperation.idempotency_key == UUID(key))
        ).one()
        entry = session.scalars(
            select(FinancialEntry).where(FinancialEntry.financial_operation_id == operation.id)
        ).one()
        assert operation.kind == KINDS[kind]
        assert (
            operation.source_type
            == operation.subject_type
            == ("OPERATIONAL_PAYMENT" if kind == "payment" else "OPERATIONAL_DISCOUNT")
        )
        assert operation.source_id == operation.subject_id == UUID(first.json()["id"])
        assert operation.amount_due == entry.amount == Decimal("10.00")
        assert entry.direction == ("OUT" if kind == "payment" else "IN")
        assert entry.payment_method_code == method and entry.state == "CONFIRMED"
        assert entry.change_amount == Decimal("0.00")
        assert entry.tendered_amount == (
            Decimal("10.00") if method == "CASH" and kind == "charge" else None
        )
        assert entry.execution_mode == ("LOCAL" if method == "CASH" else "ACCOUNTING_ONLY")
        assert entry.resolution_kind == ("LOCAL_CASH" if method == "CASH" else "EXTERNAL_RECORDING")
        assert entry.resolution_reference == (None if method == "CASH" else operation.source_id)
        _assert_trace(session, key, operation, [entry], kind)
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0


@pytest.mark.parametrize("kind", ["opening", "sale", "payment", "charge"])
@pytest.mark.parametrize("writer", ["audit", "outbox"])
def test_trace_failure_rolls_back_business_ledger_and_ack_then_same_key_retries(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str, writer: str
) -> None:
    headers, body = _setup(client, kind)
    key, before = new_idempotency_key(), _state()
    target, method = (AuditRecorder, "record") if writer == "audit" else (OutboxWriter, "append")
    original = getattr(target, method)

    def fail_after_financial_flush(self: Any, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs.get("action") == ACTIONS[kind] or kwargs.get("payload", {}).get(
            "financial_operation_id"
        ):
            session.flush()
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(FinancialOperation)
                    .where(FinancialOperation.idempotency_key == UUID(key))
                )
                == 1
            )
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(FinancialEntry)
                    .where(FinancialEntry.idempotency_key == UUID(key))
                )
                == 1
            )
            raise RuntimeError("Injected financial trace failure")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(target, method, fail_after_financial_flush)
        with pytest.raises(RuntimeError, match="Injected financial trace failure"):
            _post(client, headers, kind, body, key)
    assert _state() == before
    retried = _post(client, headers, kind, body, key)
    assert retried.status_code == 201
    after = _state()
    replay = _post(client, headers, kind, body, key)
    assert replay.json() == retried.json() and replay.headers["Idempotency-Replayed"] == "true"
    assert _state() == after


@pytest.mark.parametrize("kind", ["payment", "charge"])
def test_operating_movement_without_open_session_rejects_without_financial_facts(
    client: TestClient, kind: str
) -> None:
    headers, _ = _setup(client, "opening")
    before = _state()
    body = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "cash_session_id": str(uuid4()),
        "payee_name" if kind == "payment" else "subject_name": "No session fixture",
        "concept": "No financial effect",
        "payment_method_code": "CASH",
        "total_amount": "10.00",
    }
    response = _post(client, headers, kind, body, new_idempotency_key())
    assert response.status_code == 409 and _state() == before


@pytest.mark.parametrize("invalid", ["zero_sale", "foreign_currency", "card_overpayment"])
def test_invalid_sale_cannot_leave_a_business_or_financial_effect(
    client: TestClient, invalid: str
) -> None:
    headers, body = _setup(client, "sale")
    if invalid == "card_overpayment":
        body["payments"] = [{"payment_method_code": "CARD", "tendered_amount": "50.00"}]
    else:
        with SessionLocal() as session:
            product = session.get(Product, UUID(body["lines"][0]["product_id"]))
            assert product is not None
            if invalid == "zero_sale":
                product.unit_price = Decimal("0.00")
            else:
                product.currency_code = "USD"
            session.commit()
    before = _state()
    response = _post(client, headers, "sale", body, new_idempotency_key())
    assert response.status_code == 400 and _state() == before
