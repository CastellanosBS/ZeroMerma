from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, TypedDict, cast
from uuid import UUID

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError
from sqlalchemy import and_, delete, exists, select, true
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.admin_role_schemas import (
    AdminRoleStatusChangeRequest,
    AdminRoleUpdateRequest,
)
from zeromerma_api.modules.identity.application.admin_schemas import (
    AdminAssignmentScopeRequest,
    AdminUserBranchAssignmentCommand,
    AdminUserLockRequest,
    AdminUserStatusChangeRequest,
    AdminUserUpdateRequest,
)
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    require_capability,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.permissions import (
    INITIAL_OWNER_DESIGNATION,
    SUPERADMIN_ROLE_CODE,
    PermissionCode,
)
from zeromerma_api.modules.identity.application.privileged_schemas import (
    PrivilegedBranchTargetRequest,
    PrivilegedChangeCreateRequest,
    PrivilegedChangeView,
    PrivilegedOperation,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.security import PasswordHasher
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.identity.infrastructure.privileged_models import (
    IdentityPrivilegedChange,
    IdentityPrivilegeState,
    IdentityRecoveryCredential,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

# This versioned grant list is deliberately independent of the live capability catalog.
# Adding a catalog entry must never grant it automatically to an existing Superadministrator.
INITIAL_SUPERADMIN_PERMISSION_CODES: tuple[PermissionCode, ...] = (
    "pos.operate",
    "sales_tickets.view",
    "sales_tickets.reprint",
    "orders.view",
    "orders.manage",
    "orders.cancel",
    "returns_corrections.view",
    "returns_corrections.manage",
    "catalog.view",
    "catalog.manage",
    "catalog.availability.manage",
    "pricing.view",
    "pricing.manage",
    "recipes.view",
    "recipes.manage",
    "discounts.view",
    "discounts.manage",
    "inventory.view",
    "inventory.adjust",
    "branches.view",
    "branches.manage",
    "workstations.view",
    "workstations.manage",
    "transfers.view",
    "transfers.manage",
    "transfers.execute",
    "transfers.cancel",
    "production.view",
    "production.manage",
    "production.execute",
    "production.cancel",
    "waste.view",
    "waste.manage",
    "suppliers.view",
    "suppliers.manage",
    "purchases.view",
    "purchases.manage",
    "purchases.confirm",
    "purchases.receive",
    "purchases.cancel",
    "cash_finance.view",
    "cash_finance.manage",
    "quality_hygiene.view",
    "quality_hygiene.manage",
    "users.view",
    "users.manage",
    "roles.view",
    "roles.manage",
    "role_assignments.manage",
    "audit.view",
    "audit.export",
    "reports.view",
    "reports.export",
    "config.view",
    "config.manage",
)
_OPERATION_CAPABILITIES: dict[PrivilegedOperation, PermissionCode] = {
    "USER_UPDATE": "users.manage",
    "USER_STATUS": "users.manage",
    "USER_LOCK": "users.manage",
    "USER_UNLOCK": "users.manage",
    "USER_BRANCH_ASSIGNMENT": "role_assignments.manage",
    "USER_BRANCH_REMOVAL": "role_assignments.manage",
    "USER_BRANCH_DEFAULT": "role_assignments.manage",
    "ROLE_ASSIGNMENT": "role_assignments.manage",
    "ROLE_REMOVAL": "role_assignments.manage",
    "ROLE_UPDATE": "roles.manage",
    "ROLE_STATUS": "roles.manage",
}
_PAYLOAD_MODELS: dict[PrivilegedOperation, type[BaseModel] | None] = {
    "USER_UPDATE": AdminUserUpdateRequest,
    "USER_STATUS": AdminUserStatusChangeRequest,
    "USER_LOCK": AdminUserLockRequest,
    "USER_UNLOCK": None,
    "USER_BRANCH_ASSIGNMENT": AdminUserBranchAssignmentCommand,
    "USER_BRANCH_REMOVAL": PrivilegedBranchTargetRequest,
    "USER_BRANCH_DEFAULT": PrivilegedBranchTargetRequest,
    "ROLE_ASSIGNMENT": AdminAssignmentScopeRequest,
    "ROLE_REMOVAL": None,
    "ROLE_UPDATE": AdminRoleUpdateRequest,
    "ROLE_STATUS": AdminRoleStatusChangeRequest,
}


@dataclass(frozen=True)
class OwnerProvisioningResult:
    user_id: UUID
    recovery_material: str = field(repr=False)


def lock_privileged_lifecycle(session: Session) -> IdentityPrivilegeState:
    session.execute(insert(IdentityPrivilegeState).values(id=1).on_conflict_do_nothing())
    return session.scalars(
        select(IdentityPrivilegeState)
        .where(IdentityPrivilegeState.id == 1)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one()


def refresh_actor(session: Session, current_user: AuthenticatedUser) -> AuthenticatedUser:
    identity = session.scalars(
        select(User).where(User.id == current_user.id).execution_options(populate_existing=True)
    ).one_or_none()
    if identity is None or not identity.is_active or identity.is_locked:
        raise HTTPException(status_code=403, detail="The acting account is not active.")
    return resolve_authorization(session, identity, surface="BACKOFFICE")


def active_superadmin_ids(session: Session) -> set[UUID]:
    rows = session.execute(
        select(User, Role, UserRoleAssignment)
        .join(UserRoleAssignment, UserRoleAssignment.user_id == User.id)
        .join(Role, Role.id == UserRoleAssignment.role_id)
        .where(
            User.is_active.is_(True),
            User.is_locked.is_(False),
            Role.is_active.is_(True),
            Role.code == SUPERADMIN_ROLE_CODE,
            UserRoleAssignment.is_active.is_(True),
            UserRoleAssignment.scope_type == "GLOBAL",
        )
    ).tuples()
    return {
        user.id
        for user, role, assignment in rows
        if "BACKOFFICE" in user.allowed_surfaces
        and "BACKOFFICE" in role.surfaces
        and not session.scalar(
            select(UserRoleAssignmentBranchScope.branch_id)
            .where(UserRoleAssignmentBranchScope.assignment_id == assignment.id)
            .limit(1)
        )
    }


def has_superadmin_assignment(session: Session, user_id: UUID) -> bool:
    return (
        session.scalar(
            select(UserRoleAssignment.id)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(UserRoleAssignment.user_id == user_id, Role.code == SUPERADMIN_ROLE_CODE)
            .limit(1)
        )
        is not None
    )


def target_branch_ids(session: Session, user_id: UUID) -> set[UUID]:
    return set(
        session.scalars(
            select(UserBranchAssignment.branch_id).where(
                UserBranchAssignment.user_id == user_id, UserBranchAssignment.is_active.is_(True)
            )
        )
    )


def require_user_scope(
    session: Session,
    actor: AuthenticatedUser,
    capability: PermissionCode,
    user_id: UUID,
) -> None:
    branches = target_branch_ids(session, user_id)
    has_global_assignment = (
        session.scalar(
            select(UserRoleAssignment.id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.scope_type == "GLOBAL",
            )
            .limit(1)
        )
        is not None
    )
    require_branches(actor, capability, branches, global_only=has_global_assignment or not branches)


def can_access_user(
    session: Session, actor: AuthenticatedUser, capability: PermissionCode, user_id: UUID
) -> bool:
    try:
        require_user_scope(session, actor, capability, user_id)
    except HTTPException as error:
        if error.status_code != 403:
            raise
        return False
    return True


def user_scope_predicate(
    actor: AuthenticatedUser,
    capability: PermissionCode,
    *,
    allowed_branch_ids: Iterable[UUID] | None = None,
) -> ColumnElement[bool]:
    grant = require_capability(actor, capability)
    if grant.scope_type == "GLOBAL" and allowed_branch_ids is None:
        return true()
    branch_ids = set(grant.branch_ids)
    if allowed_branch_ids is not None:
        allowed = set(allowed_branch_ids)
        branch_ids = allowed if grant.scope_type == "GLOBAL" else branch_ids & allowed
    membership = [UserBranchAssignment.user_id == User.id, UserBranchAssignment.is_active.is_(True)]
    return and_(
        exists(select(UserBranchAssignment.id).correlate(User).where(*membership)),
        ~exists(
            select(UserBranchAssignment.id)
            .correlate(User)
            .where(*membership, UserBranchAssignment.branch_id.not_in(branch_ids))
        ),
        ~exists(
            select(UserRoleAssignment.id)
            .correlate(User)
            .where(
                UserRoleAssignment.user_id == User.id,
                UserRoleAssignment.is_active.is_(True),
                UserRoleAssignment.scope_type == "GLOBAL",
            )
        ),
    )


def assignment_branch_ids(session: Session, assignment_id: UUID) -> list[UUID]:
    return sorted(
        session.scalars(
            select(UserRoleAssignmentBranchScope.branch_id).where(
                UserRoleAssignmentBranchScope.assignment_id == assignment_id
            )
        ),
        key=str,
    )


def _record(
    session: Session,
    *,
    actor_id: UUID | None,
    action: str,
    resource_id: str,
    request_id: str | None = None,
    metadata: dict[str, Any],
) -> None:
    AuditRecorder().record(
        session,
        actor_id=actor_id,
        action=action,
        resource_type="identity_privilege",
        resource_id=resource_id,
        branch_id=None,
        request_id=request_id,
        metadata=metadata,
    )
    OutboxWriter().append(
        session,
        aggregate_type="identity_privilege",
        aggregate_id=resource_id,
        event_name=f"{action}.v1",
        payload={**metadata, "actor_id": str(actor_id) if actor_id else None},
        headers={"request_id": request_id, "scope_type": "GLOBAL"},
    )


def _require_superadmin(
    session: Session,
    user_id: UUID,
    operation: PrivilegedOperation,
) -> AuthenticatedUser:
    user = session.get(User, user_id, populate_existing=True)
    if user is None or user_id not in active_superadmin_ids(session):
        raise HTTPException(
            status_code=403, detail="An active explicit Superadministrator is required."
        )
    actor = resolve_authorization(session, user, surface="BACKOFFICE")
    require_branches(actor, _OPERATION_CAPABILITIES[operation], [], global_only=True)
    return actor


def _canonical_payload(operation: PrivilegedOperation, payload: dict[str, Any]) -> dict[str, Any]:
    model = _PAYLOAD_MODELS[operation]
    if model is None:
        if payload:
            raise HTTPException(status_code=422, detail="This operation requires an empty payload.")
        return {}
    if set(payload) - set(model.model_fields):
        raise HTTPException(status_code=422, detail="The approval payload has unknown fields.")
    try:
        return model.model_validate(payload).model_dump(mode="json", exclude_unset=True)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail="The approval payload is invalid.") from error


def _payload_digest(
    operation: str,
    user_id: UUID | None,
    role_id: UUID | None,
    payload: dict[str, Any],
) -> str:
    envelope = {
        "operation": operation,
        "target_user_id": str(user_id) if user_id else None,
        "target_role_id": str(role_id) if role_id else None,
        "payload": payload,
    }
    return hashlib.sha256(
        json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _requires_dual_approval(
    session: Session,
    operation: PrivilegedOperation,
    user_id: UUID | None,
    role_id: UUID | None,
    payload: dict[str, Any],
) -> bool:
    if operation == "USER_UPDATE":
        target = session.get(User, user_id) if user_id is not None else None
        if target is None:
            return False
        email = payload.get("email")
        surfaces = payload.get("allowed_surfaces")
        changes_identity = isinstance(email, str) and email.strip().lower() != target.email
        changes_access = isinstance(surfaces, list) and set(surfaces) != set(
            target.allowed_surfaces
        )
        if not changes_identity and not changes_access:
            return False
    if user_id is not None and has_superadmin_assignment(session, user_id):
        return True
    if role_id is not None:
        role = session.get(Role, role_id)
        if role is not None and role.code == SUPERADMIN_ROLE_CODE:
            return True
        if operation not in {"ROLE_UPDATE", "ROLE_STATUS"}:
            return False
        superadmins = active_superadmin_ids(session)
        return (
            session.scalar(
                select(UserRoleAssignment.id)
                .where(
                    UserRoleAssignment.role_id == role_id,
                    UserRoleAssignment.is_active.is_(True),
                    UserRoleAssignment.user_id.in_(superadmins),
                )
                .limit(1)
            )
            is not None
        )
    return False


def authorize_privileged_change(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    operation: PrivilegedOperation,
    target_user_id: UUID | None = None,
    target_role_id: UUID | None = None,
    payload: dict[str, Any],
    approval_id: UUID | None = None,
    request_id: str | None = None,
) -> AuthenticatedUser:
    lock_privileged_lifecycle(session)
    actor = refresh_actor(session, current_user)
    require_capability(actor, _OPERATION_CAPABILITIES[operation])
    if not _requires_dual_approval(session, operation, target_user_id, target_role_id, payload):
        if approval_id is not None:
            raise HTTPException(
                status_code=409, detail="The target no longer requires this approval."
            )
        return actor
    if len(active_superadmin_ids(session)) < 2:
        raise HTTPException(
            status_code=409, detail="A second Superadministrator requires the local recovery CLI."
        )
    if approval_id is None:
        raise HTTPException(status_code=409, detail="This change requires a durable dual approval.")
    change = session.scalars(
        select(IdentityPrivilegedChange)
        .where(IdentityPrivilegedChange.id == approval_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).one_or_none()
    now = datetime.now(tz=UTC)
    if (
        change is None
        or change.initiator_user_id != actor.id
        or change.approved_at is None
        or change.approver_user_id is None
        or change.consumed_at is not None
        or change.expires_at <= now
    ):
        raise HTTPException(
            status_code=409, detail="The approval is missing, expired, or already consumed."
        )
    expected_digest = _payload_digest(
        operation, target_user_id, target_role_id, _canonical_payload(operation, payload)
    )
    stored_digest = _payload_digest(
        change.operation, change.target_user_id, change.target_role_id, change.payload
    )
    if not hmac.compare_digest(change.payload_sha256, expected_digest) or not hmac.compare_digest(
        change.payload_sha256, stored_digest
    ):
        raise HTTPException(
            status_code=409, detail="The approved payload does not match this exact change."
        )
    _require_superadmin(session, actor.id, operation)
    _require_superadmin(session, change.approver_user_id, operation)
    if actor.id == change.approver_user_id:
        raise HTTPException(
            status_code=403, detail="Initiator and approver must be different accounts."
        )
    change.consumed_at = now
    _record(
        session,
        actor_id=actor.id,
        action="identity.privileged_change.consumed",
        resource_id=str(change.id),
        request_id=request_id,
        metadata={
            "operation": operation,
            "payload_sha256": change.payload_sha256,
            "approver_user_id": str(change.approver_user_id),
        },
    )
    return actor


def ensure_superadmin_remains(session: Session) -> None:
    session.flush()
    state = session.get(IdentityPrivilegeState, 1)
    if (
        state is not None
        and state.initial_owner_user_id is not None
        and not active_superadmin_ids(session)
    ):
        raise HTTPException(
            status_code=409,
            detail="The last active Superadministrator must remain globally authorized.",
        )
    if state is not None and state.initial_owner_user_id is not None:
        # These explicit capabilities keep the approved privileged lifecycle operable.
        codes = set(
            session.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(Role, Role.id == RolePermission.role_id)
                .where(Role.code == SUPERADMIN_ROLE_CODE, Permission.is_active.is_(True))
            )
        )
        if not {"users.manage", "roles.manage", "role_assignments.manage"} <= codes:
            raise HTTPException(
                status_code=409,
                detail="Superadministrators must retain privileged administration capabilities.",
            )


def set_role_assignment(
    session: Session,
    *,
    actor: AuthenticatedUser,
    user_id: UUID,
    role_id: UUID,
    scope: AdminAssignmentScopeRequest | None,
) -> dict[str, Any]:
    require_user_scope(session, actor, "role_assignments.manage", user_id)
    user = session.get(User, user_id)
    role = session.get(Role, role_id)
    if user is None or role is None:
        raise HTTPException(status_code=404, detail="The user or role does not exist.")
    assignment = session.scalar(
        select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == user_id, UserRoleAssignment.role_id == role_id
        )
    )
    previous = (
        None
        if assignment is None
        else {
            "scope_type": assignment.scope_type,
            "branch_ids": [str(value) for value in assignment_branch_ids(session, assignment.id)],
            "is_active": assignment.is_active,
        }
    )
    if scope is None:
        if assignment is None or not assignment.is_active:
            raise HTTPException(status_code=404, detail="The role assignment does not exist.")
        assignment.is_active = False
    else:
        if not role.is_active:
            raise HTTPException(status_code=422, detail="Inactive roles cannot be assigned.")
        require_branches(
            actor,
            "role_assignments.manage",
            scope.branch_ids,
            global_only=scope.scope_type == "GLOBAL",
        )
        if scope.scope_type == "BRANCH_SET":
            branches = set(
                session.scalars(
                    select(Branch.id).where(
                        Branch.id.in_(scope.branch_ids), Branch.is_active.is_(True)
                    )
                )
            )
            if branches != set(scope.branch_ids) or not branches <= target_branch_ids(
                session, user_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Assignment branches must be active memberships of the target user.",
                )
        if role.code == SUPERADMIN_ROLE_CODE and scope.scope_type != "GLOBAL":
            raise HTTPException(
                status_code=409,
                detail="Superadministrator assignments require explicit GLOBAL scope.",
            )
        if user_id == actor.id:
            # Replacing one's own assignment may reduce authority, never add it.
            existing_branches = (
                set(assignment_branch_ids(session, assignment.id)) if assignment else set()
            )
            if (
                assignment is None
                or not assignment.is_active
                or (scope.scope_type == "GLOBAL" and assignment.scope_type != "GLOBAL")
                or (
                    assignment.scope_type != "GLOBAL"
                    and not set(scope.branch_ids) <= existing_branches
                )
            ):
                raise HTTPException(status_code=403, detail="Self-elevation is forbidden.")
        if assignment is None:
            assignment = UserRoleAssignment(
                user_id=user_id,
                role_id=role_id,
                scope_type=scope.scope_type,
                is_active=True,
                assigned_by_user_id=actor.id,
            )
            session.add(assignment)
            session.flush()
        else:
            assignment.scope_type = scope.scope_type
            assignment.is_active = True
            assignment.assigned_by_user_id = actor.id
        session.execute(
            delete(UserRoleAssignmentBranchScope).where(
                UserRoleAssignmentBranchScope.assignment_id == assignment.id
            )
        )
        session.add_all(
            [
                UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=branch_id)
                for branch_id in scope.branch_ids
            ]
        )
    ensure_superadmin_remains(session)

    return {
        "previous_assignment": previous,
        "current_assignment": {
            "scope_type": assignment.scope_type,
            "branch_ids": [str(value) for value in assignment_branch_ids(session, assignment.id)],
            "is_active": assignment.is_active,
        },
    }


class _ExecutionArguments(TypedDict):
    current_user: AuthenticatedUser
    request_id: str | None
    approval_id: UUID


class PrivilegedAccessService:
    def propose(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: PrivilegedChangeCreateRequest,
        request_id: str | None,
    ) -> PrivilegedChangeView:
        lock_privileged_lifecycle(session)
        actor = _require_superadmin(session, current_user.id, command.operation)
        if len(active_superadmin_ids(session)) < 2:
            raise HTTPException(
                status_code=409,
                detail="A second Superadministrator requires the local recovery CLI.",
            )
        payload = _canonical_payload(command.operation, command.payload)
        if not _requires_dual_approval(
            session, command.operation, command.target_user_id, command.target_role_id, payload
        ):
            raise HTTPException(
                status_code=422, detail="This operation does not require privileged approval."
            )
        if command.target_user_id is not None and session.get(User, command.target_user_id) is None:
            raise HTTPException(status_code=404, detail="The target user does not exist.")
        if command.target_role_id is not None and session.get(Role, command.target_role_id) is None:
            raise HTTPException(status_code=404, detail="The target role does not exist.")
        now = datetime.now(tz=UTC)
        change = IdentityPrivilegedChange(
            operation=command.operation,
            target_user_id=command.target_user_id,
            target_role_id=command.target_role_id,
            payload=payload,
            payload_sha256=_payload_digest(
                command.operation, command.target_user_id, command.target_role_id, payload
            ),
            reason=command.reason.strip(),
            initiator_user_id=actor.id,
            created_at=now,
            expires_at=now + timedelta(minutes=command.expires_in_minutes),
        )
        session.add(change)
        session.flush()
        _record(
            session,
            actor_id=actor.id,
            action="identity.privileged_change.proposed",
            resource_id=str(change.id),
            request_id=request_id,
            metadata={
                "operation": change.operation,
                "payload_sha256": change.payload_sha256,
                "reason": change.reason,
                "expires_at": change.expires_at.isoformat(),
            },
        )
        session.commit()
        return PrivilegedChangeView.model_validate(change)

    def get_change(
        self, session: Session, *, current_user: AuthenticatedUser, change_id: UUID
    ) -> PrivilegedChangeView:
        change = self._get_change(session, change_id)
        _require_superadmin(session, current_user.id, cast(PrivilegedOperation, change.operation))
        return PrivilegedChangeView.model_validate(change)

    def approve(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        change_id: UUID,
        payload_sha256: str,
        request_id: str | None,
    ) -> PrivilegedChangeView:
        lock_privileged_lifecycle(session)
        change = self._get_change(session, change_id)
        operation = cast(PrivilegedOperation, change.operation)
        approver = _require_superadmin(session, current_user.id, operation)
        _require_superadmin(session, change.initiator_user_id, operation)
        if approver.id == change.initiator_user_id:
            raise HTTPException(
                status_code=403, detail="Initiator and approver must be different accounts."
            )
        if (
            change.approved_at is not None
            or change.consumed_at is not None
            or change.expires_at <= datetime.now(tz=UTC)
        ):
            raise HTTPException(status_code=409, detail="The approval is expired or already used.")
        self._verify_digest(change, payload_sha256)
        change.approver_user_id = approver.id
        change.approved_at = datetime.now(tz=UTC)
        _record(
            session,
            actor_id=approver.id,
            action="identity.privileged_change.approved",
            resource_id=str(change.id),
            request_id=request_id,
            metadata={
                "initiator_user_id": str(change.initiator_user_id),
                "payload_sha256": change.payload_sha256,
            },
        )
        session.commit()
        return PrivilegedChangeView.model_validate(change)

    def execute(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        change_id: UUID,
        payload_sha256: str,
        request_id: str | None,
    ) -> PrivilegedChangeView:
        # Domain services consume the exact approval inside their mutation transaction.
        from zeromerma_api.modules.identity.application.admin_role_services import AdminRoleService
        from zeromerma_api.modules.identity.application.admin_services import AdminUserService

        lock_privileged_lifecycle(session)
        change = self._get_change(session, change_id)
        self._verify_digest(change, payload_sha256)
        if change.initiator_user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Only the original initiator can execute this change."
            )
        users = AdminUserService()
        roles = AdminRoleService()
        common: _ExecutionArguments = dict(
            current_user=current_user, request_id=request_id, approval_id=change.id
        )
        # Explicit dispatch keeps the approved command bound to its original target and schema.
        if change.operation == "USER_UPDATE" and change.target_user_id is not None:
            users.update_user(
                session,
                user_id=change.target_user_id,
                command=AdminUserUpdateRequest.model_validate(change.payload),
                **common,
            )
        elif change.operation == "USER_STATUS" and change.target_user_id is not None:
            users.change_status(
                session,
                user_id=change.target_user_id,
                command=AdminUserStatusChangeRequest.model_validate(change.payload),
                **common,
            )
        elif change.operation == "USER_LOCK" and change.target_user_id is not None:
            users.lock_user(
                session,
                user_id=change.target_user_id,
                command=AdminUserLockRequest.model_validate(change.payload),
                **common,
            )
        elif change.operation == "USER_UNLOCK" and change.target_user_id is not None:
            users.unlock_user(session, user_id=change.target_user_id, **common)
        elif change.operation == "USER_BRANCH_ASSIGNMENT" and change.target_user_id is not None:
            users.add_branch_assignment(
                session,
                user_id=change.target_user_id,
                command=AdminUserBranchAssignmentCommand.model_validate(change.payload),
                **common,
            )
        elif change.operation == "USER_BRANCH_REMOVAL" and change.target_user_id is not None:
            users.deactivate_branch_assignment(
                session,
                user_id=change.target_user_id,
                branch_id=PrivilegedBranchTargetRequest.model_validate(change.payload).branch_id,
                **common,
            )
        elif change.operation == "USER_BRANCH_DEFAULT" and change.target_user_id is not None:
            users.set_default_branch_assignment(
                session,
                user_id=change.target_user_id,
                branch_id=PrivilegedBranchTargetRequest.model_validate(change.payload).branch_id,
                **common,
            )
        elif (
            change.operation == "ROLE_ASSIGNMENT"
            and change.target_user_id is not None
            and change.target_role_id is not None
        ):
            users.assign_role(
                session,
                user_id=change.target_user_id,
                role_id=change.target_role_id,
                command=AdminAssignmentScopeRequest.model_validate(change.payload),
                **common,
            )
        elif (
            change.operation == "ROLE_REMOVAL"
            and change.target_user_id is not None
            and change.target_role_id is not None
        ):
            users.remove_role(
                session, user_id=change.target_user_id, role_id=change.target_role_id, **common
            )
        elif change.operation == "ROLE_UPDATE" and change.target_role_id is not None:
            roles.update_role(
                session,
                role_id=change.target_role_id,
                command=AdminRoleUpdateRequest.model_validate(change.payload),
                **common,
            )
        elif change.operation == "ROLE_STATUS" and change.target_role_id is not None:
            roles.change_status(
                session,
                role_id=change.target_role_id,
                command=AdminRoleStatusChangeRequest.model_validate(change.payload),
                **common,
            )
        else:
            raise HTTPException(
                status_code=422, detail="The stored privileged operation is invalid."
            )
        return PrivilegedChangeView.model_validate(change)

    @staticmethod
    def _get_change(session: Session, change_id: UUID) -> IdentityPrivilegedChange:
        change = session.get(IdentityPrivilegedChange, change_id, populate_existing=True)
        if change is None:
            raise HTTPException(status_code=404, detail="The privileged change does not exist.")
        return change

    @staticmethod
    def _verify_digest(change: IdentityPrivilegedChange, confirmed: str) -> None:
        actual = _payload_digest(
            change.operation, change.target_user_id, change.target_role_id, change.payload
        )
        if not hmac.compare_digest(change.payload_sha256, confirmed) or not hmac.compare_digest(
            change.payload_sha256, actual
        ):
            raise HTTPException(
                status_code=409, detail="The exact persisted payload must be confirmed."
            )

    def bootstrap_owner(
        self,
        session: Session,
        *,
        email: str,
        full_name: str,
        password: str,
        authorized_host: str,
        designation: str = INITIAL_OWNER_DESIGNATION,
    ) -> OwnerProvisioningResult:
        state = lock_privileged_lifecycle(session)
        if designation != INITIAL_OWNER_DESIGNATION or not authorized_host.strip():
            raise ValueError("Explicit owner designation and authorized host are required.")
        if (
            state.initial_owner_user_id is not None
            or session.scalar(
                select(UserRoleAssignment.id)
                .where(UserRoleAssignment.scope_type == "GLOBAL")
                .limit(1)
            )
            is not None
        ):
            raise ValueError(
                "Initial owner provisioning has already occurred or GLOBAL assignments exist."
            )
        normalized_email = email.strip().lower()
        if "@" not in normalized_email or len(password) < 12 or not full_name.strip():
            raise ValueError(
                "A valid owner identity and a password of at least 12 characters are required."
            )
        if session.scalar(select(User.id).where(User.email == normalized_email)) is not None:
            raise ValueError(
                "Owner provisioning creates a new account; existing accounts cannot be promoted."
            )
        role = session.scalar(select(Role).where(Role.code == SUPERADMIN_ROLE_CODE))
        if role is not None:
            raise ValueError(
                "The reserved Superadministrator role already exists; reconcile provisioning state."
            )
        permissions = list(
            session.scalars(
                select(Permission).where(
                    Permission.code.in_(INITIAL_SUPERADMIN_PERMISSION_CODES),
                    Permission.is_active.is_(True),
                )
            )
        )
        if {permission.code for permission in permissions} != set(
            INITIAL_SUPERADMIN_PERMISSION_CODES
        ):
            raise ValueError(
                "The complete approved capability catalog must exist before owner provisioning."
            )
        user = User(
            email=normalized_email,
            full_name=full_name.strip(),
            password_hash=PasswordHasher().hash_password(password),
            allowed_surfaces=["BACKOFFICE"],
            default_surface="BACKOFFICE",
            is_active=True,
            is_locked=False,
        )
        role = Role(
            code=SUPERADMIN_ROLE_CODE,
            name="Superadministrator",
            is_system=True,
            is_active=True,
            surfaces=["POS", "BACKOFFICE"],
            description="Explicit privileged authority with individually assigned capabilities.",
        )
        session.add_all([user, role])
        session.flush()
        for permission in permissions:
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        session.add(
            UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                is_active=True,
                scope_type="GLOBAL",
                assigned_by_user_id=user.id,
            )
        )
        state.initial_owner_user_id = user.id
        state.owner_provisioned_at = datetime.now(tz=UTC)
        recovery_material = self._new_recovery_material(session, authorized_host)
        _record(
            session,
            actor_id=user.id,
            action="identity.owner.provisioned",
            resource_id=str(user.id),
            metadata={
                "designation": designation,
                "role_code": SUPERADMIN_ROLE_CODE,
                "scope_type": "GLOBAL",
                "capabilities": list(INITIAL_SUPERADMIN_PERMISSION_CODES),
            },
        )
        session.flush()
        return OwnerProvisioningResult(user.id, recovery_material)

    def recover_second_superadmin(
        self,
        session: Session,
        *,
        target_user_id: UUID,
        recovery_material: str,
        current_host: str,
    ) -> OwnerProvisioningResult:
        lock_privileged_lifecycle(session)
        current_superadmins = active_superadmin_ids(session)
        if len(current_superadmins) != 1 or target_user_id in current_superadmins:
            raise ValueError("Recovery can only promote a different second Superadministrator.")
        if len(recovery_material) < 48:
            raise ValueError("Independent recovery material is invalid.")
        digest = hashlib.sha256(recovery_material.encode()).hexdigest()
        credential = session.scalars(
            select(IdentityRecoveryCredential)
            .where(IdentityRecoveryCredential.token_sha256 == digest)
            .with_for_update()
        ).one_or_none()
        if (
            credential is None
            or credential.consumed_at is not None
            or not hmac.compare_digest(credential.authorized_host, current_host.strip().lower())
        ):
            raise ValueError(
                "Recovery material is invalid, consumed, or unauthorized on this host."
            )
        target = session.get(User, target_user_id, populate_existing=True)
        if (
            target is None
            or not target.is_active
            or target.is_locked
            or "BACKOFFICE" not in target.allowed_surfaces
        ):
            raise ValueError("Recovery requires an explicitly selected active Backoffice account.")
        role = session.scalars(
            select(Role).where(Role.code == SUPERADMIN_ROLE_CODE, Role.is_active.is_(True))
        ).one()
        assignment = session.scalar(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == target.id, UserRoleAssignment.role_id == role.id
            )
        )
        if assignment is None:
            assignment = UserRoleAssignment(
                user_id=target.id,
                role_id=role.id,
                scope_type="GLOBAL",
                is_active=True,
                assigned_by_user_id=None,
            )
            session.add(assignment)
            session.flush()
        else:
            assignment.scope_type = "GLOBAL"
            assignment.is_active = True
            session.execute(
                delete(UserRoleAssignmentBranchScope).where(
                    UserRoleAssignmentBranchScope.assignment_id == assignment.id
                )
            )
        credential.consumed_at = datetime.now(tz=UTC)
        replacement_material = self._new_recovery_material(session, credential.authorized_host)
        _record(
            session,
            actor_id=None,
            action="identity.superadmin.recovered",
            resource_id=str(target.id),
            metadata={
                "target_user_id": str(target.id),
                "credential_id": str(credential.id),
                "scope_type": "GLOBAL",
                "source": "AUTHORIZED_LOCAL_CLI",
            },
        )
        session.flush()
        if len(active_superadmin_ids(session)) != 2:
            raise ValueError("Recovery must result in exactly two active Superadministrators.")
        return OwnerProvisioningResult(target.id, replacement_material)

    @staticmethod
    def _new_recovery_material(session: Session, authorized_host: str) -> str:
        material = secrets.token_urlsafe(48)
        session.add(
            IdentityRecoveryCredential(
                token_sha256=hashlib.sha256(material.encode()).hexdigest(),
                authorized_host=authorized_host.strip().lower(),
            )
        )
        return material
