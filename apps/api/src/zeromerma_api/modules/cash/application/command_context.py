from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.idempotency.application.schemas import CommandContext
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyError
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, CapabilityCode
from zeromerma_api.modules.identity.application.session_services import (
    AUTH_CONTEXT_KEY,
    SessionAuthentication,
    auth_error,
)
from zeromerma_api.modules.identity.infrastructure.models import User


def resolve_cash_command_context(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    workstation_code: str,
    cash_session_id: UUID | None,
) -> CommandContext:
    """Resolve identity without applying admission rules to historical replays."""
    authentication = session.info.get(AUTH_CONTEXT_KEY)
    workstation = session.execute(
        select(Workstation.id, Workstation.branch_id).where(Workstation.code == workstation_code)
    ).one_or_none()
    if (
        not isinstance(authentication, SessionAuthentication)
        or authentication.record.audience != "POS"
        or authentication.user.id != current_user.id
        or workstation is None
        or authentication.record.workstation_id != workstation.id
    ):
        raise auth_error(403, "FORBIDDEN", "The cash command context is not authorized.")
    return CommandContext(
        actor_user_id=current_user.id,
        surface="POS",
        branch_id=workstation.branch_id,
        workstation_id=workstation.id,
        cash_session_id=cash_session_id,
    )


def authorize_cash_command(
    session: Session,
    current_user: AuthenticatedUser,
    context: CommandContext,
    capability: CapabilityCode,
) -> None:
    if (
        current_user.authorization_surface != "POS"
        or context.surface != "POS"
        or context.branch_id is None
    ):
        raise auth_error(403, "FORBIDDEN", "The cash command surface is not authorized.")
    refreshed = resolve_authorization(session, current_user, surface="POS")
    require_branches(refreshed, capability, [context.branch_id, *context.related_branch_ids])
    validate_cash_command_reference(session, context)


def validate_cash_command_reference(session: Session, context: CommandContext) -> None:
    """Validate a historical cash reference after authorization, before reservation."""
    if context.cash_session_id is None:
        return
    row = session.execute(
        select(CashSession.user_id, CashSession.workstation_id, CashSession.branch_id).where(
            CashSession.id == context.cash_session_id
        )
    ).one_or_none()
    if row is None:
        raise IdempotencyError("CASH_SESSION_NOT_FOUND", 409, "The cash session was not found.")
    if (
        row.user_id != context.actor_user_id
        or row.workstation_id != context.workstation_id
        or row.branch_id != context.branch_id
    ):
        raise auth_error(403, "FORBIDDEN", "The cash session belongs to another context.")


def lock_cash_session(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    workstation_id: UUID,
    branch_id: UUID,
    cash_session_id: UUID,
    require_open: bool = True,
) -> CashSession:
    """Acquire the exact shift after reservation and refresh after any lock wait."""
    row = session.scalar(
        select(CashSession)
        .where(CashSession.id == cash_session_id)
        # Reservation foreign keys hold KEY SHARE; serialize without upgrading those locks.
        .with_for_update(of=CashSession, key_share=True)
        .execution_options(populate_existing=True)
    )
    if row is None:
        raise IdempotencyError("CASH_SESSION_NOT_FOUND", 409, "The cash session was not found.")
    if (
        row.user_id != current_user.id
        or row.workstation_id != workstation_id
        or row.branch_id != branch_id
    ):
        raise auth_error(403, "FORBIDDEN", "The cash session belongs to another context.")
    if require_open and row.status != "OPEN":
        raise IdempotencyError("CASH_SESSION_CLOSED", 409, "The cash session is already closed.")
    return row


def lock_cash_opening(
    session: Session, *, current_user: AuthenticatedUser, context: CommandContext
) -> None:
    """Serialize both opening uniqueness rules and respect branch-before-station locking."""
    session.scalar(
        select(User.id).where(User.id == current_user.id).with_for_update(key_share=True)
    )
    branch = session.execute(
        select(Branch.id, Branch.is_active)
        .where(Branch.id == context.branch_id)
        .with_for_update(read=True)
    ).one_or_none()
    workstation = session.execute(
        select(Workstation.branch_id, Workstation.is_active)
        .where(Workstation.id == context.workstation_id)
        .with_for_update(key_share=True)
    ).one_or_none()
    if (
        branch is None
        or not branch.is_active
        or workstation is None
        or not workstation.is_active
        or workstation.branch_id != context.branch_id
    ):
        raise IdempotencyError("CASH_CONTEXT_CHANGED", 409, "The workstation context changed.")
