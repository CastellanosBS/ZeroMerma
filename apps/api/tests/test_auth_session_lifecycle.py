from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.application.privileged_access import PrivilegedAccessService
from zeromerma_api.modules.identity.application.schemas import IdentitySurface
from zeromerma_api.modules.identity.application.security import PasswordHasher, secret_hash
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.identity.infrastructure.privileged_models import IdentityPrivilegedChange
from zeromerma_api.modules.identity.infrastructure.session_models import (
    AuthSession,
    PasswordResetCredential,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import owner_headers
from zeromerma_api.testing.sessions import response_session_headers, surface_origin


def _login(
    client: TestClient,
    audience: IdentitySurface = "POS",
    *,
    email: str | None = None,
    password: str | None = None,
) -> tuple[dict[str, str], dict[str, object]]:
    payload = {
        "email": email or (SEED_USER_EMAIL if audience == "POS" else SEED_ADMIN_EMAIL),
        "password": password or (SEED_USER_PASSWORD if audience == "POS" else SEED_ADMIN_PASSWORD),
        "audience": audience,
    }
    if audience == "POS":
        payload["workstation_code"] = SEED_WORKSTATION_CODE
    response = client.post(
        "/v1/auth/login",
        headers={"Origin": surface_origin(audience), "X-ZeroMerma-Surface": audience},
        json=payload,
    )
    client.cookies.clear()
    assert response.status_code == 200, response.text
    for cookie in response.headers.get_list("set-cookie"):
        assert "Secure" in cookie and "HttpOnly" in cookie and "Path=/" in cookie
        assert "Domain=" not in cookie
    return response_session_headers(response, audience), response.json()


def _session_id(payload: dict[str, object]) -> UUID:
    row = payload["session"]
    assert isinstance(row, dict)
    return UUID(str(row["id"]))


def test_cookie_login_persists_activity_without_persisting_or_auditing_secrets(
    client: TestClient,
) -> None:
    headers, payload = _login(client)
    assert "access_token" not in payload and "token_type" not in payload
    credential = headers["Cookie"].split("=", 1)[1]
    with SessionLocal() as session:
        row = session.get(AuthSession, _session_id(payload))
        assert row is not None
        assert row.credential_hash == secret_hash(credential)
        assert row.csrf_hash == secret_hash(headers["X-CSRF-Token"])
        user = session.get(User, row.user_id)
        assert user is not None and user.last_login_at is not None
        traces = json.dumps(list(session.scalars(select(AuditLog.metadata_)))) + json.dumps(
            list(session.scalars(select(OutboxEvent.payload)))
        )
        assert (
            credential not in traces
            and headers["X-CSRF-Token"] not in traces
            and SEED_USER_PASSWORD not in traces
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action == "session.created")
            )
            == 1
        )


