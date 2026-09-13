from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import exists, select, true
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment


def operational_user_predicate(session: Session) -> ColumnElement[bool]:
    """Limit staff selectors to active memberships in the operation's authorized branches."""
    from zeromerma_api.db.access_scope import authorization_scope

    context = authorization_scope(session)
    if context is None:
        raise HTTPException(
            status_code=403, detail="An explicit authorization context is required."
        )
    if context.branch_ids is None:
        return true()
    return exists(
        select(UserBranchAssignment.id).where(
            UserBranchAssignment.user_id == User.id,
            UserBranchAssignment.is_active.is_(True),
            UserBranchAssignment.branch_id.in_(context.branch_ids),
        )
    )
