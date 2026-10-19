"""Trace identity across real authenticated commands, replay and rollback."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from test_cash_idempotency import _login as cash_login
from test_cash_idempotency import _post as cash_post
from test_cash_idempotency import _setup as cash_setup
from test_sale_idempotency import _setup as sale_setup
from test_sale_idempotency import _submit as sale_submit

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Brand
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.sales.infrastructure.models import Sale
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.idempotency import new_idempotency_key
from zeromerma_api.testing.sessions import fixture_session_headers


@pytest.mark.parametrize("kind", ["sale", "close", "open"])
def test_pos_context_correlates_command_audit_outbox_and_authorized_replay(
    client: TestClient,
    kind: str,
) -> None:
    headers, body = sale_setup(client) if kind == "sale" else cash_setup(client, kind)
    key, first_id, replay_id = new_idempotency_key(), str(uuid4()), str(uuid4())

    def submit(attempt: str) -> Any:
        traced = {**headers, "X-Request-ID": attempt}
        return (
            sale_submit(client, traced, body, key)
            if kind == "sale"
            else cash_post(client, kind, traced, body, key)
        )

    first = submit(first_id)
    assert first.status_code in {200, 201}
    correlation = UUID(first.headers["X-Correlation-ID"])
    with SessionLocal() as session:
        command = session.scalars(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == UUID(key))
        ).one()
        assert correlation == command.id
        audits = session.scalars(select(AuditLog).where(AuditLog.operation_id == correlation)).all()
        events = session.scalars(
            select(OutboxEvent).where(OutboxEvent.operation_id == correlation)
        ).all()
        assert audits and events
        original = {item.id: (item.request_id, item.recorded_at) for item in (*audits, *events)}
        for item in (*audits, *events):
            assert item.context_version == 1 and item.source_app == "POS"
            assert item.actor_id == command.actor_user_id and item.actor_type == "USER"
            assert item.branch_id == command.branch_id
            assert item.workstation_id == command.workstation_id
            assert item.cash_session_id == (
                UUID(first.json()["id"]) if kind == "open" else command.cash_session_id
            )
            assert item.correlation_id == correlation and item.causation_id is None
            assert item.request_id == first_id and item.idempotency_key == UUID(key)
            assert item.recorded_at is not None
        assert all(event.schema_version == 1 for event in events)
    if kind == "close":
        headers = cash_login(client)
    replay = submit(replay_id)
    assert replay.status_code == first.status_code
    assert replay.json() == first.json()
    assert replay.headers["X-Correlation-ID"] == str(correlation)
    assert replay.headers["X-Request-ID"] == replay_id
    with SessionLocal() as session:
        rows = [
            *session.scalars(select(AuditLog).where(AuditLog.operation_id == correlation)),
            *session.scalars(select(OutboxEvent).where(OutboxEvent.operation_id == correlation)),
        ]
        assert {item.id: (item.request_id, item.recorded_at) for item in rows} == original


def test_backoffice_action_records_explicit_origin_and_resource_branch(client: TestClient) -> None:
    headers = owner_headers()
    with SessionLocal() as session:
        brand_id = session.scalars(select(Brand.id)).first()
    response = client.post(
        "/v1/admin/branches",
        headers=headers,
        json={
            "brand_id": str(brand_id),
            "code": "CONTEXT",
            "name": "Context branch",
            "timezone": "America/Hermosillo",
            "is_active": True,
            "address_line": "Test address",
            "city": "Hermosillo",
            "state": "Sonora",
            "country": "Mexico",
            "phone": None,
            "contact_email": None,
        },
    )
    assert response.status_code == 201
    identity = UUID(response.headers["X-Correlation-ID"])
    with SessionLocal() as session:
        audit = session.scalars(select(AuditLog).where(AuditLog.correlation_id == identity)).one()
        event = session.scalars(
            select(OutboxEvent).where(OutboxEvent.correlation_id == identity)
        ).one()
        assert audit.source_app == event.source_app == "BACKOFFICE"
        assert audit.operation_id == event.operation_id == identity
        assert audit.branch_id == event.branch_id == UUID(response.json()["overview"]["id"])
        assert audit.request_id == event.request_id == response.headers["X-Request-ID"]


def test_denial_has_authenticated_context_and_never_copies_rejected_body(
    client: TestClient,
) -> None:
    with SessionLocal() as session:
        user = User(
            email="context-denied@example.test",
            full_name="Denied",
            password_hash="unusable",
            allowed_surfaces=["BACKOFFICE"],
            default_surface="BACKOFFICE",
        )
        session.add(user)
        session.flush()
        headers = fixture_session_headers(session, user, audience="BACKOFFICE")
        actor_id = user.id
        session.commit()
    response = client.post(
        "/v1/admin/branches", headers=headers, json={"password": "private-denial-body"}
    )
    assert response.status_code == 403
    with SessionLocal() as session:
        audit = session.scalars(
            select(AuditLog).where(AuditLog.request_id == response.headers["X-Request-ID"])
        ).one()
        assert audit.action == "authorization.denied"
        assert audit.source_app == "BACKOFFICE" and audit.actor_id == actor_id
        assert audit.correlation_id == UUID(response.headers["X-Correlation-ID"])
        assert "private-denial-body" not in str(audit.metadata_)


def test_precommit_failure_rolls_back_business_and_trace_rows(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with TestClient(client.app, base_url="https://testserver", raise_server_exceptions=False) as c:
        headers, body = sale_setup(c)
        with SessionLocal() as session:
            before = set(session.scalars(select(Sale.id)))
        append = OutboxWriter.append

        def fail(self: OutboxWriter, *args: Any, **kwargs: Any) -> OutboxEvent:
            append(self, *args, **kwargs)
            raise RuntimeError("injected trace failure")

        monkeypatch.setattr(OutboxWriter, "append", fail)
        response = sale_submit(c, headers, body, new_idempotency_key())
        assert response.status_code == 500
        identity = UUID(response.headers["X-Correlation-ID"])
        with SessionLocal() as session:
            assert set(session.scalars(select(Sale.id))) == before
            assert (
                session.scalar(select(AuditLog.id).where(AuditLog.operation_id == identity)) is None
            )
            assert (
                session.scalar(select(OutboxEvent.id).where(OutboxEvent.operation_id == identity))
                is None
            )
            assert session.get(IdempotencyRecord, identity) is None