def test_cookie_audiences_origin_and_csrf_are_independent(client: TestClient) -> None:
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        user.allowed_surfaces = ["POS", "BACKOFFICE"]
        session.commit()
    pos, _ = _login(client)
    backoffice, _ = _login(client, "BACKOFFICE", email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    combined = {**backoffice, "Cookie": pos["Cookie"] + "; " + backoffice["Cookie"]}
    assert client.get("/v1/auth/session", headers=combined).status_code == 200
    assert (
        client.get(
            "/v1/auth/session", headers={**combined, "Origin": surface_origin("POS")}
        ).status_code
        == 403
    )
    assert client.get("/v1/admin/products", headers=pos).status_code == 403
    assert client.get("/v1/auth/me?surface=BACKOFFICE", headers=pos).status_code == 403
    assert (
        client.post(
            "/v1/auth/activity", headers={**pos, "X-CSRF-Token": backoffice["X-CSRF-Token"]}
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/v1/auth/activity",
            headers={key: value for key, value in pos.items() if key != "Origin"},
        ).status_code
        == 403
    )
    assert (
        client.get("/v1/auth/me", headers={**pos, "Authorization": "Bearer obsolete"}).status_code
        == 401
    )
    assert client.get("/v1/auth/me?access_token=obsolete", headers=pos).status_code == 401


def test_pos_idle_locks_restore_without_touch_and_reauth_rotates_without_extending_absolute(
    client: TestClient,
) -> None:
    headers, payload = _login(client)
    row_id = _session_id(payload)
    with SessionLocal() as session:
        row = session.get(AuthSession, row_id)
        assert row is not None
        original_absolute = row.absolute_expires_at
        row.last_activity_at = datetime.now(UTC) - timedelta(minutes=6)
        row.idle_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()
    locked = client.get("/v1/auth/me", headers=headers)
    assert locked.status_code == 423 and locked.json()["code"] == "SESSION_LOCKED"
    restored = client.get("/v1/auth/session", headers=headers)
    assert restored.status_code == 200 and restored.json()["session"]["status"] == "LOCKED"
    assert restored.json()["csrf_token"] == headers["X-CSRF-Token"]
    unlocked = client.post(
        "/v1/auth/reauthenticate", headers=headers, json={"password": SEED_USER_PASSWORD}
    )
    client.cookies.clear()
    assert unlocked.status_code == 200, unlocked.text
    fresh = response_session_headers(unlocked, "POS")
    assert fresh["Cookie"] != headers["Cookie"] and fresh["X-CSRF-Token"] != headers["X-CSRF-Token"]
    assert client.get("/v1/auth/me", headers=headers).status_code == 401
    assert client.get("/v1/auth/me", headers=fresh).status_code == 200
    with SessionLocal() as session:
        row = session.get(AuthSession, row_id)
        assert row is not None and row.absolute_expires_at == original_absolute


def test_polling_does_not_extend_idle_and_absolute_expiry_is_authoritative(
    client: TestClient,
) -> None:
    headers, payload = _login(client, "BACKOFFICE")
    with SessionLocal() as session:
        row = session.get(AuthSession, _session_id(payload))
        assert row is not None
        before = row.idle_expires_at
    for _ in range(2):
        assert client.get("/v1/auth/session", headers=headers).status_code == 200
    with SessionLocal() as session:
        row = session.get(AuthSession, _session_id(payload))
        assert row is not None and row.idle_expires_at == before
        row.idle_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        row.absolute_expires_at = row.idle_expires_at
        session.commit()
    expired = client.get("/v1/auth/session", headers=headers)
    assert expired.status_code == 401 and expired.json()["code"] == "SESSION_EXPIRED"


def test_multiple_backoffice_sessions_revoke_others_and_logout_are_durable(
    client: TestClient,
) -> None:
    old, _ = _login(client, "BACKOFFICE")
    current, _ = _login(client, "BACKOFFICE")
    listed = client.get("/v1/auth/sessions?page_size=1", headers=current)
    assert (
        listed.status_code == 200
        and listed.json()["total"] == 2
        and len(listed.json()["items"]) == 1
    )
    assert client.post("/v1/auth/sessions/revoke-others", headers=current).status_code == 204
    assert client.get("/v1/auth/me", headers=old).status_code == 401
    assert client.get("/v1/auth/me", headers=current).status_code == 200
    assert client.post("/v1/auth/logout", headers=current).status_code == 204
    assert client.get("/v1/auth/me", headers=current).status_code == 401


def test_admin_session_listing_is_paginated_and_revokes_only_authorized_target(
    client: TestClient,
) -> None:
    actor = owner_headers()
    actor_id = client.get("/v1/auth/me", headers=actor).json()["id"]
    targets = [_login(client, "BACKOFFICE") for _ in range(3)]
    other_user, other_payload = _login(client)
    target_user = targets[0][1]["user"]
    assert isinstance(target_user, dict)
    user_id = str(target_user["id"])
    path = f"/v1/admin/users/{user_id}/sessions"
    ordered_ids = [str(_session_id(payload)) for _, payload in reversed(targets)]
    for page, expected_id in enumerate(ordered_ids, start=1):
        response = client.get(path, headers=actor, params={"page": page, "page_size": 1})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["page"] == page and body["page_size"] == 1 and body["total"] == 3
        assert [item["id"] for item in body["items"]] == [expected_id]
        assert body["items"][0]["audience"] == "BACKOFFICE"
        assert body["items"][0]["status"] == "ACTIVE"
        assert {"credential_hash", "csrf_hash", "csrf_token", "credential"}.isdisjoint(
            body["items"][0]
        )
    beyond = client.get(path, headers=actor, params={"page": 4, "page_size": 1})
    assert beyond.status_code == 200 and beyond.json()["items"] == []
    assert beyond.json()["total"] == 3
    assert client.get(path, headers=actor, params={"page_size": 101}).status_code == 422
    wrong_user = client.delete(f"{path}/{_session_id(other_payload)}", headers=actor)
    assert wrong_user.status_code == 404
    revoked_id = _session_id(targets[1][1])
    revoked = client.delete(f"{path}/{revoked_id}", headers=actor)
    assert revoked.status_code == 204, revoked.text
    for index, (headers, _) in enumerate(targets):
        response = client.get("/v1/auth/me", headers=headers)
        assert response.status_code == (401 if index == 1 else 200)
        if index == 1:
            assert response.json()["code"] == "SESSION_REVOKED"
    assert client.get("/v1/auth/me", headers=actor).status_code == 200
    assert client.get("/v1/auth/me", headers=other_user).status_code == 200
    with SessionLocal() as session:
        record = session.get(AuthSession, revoked_id)
        assert record is not None and record.status == "REVOKED"
        assert record.revocation_reason == "ADMIN_REVOKED" and record.revoked_at is not None
        audit = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "session.revoked", AuditLog.resource_id == str(revoked_id)
            )
        ).one()
        assert str(audit.actor_id) == actor_id
        event = session.scalars(
            select(OutboxEvent).where(
                OutboxEvent.event_name == "session.revoked",
                OutboxEvent.aggregate_id == str(revoked_id),
            )
        ).one()
        assert event.payload["reason"] == "ADMIN_REVOKED"
        assert event.payload["user_id"] == user_id


