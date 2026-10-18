from __future__ import annotations

import hmac
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    IdentitySurface,
    LoginRequest,
)
from zeromerma_api.modules.identity.application.security import (
    PasswordHasher,
    csrf_for_credential,
    new_session_secrets,
    secret_hash,
)
from zeromerma_api.modules.identity.application.session_schemas import (
    AuthSessionsResponse,
    AuthSessionView,
    LoginResponse,
    PasswordResetCredentialView,
)
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.session_models import (
    AuthLoginLimit,
    AuthSession,
    PasswordResetCredential,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

COOKIE_NAMES: dict[IdentitySurface, str] = {
    "POS": "__Host-zm-pos-session",
    "BACKOFFICE": "__Host-zm-backoffice-session",
}
IDLE_MINUTES: dict[IdentitySurface, int] = {"POS": 5, "BACKOFFICE": 15}
ABSOLUTE_HOURS: dict[IdentitySurface, int] = {"POS": 12, "BACKOFFICE": 8}
AUTH_CONTEXT_KEY = "zeromerma_auth_session"
_DUMMY_PASSWORD_HASH = "pbkdf2_sha256$600000$zeromerma-dummy-password$" + "0" * 64


def auth_error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def lock_identity_boundary(session: Session, *, exclusive: bool = False) -> None:
    # Match the existing identity boundary before locking users, branches or sessions.
    if exclusive:
        from zeromerma_api.modules.identity.application.privileged_access import (
            lock_privileged_lifecycle,
        )

        lock_privileged_lifecycle(session)
    else:
        session.execute(text("SELECT id FROM identity_privilege_state WHERE id=1 FOR SHARE"))


def set_audit_context(session: Session, user_id: UUID | None, request_id: str | None) -> None:
    session.execute(
        text(
            "SELECT set_config('zeromerma.actor_id', :actor, true), "
            "set_config('zeromerma.request_id', :request, true)"
        ),
        {"actor": str(user_id) if user_id else "", "request": (request_id or "")[:120]},
    )


@dataclass
class SessionAuthentication:
    record: AuthSession
    user: AuthenticatedUser
    credential: str = field(repr=False)

    def response(self) -> LoginResponse:
        user = self.user
        if user.password_reset_required:
            user = user.model_copy(update={"effective_grants": [], "is_superadministrator": False})
        return LoginResponse(
            session=AuthSessionView.model_validate(self.record),
            user=user,
            csrf_token=csrf_for_credential(self.credential),
        )


class SessionService:
    def __init__(self, settings: ApiSettings | None = None) -> None:
        self.settings = settings or get_settings()
        self.password_hasher = PasswordHasher()

    def _event(
        self,
        session: Session,
        action: str,
        *,
        user_id: UUID | None,
        session_id: UUID | None = None,
        request_id: str | None = None,
        reason: str | None = None,
        target_user_id: UUID | None = None,
    ) -> None:
        metadata = {
            "user_id": str(user_id) if user_id else None,
            "session_id": str(session_id) if session_id else None,
            "reason": reason,
            "target_user_id": str(target_user_id) if target_user_id else None,
        }
        AuditRecorder().record(
            session,
            actor_id=user_id,
            action=action,
            resource_type="user" if action.startswith("password.") else "auth_session",
            resource_id=str(target_user_id or user_id)
            if action.startswith("password.")
            else str(session_id)
            if session_id
            else None,
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        OutboxWriter().append(
            session,
            aggregate_type="auth_session",
            aggregate_id=str(session_id or user_id or "anonymous"),
            event_name=action,
            payload=metadata,
            headers={"request_id": request_id},
        )

    def _rate_attempt(
        self, session: Session, *, account: str, ip: str, now: datetime, request_id: str | None
    ) -> None:
        limits = [
            (
                "account:" + secret_hash(account.strip().lower()),
                self.settings.auth_login_account_limit,
            ),
            ("ip:" + secret_hash(ip), self.settings.auth_login_ip_limit),
        ]
        # A throttled peer cannot create account buckets for arbitrary unknown emails.
        for key, maximum in sorted(limits, key=lambda pair: pair[0].startswith("account:")):
            session.execute(
                insert(AuthLoginLimit)
                .values(key=key, attempts=0, window_started_at=now)
                .on_conflict_do_nothing()
            )
            limit = session.scalars(
                select(AuthLoginLimit)
                .where(AuthLoginLimit.key == key)
                .with_for_update()
                .execution_options(populate_existing=True)
            ).one()
            if limit.blocked_until is not None and limit.blocked_until > now:
                self._event(session, "login.rate_limited", user_id=None, request_id=request_id)
                session.commit()
                raise auth_error(
                    429, "LOGIN_RATE_LIMITED", "Too many authentication attempts. Try again later."
                )
            if now >= limit.window_started_at + timedelta(
                seconds=self.settings.auth_login_window_seconds
            ):
                limit.window_started_at = now
                limit.attempts = 0
                limit.blocked_until = None
            limit.attempts += 1
            if limit.attempts > maximum:
                limit.blocked_until = now + timedelta(
                    seconds=self.settings.auth_login_block_seconds
                )
                self._event(session, "login.rate_limited", user_id=None, request_id=request_id)
                session.commit()
                raise auth_error(
                    429, "LOGIN_RATE_LIMITED", "Too many authentication attempts. Try again later."
                )
        session.flush()

    def login(
        self, session: Session, command: LoginRequest, *, ip: str, request_id: str | None
    ) -> SessionAuthentication:
        if (command.audience == "POS") != (command.workstation_code is not None):
            raise auth_error(
                422,
                "VALIDATION_ERROR",
                "POS requires a workstation; Backoffice does not accept one.",
            )
        lock_identity_boundary(session)
        normalized_email = command.email.strip().lower()
        user = session.scalar(select(User).where(User.email == normalized_email).with_for_update())
        now = datetime.now(UTC)
        self._rate_attempt(session, account=normalized_email, ip=ip, now=now, request_id=request_id)
        valid_password = self.password_hasher.verify_password(
            command.password, user.password_hash if user else _DUMMY_PASSWORD_HASH
        )
        if (
            user is None
            or not valid_password
            or not user.is_active
            or user.is_locked
            or command.audience not in user.allowed_surfaces
        ):
            self._event(
                session,
                "login.failed",
                user_id=None,
                request_id=request_id,
                reason="INVALID_CREDENTIALS",
            )
            session.commit()
            raise auth_error(
                401, "INVALID_CREDENTIALS", "Invalid credentials or unavailable account."
            )
        set_audit_context(session, user.id, request_id)
        try:
            authentication = self.create_session(
                session,
                user=user,
                audience=command.audience,
                workstation_code=command.workstation_code,
            )
        except HTTPException:
            self._event(
                session,
                "login.failed",
                user_id=user.id,
                request_id=request_id,
                reason="UNAVAILABLE_CONTEXT",
            )
            session.commit()
            raise
        user.last_login_at = now
        self._event(
            session,
            "login.succeeded",
            user_id=user.id,
            session_id=authentication.record.id,
            request_id=request_id,
        )
        session.commit()
        return authentication

    def _workstation(self, session: Session, user: AuthenticatedUser, code: str) -> Workstation:
        row = session.scalar(select(Workstation).where(Workstation.code == code))
        if row is None:
            raise auth_error(403, "FORBIDDEN", "The workstation is not available to this user.")
        original_branch = row.branch_id
        branch = session.execute(
            select(Branch.id, Branch.is_active)
            .where(Branch.id == original_branch)
            .with_for_update(read=True)
        ).one_or_none()
        row = session.scalar(
            select(Workstation)
            .where(Workstation.id == row.id)
            .with_for_update(read=True)
            .execution_options(populate_existing=True)
        )
        if (
            row is None
            or not row.is_active
            or branch is None
            or not branch.is_active
            or row.branch_id != original_branch
        ):
            raise auth_error(403, "FORBIDDEN", "The workstation is not available to this user.")
        require_branches(user, "pos.operate", [row.branch_id])
        return row

    def create_session(
        self,
        session: Session,
        *,
        user: User,
        audience: IdentitySurface,
        workstation_code: str | None = None,
    ) -> SessionAuthentication:
        """Create within the caller's transaction; callers authenticate before invoking this.

        The public transaction seam also supports isolated fixtures without bearer tokens.
        User locking serializes replacement, with the partial unique index as the DB invariant.
        """
        lock_identity_boundary(session)
        session.flush()
        user = session.scalars(
            select(User)
            .where(User.id == user.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one()
        if not user.is_active or user.is_locked or audience not in user.allowed_surfaces:
            raise auth_error(
                401, "INVALID_CREDENTIALS", "Invalid credentials or unavailable account."
            )
        resolved_user = resolve_authorization(session, user, surface=audience)
        workstation = None
        cash_session_id = None
        now = datetime.now(UTC)
        if audience == "POS":
            if workstation_code is None:
                raise auth_error(422, "VALIDATION_ERROR", "POS requires a workstation.")
            workstation = self._workstation(session, resolved_user, workstation_code)
            for previous in session.scalars(
                select(AuthSession)
                .where(
                    AuthSession.user_id == user.id,
                    AuthSession.workstation_id == workstation.id,
                    AuthSession.audience == "POS",
                    AuthSession.status.in_(["ACTIVE", "LOCKED"]),
                )
                .order_by(AuthSession.id)
                .with_for_update()
            ):
                if now >= previous.absolute_expires_at:
                    previous.status = "EXPIRED"
                else:
                    self._revoke(previous, "REPLACED", now)
            session.flush()
            cash_session_id = session.scalar(
                select(CashSession.id).where(
                    CashSession.user_id == user.id,
                    CashSession.workstation_id == workstation.id,
                    CashSession.status == "OPEN",
                )
            )
        elif workstation_code is not None:
            raise auth_error(422, "VALIDATION_ERROR", "Backoffice does not accept a workstation.")
        credential, csrf = new_session_secrets()
        record = AuthSession(
            credential_hash=secret_hash(credential),
            csrf_hash=secret_hash(csrf),
            user_id=user.id,
            audience=audience,
            status="ACTIVE",
            created_at=now,
            last_activity_at=now,
            idle_expires_at=now + timedelta(minutes=IDLE_MINUTES[audience]),
            absolute_expires_at=now + timedelta(hours=ABSOLUTE_HOURS[audience]),
            workstation_id=workstation.id if workstation else None,
            cash_session_id=cash_session_id,
        )
        session.add(record)
        session.flush()
        return SessionAuthentication(record=record, user=resolved_user, credential=credential)

    def authenticate(
        self,
        session: Session,
        *,
        credential: str,
        audience: IdentitySurface,
        allow_locked: bool = False,
        allow_reset: bool = False,
        request_id: str | None = None,
        exclusive: bool = False,
    ) -> SessionAuthentication:
        if len(credential) != 43 or not all(
            character.isalnum() or character in "-_" for character in credential
        ):
            raise auth_error(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
        lock_identity_boundary(session, exclusive=exclusive)
        record_user_id = session.scalar(
            select(AuthSession.user_id).where(
                AuthSession.credential_hash == secret_hash(credential),
                AuthSession.audience == audience,
            )
        )
        if record_user_id is None:
            raise auth_error(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
        user = session.scalar(
            select(User)
            .where(User.id == record_user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        record = session.scalar(
            select(AuthSession)
            .where(
                AuthSession.credential_hash == secret_hash(credential),
                AuthSession.audience == audience,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if user is None or record is None:
            raise auth_error(401, "AUTHENTICATION_REQUIRED", "Authentication is required.")
        set_audit_context(session, user.id, request_id)
        now = datetime.now(UTC)
        if (
            record.status == "REVOKED"
            or not user.is_active
            or user.is_locked
            or audience not in user.allowed_surfaces
        ):
            if record.status != "REVOKED":
                self._revoke(record, "ACCOUNT_UNAVAILABLE", now)
                session.commit()
            raise auth_error(401, "SESSION_REVOKED", "The session was revoked. Sign in again.")
        if (
            record.status == "EXPIRED"
            or now >= record.absolute_expires_at
            or (audience == "BACKOFFICE" and now >= record.idle_expires_at)
        ):
            record.status = "EXPIRED"
            session.commit()
            raise auth_error(401, "SESSION_EXPIRED", "The session expired. Sign in again.")
        if audience == "POS" and now >= record.idle_expires_at and record.status == "ACTIVE":
            record.status = "LOCKED"
            session.flush()
            if not allow_locked:
                session.commit()
                raise auth_error(
                    423, "SESSION_LOCKED", "The session is locked. Reauthenticate to continue."
                )
        if record.status == "LOCKED" and not allow_locked:
            raise auth_error(
                423, "SESSION_LOCKED", "The session is locked. Reauthenticate to continue."
            )
        resolved_user = resolve_authorization(session, user, surface=audience)
        authentication = SessionAuthentication(record, resolved_user, credential)
        session.info[AUTH_CONTEXT_KEY] = authentication
        if user.password_reset_required and not allow_reset:
            raise auth_error(
                403, "PASSWORD_RESET_REQUIRED", "Change your temporary password before continuing."
            )
        return authentication

    def validate_csrf(self, authentication: SessionAuthentication, token: str | None) -> None:
        if token is None or not hmac.compare_digest(
            authentication.record.csrf_hash, secret_hash(token)
        ):
            raise auth_error(403, "CSRF_FAILED", "The request could not be verified.")

    def activity(self, session: Session, authentication: SessionAuthentication) -> AuthSessionView:
        now = datetime.now(UTC)
        record = authentication.record
        if now - record.last_activity_at >= timedelta(seconds=15):
            record.last_activity_at = now
            record.idle_expires_at = min(
                now + timedelta(minutes=IDLE_MINUTES[cast(IdentitySurface, record.audience)]),
                record.absolute_expires_at,
            )
        session.flush()
        return AuthSessionView.model_validate(record)

    def lock(self, session: Session, authentication: SessionAuthentication) -> AuthSessionView:
        if authentication.record.audience != "POS":
            raise auth_error(409, "CONFLICT", "Only POS sessions support locking.")
        authentication.record.status = "LOCKED"
        session.commit()
        return AuthSessionView.model_validate(authentication.record)

    def reauthenticate(
        self,
        session: Session,
        authentication: SessionAuthentication,
        *,
        password: str,
        ip: str,
        request_id: str | None,
    ) -> SessionAuthentication:
        user = session.get(User, authentication.user.id)
        now = datetime.now(UTC)
        self._rate_attempt(
            session, account=authentication.user.email, ip=ip, now=now, request_id=request_id
        )
        if user is None or not self.password_hasher.verify_password(password, user.password_hash):
            self._event(
                session,
                "session.reauthentication_failed",
                user_id=authentication.user.id,
                session_id=authentication.record.id,
                request_id=request_id,
            )
            session.commit()
            raise auth_error(
                401, "INVALID_CREDENTIALS", "Invalid credentials or unavailable account."
            )
        if authentication.record.audience == "POS":
            workstation = session.get(Workstation, authentication.record.workstation_id)
            if workstation is None:
                raise auth_error(403, "FORBIDDEN", "The workstation is unavailable.")
            self._workstation(session, authentication.user, workstation.code)
        credential, csrf = new_session_secrets()
        record = authentication.record
        record.credential_hash = secret_hash(credential)
        record.csrf_hash = secret_hash(csrf)
        record.status = "ACTIVE"
        record.last_activity_at = now
        record.idle_expires_at = min(
            now + timedelta(minutes=IDLE_MINUTES[cast(IdentitySurface, record.audience)]),
            record.absolute_expires_at,
        )
        authentication.credential = credential
        self._event(
            session,
            "session.reauthentication_succeeded",
            user_id=user.id,
            session_id=record.id,
            request_id=request_id,
        )
        session.commit()
        return authentication

    @staticmethod
    def _revoke(record: AuthSession, reason: str, now: datetime) -> None:
        if record.status in {"ACTIVE", "LOCKED"}:
            record.status = "REVOKED"
            record.revoked_at = now
            record.revocation_reason = reason

    def logout(
        self, session: Session, authentication: SessionAuthentication, request_id: str | None
    ) -> None:
        self._revoke(authentication.record, "LOGOUT", datetime.now(UTC))
        self._event(
            session,
            "session.logout",
            user_id=authentication.user.id,
            session_id=authentication.record.id,
            request_id=request_id,
        )
        session.commit()

    def list_sessions(
        self, session: Session, user_id: UUID, *, page: int = 1, page_size: int = 25
    ) -> AuthSessionsResponse:
        page = max(1, page)
        page_size = min(100, max(1, page_size))
        total = (
            session.scalar(select(func.count(AuthSession.id)).where(AuthSession.user_id == user_id))
            or 0
        )
        records = session.scalars(
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .order_by(AuthSession.created_at.desc(), AuthSession.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        now = datetime.now(UTC)
        items: list[AuthSessionView] = []
        for record in records:
            view = AuthSessionView.model_validate(record)
            if record.status in {"ACTIVE", "LOCKED"}:
                if now >= record.absolute_expires_at or (
                    record.audience == "BACKOFFICE" and now >= record.idle_expires_at
                ):
                    view.status = "EXPIRED"
                elif record.audience == "POS" and now >= record.idle_expires_at:
                    view.status = "LOCKED"
            items.append(view)
        return AuthSessionsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def revoke_sessions(
        self,
        session: Session,
        *,
        user_id: UUID,
        target_id: UUID | None = None,
        except_id: UUID | None = None,
        reason: str = "USER_REVOKED",
    ) -> None:
        query = select(AuthSession).where(AuthSession.user_id == user_id)
        if target_id is not None:
            query = query.where(AuthSession.id == target_id)
        if except_id is not None:
            query = query.where(AuthSession.id != except_id)
        rows = list(session.scalars(query.order_by(AuthSession.id).with_for_update()))
        if target_id is not None and not rows:
            raise auth_error(404, "NOT_FOUND", "Session not found.")
        for record in rows:
            self._revoke(record, reason, datetime.now(UTC))
        session.flush()

    def change_password(
        self,
        session: Session,
        authentication: SessionAuthentication,
        *,
        current_password: str,
        new_password: str,
        request_id: str | None,
        ip: str,
    ) -> None:
        user = session.get(User, authentication.user.id)
        self._rate_attempt(
            session,
            account=authentication.user.email,
            ip=ip,
            now=datetime.now(UTC),
            request_id=request_id,
        )
        if user is None or not self.password_hasher.verify_password(
            current_password, user.password_hash
        ):
            self._event(
                session,
                "password.change_failed",
                user_id=authentication.user.id,
                request_id=request_id,
            )
            session.commit()
            raise auth_error(
                401, "INVALID_CREDENTIALS", "Invalid credentials or unavailable account."
            )
        if hmac.compare_digest(current_password, new_password):
            raise auth_error(422, "VALIDATION_ERROR", "Choose a different password.")
        user.password_hash = self.password_hasher.hash_password(new_password)
        user.password_reset_required = False
        self._event(session, "password.changed", user_id=user.id, request_id=request_id)
        session.commit()

    def issue_password_reset(
        self,
        session: Session,
        *,
        actor: AuthenticatedUser,
        user_id: UUID,
        reason: str,
        approval_id: UUID | None,
        payload_sha256: str | None,
        request_id: str | None,
    ) -> PasswordResetCredentialView:
        from zeromerma_api.modules.identity.application.privileged_access import (
            authorize_privileged_change,
            require_user_scope,
        )
        from zeromerma_api.modules.identity.infrastructure.privileged_models import (
            IdentityPrivilegedChange,
        )

        lock_identity_boundary(session, exclusive=True)
        actor = resolve_authorization(session, actor, surface="BACKOFFICE")
        require_user_scope(session, actor, "users.manage", user_id)

        if approval_id is not None:
            approval = session.get(IdentityPrivilegedChange, approval_id)
            if (
                approval is None
                or payload_sha256 is None
                or not hmac.compare_digest(approval.payload_sha256, payload_sha256)
            ):
                raise auth_error(409, "CONFLICT", "The approval digest does not match.")
        elif payload_sha256 is not None:
            raise auth_error(
                422, "VALIDATION_ERROR", "An approval identifier is required with its digest."
            )
        actor = authorize_privileged_change(
            session,
            current_user=actor,
            operation="USER_PASSWORD_RESET",
            target_user_id=user_id,
            payload={"reason": reason},
            approval_id=approval_id,
            request_id=request_id,
        )
        require_user_scope(session, actor, "users.manage", user_id)
        user = session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise auth_error(404, "NOT_FOUND", "User not found.")
        now = datetime.now(UTC)
        session.execute(
            update(PasswordResetCredential)
            .where(
                PasswordResetCredential.user_id == user_id,
                PasswordResetCredential.consumed_at.is_(None),
            )
            .values(consumed_at=now)
        )
        credential = secrets.token_urlsafe(32)
        expires_at = now + timedelta(minutes=self.settings.password_reset_ttl_minutes)
        session.add(
            PasswordResetCredential(
                user_id=user_id,
                credential_hash=secret_hash(credential),
                created_at=now,
                expires_at=expires_at,
            )
        )
        user.password_reset_required = True
        self.revoke_sessions(session, user_id=user_id, reason="PASSWORD_RESET")
        self._event(
            session,
            "password.reset_issued",
            user_id=actor.id,
            target_user_id=user_id,
            request_id=request_id,
            reason="ADMINISTRATIVE_RESET",
        )
        session.commit()
        return PasswordResetCredentialView(reset_token=credential, expires_at=expires_at)

    def complete_password_reset(
        self,
        session: Session,
        *,
        credential: str,
        new_password: str,
        ip: str,
        request_id: str | None,
    ) -> None:
        lock_identity_boundary(session, exclusive=True)
        row = session.scalar(
            select(PasswordResetCredential)
            .where(PasswordResetCredential.credential_hash == secret_hash(credential))
            .with_for_update()
        )
        now = datetime.now(UTC)
        self._rate_attempt(
            session,
            account="password-reset:" + secret_hash(credential),
            ip=ip,
            now=now,
            request_id=request_id,
        )
        if row is None or row.consumed_at is not None or row.expires_at <= now:
            self._event(session, "password.reset_failed", user_id=None, request_id=request_id)
            session.commit()
            raise auth_error(
                401, "INVALID_CREDENTIALS", "The reset credential is invalid or expired."
            )
        user = session.scalar(select(User).where(User.id == row.user_id).with_for_update())
        if user is None or not user.is_active or user.is_locked:
            self._event(session, "password.reset_failed", user_id=None, request_id=request_id)
            session.commit()
            raise auth_error(
                401, "INVALID_CREDENTIALS", "The reset credential is invalid or expired."
            )
        set_audit_context(session, user.id, request_id)
        row.consumed_at = now
        user.password_hash = self.password_hasher.hash_password(new_password)
        user.password_reset_required = False
        self.revoke_sessions(session, user_id=user.id, reason="PASSWORD_RESET")
        self._event(session, "password.reset_completed", user_id=user.id, request_id=request_id)
        session.commit()
