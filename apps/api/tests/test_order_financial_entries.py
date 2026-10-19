"""Order receipts and canonical financial facts share one admitted transaction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from order_fixtures import committed_order_clock, quote_order_payload, seed_order_stock
from sqlalchemy import and_, func, or_, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
    InventoryReservation,
    InventoryReservationEvent,
)
from zeromerma_api.modules.orders.infrastructure.models import (
    CustomerOrder,
    CustomerOrderItem,
    CustomerOrderPayment,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers


def _post(
    client: TestClient,
    headers: dict[str, str],
    path: str,
    body: dict[str, Any],
    key: str | None = None,
) -> Any:
    return client.post(
        path,
        headers={**headers, "Idempotency-Key": key or new_idempotency_key()},
        json=body,
    )


def _setup(client: TestClient) -> tuple[dict[str, str], dict[str, str], str]:
    seed_order_stock()
    headers = login_headers(
        client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS"
    )
    opened = _post(
        client,
        headers,
        "/v1/cash-sessions/open",
        {"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "100.00"},
    )
    assert opened.status_code == 201
    with SessionLocal() as session:
        product_id = session.scalar(
            select(Product.id).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        )
    return (
        headers,
        {"workstation_code": SEED_WORKSTATION_CODE, "cash_session_id": opened.json()["id"]},
        str(product_id),
    )


def _payment(method: str, amount: str, prefix: str) -> dict[str, Any]:
    return {
        f"{prefix}_amount": amount,
        f"{prefix}_payment_method_code": method,
        f"{prefix}_payments": [
            {"payment_method_code": "CASH", "amount": str(Decimal(amount) / 3)},
            {"payment_method_code": "CARD", "amount": str(Decimal(amount) * 2 / 3)},
        ]
        if method == "MIXED"
        else [],
    }


def _create_body(context: dict[str, str], product_id: str) -> dict[str, Any]:
    return {
        **context,
        "customer_name": "Private producer fixture",
        "customer_phone": "6621234567",
        "notes": "Private instructions never copied into financial facts",
        "requested_for_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        "items": [{"product_id": product_id, "quantity": "2"}],
        "advance_amount": "0.00",
        "quote_fingerprint": "0" * 64,
    }


@pytest.mark.parametrize("method", ["CASH", "CARD", "MIXED"])
def test_paid_order_without_open_cash_session_rejects_without_partial_facts(
    client: TestClient, method: str
) -> None:
    headers = login_headers(
        client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD, audience="POS"
    )
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashSession)) == 0
        product_id = session.scalar(
            select(Product.id).where(Product.code == SEED_PRODUCT_BOLILLO_STD_CODE)
        )
        assert product_id is not None
    context = {
        "workstation_code": SEED_WORKSTATION_CODE,
        "cash_session_id": str(uuid4()),
    }
    key = new_idempotency_key()
    # Authentication has completed before taking the business-effects baseline.
    before = _state()
    response = _post(
        client,
        headers,
        "/v1/orders",
        {**_create_body(context, str(product_id)), **_payment(method, "3.00", "advance")},
        key,
    )
    assert response.status_code == 409
    assert response.json()["message"] == (
        "Necesitas una caja abierta en esta estacion para operar pedidos."
    )
    assert _state() == before
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashSession)) == 0
        assert (
            session.scalar(
                select(IdempotencyRecord.id).where(IdempotencyRecord.idempotency_key == UUID(key))
            )
            is None
        )


def test_unsupported_order_payment_currency_is_a_domain_rejection_without_partial_facts(
    client: TestClient,
) -> None:
    headers, context, product_id = _setup(client)
    with SessionLocal() as session:
        product = session.get(Product, UUID(product_id))
        assert product is not None
        product.currency_code = "USD"
        session.commit()
    body = quote_order_payload(
        client,
        headers,
        {**_create_body(context, product_id), **_payment("CASH", "3.00", "advance")},
    )
    before = _state()
    response = _post(
        client,
        headers,
        "/v1/orders",
        body,
    )
    assert response.status_code == 400
    assert "MXN" in response.json()["message"]
    assert _state() == before


def _prepare(
    client: TestClient, action: str, method: str
) -> tuple[dict[str, str], dict[str, str], str, dict[str, Any]]:
    headers, context, product_id = _setup(client)
    create = _create_body(context, product_id)
    if action in {"create", "cancel"}:
        create.update(_payment(method, "3.00", "advance"))
    else:
        create.update(_payment("CASH", "3.00", "advance"))
    create = quote_order_payload(client, headers, create)
    if action == "create":
        return headers, context, "/v1/orders", create
    created = _post(client, headers, "/v1/orders", create)
    assert created.status_code == 201
    order_id = created.json()["id"]
    if action == "deliver":
        with committed_order_clock(order_id):
            ready = _post(client, headers, f"/v1/orders/{order_id}/mark-ready", context)
        assert ready.status_code == 200
        body = {**context, **_payment(method, "3.00", "settlement")}
    else:
        body = {
            **context,
            "cancellation_reason": "Customer requested refund",
            "cancellation_responsibility": "CUSTOMER",
        }
    return headers, context, f"/v1/orders/{order_id}/{action}", body


def _state() -> tuple[Any, ...]:
    with SessionLocal() as session:
        counts = tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                CustomerOrder,
                CustomerOrderItem,
                CustomerOrderPayment,
                FinancialOperation,
                FinancialEntry,
                CashMovement,
                InventoryMovement,
                InventoryReservation,
                InventoryReservationEvent,
            )
        )
        order_rows = session.execute(
            select(
                CustomerOrder.id,
                CustomerOrder.status,
                CustomerOrder.advance_amount,
                CustomerOrder.remaining_balance_amount,
                CustomerOrder.updated_at_utc,
            ).order_by(CustomerOrder.id)
        ).all()
        traces = tuple(
            session.scalar(select(func.count()).select_from(model).where(predicate))
            for model, predicate in (
                (AuditLog, AuditLog.action.like("order.%")),
                (OutboxEvent, OutboxEvent.event_name.like("order.%")),
                (IdempotencyRecord, IdempotencyRecord.operation_code.like("order.%")),
            )
        )
        inventory = session.execute(
            select(
                InventoryBalance.id,
                InventoryBalance.quantity_on_hand,
                InventoryBalance.quantity_reserved,
                InventoryBalance.inventory_value,
            ).order_by(InventoryBalance.id)
        ).all()
    return counts, order_rows, traces, inventory


@pytest.mark.parametrize("action", ["create", "deliver", "cancel"])
@pytest.mark.parametrize("method", ["CASH", "CARD", "MIXED"])
def test_actual_order_payment_legs_have_one_causal_fact_and_replay_without_duplicates(
    client: TestClient, action: str, method: str
) -> None:
    headers, context, path, body = _prepare(client, action, method)
    key = new_idempotency_key()
    response = _post(client, headers, path, body, key)
    assert response.status_code == (201 if action == "create" else 200)
    ack = response.json()
    before_replay = _state()
    replay = _post(client, headers, path, body, key)
    assert replay.status_code == response.status_code
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json() == ack
    recovered = client.get(f"/v1/orders/commands/{action}/{key}", headers=headers, params=context)
    assert recovered.status_code == 200 and recovered.json() == ack
    assert _state() == before_replay
    # The stored 030 acknowledgement stays unchanged; new references belong to detail GETs.
    assert all("financial_entry_id" not in payment for payment in ack["payments"])
    expected_type = {"create": "ADVANCE", "deliver": "SETTLEMENT", "cancel": "REFUND"}[action]
    with SessionLocal() as session:
        rows = session.execute(
            select(CustomerOrderPayment, FinancialOperation, FinancialEntry)
            .join(
                FinancialOperation,
                or_(
                    and_(
                        FinancialOperation.source_type == "ORDER_PAYMENT",
                        FinancialOperation.source_id == CustomerOrderPayment.id,
                    ),
                    and_(
                        FinancialOperation.source_type == "ORDER_CANCELLATION",
                        FinancialOperation.subject_id == CustomerOrderPayment.customer_order_id,
                        CustomerOrderPayment.payment_type == "REFUND",
                    ),
                ),
            )
            .join(FinancialEntry, FinancialEntry.financial_operation_id == FinancialOperation.id)
            .where(
                FinancialOperation.idempotency_key == UUID(key),
                or_(
                    CustomerOrderPayment.financial_entry_id.is_(None),
                    CustomerOrderPayment.financial_entry_id == FinancialEntry.id,
                ),
            )
        ).all()
        assert len(rows) == (2 if method == "MIXED" and action != "cancel" else 1)
        assert {row[0].payment_method_code for row in rows} == (
            {"CASH"} if action == "cancel" else {"CASH", "CARD"} if method == "MIXED" else {method}
        )
        record = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        ).one()
        audit = session.scalars(select(AuditLog).where(AuditLog.operation_id == record.id)).one()
        event = session.scalars(
            select(OutboxEvent).where(OutboxEvent.operation_id == record.id)
        ).one()
        references = []
        for payment, operation, entry in rows:
            assert payment.payment_type == expected_type
            assert operation.kind == operation.effect_code == f"ORDER_{expected_type}"
            assert operation.source_type == (
                "ORDER_CANCELLATION" if action == "cancel" else "ORDER_PAYMENT"
            )
            assert operation.source_id == (
                payment.customer_order_id if action == "cancel" else payment.id
            )
            assert operation.subject_type == "ORDER" and operation.subject_id == UUID(ack["id"])
            assert entry.amount == operation.amount_due == payment.amount
            assert entry.currency_code == operation.currency_code == payment.currency_code == "MXN"
            assert entry.state == "CONFIRMED" and entry.confirmed_at == payment.recorded_at_utc
            assert entry.direction == ("OUT" if action == "cancel" else "IN")
            assert entry.payment_method_code == payment.payment_method_code
            for fact in (operation, entry):
                assert fact.actor_id == payment.recorded_by_user_id == audit.actor_id
                assert fact.branch_id == audit.branch_id == event.branch_id
                assert (
                    fact.cash_session_id
                    == payment.cash_session_id
                    == UUID(context["cash_session_id"])
                )
                assert fact.workstation_id == payment.workstation_id
                assert fact.operation_id == audit.operation_id == event.operation_id == record.id
                assert fact.correlation_id == audit.correlation_id == event.correlation_id
                assert fact.idempotency_key == UUID(key)
                assert fact.source_app == "POS" and fact.actor_type == "USER"
                assert fact.recorded_at is not None
            if payment.payment_method_code == "CARD":
                assert entry.execution_mode == "ACCOUNTING_ONLY"
                assert entry.resolution_kind == "EXTERNAL_RECORDING"
                assert entry.resolution_reference == payment.id
                assert entry.tendered_amount is None
            else:
                assert entry.execution_mode == "LOCAL" and entry.resolution_kind == "LOCAL_CASH"
                assert entry.resolution_reference is None
                assert entry.tendered_amount == (None if action == "cancel" else payment.amount)
            assert entry.change_amount == Decimal("0.00")
            references.append(
                {
                    "payment_id": str(payment.id),
                    "financial_operation_id": str(operation.id),
                    "financial_entry_id": str(entry.id),
                }
            )
        if action == "cancel":
            for trace in (audit.metadata_, event.payload):
                assert (
                    trace["financial_refund"]["financial_operation_id"]
                    == references[0]["financial_operation_id"]
                )
                assert (
                    trace["financial_refund"]["entries"][0]["id"]
                    == references[0]["financial_entry_id"]
                )
        else:
            assert sorted(audit.metadata_["financial_records"], key=str) == sorted(
                references, key=str
            )
            assert sorted(event.payload["financial_records"], key=str) == sorted(
                references, key=str
            )
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0
    admin = owner_headers()
    for url, auth, params in (
        (f"/v1/orders/{ack['id']}", headers, {"workstation_code": SEED_WORKSTATION_CODE}),
        (f"/v1/admin/orders/{ack['id']}", admin, {}),
    ):
        detail = client.get(url, headers=auth, params=params)
        assert detail.status_code == 200
        payload = detail.json()
        payments = payload.get("order", payload)["payments"]
        for reference in references:
            payment = next(item for item in payments if item["id"] == reference["payment_id"])
            assert payment["financial_operation_id"] == reference["financial_operation_id"]
            assert payment["financial_entry_id"] == reference["financial_entry_id"]
            assert payment["cash_session_id"] == context["cash_session_id"]
            assert payment["workstation_id"] == str(rows[0][0].workstation_id)


@pytest.mark.parametrize("action", ["create", "deliver", "cancel"])
@pytest.mark.parametrize("writer", ["audit", "outbox"])
def test_failed_order_trace_rolls_back_flushed_payment_and_ledger_then_same_key_can_retry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, action: str, writer: str
) -> None:
    headers, _, path, body = _prepare(client, action, "MIXED")
    before = _state()
    key = new_idempotency_key()
    expected_facts = 1 if action == "cancel" else 2
    target, method = (AuditRecorder, "record") if writer == "audit" else (OutboxWriter, "append")
    original = getattr(target, method)

    def fail_after_trace_flush(self: Any, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        name = kwargs.get("action", kwargs.get("event_name", ""))
        if name.startswith("order."):
            session.flush()
            facts = session.scalars(
                select(FinancialEntry).where(FinancialEntry.idempotency_key == UUID(key))
            ).all()
            assert len(facts) == expected_facts, (
                "The fault must occur after the actual payment facts were flushed."
            )
            raise RuntimeError("Injected order trace failure after financial flush")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(target, method, fail_after_trace_flush)
        with pytest.raises(RuntimeError, match="Injected order trace failure"):
            _post(client, headers, path, body, key)
    assert _state() == before
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(IdempotencyRecord.id).where(IdempotencyRecord.idempotency_key == UUID(key))
            )
            is None
        )
    retried = _post(client, headers, path, body, key)
    assert retried.status_code == (201 if action == "create" else 200)
    after = _state()
    assert after[0][3] == before[0][3] + expected_facts
    assert after[0][4] == before[0][4] + expected_facts
    replay = _post(client, headers, path, body, key)
    assert replay.json() == retried.json() and _state() == after


def test_nonfinancial_transitions_do_not_create_facts_and_legacy_detail_does_not_backfill(
    client: TestClient,
) -> None:
    headers, context, product_id = _setup(client)
    create = quote_order_payload(
        client,
        headers,
        {**_create_body(context, product_id), **_payment("CASH", "3.00", "advance")},
    )
    created = _post(client, headers, "/v1/orders", create)
    assert created.status_code == 201
    order_id = UUID(created.json()["id"])
    financial_counts_before = _state()[0][3:5]
    # A deliberately unadopted demo payment remains visible without fabricated ledger identity.
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(context["cash_session_id"]))
        assert cash is not None
        order = session.get(CustomerOrder, order_id)
        assert order is not None
        order.advance_amount = Decimal("6.00")
        order.remaining_balance_amount = Decimal("0.00")
        payment = CustomerOrderPayment(
            id=uuid4(),
            customer_order_id=order_id,
            sequence=2,
            payment_type="ADVANCE",
            payment_method_code="CASH",
            amount=Decimal("3.00"),
            currency_code="MXN",
            cash_session_id=cash.id,
            workstation_id=cash.workstation_id,
            recorded_by_user_id=cash.user_id,
            recorded_at_utc=datetime.now(UTC),
        )
        session.add(payment)
        session.commit()
    admin = owner_headers()
    with committed_order_clock(order_id):
        for action in ("mark-ready", "deliver"):
            response = _post(client, admin, f"/v1/admin/orders/{order_id}/{action}", {})
            assert response.status_code == 200
    for url, auth, params in (
        (f"/v1/orders/{order_id}", headers, {"workstation_code": SEED_WORKSTATION_CODE}),
        (f"/v1/admin/orders/{order_id}", admin, {}),
    ):
        response = client.get(url, headers=auth, params=params)
        assert response.status_code == 200
        payload = response.json()
        rows = payload.get("order", payload)["payments"]
        assert len(rows) == 2
        assert rows[1]["financial_operation_id"] is None
        assert rows[1]["financial_entry_id"] is None
        assert rows[1]["cash_session_id"] == context["cash_session_id"]
    assert _state()[0][3:5] == financial_counts_before
