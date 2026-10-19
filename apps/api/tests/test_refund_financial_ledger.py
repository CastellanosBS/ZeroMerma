"""Real refund admission, partial cash settlement and continuation across drawers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from decimal import Decimal
from http.cookies import SimpleCookie
from threading import Event
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_order_idempotency import _setup as setup_order
from test_return_idempotency import _post, _setup

from zeromerma_api.bootstrap.seed_local import SEED_USER_PASSWORD, SEED_WORKSTATION_CODE
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.financial_ledger.application.refund_commands import (
    RefundSettlementService,
)
from zeromerma_api.modules.financial_ledger.application.refund_schemas import (
    RefundSettlementCommand,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    COOKIE_NAMES,
    SessionAuthentication,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.infrastructure.models import CashMovement
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.concurrency import transaction_probe, wait_until_blocked
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email


def _movement(
    client: TestClient,
    headers: dict[str, str],
    context: dict[str, Any],
    amount: Decimal,
    *,
    incoming: bool = False,
) -> None:
    result = client.post(
        "/v1/discounts" if incoming else "/v1/payments",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": context["workstation_code"],
            "cash_session_id": context["cash_session_id"],
            "subject_name" if incoming else "payee_name": "Refund capacity fixture",
            "concept": "Actual drawer movement",
            "payment_method_code": "CASH",
            "total_amount": str(amount),
        },
    )
    assert result.status_code == 201


def _cash_capacity(cash_id: str) -> Decimal:
    with SessionLocal() as session:
        entries = list(
            session.scalars(
                select(FinancialEntry).where(
                    FinancialEntry.cash_session_id == UUID(cash_id),
                    FinancialEntry.state == "CONFIRMED",
                    FinancialEntry.payment_method_code == "CASH",
                )
            )
        )
        return sum(
            (entry.amount if entry.direction == "IN" else -entry.amount for entry in entries),
            Decimal("0.00"),
        )


def _partial_return(client: TestClient, payment: str = "CASH") -> tuple[Any, ...]:
    headers, body, _ = _setup(client, payment=payment)
    _movement(client, headers, body, _cash_capacity(body["cash_session_id"]) - Decimal("7.00"))
    result = _post(client, headers, body, new_idempotency_key())
    assert result.status_code == 201
    receipt = result.json()
    refund = receipt["financial_refund"]
    assert Decimal(refund["amount_settled"]) == Decimal("7.00")
    assert Decimal(refund["amount_pending"]) == Decimal(receipt["total_refund_amount"]) - 7
    assert refund["state"] == "PARTIALLY_SETTLED"
    assert refund["entries"][0]["payment_method_code"] == "CASH"
    assert receipt["refund_cash_movement_id"] is None
    assert _cash_capacity(body["cash_session_id"]) == 0
    listing = client.get("/v1/admin/returns-corrections/returns", headers=owner_headers())
    assert listing.status_code == 200
    assert Decimal(listing.json()["metrics"]["cash_refunded_amount"]) == Decimal("7.00")
    assert Decimal(listing.json()["metrics"]["refunded_amount"]) == Decimal("7.00")
    return headers, body, receipt


def _resume(
    client: TestClient,
    headers: dict[str, str],
    body: dict[str, Any],
    source_id: str,
    *,
    key: str | None = None,
    kind: str = "returns",
) -> Any:
    return client.post(
        f"/v1/{kind}/{source_id}/refund-settlements",
        headers={**headers, "Idempotency-Key": key or new_idempotency_key()},
        json={name: body[name] for name in ("workstation_code", "cash_session_id")},
    )


@pytest.mark.parametrize("payment", ["CASH", "CARD", "MIXED"])
def test_cash_first_refund_uses_actual_capacity_without_fabricating_card(
    client: TestClient, payment: str
) -> None:
    headers, body, receipt = _partial_return(client, payment)
    pending = receipt["financial_refund"]["amount_pending"]
    retry = _resume(client, headers, body, receipt["id"])
    assert retry.status_code == 200
    assert retry.json()["amount_pending"] == pending
    assert len(retry.json()["entries"]) == 1
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0
        assert (
            session.scalar(
                select(func.count())
                .select_from(FinancialEntry)
                .where(
                    FinancialEntry.financial_operation_id
                    == UUID(receipt["financial_refund"]["financial_operation_id"]),
                    FinancialEntry.payment_method_code == "CARD",
                )
            )
            == 0
        )


def test_partial_refund_resumes_in_new_session_and_preserves_old_ack(client: TestClient) -> None:
    headers, body, receipt = _partial_return(client)
    before = receipt["financial_refund"]
    old_cash_id = body["cash_session_id"]
    # The close lifecycle is covered independently; this fixture models its durable result.
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(old_cash_id))
        cash.status, cash.closed_at = "CLOSED", datetime.now(UTC)
        session.commit()
    headers = login_headers(
        client,
        email=transfer_cashier_email(SEED_WORKSTATION_CODE),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    opening = client.post(
        "/v1/cash-sessions/open",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "50.00"},
    )
    assert opening.status_code == 201
    body["cash_session_id"] = opening.json()["id"]
    key = new_idempotency_key()
    result = _resume(client, headers, body, receipt["id"], key=key)
    assert result.status_code == 200
    settled = result.json()
    assert settled["state"] == "COMPLETED" and Decimal(settled["amount_pending"]) == 0
    assert len(settled["entries"]) == 2
    assert settled["entries"][0] == before["entries"][0]
    assert settled["entries"][1]["cash_session_id"] == body["cash_session_id"]
    assert _cash_capacity(old_cash_id) == 0
    assert _resume(client, headers, body, receipt["id"], key=key).json() == settled
    recovery = client.get(
        f"/v1/returns/refund-settlements/{key}",
        headers=headers,
        params={name: body[name] for name in ("workstation_code", "cash_session_id")},
    )
    assert recovery.status_code == 200 and recovery.json() == settled
    assert _resume(client, headers, body, receipt["id"]).json() == settled


def test_two_continuations_cannot_repeat_completed_refund_leg(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body, receipt = _partial_return(client)
    _movement(client, headers, body, Decimal("50.00"), incoming=True)
    rival_station = "POS-REFUND-RESUME-02"
    with SessionLocal() as session:
        original = session.get(CashSession, UUID(body["cash_session_id"]))
        session.add(
            Workstation(
                branch_id=original.branch_id, code=rival_station, name="Refund contention fixture"
            )
        )
        session.commit()
    rival_headers = login_headers(
        client,
        email=transfer_cashier_email(rival_station),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=rival_station,
    )
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**rival_headers, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": rival_station, "opening_amount": "50.00"},
    )
    assert opened.status_code == 201
    rival_body = {"workstation_code": rival_station, "cash_session_id": opened.json()["id"]}
    held, release, entered = Event(), Event(), Event()
    owner_pid: dict[str, int] = {}
    contender_pid: dict[str, int] = {}
    original_append = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original_append(self, session, **kwargs)
        if kwargs["event_name"] == "financial_refund.settlement_recorded.v1" and not held.is_set():
            owner_pid["pid"] = transaction_probe(session).backend_pid
            held.set()
            assert release.wait(timeout=20)
        return result

    def run(auth: dict[str, str], command: dict[str, Any], *, contender: bool = False) -> Any:
        cookies = SimpleCookie()
        cookies.load(auth["Cookie"])
        credential = cookies[COOKIE_NAMES["POS"]].value
        with SessionLocal() as session:
            if contender:
                contender_pid["pid"] = session.scalar(select(func.pg_backend_pid()))
            record = session.scalar(
                select(AuthSession).where(
                    AuthSession.credential_hash == secret_hash(credential),
                    AuthSession.status == "ACTIVE",
                )
            )
            actor = session.get(User, record.user_id)
            user = resolve_authorization(session, actor, surface="POS")
            session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
            bind_authorization_scope(
                session,
                user=user,
                capabilities=("returns_corrections.manage",),
                mutation=True,
                surface="POS",
            )
            if contender:
                entered.set()
            return RefundSettlementService("SALE_RETURN").settle(
                session,
                current_user=user,
                key=UUID(new_idempotency_key()),
                request_id=None,
                command=RefundSettlementCommand(
                    source_id=UUID(receipt["id"]),
                    **{name: command[name] for name in ("workstation_code", "cash_session_id")},
                ),
            )

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        first = pool.submit(run, headers, body)
        try:
            assert held.wait(timeout=15)
            second = pool.submit(run, rival_headers, rival_body, contender=True)
            assert entered.wait(timeout=10)
            wait_until_blocked(contender_pid["pid"], owner_pid["pid"])
        finally:
            release.set()
        results = [first.result(timeout=15), second.result(timeout=15)]
    assert [result.status_code for result in results] == [200, 200]
    assert all(result.payload["state"] == "COMPLETED" for result in results)
    assert all(len(result.payload["entries"]) == 2 for result in results)
    expected = Decimal("50.00") - Decimal(receipt["financial_refund"]["amount_pending"])
    assert _cash_capacity(body["cash_session_id"]) == expected
    assert _cash_capacity(rival_body["cash_session_id"]) == Decimal("50.00")


def test_resume_rollback_keeps_obligation_and_cash_unchanged(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers, body, receipt = _partial_return(client)
    _movement(client, headers, body, Decimal("50.00"), incoming=True)
    original = OutboxWriter.append

    def fail(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == "financial_refund.settlement_recorded.v1":
            session.flush()
            raise RuntimeError("Injected refund settlement rollback")
        return result

    key = new_idempotency_key()
    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail)
        with pytest.raises(RuntimeError, match="Injected refund settlement rollback"):
            _resume(client, headers, body, receipt["id"], key=key)
    assert _cash_capacity(body["cash_session_id"]) == Decimal("50.00")
    result = _resume(client, headers, body, receipt["id"], key=key)
    assert result.status_code == 200 and len(result.json()["entries"]) == 2


def test_order_cancel_creates_obligation_and_only_actual_refund_payments(
    client: TestClient,
) -> None:
    headers, body = setup_order(client)
    body["advance_payment_method_code"] = "CARD"
    created = client.post(
        "/v1/orders", headers={**headers, "Idempotency-Key": new_idempotency_key()}, json=body
    )
    assert created.status_code == 201
    order_id = created.json()["id"]
    _movement(client, headers, body, _cash_capacity(body["cash_session_id"]) - Decimal("7.00"))
    canceled = client.post(
        f"/v1/orders/{order_id}/cancel",
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
        json={
            "workstation_code": body["workstation_code"],
            "cash_session_id": body["cash_session_id"],
            "cancellation_reason": "Requested by customer",
        },
    )
    assert canceled.status_code == 200
    refund = canceled.json()["financial_refund"]
    assert Decimal(refund["amount_due"]) == Decimal("20.00")
    assert Decimal(refund["amount_settled"]) == Decimal("7.00")
    assert Decimal(refund["amount_pending"]) == Decimal("13.00")
    _movement(client, headers, body, Decimal("50.00"), incoming=True)
    settled = _resume(client, headers, body, order_id, kind="orders")
    assert settled.status_code == 200 and settled.json()["state"] == "COMPLETED"
    with SessionLocal() as session:
        payments = list(
            session.scalars(
                select(CustomerOrderPayment)
                .where(
                    CustomerOrderPayment.customer_order_id == UUID(order_id),
                    CustomerOrderPayment.payment_type == "REFUND",
                )
                .order_by(CustomerOrderPayment.sequence)
            )
        )
        assert [payment.amount for payment in payments] == [Decimal("7.00"), Decimal("13.00")]
        assert all(
            payment.payment_method_code == "CASH" and payment.financial_entry_id
            for payment in payments
        )
        operation = session.get(FinancialOperation, UUID(refund["financial_operation_id"]))
        assert operation.source_type == "ORDER_CANCELLATION" and operation.source_id == UUID(
            order_id
        )


def test_sale_entitlement_is_not_reopened_by_partial_financial_settlement(
    client: TestClient,
) -> None:
    headers, body, receipt = _partial_return(client)
    body["lines"][0]["returned_quantity"] = "4.000"
    rejected = _post(client, headers, body, new_idempotency_key())
    assert rejected.status_code == 409
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(SaleReturn)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(FinancialOperation)
                .where(FinancialOperation.kind == "SALE_REFUND")
            )
            == 1
        )
    assert Decimal(receipt["financial_refund"]["amount_pending"]) > 0


def test_uncertain_external_leg_reserves_remaining_budget_against_cash_retry(
    client: TestClient,
) -> None:
    headers, body, receipt = _partial_return(client)
    projection = receipt["financial_refund"]
    # A controlled provider fixture models a previously admitted, unresolved external attempt.
    with SessionLocal() as session:
        cash_entry = session.get(FinancialEntry, UUID(projection["entries"][0]["id"]))
        fields = {
            column.name: getattr(cash_entry, column.name)
            for column in FinancialEntry.__table__.columns
            if column.name not in {"id", "recorded_at"}
        }
        fields.update(
            leg_key="provider-fixture",
            payment_method_code="CARD",
            amount=Decimal(projection["amount_pending"]),
            execution_mode="PROVIDER_INTEGRATED",
            state="UNKNOWN",
            confirmed_at=None,
            resolution_kind=None,
            resolution_reference=None,
        )
        session.add(FinancialEntry(**fields))
        session.commit()
    _movement(client, headers, body, Decimal("50.00"), incoming=True)
    result = _resume(client, headers, body, receipt["id"])
    assert result.status_code == 200
    assert result.json()["state"] == "UNKNOWN"
    assert len(result.json()["entries"]) == 2
    assert result.json()["amount_pending"] == projection["amount_pending"]
    assert _cash_capacity(body["cash_session_id"]) == Decimal("50.00")


def test_unadopted_opening_cannot_fabricate_refund_capacity(client: TestClient) -> None:
    headers, body, receipt = _partial_return(client)
    new_cash_id = uuid4()
    with SessionLocal() as session:
        old = session.get(CashSession, UUID(body["cash_session_id"]))
        old.status, old.closed_at = "CLOSED", datetime.now(UTC)
        session.flush()
        session.add(
            CashSession(
                id=new_cash_id,
                branch_id=old.branch_id,
                workstation_id=old.workstation_id,
                user_id=old.user_id,
                opening_amount=Decimal("100.00"),
                status="OPEN",
            )
        )
        session.commit()
    headers = login_headers(
        client,
        email=transfer_cashier_email(SEED_WORKSTATION_CODE),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )
    body["cash_session_id"] = str(new_cash_id)
    result = _resume(client, headers, body, receipt["id"])
    assert result.status_code == 409
    assert _cash_capacity(str(new_cash_id)) == 0
