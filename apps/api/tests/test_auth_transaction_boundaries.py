"""Identity transaction ownership on guarded, disposable PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_DESTINATION_WORKSTATION_CODE,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity.application.admin_role_schemas import AdminRoleCreateRequest
from zeromerma_api.modules.identity.application.admin_role_services import AdminRoleService
from zeromerma_api.modules.identity.application.admin_schemas import (
    AdminUserCreateRequest,
    AdminUserUpdateRequest,
)
from zeromerma_api.modules.identity.application.admin_services import AdminUserService
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.privileged_access import PrivilegedAccessService
from zeromerma_api.modules.identity.application.privileged_schemas import (
    PrivilegedChangeCreateRequest,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, LoginRequest
from zeromerma_api.modules.identity.application.security import secret_hash
from zeromerma_api.modules.identity.application.session_services import (
    SessionAuthentication,
    SessionService,
)
from zeromerma_api.modules.identity.domain.exceptions import (
    RoleValidationError,
    UserValidationError,
)
from zeromerma_api.modules.identity.infrastructure.models import Role, User
from zeromerma_api.modules.identity.infrastructure.privileged_models import IdentityPrivilegedChange
from zeromerma_api.modules.identity.infrastructure.session_models import (
    AuthLoginLimit,
    AuthSession,
    PasswordResetCredential,
)
from zeromerma_api.modules.identity.presentation import router as identity_router
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import provision_test_owner
from zeromerma_api.testing.sessions import login_headers

REQUEST_ID = "4e39d274-80cd-4856-b904-0f1057542027"
NEW_PASSWORD = "Only-test-new-password-039!"


def _command(*, password: str = SEED_USER_PASSWORD) -> LoginRequest:
    return LoginRequest(
        email=SEED_USER_EMAIL,
        password=password,
        audience="POS",
        workstation_code=SEED_WORKSTATION_CODE,
    )


def _login() -> tuple[str, UUID]:
    with SessionLocal() as session:
        authentication = SessionService().login(
            session, _command(), ip="127.0.0.1", request_id=REQUEST_ID
        )
        return authentication.credential, authentication.record.id


def _authenticate(session: Session, credential: str) -> SessionAuthentication:
    return SessionService().authenticate(
        session,
        credential=credential,
        audience="POS",
        allow_locked=True,
        allow_reset=True,
        exclusive=True,
        request_id=REQUEST_ID,
    )


def _state() -> dict[str, tuple[Any, ...]]:
    """Compare durable state, including DB-trigger traces, without storing raw credentials."""
    with SessionLocal() as session:
        state = {
            model.__tablename__: tuple(
                session.execute(
                    select(*model.__table__.c).order_by(*model.__table__.primary_key.columns)
                ).all()
            )
            for model in (
                AuthSession,
                AuthLoginLimit,
                PasswordResetCredential,
                IdentityPrivilegedChange,
                Role,
            )
        }
        state["users"] = tuple(
            (
                row.id,
                row.full_name,
                row.email,
                secret_hash(row.password_hash),
                row.password_reset_required,
                row.last_login_at,
            )
            for row in session.scalars(select(User).order_by(User.id))
        )
        for model in (AuditLog, OutboxEvent):
            state[model.__tablename__] = tuple(session.scalars(select(model.id).order_by(model.id)))
        return state


def _trace_count(action: str) -> tuple[int, int]:
    with SessionLocal() as session:
        return (
            session.scalar(select(func.count(AuditLog.id)).where(AuditLog.action == action)) or 0,
            session.scalar(
                select(func.count(OutboxEvent.id)).where(OutboxEvent.event_name == action)
            )
            or 0,
        )


def _inject_trace_failure(
    monkeypatch: pytest.MonkeyPatch, component: str, stage: str = "after_flush"
) -> None:
    target, method = (AuditRecorder, "record") if component == "audit" else (OutboxWriter, "append")
    original = getattr(target, method)

    def fail(self: Any, session: Session, **kwargs: Any) -> Any:
        if stage != "before_add":
            original(self, session, **kwargs)
        if stage == "after_flush":
            session.flush()
        raise RuntimeError("Injected identity trace failure")

    monkeypatch.setattr(target, method, fail)


def _assert_clean_and_reusable(session: Session) -> None:
    assert not session.in_transaction()
    assert not session.new and not session.dirty and not session.deleted
    # A subsequent caller's commit must not revive a failed operation's flushed effects.
    session.commit()
    assert session.scalar(select(1)) == 1
    session.rollback()


def _owner() -> AuthenticatedUser:
    with SessionLocal() as session:
        owner = provision_test_owner(session)
        session.commit()
        return resolve_authorization(session, owner, surface="BACKOFFICE")


def test_login_commits_last_login_session_and_traces_once(monkeypatch: pytest.MonkeyPatch) -> None:
    with SessionLocal() as session:
        commit = Mock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit)
        authentication = SessionService().login(
            session, _command(), ip="127.0.0.1", request_id=REQUEST_ID
        )
        assert commit.call_count == 1
        user_id, session_id = authentication.user.id, authentication.record.id
    with SessionLocal() as verification:
        assert verification.get(User, user_id).last_login_at is not None
        assert verification.get(AuthSession, session_id).status == "ACTIVE"
    assert _trace_count("login.succeeded") == (1, 1)
    assert _trace_count("session.created") == (1, 1)


@pytest.mark.parametrize("component", ["audit", "outbox"])
@pytest.mark.parametrize("stage", ["before_add", "after_add", "after_flush"])
def test_failed_login_replacement_rolls_back_and_session_can_be_reused(
    monkeypatch: pytest.MonkeyPatch, component: str, stage: str
) -> None:
    old_credential, old_id = _login()
    before = _state()
    _inject_trace_failure(monkeypatch, component, stage)
    with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="Injected identity trace failure"):
            SessionService().login(session, _command(), ip="127.0.0.1", request_id=REQUEST_ID)
        _assert_clean_and_reusable(session)
    assert _state() == before
    with SessionLocal() as session:
        restored = _authenticate(session, old_credential)
        assert restored.record.id == old_id and restored.record.status == "ACTIVE"


def test_login_integrity_failure_reverts_replacement_and_clears_failed_transaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _login()
    before = _state()
    original = OutboxWriter.append

    def fail(self: OutboxWriter, session: Session, **kwargs: Any) -> Any:
        original(self, session, **kwargs)
        session.flush()
        session.execute(
            text(
                "DO $$ BEGIN RAISE EXCEPTION 'Injected trace failure' USING ERRCODE='23502'; END $$"
            )
        )

    monkeypatch.setattr(OutboxWriter, "append", fail)
    with SessionLocal() as session:
        with pytest.raises(IntegrityError) as failure:
            SessionService().login(session, _command(), ip="127.0.0.1", request_id=REQUEST_ID)
        assert failure.value.orig.sqlstate == "23502"
        _assert_clean_and_reusable(session)
    assert _state() == before


def test_service_scope_denial_keeps_independent_http_audit_after_rollback(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = login_headers(
        client,
        email=SEED_ADMIN_EMAIL,
        password=SEED_ADMIN_PASSWORD,
        audience="BACKOFFICE",
    )
    before = _state()
    create = AdminUserService.create_user
    reached_service: list[bool] = []

    def record_entry(self: AdminUserService, session: Session, **kwargs: Any) -> Any:
        reached_service.append(True)
        return create(self, session, **kwargs)

    monkeypatch.setattr(AdminUserService, "create_user", record_entry)
    response = client.post(
        "/v1/admin/users",
        headers={**headers, "X-Request-ID": REQUEST_ID},
        json={
            "email": "denied-global-user@example.test",
            "full_name": "Denied global user",
            "temporary_password": NEW_PASSWORD,
            "allowed_surfaces": ["BACKOFFICE"],
        },
    )
    assert response.status_code == 403
    assert reached_service == [True]
    after = _state()
    assert after["outbox_events"] == before["outbox_events"]
    assert after["users"] == before["users"]
    assert after["auth_sessions"] == before["auth_sessions"]
    assert len(after["audit_log"]) == len(before["audit_log"]) + 1
    with SessionLocal() as session:
        denial = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "authorization.denied", AuditLog.request_id == REQUEST_ID
            )
        ).one()
        assert denial.resource_id == "POST /v1/admin/users"
        assert denial.metadata_["authorization"]["decision"] == "DENIED"


def test_context_rejection_after_flushed_replacement_keeps_only_failed_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_credential, old_id = _login()
    before = _state()
    create = SessionService.create_session

    def reject(self: SessionService, session: Session, **kwargs: Any) -> SessionAuthentication:
        create(self, session, **kwargs)
        raise HTTPException(status_code=403, detail="Injected context rejection after flush")

    monkeypatch.setattr(SessionService, "create_session", reject)
    with SessionLocal() as session:
        commit = Mock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit)
        with pytest.raises(HTTPException) as rejected:
            SessionService().login(session, _command(), ip="127.0.0.1", request_id=REQUEST_ID)
        assert rejected.value.status_code == 403
        assert commit.call_count == 1
        _assert_clean_and_reusable(session)
    after = _state()
    assert after["auth_sessions"] == before["auth_sessions"]
    assert after["users"] == before["users"]
    assert _trace_count("login.failed") == (1, 1)
    assert _trace_count("login.succeeded") == _trace_count("session.created") == (1, 1)
    with SessionLocal() as session:
        assert _authenticate(session, old_credential).record.id == old_id
        account = session.get(AuthLoginLimit, "account:" + secret_hash(SEED_USER_EMAIL))
        assert account is not None and account.attempts == 2


@pytest.mark.parametrize("operation", ["reauthenticate", "logout", "change_password"])
@pytest.mark.parametrize("component", ["audit", "outbox"])
def test_failed_session_command_restores_credentials_status_and_password(
    monkeypatch: pytest.MonkeyPatch, operation: str, component: str
) -> None:
    credential, session_id = _login()
    if operation == "reauthenticate":
        with SessionLocal() as session:
            session.get(AuthSession, session_id).status = "LOCKED"
            session.commit()
    before = _state()
    with SessionLocal() as session:
        authentication = _authenticate(session, credential)
        _inject_trace_failure(monkeypatch, component)
        with pytest.raises(RuntimeError, match="Injected identity trace failure"):
            if operation == "reauthenticate":
                SessionService().reauthenticate(
                    session,
                    authentication,
                    password=SEED_USER_PASSWORD,
                    ip="127.0.0.1",
                    request_id=REQUEST_ID,
                )
            elif operation == "logout":
                SessionService().logout(session, authentication, REQUEST_ID)
            else:
                SessionService().change_password(
                    session,
                    authentication,
                    current_password=SEED_USER_PASSWORD,
                    new_password=NEW_PASSWORD,
                    ip="127.0.0.1",
                    request_id=REQUEST_ID,
                )
        assert authentication.credential == credential
        _assert_clean_and_reusable(session)
    assert _state() == before


@pytest.mark.parametrize("operation", ["issue", "complete"])
def test_password_reset_failure_preserves_token_user_and_sessions(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    actor = _owner()
    _credential, session_id = _login()
    with SessionLocal() as session:
        user_id = session.get(AuthSession, session_id).user_id
    token = None
    if operation == "complete":
        with SessionLocal() as session:
            token = (
                SessionService()
                .issue_password_reset(
                    session,
                    actor=actor,
                    user_id=user_id,
                    reason="Verified isolated password recovery",
                    approval_id=None,
                    payload_sha256=None,
                    request_id=REQUEST_ID,
                )
                .reset_token
            )
    before = _state()
    _inject_trace_failure(monkeypatch, "outbox")
    with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="Injected identity trace failure"):
            if operation == "issue":
                SessionService().issue_password_reset(
                    session,
                    actor=actor,
                    user_id=user_id,
                    reason="Verified isolated password recovery",
                    approval_id=None,
                    payload_sha256=None,
                    request_id=REQUEST_ID,
                )
            else:
                assert token is not None
                SessionService().complete_password_reset(
                    session,
                    credential=token,
                    new_password=NEW_PASSWORD,
                    ip="127.0.0.1",
                    request_id=REQUEST_ID,
                )
        _assert_clean_and_reusable(session)
    assert _state() == before


def _rejectable_command(
    operation: str, session: Session, service: SessionService, credential: str | None
) -> None:
    if operation == "login":
        service.login(
            session, _command(password="wrong-password"), ip="127.0.0.1", request_id=REQUEST_ID
        )
    elif operation == "reset":
        service.complete_password_reset(
            session,
            credential="invalid-reset-credential" * 3,
            new_password=NEW_PASSWORD,
            ip="127.0.0.1",
            request_id=REQUEST_ID,
        )
    else:
        assert credential is not None
        authentication = _authenticate(session, credential)
        if operation == "reauthenticate":
            service.reauthenticate(
                session,
                authentication,
                password="wrong-password",
                ip="127.0.0.1",
                request_id=REQUEST_ID,
            )
        else:
            service.change_password(
                session,
                authentication,
                current_password="wrong-password",
                new_password=NEW_PASSWORD,
                ip="127.0.0.1",
                request_id=REQUEST_ID,
            )


@pytest.mark.parametrize(
    ("operation", "event"),
    [
        ("login", "login.failed"),
        ("reauthenticate", "session.reauthentication_failed"),
        ("password", "password.change_failed"),
        ("reset", "password.reset_failed"),
    ],
)
@pytest.mark.parametrize("throttled", [False, True])
def test_intentional_rejections_commit_security_evidence_once_at_the_owner(
    monkeypatch: pytest.MonkeyPatch, operation: str, event: str, throttled: bool
) -> None:
    credential = _login()[0] if operation in {"reauthenticate", "password"} else None
    service = SessionService()
    if throttled:
        with SessionLocal() as session:
            key = "ip:" + secret_hash("127.0.0.1")
            row = session.get(AuthLoginLimit, key)
            if row is None:
                row = AuthLoginLimit(key=key, attempts=1, window_started_at=datetime.now(UTC))
                session.add(row)
            row.blocked_until = datetime.now(UTC) + timedelta(minutes=5)
            session.commit()
    before = _state()
    with SessionLocal() as session:
        commit = Mock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit)
        with pytest.raises(HTTPException) as rejected:
            _rejectable_command(operation, session, service, credential)
        assert rejected.value.status_code == (429 if throttled else 401)
        assert rejected.value.detail["code"] == (
            "LOGIN_RATE_LIMITED" if throttled else "INVALID_CREDENTIALS"
        )
        assert commit.call_count == 1
        _assert_clean_and_reusable(session)
    after = _state()
    assert after["auth_sessions"] == before["auth_sessions"]
    assert after["users"] == before["users"]
    assert _trace_count("login.rate_limited" if throttled else event) == (1, 1)
    with SessionLocal() as session:
        assert session.get(AuthLoginLimit, "ip:" + secret_hash("127.0.0.1")) is not None


@pytest.mark.parametrize(
    ("terminal", "status", "code"),
    [("EXPIRED", 401, "SESSION_EXPIRED"), ("LOCKED", 423, "SESSION_LOCKED")],
)
def test_authentication_terminal_state_is_durable_before_rejecting(
    terminal: str, status: int, code: str
) -> None:
    credential, session_id = _login()
    with SessionLocal() as session:
        record = session.get(AuthSession, session_id)
        if terminal == "EXPIRED":
            record.created_at -= timedelta(hours=13)
            record.absolute_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        record.idle_expires_at = datetime.now(UTC) - timedelta(seconds=2)
        session.commit()
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as rejected:
            SessionService().authenticate(session, credential=credential, audience="POS")
        assert rejected.value.status_code == status and rejected.value.detail["code"] == code
        _assert_clean_and_reusable(session)
    with SessionLocal() as session:
        assert session.get(AuthSession, session_id).status == terminal
    assert _trace_count("session." + terminal.lower()) == (1, 1)


def test_authentication_unexpected_failure_reverts_pending_idle_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential, session_id = _login()
    with SessionLocal() as session:
        session.get(AuthSession, session_id).idle_expires_at = datetime.now(UTC) - timedelta(
            seconds=1
        )
        session.commit()
    before = _state()

    def fail(*args: Any, **kwargs: Any) -> AuthenticatedUser:
        raise RuntimeError("Injected authorization read failure")

    monkeypatch.setattr(
        "zeromerma_api.modules.identity.application.session_services.resolve_authorization", fail
    )
    with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="Injected authorization read failure"):
            _authenticate(session, credential)
        _assert_clean_and_reusable(session)
    assert _state() == before


def test_session_participants_and_read_only_authentication_do_not_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential, session_id = _login()
    with SessionLocal() as session:
        record = session.get(AuthSession, session_id)
        record.last_activity_at -= timedelta(minutes=1)
        session.commit()
    before = _state()
    with SessionLocal() as session:
        commit = Mock(wraps=session.commit)
        monkeypatch.setattr(session, "commit", commit)
        authentication = _authenticate(session, credential)
        SessionService().list_sessions(session, authentication.user.id)
        SessionService().activity(session, authentication)
        SessionService().revoke_sessions(session, user_id=authentication.user.id)
        assert commit.call_count == 0
        session.rollback()
    assert _state() == before


@pytest.mark.parametrize("operation", ["restore", "activity", "revoke", "revoke_others"])
def test_router_owned_commit_failure_rolls_back_for_reusable_session(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    credential, session_id = _login()
    with SessionLocal() as session:
        record = session.get(AuthSession, session_id)
        record.last_activity_at -= timedelta(minutes=1)
        if operation == "restore":
            record.idle_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        if operation == "revoke_others":
            user = session.get(User, record.user_id)
            assert user is not None
            SessionService().create_session(
                session,
                user=user,
                audience="POS",
                workstation_code=SEED_DESTINATION_WORKSTATION_CODE,
            )
        session.commit()
    before = _state()
    with SessionLocal() as session:
        authentication = _authenticate(session, credential)

        def fail_commit() -> None:
            session.flush()
            raise RuntimeError("Injected pre-commit failure")

        with monkeypatch.context() as patch:
            patch.setattr(session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="Injected pre-commit failure"):
                if operation == "restore":
                    identity_router.current_session(authentication, session, Response())
                elif operation == "activity":
                    identity_router.session_activity(authentication, session)
                elif operation == "revoke":
                    identity_router.revoke_own_session(
                        session_id, Response(), authentication, session
                    )
                else:
                    identity_router.revoke_other_sessions(authentication, session)
        _assert_clean_and_reusable(session)
    assert _state() == before


@pytest.mark.parametrize("operation", ["create_user", "update_user", "create_role"])
@pytest.mark.parametrize("failure", ["expected_unique", "unrelated_unique", "other_sqlstate"])
def test_admin_identity_translates_only_its_exact_business_constraint(
    monkeypatch: pytest.MonkeyPatch, operation: str, failure: str
) -> None:
    actor = _owner()
    before = _state()
    constraint = "uq_roles_code" if operation == "create_role" else "uq_users_email"
    if failure == "unrelated_unique":
        constraint = "injected_outbox_unique"
    sqlstate = "23503" if failure == "other_sqlstate" else "23505"
    original = OutboxWriter.append

    def fail(self: OutboxWriter, session: Session, **kwargs: Any) -> Any:
        original(self, session, **kwargs)
        session.flush()
        # PostgreSQL supplies the actual SQLSTATE and diagnostic constraint metadata.
        session.execute(
            text(
                "DO $$ BEGIN RAISE EXCEPTION 'Injected constraint failure' "
                f"USING ERRCODE = '{sqlstate}', CONSTRAINT = '{constraint}'; END $$"
            )
        )

    monkeypatch.setattr(OutboxWriter, "append", fail)
    error_type = (
        (RoleValidationError if operation == "create_role" else UserValidationError)
        if failure == "expected_unique"
        else IntegrityError
    )
    with SessionLocal() as session:
        with pytest.raises(error_type):
            if operation == "create_role":
                AdminRoleService().create_role(
                    session,
                    current_user=actor,
                    command=AdminRoleCreateRequest(
                        code="transaction_test_role",
                        name="Transaction test role",
                        surfaces=["BACKOFFICE"],
                        permission_codes=["catalog.view"],
                    ),
                    request_id=REQUEST_ID,
                )
            elif operation == "create_user":
                AdminUserService().create_user(
                    session,
                    current_user=actor,
                    command=AdminUserCreateRequest(
                        email="transaction-user@example.test",
                        full_name="Transaction user",
                        temporary_password=NEW_PASSWORD,
                        allowed_surfaces=["BACKOFFICE"],
                    ),
                    request_id=REQUEST_ID,
                )
            else:
                target = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
                AdminUserService().update_user(
                    session,
                    current_user=actor,
                    user_id=target.id,
                    command=AdminUserUpdateRequest(full_name="Updated transaction user"),
                    request_id=REQUEST_ID,
                )
        _assert_clean_and_reusable(session)
    assert _state() == before


@pytest.mark.parametrize("operation", ["propose", "approve"])
def test_privileged_approval_owner_rolls_back_flushed_trace_failure(
    monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    service = PrivilegedAccessService()
    with SessionLocal() as session:
        owner = service.bootstrap_owner(
            session,
            email="transaction-owner@example.test",
            full_name="Transaction owner",
            password=NEW_PASSWORD,
            authorized_host="isolated-control-plane",
        )
        second = User(
            email="transaction-second@example.test",
            full_name="Transaction second authority",
            password_hash="unusable-test-only",
            allowed_surfaces=["BACKOFFICE"],
            default_surface="BACKOFFICE",
        )
        session.add(second)
        session.flush()
        service.recover_second_superadmin(
            session,
            target_user_id=second.id,
            recovery_material=owner.recovery_material,
            current_host="isolated-control-plane",
        )
        session.commit()
        first = session.get(User, owner.user_id)
        assert first is not None
        initiator = resolve_authorization(session, first, surface="BACKOFFICE")
        approver = resolve_authorization(session, second, surface="BACKOFFICE")
    command = PrivilegedChangeCreateRequest(
        operation="USER_LOCK",
        target_user_id=initiator.id,
        payload={"reason": "Proposed owner lock"},
        reason="Verified isolated privileged transaction",
    )
    change = None
    if operation == "approve":
        with SessionLocal() as session:
            change = service.propose(
                session, current_user=initiator, command=command, request_id=REQUEST_ID
            )
    before = _state()
    _inject_trace_failure(monkeypatch, "outbox")
    with SessionLocal() as session:
        with pytest.raises(RuntimeError, match="Injected identity trace failure"):
            if operation == "propose":
                service.propose(
                    session, current_user=initiator, command=command, request_id=REQUEST_ID
                )
            else:
                assert change is not None
                service.approve(
                    session,
                    current_user=approver,
                    change_id=change.id,
                    payload_sha256=change.payload_sha256,
                    request_id=REQUEST_ID,
                )
        _assert_clean_and_reusable(session)
    assert _state() == before