def test_delete_own_session_preserves_other_users_and_can_revoke_current_session(
    client: TestClient,
) -> None:
    old, old_payload = _login(client, "BACKOFFICE")
    current, current_payload = _login(client, "BACKOFFICE")
    other, other_payload = _login(client)
    denied = client.delete(f"/v1/auth/sessions/{_session_id(other_payload)}", headers=current)
    assert denied.status_code == 404 and denied.json()["code"] == "NOT_FOUND"
    assert client.get("/v1/auth/me", headers=other).status_code == 200
    deleted = client.delete(f"/v1/auth/sessions/{_session_id(old_payload)}", headers=current)
    assert deleted.status_code == 204, deleted.text
    assert client.get("/v1/auth/me", headers=old).status_code == 401
    assert client.get("/v1/auth/me", headers=current).status_code == 200
    deleted_current = client.delete(
        f"/v1/auth/sessions/{_session_id(current_payload)}", headers=current
    )
    assert deleted_current.status_code == 204, deleted_current.text
    assert any(
        "__Host-zm-backoffice-session=" in cookie and "Max-Age=0" in cookie
        for cookie in deleted_current.headers.get_list("set-cookie")
    )
    assert client.get("/v1/auth/me", headers=current).status_code == 401
    assert client.get("/v1/auth/me", headers=other).status_code == 200
    with SessionLocal() as session:
        records = list(
            session.scalars(
                select(AuthSession).where(
                    AuthSession.id.in_([_session_id(old_payload), _session_id(current_payload)])
                )
            )
        )
        assert len(records) == 2
        assert all(
            record.status == "REVOKED" and record.revocation_reason == "USER_REVOKED"
            for record in records
        )
        foreign = session.get(AuthSession, _session_id(other_payload))
        assert foreign is not None and foreign.status == "ACTIVE"


def test_pos_new_login_replaces_one_slot_atomically_under_concurrency(client: TestClient) -> None:
    barrier = Barrier(2)

    def login_once() -> dict[str, str]:
        with TestClient(create_app(), base_url="https://testserver") as concurrent_client:
            barrier.wait(timeout=5)
            return _login(concurrent_client)[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: login_once(), range(2)))
    statuses = sorted(client.get("/v1/auth/me", headers=headers).status_code for headers in results)
    assert statuses == [200, 401]
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(func.count())
                .select_from(AuthSession)
                .where(AuthSession.audience == "POS", AuthSession.status.in_(["ACTIVE", "LOCKED"]))
            )
            == 1
        )


