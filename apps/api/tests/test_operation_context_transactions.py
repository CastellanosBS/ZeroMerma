"""Keep PostgreSQL trace settings and request/session snapshots consistent across savepoints."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from zeromerma_api.core.operation_context import (
    OperationContext,
    RequestOperation,
    SourceApp,
    request_operation,
)
from zeromerma_api.db.operation_context import bind_operation_context, get_operation_context
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity.application.session_services import SessionService
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def _context(source: SourceApp) -> OperationContext:
    return replace(
        OperationContext.start(source, request_id=str(uuid4())),
        actor_id=uuid4(),
        branch_id=uuid4(),
        workstation_id=uuid4(),
        cash_session_id=uuid4(),
        related_branch_ids=(uuid4(),),
        causation_id=uuid4(),
        idempotency_key=uuid4(),
        operation_code="context.transaction.test",
    )


def _assert_context(
    session: Session, carrier: RequestOperation, expected: OperationContext
) -> None:
    assert get_operation_context(session) == expected
    assert carrier.context == expected
    values = expected.log_fields()
    actual = (
        session.execute(
            select(
                *(func.current_setting(f"zeromerma.{field}", True).label(field) for field in values)
            )
        )
        .mappings()
        .one()
    )
    for field, value in values.items():
        assert actual[field] == (json.dumps(value) if isinstance(value, list) else value or "")


def _assert_new_trace_pair(session: Session, expected: OperationContext) -> None:
    audit = AuditRecorder().record(
        session,
        actor_id=expected.actor_id,
        branch_id=expected.branch_id,
        action="context.transaction.test",
        resource_type="context_test",
        resource_id="savepoint",
        request_id=expected.request_id,
        metadata={},
    )
    event = OutboxWriter().append(
        session,
        aggregate_type="context_test",
        aggregate_id="savepoint",
        event_name="context.transaction.test",
        payload={},
    )
    session.flush()
    for row in (audit, event):
        assert row.operation_id == expected.operation_id
        assert row.correlation_id == expected.correlation_id
        assert row.request_id == expected.request_id
        assert row.source_app == expected.source_app
        assert row.actor_id == expected.actor_id


@pytest.mark.parametrize("materialize_savepoint", [False, True])
def test_savepoint_rollback_restores_database_session_and_request_context(
    materialize_savepoint: bool,
) -> None:
    original, replacement = _context(SourceApp.POS), _context(SourceApp.BACKOFFICE)
    carrier = RequestOperation(original)
    token = request_operation.set(carrier)
    try:
        with SessionLocal() as session:
            _assert_context(session, carrier, original)
            nested = session.begin_nested()
            if materialize_savepoint:
                session.execute(select(1))
            bind_operation_context(session, replacement)
            _assert_context(session, carrier, replacement)
            nested.rollback()
            _assert_context(session, carrier, original)
            _assert_new_trace_pair(session, original)
            session.rollback()
    finally:
        request_operation.reset(token)


def test_committed_savepoint_context_is_the_parent_for_a_later_rollback() -> None:
    original, committed, rejected = (
        _context(SourceApp.POS),
        _context(SourceApp.BACKOFFICE),
        _context(SourceApp.API),
    )
    carrier = RequestOperation(original)
    token = request_operation.set(carrier)
    try:
        with SessionLocal() as session:
            _assert_context(session, carrier, original)
            with session.begin_nested():
                bind_operation_context(session, committed)
            _assert_context(session, carrier, committed)
            nested = session.begin_nested()
            bind_operation_context(session, rejected)
            nested.rollback()
            _assert_context(session, carrier, committed)
            _assert_new_trace_pair(session, committed)
            session.rollback()
    finally:
        request_operation.reset(token)


def test_lazy_root_savepoint_rollback_restores_the_original_request_context() -> None:
    original, replacement = _context(SourceApp.POS), _context(SourceApp.BACKOFFICE)
    carrier = RequestOperation(original)
    token = request_operation.set(carrier)
    try:
        with SessionLocal() as session:
            nested = session.begin_nested()
            bind_operation_context(session, replacement)
            _assert_context(session, carrier, replacement)
            nested.rollback()
            _assert_context(session, carrier, original)
            _assert_new_trace_pair(session, original)
            session.rollback()
    finally:
        request_operation.reset(token)


def test_outer_savepoint_rollback_undoes_context_from_released_inner_savepoint() -> None:
    original, middle, inner = (
        _context(SourceApp.POS),
        _context(SourceApp.BACKOFFICE),
        _context(SourceApp.API),
    )
    carrier = RequestOperation(original)
    token = request_operation.set(carrier)
    try:
        with SessionLocal() as session:
            _assert_context(session, carrier, original)
            outer = session.begin_nested()
            bind_operation_context(session, middle)
            with session.begin_nested():
                bind_operation_context(session, inner)
            _assert_context(session, carrier, inner)
            outer.rollback()
            _assert_context(session, carrier, original)
            session.rollback()
    finally:
        request_operation.reset(token)


@pytest.mark.parametrize("commit_first", [False, True])
def test_reused_session_uses_the_next_request_context_after_root_end(commit_first: bool) -> None:
    first, second = _context(SourceApp.POS), _context(SourceApp.BACKOFFICE)
    with SessionLocal() as session:
        first_carrier = RequestOperation(first)
        token = request_operation.set(first_carrier)
        try:
            _assert_context(session, first_carrier, first)
            session.commit() if commit_first else session.rollback()
        finally:
            request_operation.reset(token)
        second_carrier = RequestOperation(second)
        token = request_operation.set(second_carrier)
        try:
            _assert_context(session, second_carrier, second)
            _assert_new_trace_pair(session, second)
            assert first_carrier.context == first
            session.rollback()
        finally:
            request_operation.reset(token)


def test_disconnected_savepoint_preserves_error_and_next_transaction_context() -> None:
    original, interrupted, healthy = (
        _context(SourceApp.POS),
        _context(SourceApp.BACKOFFICE),
        _context(SourceApp.API),
    )
    carrier = RequestOperation(original)
    token = request_operation.set(carrier)
    try:
        with SessionLocal() as session:
            _assert_context(session, carrier, original)
            connection = session.connection()
            original_error: DBAPIError | None = None
            with pytest.raises(DBAPIError) as failure:
                with session.begin_nested():
                    bind_operation_context(session, interrupted)
                    _assert_new_trace_pair(session, interrupted)
                    backend_pid = session.scalar(select(func.pg_backend_pid()))
                    with SessionLocal() as controller:
                        assert controller.scalar(select(func.pg_terminate_backend(backend_pid)))
                    try:
                        session.execute(select(1))
                    except DBAPIError as error:
                        original_error = error
                        raise
            assert failure.value is original_error
            assert original_error.connection_invalidated
            assert connection.invalidated
            # Cleanup must restore snapshots without issuing SQL on the dead transaction.
            assert get_operation_context(session) == carrier.context == original
            session.rollback()
            assert not session.in_transaction()

            next_carrier = RequestOperation(healthy)
            next_token = request_operation.set(next_carrier)
            try:
                _assert_context(session, next_carrier, healthy)
                _assert_new_trace_pair(session, healthy)
                session.commit()
                assert carrier.context == original
            finally:
                request_operation.reset(next_token)
        with SessionLocal() as observer:
            for model in (AuditLog, OutboxEvent):
                assert (
                    observer.scalar(
                        select(model.id).where(model.operation_id == interrupted.operation_id)
                    )
                    is None
                )
                row = observer.scalars(
                    select(model).where(model.operation_id == healthy.operation_id)
                ).one()
                assert row.correlation_id == healthy.correlation_id
                assert row.request_id == healthy.request_id
                assert row.source_app == healthy.source_app
    finally:
        request_operation.reset(token)


@pytest.mark.parametrize("authenticated", [False, True])
def test_authentication_rate_limit_keeps_audit_and_outbox_actor_consistent(
    authenticated: bool,
) -> None:
    context = (
        _context(SourceApp.POS)
        if authenticated
        else OperationContext.start(SourceApp.API, request_id=str(uuid4()))
    )
    service = SessionService()
    service.settings = service.settings.model_copy(
        update={"auth_login_account_limit": 1, "auth_login_ip_limit": 100}
    )
    carrier = RequestOperation(context)
    token = request_operation.set(carrier)
    now = datetime.now(UTC)
    try:
        with SessionLocal() as session:
            bind_operation_context(session, context)
            for attempt in range(3):
                rejection = service._rate_attempt(
                    session,
                    account="trace-rate-limit@example.test",
                    ip="127.0.0.1",
                    now=now,
                    request_id=context.request_id,
                )
                if attempt == 0:
                    assert rejection is None
                else:
                    assert rejection is not None and rejection.status_code == 429
                session.flush()
            audits = session.scalars(
                select(AuditLog).where(AuditLog.operation_id == context.operation_id)
            ).all()
            events = session.scalars(
                select(OutboxEvent).where(OutboxEvent.operation_id == context.operation_id)
            ).all()
            assert len(audits) == len(events) == 2
            assert all(row.action == "login.rate_limited" for row in audits)
            assert all(row.event_name == "login.rate_limited" for row in events)
            for row in (*audits, *events):
                assert row.actor_id == context.actor_id
                assert row.actor_type == ("USER" if authenticated else "ANONYMOUS")
                assert row.branch_id == context.branch_id
                assert row.request_id == context.request_id
                assert row.correlation_id == context.correlation_id
                assert row.source_app == context.source_app
            session.rollback()
    finally:
        request_operation.reset(token)
