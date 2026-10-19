"""Real PostgreSQL and HTTP boundary with a test-only authenticated provider double."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from threading import Event
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal, engine
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import Role, User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.payment_terminal.application.services import PaymentTerminalService
from zeromerma_api.modules.payment_terminal.domain.provider import (
    ProviderEvidence,
    ProviderReadiness,
    ProviderState,
    TerminalError,
)
from zeromerma_api.modules.payment_terminal.infrastructure.models import (
    ExternalPaymentEvidence,
    ExternalPaymentOperation,
    PaymentTerminalBinding,
)
from zeromerma_api.modules.payment_terminal.presentation.router import terminal_service
from zeromerma_api.testing.authorization import TEST_OWNER_EMAIL, owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import login_headers

PREFIX = "/v1/payment-terminal"


class FakeProvider:
    """Never registered outside these tests; no network or card data is accepted."""

    def __init__(self):
        self.readiness = ProviderReadiness(
            provider_code="TEST_ONLY",
            environment="SANDBOX",
            contract_evidence_id=uuid4(),
            hardware_evidence_id=uuid4(),
            certification_evidence_id=uuid4(),
        )
        self.calls = []
        self.state = ProviderState.CAPTURED
        self.fail = False
        self.request = None
        self.last_evidence = None
        self.hook = None

    def _result(self, request, method):
        # A second connection sees the committed claim/outbox before any provider contact.
        with SessionLocal() as session:
            operation = session.get(ExternalPaymentOperation, request.operation_id)
            assert operation is not None
            assert session.scalar(
                select(OutboxEvent.id).where(
                    OutboxEvent.aggregate_id == str(operation.id),
                    OutboxEvent.event_name == "payment_terminal.requested.v1",
                )
            )
        self.calls.append(method)
        self.request = request
        if self.hook is not None:
            self.hook()
        if self.fail:
            raise TimeoutError("DO_NOT_PERSIST_PROVIDER_BODY")
        value = ProviderEvidence(
            event_id=f"event-{len(self.calls)}",
            provider_idempotency_key=request.provider_idempotency_key,
            account_reference=request.account_reference,
            terminal_reference=request.terminal_reference,
            amount=request.amount,
            currency_code=request.currency_code,
            state=self.state,
            occurred_at=datetime.now(UTC),
            provider_operation_id=f"provider-{request.operation_id}",
        )
        self.last_evidence = value
        return value

    def execute(self, request):
        return self._result(request, "execute")

    def query(self, request):
        return self._result(request, "query")

    def authenticate_callback(self, body, signature):
        if signature != "test-authenticated" or body != b"opaque-provider-event":
            raise ValueError("DO_NOT_PERSIST_PROVIDER_BODY")
        assert self.last_evidence is not None
        return self.last_evidence


@pytest.fixture
def terminal(client):
    pos = login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    opened = client.post(
        "/v1/cash-sessions/open",
        headers={**pos, "Idempotency-Key": new_idempotency_key()},
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "0.00"},
    )
    assert opened.status_code == 201
    headers = owner_headers()
    provider = FakeProvider()
    service = PaymentTerminalService({("TEST_ONLY", "SANDBOX"): provider})
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(opened.json()["id"]))
        actor = session.scalar(select(User).where(User.email == TEST_OWNER_EMAIL))
        binding = PaymentTerminalBinding(
            id=uuid4(),
            branch_id=cash.branch_id,
            workstation_id=cash.workstation_id,
            provider_code="TEST_ONLY",
            environment="SANDBOX",
            account_reference="merchant-1",
            terminal_reference="terminal-1",
            is_active=True,
            contract_evidence_id=provider.readiness.contract_evidence_id,
            hardware_evidence_id=provider.readiness.hardware_evidence_id,
            certification_evidence_id=provider.readiness.certification_evidence_id,
        )
        session.add(binding)
        session.commit()
        values = dict(
            branch_id=cash.branch_id,
            workstation_id=cash.workstation_id,
            cash_session_id=cash.id,
            actor_id=actor.id,
            currency_code="MXN",
            context_version=1,
            source_app="BACKOFFICE",
            actor_type="USER",
            operation_id=uuid4(),
            correlation_id=uuid4(),
            related_branch_ids=[str(cash.branch_id)],
            occurred_at=datetime.now(UTC),
        )
        context = {
            "headers": headers,
            "pos": pos,
            "provider": provider,
            "service": service,
            "binding_id": binding.id,
            "values": values,
            "subject_id": uuid4(),
        }
    context["entry_id"] = _leg(context)
    client.app.dependency_overrides[terminal_service] = lambda: service
    yield context
    client.app.dependency_overrides.pop(terminal_service, None)


def _leg(context, *, refund=False, amount="20.00", **overrides):
    with SessionLocal() as session:
        kind = "ORDER_REFUND" if refund else "ORDER_ADVANCE"
        parent = FinancialOperation(
            id=uuid4(),
            kind=kind,
            source_type="ORDER_PAYMENT",
            source_id=uuid4(),
            effect_code=kind,
            subject_type="ORDER",
            subject_id=context["subject_id"],
            amount_due=Decimal(amount),
            **context["values"],
        )
        session.add(parent)
        session.flush()
        values = dict(
            id=uuid4(),
            financial_operation_id=parent.id,
            leg_key="provider-1",
            payment_method_code="CARD",
            direction="OUT" if refund else "IN",
            amount=Decimal(amount),
            change_amount=Decimal("0.00"),
            state="PENDING",
            execution_mode="PROVIDER_INTEGRATED",
            **context["values"],
        )
        values.update(overrides)
        entry = FinancialEntry(**values)
        session.add(entry)
        session.commit()
        return entry.id


def _admit(client, context, *, key=None, **changes):
    body = {
        "financial_entry_id": str(context["entry_id"]),
        "terminal_binding_id": str(context["binding_id"]),
    }
    body.update(changes)
    return client.post(
        f"{PREFIX}/operations",
        headers={**context["headers"], "Idempotency-Key": key or new_idempotency_key()},
        json=body,
    )


def _operation(client, context):
    response = _admit(client, context)
    assert response.status_code == 202, response.text
    return UUID(response.json()["id"])


def _dispatch(client, context, operation_id, action="dispatch"):
    return client.post(f"{PREFIX}/operations/{operation_id}/{action}", headers=context["headers"])


def _authorized(session):
    actor = session.scalar(select(User).where(User.email == TEST_OWNER_EMAIL))
    user = resolve_authorization(session, actor, surface="BACKOFFICE")
    bind_authorization_scope(
        session,
        user=user,
        capabilities=("orders.manage", "orders.cancel"),
        mutation=True,
        surface="BACKOFFICE",
    )
    return user


def test_default_bootstrap_and_request_keep_real_provider_gate_closed(client, terminal):
    client.app.dependency_overrides.pop(terminal_service)
    bootstrap = client.get(f"{PREFIX}/bootstrap", headers=terminal["headers"])
    assert bootstrap.status_code == 200
    assert bootstrap.json()["integrated_payments_enabled"] is False
    assert bootstrap.json()["manual_fallback_enabled"] is False
    assert bootstrap.json()["final_pilot_start"] == "POSTPONED"
    assert _admit(client, terminal).status_code == 503
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExternalPaymentOperation)) == 0


def test_admission_replay_and_new_key_cannot_duplicate_the_same_causal_leg(client, terminal):
    key = new_idempotency_key()
    first = _admit(client, terminal, key=key)
    assert first.status_code == 202
    replay = _admit(client, terminal, key=key)
    assert replay.status_code == 202 and replay.json() == first.json()
    assert replay.headers["Idempotency-Replayed"] == "true"
    duplicate = _admit(client, terminal)
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "EXTERNAL_PAYMENT_ALREADY_PENDING"
    assert terminal["provider"].calls == []
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExternalPaymentOperation)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.event_name == "payment_terminal.requested.v1")
            )
            == 1
        )


@pytest.mark.parametrize(
    "state,entry_state",
    [
        (ProviderState.CAPTURED, "CONFIRMED"),
        (ProviderState.AUTHORIZED, "PROCESSING"),
        (ProviderState.DECLINED, "REJECTED"),
        (ProviderState.FAILED, "REJECTED"),
        (ProviderState.PROCESSING, "PROCESSING"),
        (ProviderState.UNKNOWN, "UNKNOWN"),
    ],
)
def test_only_captured_evidence_confirms_and_other_states_remain_explicit(
    client, terminal, state, entry_state
):
    operation_id = _operation(client, terminal)
    terminal["provider"].state = state
    response = _dispatch(client, terminal, operation_id)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == state.value
    with SessionLocal() as session:
        entry = session.get(FinancialEntry, terminal["entry_id"])
        assert entry.state == entry_state
        assert (entry.confirmed_at is not None) == (state == ProviderState.CAPTURED)
    assert terminal["provider"].calls == ["execute"]


def test_timeout_reconcile_and_late_callback_preserve_one_identity_and_one_fact(client, terminal):
    operation_id = _operation(client, terminal)
    provider = terminal["provider"]
    provider.fail = True
    unknown = _dispatch(client, terminal, operation_id)
    assert unknown.status_code == 200 and unknown.json()["status"] == "UNKNOWN"
    original_key = provider.request.provider_idempotency_key
    provider.fail = False
    captured = _dispatch(client, terminal, operation_id, "reconcile")
    assert captured.status_code == 200 and captured.json()["status"] == "CAPTURED"
    assert provider.request.provider_idempotency_key == original_key
    assert provider.calls == ["execute", "query"]
    with SessionLocal() as session:
        user = _authorized(session)
        terminal["service"].callback(
            session,
            current_user=user,
            operation_id=operation_id,
            body=b"opaque-provider-event",
            signature="test-authenticated",
        )
    assert _dispatch(client, terminal, operation_id).status_code == 200
    assert provider.calls == ["execute", "query"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExternalPaymentEvidence)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.event_name == "payment_terminal.evidence_recorded.v1")
            )
            == 1
        )
        traces = session.scalars(select(AuditLog.metadata_)).all()
        assert "DO_NOT_PERSIST_PROVIDER_BODY" not in json.dumps(traces)
        operation = session.get(ExternalPaymentOperation, operation_id)
        transitions = session.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == str(operation_id),
                AuditLog.action == "payment_terminal.evidence_recorded",
            )
        ).all()
        assert len(transitions) == 1
        assert transitions[0].correlation_id == operation.idempotency_record_id
        assert transitions[0].causation_id == operation.idempotency_record_id
        assert transitions[0].metadata_["previous_status"] == "UNKNOWN"
        assert transitions[0].metadata_["amount"] == "20.00"


def test_failed_local_result_commit_recovers_by_query_without_reexecuting_provider(
    client, terminal, monkeypatch
):
    operation_id = _operation(client, terminal)
    original = OutboxWriter.append

    def fail_result(self, session, **kwargs):
        if kwargs["event_name"] == "payment_terminal.evidence_recorded.v1":
            raise RuntimeError("injected result failure")
        return original(self, session, **kwargs)

    monkeypatch.setattr(OutboxWriter, "append", fail_result)
    with pytest.raises(RuntimeError, match="injected result failure"):
        _dispatch(client, terminal, operation_id)
    monkeypatch.setattr(OutboxWriter, "append", original)
    with SessionLocal() as session:
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "PROCESSING"
        assert session.scalar(select(func.count()).select_from(ExternalPaymentEvidence)) == 0
    response = _dispatch(client, terminal, operation_id)
    assert response.status_code == 200 and response.json()["status"] == "CAPTURED"
    assert terminal["provider"].calls == ["execute", "query"]


def test_external_contact_holds_no_cash_lock_and_closed_turn_rejects_late_posting(client, terminal):
    operation_id = _operation(client, terminal)

    def close_during_contact():
        with SessionLocal() as session:
            session.execute(text("SET LOCAL lock_timeout = '200ms'"))
            cash = session.scalar(
                select(CashSession)
                .where(CashSession.id == terminal["values"]["cash_session_id"])
                .with_for_update()
            )
            cash.status = "CLOSED"
            cash.closed_at = datetime.now(UTC)
            session.commit()

    terminal["provider"].hook = close_during_contact
    response = _dispatch(client, terminal, operation_id)
    assert response.status_code == 409
    assert response.json()["code"] == "CASH_SESSION_CLOSED"
    with SessionLocal() as session:
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "PROCESSING"
        assert session.scalar(select(func.count()).select_from(ExternalPaymentEvidence)) == 0
    assert (
        client.get(f"{PREFIX}/operations/{operation_id}", headers=terminal["headers"]).status_code
        == 200
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", Decimal("21.00")),
        ("currency_code", "USD"),
        ("terminal_reference", "other-terminal"),
    ],
)
def test_mismatched_provider_evidence_never_confirms(client, terminal, field, value):
    operation_id = _operation(client, terminal)
    provider = terminal["provider"]
    original = provider.execute
    provider.execute = lambda request: replace(original(request), **{field: value})
    response = _dispatch(client, terminal, operation_id)
    assert response.status_code == 409
    with SessionLocal() as session:
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "PROCESSING"
        assert session.scalar(select(func.count()).select_from(ExternalPaymentEvidence)) == 0


def test_callback_authentication_and_duplicate_event_payload_are_enforced(client, terminal):
    operation_id = _operation(client, terminal)
    assert _dispatch(client, terminal, operation_id).status_code == 200
    with SessionLocal() as session:
        user = _authorized(session)
        with pytest.raises(TerminalError, match="authentication failed"):
            terminal["service"].callback(
                session,
                current_user=user,
                operation_id=operation_id,
                body=b"untrusted",
                signature="invalid",
            )
    with SessionLocal() as session:
        user = _authorized(session)
        changed = replace(terminal["provider"].last_evidence, occurred_at=datetime.now(UTC))
        with pytest.raises(TerminalError, match="reused"):
            terminal["service"].apply_evidence(
                session, current_user=user, operation_id=operation_id, evidence=changed
            )


def test_partial_provider_refunds_reserve_cumulative_capture_and_use_original_identity(
    client, terminal
):
    captured_id = _operation(client, terminal)
    assert _dispatch(client, terminal, captured_id).status_code == 200
    terminal["entry_id"] = _leg(terminal, refund=True, amount="12.00")
    first = _admit(client, terminal, original_operation_id=str(captured_id))
    assert first.status_code == 202, first.text
    terminal["provider"].state = ProviderState.REFUNDED
    refund_id = UUID(first.json()["id"])
    assert _dispatch(client, terminal, refund_id).json()["status"] == "REFUNDED"
    assert terminal["provider"].request.original_provider_operation_id == f"provider-{captured_id}"
    terminal["entry_id"] = _leg(terminal, refund=True, amount="9.00")
    exceeded = _admit(client, terminal, original_operation_id=str(captured_id))
    assert (
        exceeded.status_code == 409
        and exceeded.json()["code"] == "EXTERNAL_REFUND_EXCEEDS_ELIGIBLE_AMOUNT"
    )


def test_accounting_only_and_manual_fallback_legs_cannot_be_submitted(client, terminal):
    for mode in ("ACCOUNTING_ONLY", "MANUAL_FALLBACK"):
        terminal["entry_id"] = _leg(terminal, execution_mode=mode)
        response = _admit(client, terminal)
        assert (
            response.status_code == 409
            and response.json()["code"] == "EXTERNAL_PAYMENT_LEG_INVALID"
        )
    assert terminal["provider"].calls == []


def test_wrong_station_actor_cannot_read_or_dispatch_backoffice_leg(client, terminal):
    operation_id = _operation(client, terminal)
    response = client.get(f"{PREFIX}/operations/{operation_id}", headers=terminal["pos"])
    assert response.status_code in {403, 404}
    assert client.post(
        f"{PREFIX}/operations/{operation_id}/dispatch", headers=terminal["pos"]
    ).status_code in {403, 404}
    assert client.get(f"{PREFIX}/operations/{operation_id}").status_code == 401


def test_binding_gate_evidence_and_activity_are_enforced(client, terminal):
    with SessionLocal() as session:
        binding = session.get(PaymentTerminalBinding, terminal["binding_id"])
        binding.is_active = False
        session.commit()
    response = _admit(client, terminal)
    assert (
        response.status_code == 409
        and response.json()["code"] == "EXTERNAL_PAYMENT_TERMINAL_INVALID"
    )


@pytest.mark.parametrize(
    "change",
    ["inactive", "contract_evidence_id", "hardware_evidence_id", "certification_evidence_id"],
)
def test_first_dispatch_revalidates_admitted_binding_approval(client, terminal, change):
    operation_id = _operation(client, terminal)
    provider = terminal["provider"]
    if change == "inactive":
        with SessionLocal() as session:
            binding = session.get(PaymentTerminalBinding, terminal["binding_id"])
            binding.is_active = False
            session.commit()
    else:
        provider.readiness = replace(provider.readiness, **{change: uuid4()})
    response = _dispatch(client, terminal, operation_id)
    assert response.status_code == 409
    assert response.json()["code"] == (
        "EXTERNAL_PAYMENT_TERMINAL_INVALID"
        if change == "inactive"
        else "EXTERNAL_PAYMENT_GATE_CLOSED"
    )
    assert provider.calls == []
    with SessionLocal() as session:
        assert session.get(ExternalPaymentOperation, operation_id).status == "CREATED"
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "PENDING"
        assert session.scalar(select(ExternalPaymentEvidence.id)) is None
        assert (
            session.scalar(
                select(OutboxEvent.id).where(
                    OutboxEvent.aggregate_id == str(operation_id),
                    OutboxEvent.event_name == "payment_terminal.processing.v1",
                )
            )
            is None
        )


def test_uncertain_operation_can_reconcile_after_binding_approval_changes(client, terminal):
    operation_id = _operation(client, terminal)
    provider = terminal["provider"]
    provider.fail = True
    assert _dispatch(client, terminal, operation_id).json()["status"] == "UNKNOWN"
    original_key = provider.request.provider_idempotency_key
    with SessionLocal() as session:
        binding = session.get(PaymentTerminalBinding, terminal["binding_id"])
        binding.is_active = False
        session.commit()
    provider.readiness = replace(provider.readiness, certification_evidence_id=uuid4())
    provider.fail = False
    recovered = _dispatch(client, terminal, operation_id, "reconcile")
    assert recovered.status_code == 200 and recovered.json()["status"] == "CAPTURED"
    assert provider.calls == ["execute", "query"]
    assert provider.request.provider_idempotency_key == original_key
    with SessionLocal() as session:
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "CONFIRMED"


def test_provider_evidence_and_intention_identity_are_immutable(client, terminal):
    operation_id = _operation(client, terminal)
    assert _dispatch(client, terminal, operation_id).status_code == 200
    with engine.connect() as connection:
        for statement in (
            "UPDATE external_payment_operations SET amount=amount+1",
            "DELETE FROM external_payment_operations",
            "UPDATE external_payment_evidence SET state='DECLINED'",
            "DELETE FROM external_payment_evidence",
        ):
            with pytest.raises(IntegrityError):
                connection.execute(text(statement))
            connection.rollback()


def test_late_conflicting_evidence_is_auditable_without_rewriting_confirmed_money(client, terminal):
    operation_id = _operation(client, terminal)
    assert _dispatch(client, terminal, operation_id).status_code == 200
    with SessionLocal() as session:
        user = _authorized(session)
        original = terminal["provider"].last_evidence
        changed = replace(original, event_id="late-contradiction", state=ProviderState.DECLINED)
        result = terminal["service"].apply_evidence(
            session, current_user=user, operation_id=operation_id, evidence=changed
        )
        assert result.status == "CAPTURED"
        assert result.reconciliation_status == "DISCREPANCY"
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "CONFIRMED"
        assert session.scalar(select(func.count()).select_from(ExternalPaymentEvidence)) == 2
        assert session.scalar(
            select(OutboxEvent.id).where(
                OutboxEvent.event_name == "payment_terminal.discrepancy_detected.v1"
            )
        )


def test_concurrent_dispatch_and_poll_send_once_and_converge_on_one_financial_fact(
    client, terminal
):
    operation_id = _operation(client, terminal)
    reached_provider = Event()
    release_provider = Event()
    provider = terminal["provider"]
    original_execute = provider.execute

    def delayed_execute(request):
        reached_provider.set()
        assert release_provider.wait(15)
        return original_execute(request)

    provider.execute = delayed_execute

    def run_dispatch(reconcile):
        with SessionLocal() as session:
            user = _authorized(session)
            return terminal["service"].dispatch(
                session, current_user=user, operation_id=operation_id, reconcile_only=reconcile
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        sending = pool.submit(run_dispatch, False)
        try:
            assert reached_provider.wait(15)
            polling = pool.submit(run_dispatch, True)
            assert polling.result(timeout=15).status == "CAPTURED"
        finally:
            release_provider.set()
        assert sending.result(timeout=15).status == "CAPTURED"
    assert sorted(provider.calls) == ["execute", "query"]
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExternalPaymentOperation)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(FinancialEntry)
                .where(
                    FinancialEntry.financial_operation_id
                    == session.get(FinancialEntry, terminal["entry_id"]).financial_operation_id,
                    FinancialEntry.state == "CONFIRMED",
                )
            )
            == 1
        )


def test_unknown_integrated_leg_blocks_close_and_admission_failure_is_atomic(
    client, terminal, monkeypatch
):
    original = OutboxWriter.append

    def fail_requested(self, session, **kwargs):
        if kwargs["event_name"] == "payment_terminal.requested.v1":
            raise RuntimeError("injected admission failure")
        return original(self, session, **kwargs)

    monkeypatch.setattr(OutboxWriter, "append", fail_requested)
    with pytest.raises(RuntimeError, match="injected admission failure"):
        _admit(client, terminal)
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ExternalPaymentOperation)) == 0
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "payment_terminal.requested")
            )
            == 0
        )
    monkeypatch.setattr(OutboxWriter, "append", original)
    operation_id = _operation(client, terminal)
    terminal["provider"].fail = True
    assert _dispatch(client, terminal, operation_id).json()["status"] == "UNKNOWN"
    preview = client.post(
        "/v1/cash-close/preview",
        headers=terminal["pos"],
        json={
            "workstation_code": SEED_WORKSTATION_CODE,
            "close_mode": "WITH_COUNT",
            "counter_empty_confirmed": True,
            "counted_payment_methods": [
                {"payment_method_code": "CASH", "counted_amount": "0.00"},
                {"payment_method_code": "CARD", "counted_amount": "0.00"},
            ],
        },
    )
    assert preview.status_code == 200
    assert "UNRESOLVED_FINANCIAL_EFFECT" in {item["code"] for item in preview.json()["blockers"]}


def test_permission_revoked_during_provider_contact_cannot_post_a_late_financial_fact(
    client, terminal
):
    terminal["headers"] = login_headers(
        client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD, audience="BACKOFFICE"
    )
    operation_id = _operation(client, terminal)

    def revoke_during_contact():
        with SessionLocal() as session:
            role = session.scalar(select(Role).where(Role.code == "admin"))
            role.is_active = False
            session.commit()

    terminal["provider"].hook = revoke_during_contact
    response = _dispatch(client, terminal, operation_id)
    assert response.status_code == 403
    with SessionLocal() as session:
        assert session.get(FinancialEntry, terminal["entry_id"]).state == "PROCESSING"
        assert session.scalar(select(func.count()).select_from(ExternalPaymentEvidence)) == 0
    assert terminal["provider"].calls == ["execute"]