def test_authorization_change_revokes_same_transaction_and_rollback_preserves_session(
    client: TestClient,
) -> None:
    headers, payload = _login(client)
    with SessionLocal() as session:
        record = session.get(AuthSession, _session_id(payload))
        assert record is not None
        user = session.get(User, record.user_id)
        assert user is not None
        user.is_locked = True
        session.flush()
        assert (
            session.scalar(select(AuthSession.status).where(AuthSession.id == record.id))
            == "REVOKED"
        )
        session.rollback()
    assert client.get("/v1/auth/me", headers=headers).status_code == 200
    with SessionLocal() as session:
        record = session.get(AuthSession, _session_id(payload))
        assert record is not None
        assignment = session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == record.user_id)
        ).first()
        assert assignment is not None
        assignment.is_active = False
        session.commit()
    assert client.get("/v1/auth/me", headers=headers).status_code == 401


def test_cash_open_binds_and_close_revokes_only_related_pos_sessions(client: TestClient) -> None:
    pos, payload = _login(client)
    other, _ = _login(client, "BACKOFFICE")
    response = client.post(
        "/v1/cash-sessions/open",
        headers=pos,
        json={"workstation_code": SEED_WORKSTATION_CODE, "opening_amount": "100.00"},
    )
    assert response.status_code == 201, response.text
    assert client.post("/v1/auth/lock", headers=pos).status_code == 200
    with SessionLocal() as session:
        auth = session.get(AuthSession, _session_id(payload))
        assert auth is not None and auth.cash_session_id == UUID(response.json()["id"])
        cash = session.get(CashSession, auth.cash_session_id)
        assert cash is not None and cash.status == "OPEN"
        cash.status = "CLOSED"
        cash.closed_at = datetime.now(UTC)
        session.commit()
    assert client.get("/v1/auth/me", headers=pos).status_code == 401
    assert client.get("/v1/auth/me", headers=other).status_code == 200


@pytest.mark.parametrize("audience", ["BACKOFFICE", "POS"])
def test_temporary_password_is_limited_and_change_revokes_all_sessions(
    client: TestClient, audience: IdentitySurface
) -> None:
    email = SEED_USER_EMAIL if audience == "POS" else SEED_ADMIN_EMAIL
    password = SEED_USER_PASSWORD if audience == "POS" else SEED_ADMIN_PASSWORD
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == email)).one()
        user.password_reset_required = True
        session.commit()
    headers, payload = _login(client, audience)
    assert isinstance(payload["user"], dict) and payload["user"]["password_reset_required"] is True
    assert payload["user"]["effective_grants"] == []
    denied = client.get("/v1/admin/products", headers=headers)
    assert denied.status_code == 403 and denied.json()["code"] == "PASSWORD_RESET_REQUIRED"
    assert client.get("/v1/auth/session", headers=headers).status_code == 200
    if audience == "POS":
        with SessionLocal() as session:
            row = session.get(AuthSession, _session_id(payload))
            assert row is not None
            row.idle_expires_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
        restored = client.get("/v1/auth/session", headers=headers)
        assert restored.status_code == 200 and restored.json()["session"]["status"] == "LOCKED"
        reauthenticated = client.post(
            "/v1/auth/reauthenticate", headers=headers, json={"password": password}
        )
        client.cookies.clear()
        assert reauthenticated.status_code == 200, reauthenticated.text
        assert reauthenticated.json()["user"]["password_reset_required"] is True
        assert reauthenticated.json()["user"]["effective_grants"] == []
        headers = response_session_headers(reauthenticated, audience)
    assert (
        client.post(
            "/v1/auth/password/change",
            headers=headers,
            json={
                "current_password": password,
                "new_password": "A-new-strong-password-123",
            },
        ).status_code
        == 204
    )
    assert client.get("/v1/auth/session", headers=headers).status_code == 401
    _login(client, audience, password="A-new-strong-password-123")


