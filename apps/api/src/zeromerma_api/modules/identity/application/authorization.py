from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import cast
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.identity.application.permissions import (
    PERMISSION_CODES,
    SUPERADMIN_ROLE_CODE,
    PermissionCode,
)
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    EffectiveGrant,
    IdentitySurface,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)


def resolve_authorization(
    session: Session,
    user: User | AuthenticatedUser,
    *,
    surface: IdentitySurface | None = None,
) -> AuthenticatedUser:
    """Resolve current database grants per capability; tokens contain no authority."""
    # Column projections see current database authority without overwriting pending ORM edits.
    identity = session.execute(
        select(
            User.id,
            User.email,
            User.full_name,
            User.allowed_surfaces,
            User.default_surface,
            User.is_active,
            User.is_locked,
        ).where(User.id == user.id)
    ).one_or_none()
    result = AuthenticatedUser.model_validate(identity if identity is not None else user)
    grants: list[EffectiveGrant] = []
    is_superadministrator = False
    if identity is not None and identity.is_active and not identity.is_locked:
        assignments = list(
            session.execute(
                select(
                    UserRoleAssignment.id,
                    UserRoleAssignment.scope_type,
                    Role.id,
                    Role.code,
                    Role.surfaces,
                )
                .select_from(UserRoleAssignment)
                .join(Role, Role.id == UserRoleAssignment.role_id)
                .where(
                    UserRoleAssignment.user_id == identity.id,
                    UserRoleAssignment.is_active.is_(True),
                    Role.is_active.is_(True),
                )
            ).tuples()
        )
        assigned_branches = set(
            session.scalars(
                select(UserBranchAssignment.branch_id).where(
                    UserBranchAssignment.user_id == identity.id,
                    UserBranchAssignment.is_active.is_(True),
                )
            )
        )
        assignment_ids = [assignment_id for assignment_id, *_ in assignments]
        branch_rows = session.execute(
            select(
                UserRoleAssignmentBranchScope.assignment_id,
                UserRoleAssignmentBranchScope.branch_id,
            ).where(UserRoleAssignmentBranchScope.assignment_id.in_(assignment_ids))
        ).tuples()
        branches_by_assignment: dict[UUID, set[UUID]] = {}
        for assignment_id, branch_id in branch_rows:
            branches_by_assignment.setdefault(assignment_id, set()).add(branch_id)
        permission_rows = session.execute(
            select(RolePermission.role_id, Permission.code, Permission.surfaces)
            .select_from(RolePermission)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(
                RolePermission.role_id.in_([row[2] for row in assignments]),
                Permission.is_active.is_(True),
                Permission.code.in_(PERMISSION_CODES),
            )
        ).tuples()
        permissions_by_role: dict[UUID, list[tuple[PermissionCode, list[str]]]] = {}
        for role_id, code, permission_surfaces in permission_rows:
            permissions_by_role.setdefault(role_id, []).append(
                (cast(PermissionCode, code), permission_surfaces)
            )
        global_codes: set[PermissionCode] = set()
        branches_by_code: dict[PermissionCode, set[UUID]] = {}
        for assignment_id, scope_type, role_id, role_code, role_surfaces in assignments:
            branch_ids = branches_by_assignment.get(assignment_id, set())
            if scope_type == "GLOBAL":
                if branch_ids:
                    continue
            elif scope_type == "BRANCH_SET":
                if not branch_ids or role_code == SUPERADMIN_ROLE_CODE:
                    continue
            else:
                continue
            surfaces = set(role_surfaces) & set(identity.allowed_surfaces)
            if surface is not None:
                surfaces &= {surface}
            if not surfaces:
                continue
            if role_code == SUPERADMIN_ROLE_CODE and "BACKOFFICE" in surfaces:
                is_superadministrator = True
            for code, permission_surfaces in permissions_by_role.get(role_id, []):
                if not surfaces.intersection(permission_surfaces):
                    continue
                if scope_type == "GLOBAL":
                    global_codes.add(code)
                else:
                    branches_by_code.setdefault(code, set()).update(
                        branch_ids & assigned_branches,
                    )
        for code in sorted(global_codes | branches_by_code.keys()):
            if code in global_codes:
                grants.append(EffectiveGrant(capability=code, scope_type="GLOBAL", branch_ids=[]))
            elif branches_by_code[code]:
                grants.append(
                    EffectiveGrant(
                        capability=code,
                        scope_type="BRANCH_SET",
                        branch_ids=sorted(branches_by_code[code], key=str),
                    )
                )
    payload = {
        "user_id": str(result.id),
        "is_active": result.is_active,
        "surfaces": sorted(result.allowed_surfaces),
        "authorization_surface": surface,
        "is_superadministrator": is_superadministrator,
        "grants": [grant.model_dump(mode="json") for grant in grants],
    }
    version = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return result.model_copy(
        update={
            "effective_grants": grants,
            "authorization_version": version,
            "authorization_surface": surface,
            "is_superadministrator": is_superadministrator,
        }
    )


def require_capability(user: AuthenticatedUser, code: PermissionCode) -> EffectiveGrant:
    if user.is_active and code in PERMISSION_CODES:
        for grant in user.effective_grants:
            if grant.capability == code and (
                (grant.scope_type == "GLOBAL" and not grant.branch_ids)
                or (grant.scope_type == "BRANCH_SET" and grant.branch_ids)
            ):
                return grant
    raise HTTPException(status_code=403, detail="This operation is not authorized.")


def require_branches(
    user: AuthenticatedUser,
    code: PermissionCode,
    branch_ids: Iterable[UUID],
    *,
    global_only: bool = False,
) -> EffectiveGrant:
    grant = require_capability(user, code)
    if grant.scope_type == "GLOBAL":
        return grant
    if global_only or not set(branch_ids).issubset(grant.branch_ids):
        raise HTTPException(status_code=403, detail="This operation is outside your branch scope.")
    return grant
