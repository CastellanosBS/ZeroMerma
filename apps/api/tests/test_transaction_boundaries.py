"""PostgreSQL evidence for ownership, failure cleanup and nested participants."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from test_idempotency import (
    PROBE_OPERATION,
    ProbePayload,
    ProbeSnapshot,
    _retained_result,
    assert_effects,
    authorize,
    context_for,
    create_effect,
    execute_probe,
    new_key,
)
from test_tickets_module import _confirm_sale, _open_cash_session

from zeromerma_api.bootstrap.seed_local import SEED_USER_EMAIL, SEED_WORKSTATION_CODE
from zeromerma_api.db import session as session_module
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.db.transactions import rollback_on_failure
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.idempotency.application.schemas import CommandResult, ResponsePolicy
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.tickets.application import services as ticket_services
from zeromerma_api.modules.tickets.application.services import TicketsCommandService


@pytest.mark.parametrize("flush", [False, True])
@pytest.mark.parametrize("fail", [False, True])
def test_request_cleanup_never_commits_unfinished_writes(flush: bool, fail: bool) -> None:
    dependency = session_module.get_session()
    session = next(dependency)
    user = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
    original_name, user_id = user.full_name, user.id
    user.full_name = "Uncommitted request name"
    if flush:
        session.flush()
    if fail:
        with pytest.raises(RuntimeError, match="request failed"):
            dependency.throw(RuntimeError("request failed"))
    else:
        with pytest.raises(StopIteration):
            next(dependency)
    assert not session.in_transaction()
    # Even reusing the closed request Session cannot publish its discarded changes.
    session.commit()
    with SessionLocal() as verification:
        assert verification.get(User, user_id).full_name == original_name
    session.close()


def test_request_cleanup_preserves_explicit_commit_and_closes_read_transaction() -> None:
    dependency = session_module.get_session()
    session = next(dependency)
    user = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
    user_id = user.id
    user.full_name = "Explicitly committed request"
    session.commit()
    assert session.scalar(select(User.full_name).where(User.id == user_id)) == user.full_name
    assert session.in_transaction()
    with pytest.raises(StopIteration):
        next(dependency)
    assert not session.in_transaction()
    with SessionLocal() as verification:
        assert verification.get(User, user_id).full_name == "Explicitly committed request"


class InterruptedCommand(BaseException):
    pass


def test_failure_guard_preserves_explicit_ownership_and_cleans_cancellation() -> None:
    class Service:
        @rollback_on_failure
        def change(self, session: Session, *, cancel: bool = False) -> UUID:
            user = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
            user.full_name = "Pending participant change"
            session.flush()
            if cancel:
                raise InterruptedCommand()
            return user.id

    with SessionLocal() as session:
        original = session.scalar(select(User.full_name).where(User.email == SEED_USER_EMAIL))
        with pytest.raises(InterruptedCommand):
            Service().change(session=session, cancel=True)
        assert not session.in_transaction()
        session.commit()
        assert (
            session.scalar(select(User.full_name).where(User.email == SEED_USER_EMAIL)) == original
        )
        session.rollback()
        user_id = Service().change(session=session)
        assert session.in_transaction(), "The failure guard must not introduce auto-commit"
        with SessionLocal() as verification:
            assert verification.get(User, user_id).full_name == original
        session.rollback()


@pytest.mark.parametrize("nested", ["execute", "recover", "purge"])
@pytest.mark.parametrize("propagate", [False, True])
def test_rejected_nested_executor_leaves_rollback_to_outer_owner(
    nested: str, propagate: bool
) -> None:
    context, key = context_for(), new_key()
    policy = ResponsePolicy(snapshot_model=ProbeSnapshot)

    def action(session: Session) -> CommandResult:
        outcome = create_effect(session, context, ProbePayload())
        transaction = session.get_transaction()
        assert transaction is not None

        def inner() -> None:
            executor = IdempotencyExecutor()
            if nested == "purge":
                executor.purge_expired_payloads(
                    session, operation_code=PROBE_OPERATION, response_policy=policy
                )
            elif nested == "recover":
                executor.recover(
                    session,
                    key=new_key(),
                    operation_code=PROBE_OPERATION,
                    resolve_context=lambda _session, _saved: context,
                    authorize=authorize,
                    response_policy=policy,
                )
            else:
                executor.execute(
                    session,
                    key=new_key(),
                    operation_code=PROBE_OPERATION,
                    payload=ProbePayload(),
                    resolve_context=lambda _session, _saved: context,
                    authorize=authorize,
                    action=lambda current: create_effect(current, context, ProbePayload()),
                    response_policy=policy,
                )

        if propagate:
            inner()
        else:
            with pytest.raises(IdempotencyBoundaryError, match="Nested"):
                inner()
            assert session.get_transaction() is transaction and transaction.is_active
        return outcome

    if propagate:
        with pytest.raises(IdempotencyBoundaryError, match="Nested"):
            execute_probe(key, context, action=action)
        assert_effects(0)
        execute_probe(key, context)
    else:
        execute_probe(key, context, action=action)
    assert_effects(1)
    assert execute_probe(key, context).replayed
    assert_effects(1)


def test_failed_payload_purge_has_one_rollback_owner_and_preserves_original_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key, context, first, policy = _retained_result()

    def fail_restore(_session: Session, _reference: Any) -> Any:
        raise RuntimeError("reconstruction failed")

    failed_policy = ResponsePolicy(
        snapshot_model=ProbeSnapshot,
        reference_model=ProbeSnapshot,
        restore=fail_restore,
        payload_retention=policy.payload_retention,
    )
    with SessionLocal() as session:
        rollback, calls = session.rollback, []

        def counted_rollback() -> None:
            calls.append("rollback")
            rollback()

        monkeypatch.setattr(session, "rollback", counted_rollback)
        with pytest.raises(RuntimeError, match="reconstruction failed"):
            IdempotencyExecutor().purge_expired_payloads(
                session, operation_code=PROBE_OPERATION, response_policy=failed_policy
            )
        assert calls == ["rollback"]
        assert not session.in_transaction()
        session.commit()
        assert session.get(IdempotencyRecord, first.record_id).response_payload == first.payload
    assert execute_probe(key, context, policy=policy).payload == first.payload


@pytest.mark.parametrize("trace", ["audit", "outbox"])
@pytest.mark.parametrize("fault", ["runtime", "integrity"])
def test_trace_failure_after_flush_rolls_back_complete_idempotent_command(
    monkeypatch: pytest.MonkeyPatch, trace: str, fault: str
) -> None:
    context, key = context_for(), new_key()
    target, method = (AuditRecorder, "record") if trace == "audit" else (OutboxWriter, "append")
    original = getattr(target, method)

    def fail_after_trace(self: Any, session: Session, **kwargs: Any) -> Any:
        row = original(self, session, **kwargs)
        if fault == "integrity":
            setattr(row, "action" if trace == "audit" else "event_name", None)
        session.flush()
        raise RuntimeError("trace failed after flush")

    with monkeypatch.context() as patch:
        patch.setattr(target, method, fail_after_trace)
        with pytest.raises(IntegrityError if fault == "integrity" else RuntimeError):
            execute_probe(key, context)
    assert_effects(0)
    execute_probe(key, context)
    assert_effects(1)


@pytest.mark.parametrize("fault", ["audit", "response", "commit"])
def test_pos_reprint_failure_leaves_no_audit_and_same_session_can_retry(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    _open_cash_session(client)
    ticket_id = UUID(str(_confirm_sale(client)["id"]))
    with SessionLocal() as session:
        actor = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        user = resolve_authorization(session, actor, surface="POS")
        bind_authorization_scope(
            session,
            user=user,
            capabilities=("sales_tickets.reprint",),
            mutation=True,
            surface="POS",
        )

        def reprint() -> Any:
            return TicketsCommandService().reprint_ticket(
                session,
                current_user=user,
                workstation_code=SEED_WORKSTATION_CODE,
                ticket_id=ticket_id,
                request_id="transaction-reprint-probe",
            )

        def fail_response(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("response failed")

        original = AuditRecorder.record

        def fail_audit(self: AuditRecorder, current: Session, **kwargs: Any) -> Any:
            original(self, current, **kwargs)
            current.flush()
            raise RuntimeError("audit failed")

        def fail_commit() -> None:
            session.flush()
            raise RuntimeError("commit failed")

        with monkeypatch.context() as patch:
            if fault == "audit":
                patch.setattr(AuditRecorder, "record", fail_audit)
            elif fault == "response":
                patch.setattr(ticket_services, "_to_ticket_detail_response", fail_response)
            else:
                patch.setattr(session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="failed"):
                reprint()
        assert not session.in_transaction()
        session.commit()
        with SessionLocal() as verification:
            assert (
                verification.scalar(
                    select(func.count(AuditLog.id)).where(AuditLog.action == "ticket.reprinted")
                )
                == 0
            )
        assert reprint().id == ticket_id
    with SessionLocal() as verification:
        assert (
            verification.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action == "ticket.reprinted")
            )
            == 1
        )