def test_admin_reset_is_single_use_expires_and_revokes_sessions(client: TestClient) -> None:
    actor = owner_headers()
    old, payload = _login(client, "BACKOFFICE")
    user_payload = payload["user"]
    assert isinstance(user_payload, dict)
    user_id = str(user_payload["id"])
    issued = client.post(
        f"/v1/admin/users/{user_id}/password-reset",
        headers=actor,
        json={"reason": "Verified recovery request"},
    )
    assert issued.status_code == 200, issued.text
    assert client.get("/v1/auth/me", headers=old).status_code == 401
    command = {
        "reset_token": issued.json()["reset_token"],
        "new_password": "Recovered-password-123",
    }
    public_headers = {"Origin": surface_origin("BACKOFFICE"), "X-ZeroMerma-Surface": "BACKOFFICE"}
    assert (
        client.post("/v1/auth/password/reset", headers=public_headers, json=command).status_code
        == 204
    )
    assert (
        client.post("/v1/auth/password/reset", headers=public_headers, json=command).status_code
        == 401
    )
    second = client.post(
        f"/v1/admin/users/{user_id}/password-reset",
        headers=actor,
        json={"reason": "Second verified recovery"},
    )
    assert second.status_code == 200, second.text
    with SessionLocal() as session:
        row = session.scalars(
            select(PasswordResetCredential).where(
                PasswordResetCredential.credential_hash == secret_hash(second.json()["reset_token"])
            )
        ).one()
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    command["reset_token"] = second.json()["reset_token"]
    assert (
        client.post("/v1/auth/password/reset", headers=public_headers, json=command).status_code
        == 401
    )


def test_login_rate_limit_does_not_reveal_account_existence(client: TestClient) -> None:
    headers = {"Origin": surface_origin("BACKOFFICE"), "X-ZeroMerma-Surface": "BACKOFFICE"}
    outcomes = []
    for email in ("missing@example.test", SEED_ADMIN_EMAIL):
        responses = [
            client.post(
                "/v1/auth/login",
                headers=headers,
                json={"email": email, "password": "wrong", "audience": "BACKOFFICE"},
            )
            for _ in range(11)
        ]
        outcomes.append([(response.status_code, response.json()["code"]) for response in responses])
    assert outcomes[0] == outcomes[1]
    assert outcomes[0][-1] == (429, "LOGIN_RATE_LIMITED")


def test_pos_workstation_binding_prevents_switch_and_inactive_unlock(client: TestClient) -> None:
    headers, _ = _login(client)
    response = client.post(
        "/v1/cash-sessions/open",
        headers=headers,
        json={"workstation_code": "POS-02", "opening_amount": "0.00"},
    )
    assert response.status_code in (403, 404)
    assert client.post("/v1/auth/lock", headers=headers).status_code == 200
    with SessionLocal() as session:
        station = session.scalars(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
        ).one()
        station.is_active = False
        session.commit()
    assert (
        client.post(
            "/v1/auth/reauthenticate", headers=headers, json={"password": SEED_USER_PASSWORD}
        ).status_code
        == 403
    )


