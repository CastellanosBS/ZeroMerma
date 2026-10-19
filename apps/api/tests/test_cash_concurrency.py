"""DEC-06 races on disposable PostgreSQL, independently of HTTP authentication locks.

Each competitor uses real persisted authority and a separate transaction. HTTP authenticates
User/AuthSession first and serializes one user's requests; these tests deliberately exercise
the business boundary itself, including order ledger admission and its cash-close effect.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from http.cookies import SimpleCookie
from threading import Barrier, Event
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_PRODUCT_BOLILLO_STD_CODE,
    SEED_PRODUCT_CAFE_AMERICANO_CODE,
    SEED_PRODUCT_COCA_355_CODE,
    SEED_PRODUCT_CONCHA_VAN_CODE,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.concurrency import CommandConcurrencyConflict
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.application.idempotency import CashCloseCommitService
from zeromerma_api.modules.cash_close.application.schemas import CashCloseCommitRequest
from zeromerma_api.modules.cash_close.infrastructure.models import (
    BranchCounterSnapshot,
    BranchCounterSnapshotLine,
    CashSessionClose,
    CashSessionCloseReconciliationAttribution,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.discounts.application.idempotency import OperationalDiscountCommitService
from zeromerma_api.modules.discounts.application.schemas import CreateOperationalDiscountRequest
from zeromerma_api.modules.discounts.infrastructure.models import OperationalDiscount
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.schemas import IdempotencyResult
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyError
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    COOKIE_NAMES,
    SessionAuthentication,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.orders.application.idempotency import OrdersIdempotencyService
from zeromerma_api.modules.orders.application.schemas import (
    CancelCustomerOrderRequest,
    CreateCustomerOrderRequest,
    DeliverCustomerOrderRequest,
)
from zeromerma_api.modules.orders.domain.exceptions import OrderStateConflictError
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrderPayment
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.payments.application.idempotency import OperationalPaymentCommitService
from zeromerma_api.modules.payments.application.schemas import CreateOperationalPaymentRequest
from zeromerma_api.modules.payments.infrastructure.models import OperationalPayment
from zeromerma_api.modules.returns.application.idempotency import ReturnCommitService
from zeromerma_api.modules.returns.application.schemas import ReturnCommitRequest
from zeromerma_api.modules.sales.application.idempotency import SaleConfirmationService
from zeromerma_api.modules.sales.application.schemas import ConfirmSaleRequest
from zeromerma_api.modules.sales.infrastructure.models import CashMovement, Sale
from zeromerma_api.testing.concurrency import (
    TransactionProbe,
    transaction_probe,
    wait_until_blocked,
)
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers
from zeromerma_api.testing.transfer_operators import transfer_cashier_email


@dataclass(frozen=True)
class Command:
    kind: str
    body: dict[str, Any]
    headers: dict[str, str]
    key: str
    order_id: str | None = None


EVENTS = {
    "sale": "sale.confirmed.v1",
    "return": "sale_return.committed.v1",
    "create": "order.created.v1",
    "deliver": "order.delivered.v1",
    "cancel": "order.canceled.v1",
    "close": "cash_session.closed.v1",
    "payment": "operational_payment.committed.v1",
    "discount": "operational_discount.committed.v1",
}


def _post(client: TestClient, headers: dict[str, str], path: str, body: dict[str, Any]) -> Any:
    result = client.post(
        path, headers={**headers, "Idempotency-Key": new_idempotency_key()}, json=body
    )
    assert result.status_code in {200, 201}, result.text
    return result.json()


def _baseline(cash_id: str, product_code: str, quantity: int) -> tuple[str, str]:
    """Provide real physical stock so cash tests do not bypass reconciliation blockers."""
    with SessionLocal() as session:
        shift = session.get(CashSession, UUID(cash_id))
        product = session.scalars(select(Product).where(Product.code == product_code)).one()
        product_class = session.get(ProductClass, product.product_class_id)
        baseline = BranchCounterSnapshot(
            branch_id=shift.branch_id,
            source_cash_session_close_id=None,
            snapshot_type="CLOSE_BASELINE",
            captured_by_user_id=shift.user_id,
        )
        session.add(baseline)
        session.flush()
        session.add(
            BranchCounterSnapshotLine(
                snapshot_id=baseline.id,
                product_id=product.id,
                product_code_snapshot=product.code,
                product_name_snapshot=product.name,
                product_class_id=product_class.id,
                product_class_code_snapshot=product_class.code,
                product_class_name_snapshot=product_class.name,
                quantity=quantity,
                bucket_code="COUNTER",
            )
        )
        product_id, class_id = str(product.id), str(product_class.id)
        session.commit()
        return product_id, class_id


def _retain_unsold_stock(close: Command, sale: Command) -> None:
    close.body.update(
        counter_empty_confirmed=False,
        counted_product_lines=[
            {"product_id": sale.body["lines"][0]["product_id"], "counted_quantity": "2.000"}
        ],
    )


def _setup(
    client: TestClient,
    kind: str,
    workstation: str = SEED_WORKSTATION_CODE,
    *,
    payment: str = "CASH",
) -> tuple[Command, Command]:
    email = transfer_cashier_email(workstation)
    headers = login_headers(
        client,
        email=email,
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=workstation,
    )
    opened = _post(
        client,
        headers,
        "/v1/cash-sessions/open",
        {"workstation_code": workstation, "opening_amount": "1000.00"},
    )
    context = {"workstation_code": workstation, "cash_session_id": opened["id"]}
    if kind in {"sale", "return"}:
        _baseline(opened["id"], SEED_PRODUCT_COCA_355_CODE, 2)
    with SessionLocal() as session:
        products = dict(session.execute(select(Product.code, Product.id)).all())
    sale = {
        **context,
        "lines": [
            {
                "capture_mode": "PRODUCT_DIRECT",
                "product_id": str(products[SEED_PRODUCT_COCA_355_CODE]),
                "quantity": "2",
            }
        ],
        "payments": [{"payment_method_code": payment, "tendered_amount": "36.00"}],
    }
    order_id = None
    if kind == "sale":
        body = sale
    elif kind in {"payment", "discount"}:
        body = {
            **context,
            "payee_name" if kind == "payment" else "subject_name": "Fixture party",
            "concept": "Concurrency fixture",
            "payment_method_code": payment,
            "total_amount": "10.00",
        }
    elif kind == "return":
        original = _post(client, headers, "/v1/sales/confirm", sale)
        body = {
            **context,
            "original_sale_id": original["id"],
            "reason_code": "WRONG_ITEM",
            "refund_method_code": "CASH",
            "lines": [
                {
                    "original_sale_line_id": original["lines"][0]["id"],
                    "returned_quantity": "1.000",
                    "disposition_code": "RESTOCK_BACKROOM",
                }
            ],
        }
    else:
        create = {
            **context,
            "customer_name": "Concurrency fixture",
            "requested_for_at": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "items": [
                {"product_id": str(products[SEED_PRODUCT_BOLILLO_STD_CODE]), "quantity": "4"},
                {"product_id": str(products[SEED_PRODUCT_CAFE_AMERICANO_CODE]), "quantity": "1"},
            ],
            "advance_amount": "20.00",
            "advance_payment_method_code": payment,
        }
        body = create
        if kind in {"deliver", "cancel"}:
            created = _post(client, headers, "/v1/orders", create)
            order_id = created["id"]
            if kind == "deliver":
                _post(client, headers, f"/v1/orders/{order_id}/mark-ready", context)
                body = {
                    **context,
                    "settlement_amount": created["remaining_balance_amount"],
                    "settlement_payment_method_code": payment,
                }
            else:
                body = {**context, "cancellation_reason": "Concurrency fixture cancellation"}
    close = {
        **context,
        "close_mode": "WITH_COUNT",
        "counter_empty_confirmed": True,
        "counted_payment_methods": [{"payment_method_code": "CASH", "counted_amount": "1000"}],
        "notes": "Concurrency fixture counted cash",
    }
    return (
        Command(kind, body, headers, new_idempotency_key(), order_id),
        Command("close", close, headers, new_idempotency_key()),
    )


def _run(
    command: Command,
    probes: dict[str, TransactionProbe] | None = None,
    entered: Event | None = None,
) -> IdempotencyResult:
    cookies = SimpleCookie()
    cookies.load(command.headers["Cookie"])
    credential = cookies[COOKIE_NAMES["POS"]].value
    with SessionLocal() as session:
        record = session.scalars(
            select(AuthSession).where(
                AuthSession.credential_hash == secret_hash(credential),
                AuthSession.status == "ACTIVE",
            )
        ).one()
        actor = session.get(User, record.user_id)
        assert actor is not None
        user = resolve_authorization(session, actor, surface="POS")
        session.info[AUTH_CONTEXT_KEY] = SessionAuthentication(record, user, credential)
        capability = (
            "returns_corrections.manage"
            if command.kind == "return"
            else "discounts.manage"
            if command.kind == "discount"
            else "orders.cancel"
            if command.kind == "cancel"
            else "orders.manage"
            if command.kind in {"create", "deliver"}
            else "pos.operate"
        )
        bind_authorization_scope(
            session, user=user, capabilities=(capability,), mutation=True, surface="POS"
        )
        if probes is not None:
            probes[command.key] = transaction_probe(session)
        if entered is not None:
            entered.set()
        common = {"current_user": user, "key": UUID(command.key), "request_id": "cash-race"}
        if command.kind == "sale":
            return SaleConfirmationService().confirm(
                session, command=ConfirmSaleRequest.model_validate(command.body), **common
            )
        if command.kind == "return":
            return ReturnCommitService().commit(
                session, command=ReturnCommitRequest.model_validate(command.body), **common
            )
        if command.kind == "close":
            return CashCloseCommitService().commit(
                session, command=CashCloseCommitRequest.model_validate(command.body), **common
            )
        if command.kind == "payment":
            return OperationalPaymentCommitService().commit(
                session,
                command=CreateOperationalPaymentRequest.model_validate(command.body),
                **common,
            )
        if command.kind == "discount":
            return OperationalDiscountCommitService().commit(
                session,
                command=CreateOperationalDiscountRequest.model_validate(command.body),
                **common,
            )
        schema = {
            "create": CreateCustomerOrderRequest,
            "deliver": DeliverCustomerOrderRequest,
            "cancel": CancelCustomerOrderRequest,
        }[command.kind]
        return OrdersIdempotencyService().execute_pos(
            session,
            command_code=command.kind,
            command=schema.model_validate(command.body),
            order_id=UUID(command.order_id) if command.order_id else None,
            **common,
        )


def _contend(
    monkeypatch: pytest.MonkeyPatch, first: Command, second: Command, *, abort_first: bool = False
) -> tuple[Any, Any]:
    held, release, entered = Event(), Event(), Event()
    probes: dict[str, TransactionProbe] = {}
    original = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == EVENTS[first.kind] and not held.is_set():
            held.set()
            assert release.wait(timeout=20)
            if abort_first:
                raise RuntimeError("Injected rollback while holding the cash boundary")
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        winner = pool.submit(_run, first, probes)
        try:
            assert held.wait(timeout=15)
            waiter = pool.submit(_run, second, probes, entered)
            assert entered.wait(timeout=10)
            a, b = probes[first.key], probes[second.key]
            assert a.transaction_id != b.transaction_id
            wait_until_blocked(b.backend_pid, a.backend_pid)
            print(f"cash boundary transactions: {a} -> {b}")
        finally:
            release.set()
        outcomes = []
        for future in (winner, waiter):
            try:
                outcomes.append(future.result(timeout=20))
            except Exception as error:
                outcomes.append(error)
        return outcomes[0], outcomes[1]


def _effect_counts() -> tuple[int, ...]:
    with SessionLocal() as session:
        return tuple(
            int(session.scalar(select(func.count()).select_from(model)) or 0)
            for model in (
                Sale,
                CustomerOrderPayment,
                CashMovement,
                CashSessionClose,
                IdempotencyRecord,
                AuditLog,
                OutboxEvent,
                FinancialOperation,
                FinancialEntry,
            )
        )


@pytest.mark.parametrize("kind", ["sale", "return", "create", "deliver", "cancel"])
@pytest.mark.parametrize("close_first", [False, True])
def test_financial_commands_and_close_share_exact_shift_boundary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str, close_first: bool
) -> None:
    command, close = _setup(client, kind)
    if close_first and kind == "sale":
        _retain_unsold_stock(close, command)
    before = _effect_counts()
    first, second = (close, command) if close_first else (command, close)
    committed, waited = _contend(monkeypatch, first, second)
    assert isinstance(committed, IdempotencyResult), repr(committed)
    if close_first:
        assert isinstance(waited, IdempotencyError) and waited.code == "CASH_SESSION_CLOSED", repr(
            waited
        )
        with SessionLocal() as session:
            assert (
                session.scalar(
                    select(IdempotencyRecord.id).where(
                        IdempotencyRecord.idempotency_key == UUID(command.key)
                    )
                )
                is None
            )
        after = _effect_counts()
        assert after[:3] == before[:3]
        assert after[-2:] == before[-2:]
    else:
        assert isinstance(waited, IdempotencyResult), repr(waited)
    with SessionLocal() as session:
        shift = session.get(CashSession, UUID(command.body["cash_session_id"]))
        assert shift is not None and shift.status == "CLOSED"
        closed = session.scalars(
            select(CashSessionClose).where(CashSessionClose.cash_session_id == shift.id)
        ).one()
        movements = session.execute(
            select(CashMovement.direction, CashMovement.amount).where(
                CashMovement.cash_session_id == shift.id
            )
        ).all()
        assert movements == []
        cash_entries = session.execute(
            select(FinancialEntry.direction, FinancialEntry.amount, FinancialOperation.kind)
            .join(FinancialOperation)
            .where(
                FinancialEntry.cash_session_id == shift.id,
                FinancialEntry.payment_method_code == "CASH",
                FinancialEntry.state == "CONFIRMED",
            )
        ).all()
        expected = sum(
            (amount if direction == "IN" else -amount for direction, amount, _ in cash_entries),
            Decimal("0"),
        )
        opening_entries = [entry for entry in cash_entries if entry.kind == "CASH_OPENING"]
        assert opening_entries == [("IN", Decimal("1000.00"), "CASH_OPENING")]
        prior_cash = {"return": Decimal("36"), "deliver": Decimal("20"), "cancel": Decimal("20")}
        command_cash = {
            "sale": Decimal("36"),
            "return": Decimal("-18"),
            "create": Decimal("20"),
            "deliver": Decimal("14"),
            "cancel": Decimal("-20"),
        }
        assert expected == Decimal("1000") + prior_cash.get(kind, Decimal("0")) + (
            Decimal("0") if close_first else command_cash[kind]
        )
        assert closed.expected_cash_amount == expected
        # Each order effect has one canonical entry and no mirrored CashMovement.
        if kind in {"create", "deliver", "cancel"}:
            count = session.scalar(
                select(func.count())
                .select_from(CustomerOrderPayment)
                .where(CustomerOrderPayment.cash_session_id == shift.id)
            )
            assert count == before[1] + (0 if close_first else 1)
            assert len(cash_entries) == count + 1  # Opening is also a canonical financial entry.
    fresh = login_headers(
        client,
        email=transfer_cashier_email(command.body["workstation_code"]),
        password=SEED_USER_PASSWORD,
        audience="POS",
        workstation_code=command.body["workstation_code"],
    )
    replay_target = close if close_first else command
    replay = Command(
        replay_target.kind, replay_target.body, fresh, replay_target.key, replay_target.order_id
    )
    effects = _effect_counts()
    recovered = _run(replay)
    assert recovered.replayed and recovered.payload == committed.payload
    assert _effect_counts() == effects


@pytest.mark.parametrize("kind", ["sale", "return", "create", "deliver", "cancel"])
def test_rolled_back_financial_command_releases_close_without_partial_effects(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    command, close = _setup(client, kind)
    if kind == "sale":
        _retain_unsold_stock(close, command)
    before = _effect_counts()
    failed, closed = _contend(monkeypatch, command, close, abort_first=True)
    assert isinstance(failed, RuntimeError) and "Injected rollback" in str(failed)
    assert isinstance(closed, IdempotencyResult), repr(closed)
    assert _effect_counts()[:3] == before[:3]
    assert _effect_counts()[-2:] == before[-2:]
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(IdempotencyRecord.id).where(
                    IdempotencyRecord.idempotency_key == UUID(command.key)
                )
            )
            is None
        )


@pytest.mark.parametrize("kind", ["sale", "return", "create", "close"])
def test_distinct_cash_sessions_make_progress_independently(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    first, first_close = _setup(client, "sale" if kind == "close" else kind)
    second, second_close = _setup(
        client, "sale" if kind == "close" else kind, SEED_DESTINATION_WORKSTATION_CODE
    )
    commands = (first_close, second_close) if kind == "close" else (first, second)
    if kind == "close":
        _retain_unsold_stock(first_close, first)
        _retain_unsold_stock(second_close, second)
    barrier, original = Barrier(2), OutboxWriter.append

    def meet(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == EVENTS[kind]:
            barrier.wait(timeout=15)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", meet)
        futures = [pool.submit(_run, command) for command in commands]
        results = [future.result(timeout=25) for future in futures]
    assert all(isinstance(result, IdempotencyResult) and not result.replayed for result in results)


@pytest.mark.parametrize("close_first", [False, True])
def test_card_sale_also_uses_the_close_boundary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, close_first: bool
) -> None:
    sale, close = _setup(client, "sale", payment="CARD")
    if close_first:
        _retain_unsold_stock(close, sale)
    first, second = _contend(monkeypatch, *((close, sale) if close_first else (sale, close)))
    assert isinstance(first, IdempotencyResult), repr(first)
    if close_first:
        assert isinstance(second, IdempotencyError) and second.code == "CASH_SESSION_CLOSED"
    else:
        assert isinstance(second, IdempotencyResult), repr(second)
        assert second.payload["expected_cash_amount"] == "1000.00"
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0


@pytest.mark.parametrize("close_first", [False, True])
def test_class_sale_is_attributed_only_when_it_precedes_the_locked_close(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, close_first: bool
) -> None:
    sale, close = _setup(client, "sale")
    product_id, class_id = _baseline(sale.body["cash_session_id"], SEED_PRODUCT_CONCHA_VAN_CODE, 3)
    sale.body["lines"] = [
        {"capture_mode": "CLASS_CAPTURE", "product_class_id": class_id, "quantity": "1"}
    ]
    sale.body["payments"] = [{"payment_method_code": "CASH", "tendered_amount": "12.00"}]
    close.body.update(
        counter_empty_confirmed=False,
        counted_product_lines=[
            {"product_id": product_id, "counted_quantity": "3.000" if close_first else "2.000"}
        ],
    )
    first, second = _contend(monkeypatch, *((close, sale) if close_first else (sale, close)))
    assert isinstance(first, IdempotencyResult), repr(first)
    if close_first:
        assert isinstance(second, IdempotencyError) and second.code == "CASH_SESSION_CLOSED"
    else:
        assert isinstance(second, IdempotencyResult), repr(second)
        assert second.payload["expected_cash_amount"] == "1012.00"
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Sale)) == (0 if close_first else 1)
        assert session.scalar(
            select(func.count()).select_from(CashSessionCloseReconciliationAttribution)
        ) == (0 if close_first else 1)


def test_two_distinct_sale_intentions_serialize_without_losing_either_effect(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _close = _setup(client, "sale")
    second = Command("sale", first.body, first.headers, new_idempotency_key())
    a, b = _contend(monkeypatch, first, second)
    assert isinstance(a, IdempotencyResult) and isinstance(b, IdempotencyResult), repr((a, b))
    assert a.payload["id"] != b.payload["id"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Sale)) == 2
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0
        sale_entries = session.scalars(
            select(FinancialEntry)
            .join(FinancialOperation)
            .where(FinancialOperation.kind == "SALE_COLLECTION")
        ).all()
        assert len(sale_entries) == 2
        assert all(
            entry.amount == Decimal("36.00")
            and entry.direction == "IN"
            and entry.payment_method_code == "CASH"
            and entry.state == "CONFIRMED"
            for entry in sale_entries
        )


def test_two_order_settlement_intentions_cannot_collect_the_same_remaining_balance(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _close = _setup(client, "deliver")
    second = Command("deliver", first.body, first.headers, new_idempotency_key(), first.order_id)
    paid, rejected = _contend(monkeypatch, first, second)
    assert isinstance(paid, IdempotencyResult), repr(paid)
    assert isinstance(rejected, OrderStateConflictError), repr(rejected)
    with SessionLocal() as session:
        payments = session.scalars(
            select(CustomerOrderPayment).where(
                CustomerOrderPayment.customer_order_id == UUID(first.order_id),
                CustomerOrderPayment.payment_type == "SETTLEMENT",
            )
        ).all()
        assert len(payments) == 1
        assert payments[0].amount == Decimal("14.00")
        entries = session.scalars(
            select(FinancialEntry)
            .join(FinancialOperation)
            .where(FinancialOperation.kind == "ORDER_SETTLEMENT")
        ).all()
        assert len(entries) == 1 and entries[0].amount == Decimal("14.00")
    before_replay = _effect_counts()
    assert _run(first).replayed
    assert _effect_counts() == before_replay


@pytest.mark.parametrize("kind", ["create", "deliver", "cancel"])
@pytest.mark.parametrize("close_first", [False, True])
def test_card_order_effects_and_cash_first_refunds_serialize_with_close(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str, close_first: bool
) -> None:
    command, close = _setup(client, kind, payment="CARD")
    before = _effect_counts()
    first, second = _contend(monkeypatch, *((close, command) if close_first else (command, close)))
    assert isinstance(first, IdempotencyResult), repr(first)
    if close_first:
        assert isinstance(second, IdempotencyError) and second.code == "CASH_SESSION_CLOSED"
        assert _effect_counts()[-2:] == before[-2:]
    else:
        assert isinstance(second, IdempotencyResult), repr(second)
        assert second.payload["expected_cash_amount"] == (
            "980.00" if kind == "cancel" else "1000.00"
        )
        assert _effect_counts()[-2:] == (before[-2] + 1, before[-1] + 1)
        with SessionLocal() as session:
            effect = session.scalars(
                select(FinancialEntry).where(FinancialEntry.idempotency_key == UUID(command.key))
            ).one()
            assert effect.payment_method_code == ("CASH" if kind == "cancel" else "CARD")
            assert effect.direction == ("OUT" if kind == "cancel" else "IN")
            assert effect.state == "CONFIRMED"


def test_cash_lock_timeout_rolls_back_sale_identity_then_retries_same_intention(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _close = _setup(client, "sale")
    second = Command("sale", first.body, first.headers, new_idempotency_key())
    held, release, entered = Event(), Event(), Event()
    probes: dict[str, TransactionProbe] = {}
    original = OutboxWriter.append

    def hold(self: OutboxWriter, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == EVENTS["sale"] and not held.is_set():
            held.set()
            assert release.wait(timeout=20)
        return result

    with monkeypatch.context() as patch, ThreadPoolExecutor(max_workers=2) as pool:
        patch.setattr(OutboxWriter, "append", hold)
        winner = pool.submit(_run, first, probes)
        try:
            assert held.wait(timeout=15)
            waiter = pool.submit(_run, second, probes, entered)
            assert entered.wait(timeout=10)
            wait_until_blocked(probes[second.key].backend_pid, probes[first.key].backend_pid)
            with pytest.raises(CommandConcurrencyConflict):
                waiter.result(timeout=10)
            with SessionLocal() as session:
                assert (
                    session.scalar(
                        select(IdempotencyRecord.id).where(
                            IdempotencyRecord.idempotency_key == UUID(second.key)
                        )
                    )
                    is None
                )
                assert session.scalar(select(func.count()).select_from(Sale)) == 0
        finally:
            release.set()
        assert winner.result(timeout=15).status_code == 201
    retried = _run(second)
    assert retried.status_code == 201 and not retried.replayed
    replay = _run(second)
    assert replay.replayed and replay.payload == retried.payload
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(Sale)) == 2
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0
        sale_entries = session.scalars(
            select(FinancialEntry)
            .join(FinancialOperation)
            .where(FinancialOperation.kind == "SALE_COLLECTION")
        ).all()
        assert len(sale_entries) == 2
        assert all(
            entry.amount == Decimal("36.00")
            and entry.direction == "IN"
            and entry.payment_method_code == "CASH"
            and entry.state == "CONFIRMED"
            for entry in sale_entries
        )


@pytest.mark.parametrize("kind", ["payment", "discount"])
@pytest.mark.parametrize("close_first", [False, True])
def test_non_cash_operational_commands_still_observe_the_shift_boundary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str, close_first: bool
) -> None:
    command, close = _setup(client, kind, payment="CARD")
    first, second = _contend(monkeypatch, *((close, command) if close_first else (command, close)))
    assert isinstance(first, IdempotencyResult), repr(first)
    if close_first:
        assert isinstance(second, IdempotencyError) and second.code == "CASH_SESSION_CLOSED"
    else:
        assert isinstance(second, IdempotencyResult), repr(second)
        assert second.payload["expected_cash_amount"] == "1000.00"
    with SessionLocal() as session:
        model = OperationalPayment if kind == "payment" else OperationalDiscount
        assert session.scalar(select(func.count()).select_from(model)) == (0 if close_first else 1)
        assert session.scalar(select(func.count()).select_from(CashMovement)) == 0
