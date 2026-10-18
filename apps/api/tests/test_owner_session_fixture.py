from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.db import session as database_session
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.infrastructure.session_models import AuthLoginLimit, AuthSession
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.database_safety import DestructiveTestDatabaseSafetyError


def test_owner_fixture_uses_persisted_authorized_sessions_without_login_rate_buckets(
    client: TestClient,
) -> None:
    headers = [owner_headers() for _ in range(12)]
    with database_session.SessionLocal() as session:
        assert session.scalar(select(func.count(AuthLoginLimit.key))) == 0
        assert session.scalar(select(func.count(AuthSession.id))) == 12
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action == "session.created")
            )
            == 12
        )
        assert (
            session.scalar(
                select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.event_name == "session.created"
                )
            )
            == 12
        )
        credential = headers[-1]["Cookie"].split("=", 1)[1]
        record = session.scalar(
            select(AuthSession).where(AuthSession.credential_hash == secret_hash(credential))
        )
        assert record is not None
        assert record.audience == "BACKOFFICE"
        assert record.csrf_hash == secret_hash(headers[-1]["X-CSRF-Token"])
    assert client.get("/v1/admin/roles/permissions", headers=headers[-1]).status_code == 200


def test_owner_fixture_refuses_unguarded_environment_before_opening_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ZEROMERMA_TEST_ENVIRONMENT")

    def unexpected_session() -> None:
        pytest.fail("The owner fixture must reject before opening a database session.")

    monkeypatch.setattr(database_session, "SessionLocal", unexpected_session)
    with pytest.raises(DestructiveTestDatabaseSafetyError):
        owner_headers()