def test_privileged_password_reset_requires_exact_dual_approval_and_cannot_replay(
    client: TestClient,
) -> None:
    password = "Original-owner-password-123"
    with SessionLocal() as session:
        service = PrivilegedAccessService()
        first = service.bootstrap_owner(
            session,
            email="first@session.test",
            full_name="First owner",
            password=password,
            authorized_host="test-control-plane",
        )
        second = User(
            email="second@session.test",
            full_name="Second owner",
            password_hash=PasswordHasher().hash_password(password),
            allowed_surfaces=["BACKOFFICE"],
            default_surface="BACKOFFICE",
            is_active=True,
        )
        session.add(second)
        session.flush()
        second_id = second.id
        service.recover_second_superadmin(
            session,
            target_user_id=second_id,
            recovery_material=first.recovery_material,
            current_host="test-control-plane",
        )
        session.commit()
    first_headers, _ = _login(client, "BACKOFFICE", email="first@session.test", password=password)
    second_headers, _ = _login(client, "BACKOFFICE", email="second@session.test", password=password)
    reset_path = f"/v1/admin/users/{second_id}/password-reset"
    reason = "Verified protected account recovery"
    assert (
        client.post(reset_path, headers=first_headers, json={"reason": reason}).status_code == 409
    )
    proposed = client.post(
        "/v1/admin/roles/privileged-changes",
        headers=first_headers,
        json={
            "operation": "USER_PASSWORD_RESET",
            "target_user_id": str(second_id),
            "payload": {"reason": reason},
            "reason": reason,
        },
    )
    assert proposed.status_code == 201, proposed.text
    change = proposed.json()
    approve_path = f"/v1/admin/roles/privileged-changes/{change['id']}/approve"
    approved = client.post(
        approve_path, headers=second_headers, json={"payload_sha256": change["payload_sha256"]}
    )
    assert approved.status_code == 200, approved.text
    generic = client.post(
        f"/v1/admin/roles/privileged-changes/{change['id']}/execute",
        headers=first_headers,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert generic.status_code == 409
    with SessionLocal() as session:
        pending = session.get(IdentityPrivilegedChange, UUID(change["id"]))
        assert pending is not None and pending.consumed_at is None
    command = {
        "reason": reason,
        "approval_id": change["id"],
        "payload_sha256": change["payload_sha256"],
    }
    mismatch = client.post(
        reset_path,
        headers=first_headers,
        json={**command, "reason": "Different protected recovery"},
    )
    assert mismatch.status_code == 409
    issued = client.post(reset_path, headers=first_headers, json=command)
    assert issued.status_code == 200, issued.text
    assert client.get("/v1/auth/me", headers=second_headers).status_code == 401
    assert client.post(reset_path, headers=first_headers, json=command).status_code == 409
    with SessionLocal() as session:
        consumed = session.get(IdentityPrivilegedChange, UUID(change["id"]))
        assert consumed is not None and consumed.consumed_at is not None
        assert "reset_token" not in consumed.payload


def test_restore_same_origin_and_referer_fallback_keep_audience_isolation(
    client: TestClient,
) -> None:
    headers, _ = _login(client, "BACKOFFICE")
    without_origin = {key: value for key, value in headers.items() if key != "Origin"}
    correct = client.get(
        "/v1/auth/session",
        headers={**without_origin, "Referer": surface_origin("BACKOFFICE") + "/users"},
    )
    assert correct.status_code == 200
    wrong = client.get(
        "/v1/auth/session", headers={**without_origin, "Referer": surface_origin("POS") + "/sales"}
    )
    assert wrong.status_code == 403
    injected = client.get(
        "/v1/auth/session",
        headers={**without_origin, "Referer": "http://attacker@localhost:5174/users"},
    )
    assert injected.status_code == 403


@pytest.mark.parametrize(
    "change",
    [
        "password",
        "surface",
        "role",
        "permission",
        "role_permission",
        "assignment",
        "assignment_scope",
    ],
)
def test_all_authority_sources_revoke_affected_sessions_at_commit(
    client: TestClient, change: str
) -> None:
    headers, payload = _login(client, "BACKOFFICE")
    with SessionLocal() as session:
        record = session.get(AuthSession, _session_id(payload))
        assert record is not None
        user = session.get(User, record.user_id)
        assert user is not None
        assignment = session.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id == user.id)
        ).first()
        assert assignment is not None
        role = session.get(Role, assignment.role_id)
        assert role is not None
        if change == "password":
            user.password_hash = PasswordHasher().hash_password("Changed-secret-password-123")
        elif change == "surface":
            user.allowed_surfaces = ["POS"]
        elif change == "role":
            role.is_active = False
        elif change in {"permission", "role_permission"}:
            permission_link = session.scalars(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).first()
            assert permission_link is not None
            if change == "role_permission":
                session.delete(permission_link)
            else:
                permission = session.get(Permission, permission_link.permission_id)
                assert permission is not None
                permission.is_active = False
        elif change == "assignment":
            assignment.is_active = False
        else:
            scope = session.scalars(
                select(UserRoleAssignmentBranchScope).where(
                    UserRoleAssignmentBranchScope.assignment_id == assignment.id
                )
            ).first()
            assert scope is not None
            session.delete(scope)
            assignment.is_active = False
        session.commit()
    assert client.get("/v1/auth/me", headers=headers).status_code == 401


def test_scoped_session_admin_cannot_manage_global_owner_sessions(client: TestClient) -> None:
    owner = owner_headers()
    owner_session = client.get("/v1/auth/session", headers=owner).json()
    actor, _ = _login(client, "BACKOFFICE")
    user_id = owner_session["user"]["id"]
    session_id = owner_session["session"]["id"]
    assert client.get(f"/v1/admin/users/{user_id}/sessions", headers=actor).status_code == 403
    assert (
        client.delete(f"/v1/admin/users/{user_id}/sessions/{session_id}", headers=actor).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/admin/users/{user_id}/password-reset",
            headers=actor,
            json={"reason": "Unprivileged reset attempt"},
        ).status_code
        == 403
    )
    assert client.get("/v1/auth/me", headers=owner).status_code == 200
