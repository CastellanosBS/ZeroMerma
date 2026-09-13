from __future__ import annotations

from collections.abc import Iterable, Mapping
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from zeromerma_api.modules.identity.application.authorization import require_branches
from zeromerma_api.modules.identity.application.permissions import PermissionCode


def action_allowed(
    session: Session,
    capability: PermissionCode,
    branch_ids: Iterable[UUID] = (),
    *,
    global_only: bool = False,
) -> bool:
    """Project the current server grant into an action hint; enforcement stays at the boundary."""
    from zeromerma_api.db.access_scope import authorization_scope

    context = authorization_scope(session)
    if context is None:
        return False
    try:
        require_branches(context.user, capability, branch_ids, global_only=global_only)
    except HTTPException:
        return False
    return True


def restrict_actions[ActionView: BaseModel](
    session: Session,
    actions: ActionView,
    requirements: Mapping[str, PermissionCode],
    *,
    branch_ids: Iterable[UUID] = (),
    global_only: bool = False,
) -> ActionView:
    """Intersect domain state with explicit capability and resource scope requirements."""
    branches = tuple(branch_ids)
    updates = {
        field: bool(getattr(actions, field))
        and action_allowed(session, capability, branches, global_only=global_only)
        for field, capability in requirements.items()
    }
    return actions.model_copy(update=updates)
