from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.admin_role_schemas import (
    AdminPermissionGroupView,
    AdminPermissionsResponse,
    AdminPermissionView,
    AdminRoleAccessSurfacesView,
    AdminRoleAssignedUserView,
    AdminRoleAuditEventView,
    AdminRoleAvailableActionsView,
    AdminRoleBackendContractView,
    AdminRoleCreateRequest,
    AdminRoleDetailView,
    AdminRoleFilterOptionsView,
    AdminRoleFilterOptionView,
    AdminRoleListItemView,
    AdminRoleMetricsView,
    AdminRoleOverviewView,
    AdminRoleReadinessState,
    AdminRoleScopeView,
    AdminRolesListResponse,
    AdminRoleStatus,
    AdminRoleStatusChangeRequest,
    AdminRoleUpdateRequest,
    AdminRoleWarningView,
)
from zeromerma_api.modules.identity.application.admin_schemas import AdminAssignmentScopeRequest
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    require_capability,
)
from zeromerma_api.modules.identity.application.permissions import (
    PERMISSION_CODES,
    SENSITIVE_PERMISSION_CODES,
    SUPERADMIN_ROLE_CODE,
)
from zeromerma_api.modules.identity.application.privileged_access import (
    assignment_branch_ids,
    authorize_privileged_change,
    can_access_user,
    ensure_superadmin_remains,
    lock_privileged_lifecycle,
    refresh_actor,
    set_role_assignment,
    user_scope_predicate,
)
from zeromerma_api.modules.identity.application.schemas import (
    AuthenticatedUser,
    IdentitySurface,
    ScopeType,
)
from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_ALLOWED_SURFACES,
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)
from zeromerma_api.modules.identity.domain.exceptions import (
    RoleConflictError,
    RoleNotFoundError,
    RoleValidationError,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter

_SCOPE_TYPE_ADAPTER: TypeAdapter[ScopeType] = TypeAdapter(ScopeType)
_LIST_IDENTITY_SURFACE_ADAPTER: TypeAdapter[list[IdentitySurface]] = TypeAdapter(
    list[IdentitySurface]
)
AUDIT_ACTION_ADMIN_ROLE_CREATED = "admin.role.created"
AUDIT_ACTION_ADMIN_ROLE_UPDATED = "admin.role.updated"
AUDIT_ACTION_ADMIN_ROLE_STATUS_CHANGED = "admin.role.status_changed"
AUDIT_ACTION_ADMIN_ROLE_USER_ASSIGNED = "admin.role.user_assigned"
AUDIT_ACTION_ADMIN_ROLE_USER_REMOVED = "admin.role.user_removed"

OUTBOX_EVENT_ADMIN_ROLE_CREATED_V1 = "admin.role.created.v1"
OUTBOX_EVENT_ADMIN_ROLE_UPDATED_V1 = "admin.role.updated.v1"
OUTBOX_EVENT_ADMIN_ROLE_STATUS_CHANGED_V1 = "admin.role.status_changed.v1"
OUTBOX_EVENT_ADMIN_ROLE_USER_ASSIGNMENT_CHANGED_V1 = "admin.role.user_assignment_changed.v1"

ROLE_RESOURCE_TYPE = "role"


@dataclass(frozen=True)
class _RoleContext:
    role: Role
    permissions: list[Permission]
    assigned_users: list[tuple[UserRoleAssignment, User]]


class AdminRoleService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_roles(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        search: str | None,
        status_filter: str | None,
        app_surface: str | None,
        high_privilege: str | None,
        has_users: str | None,
        permission_module: str | None,
        warning_state: str | None,
        system_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminRolesListResponse:
        current_user = refresh_actor(session, current_user)
        require_capability(current_user, "roles.view")
        contexts = [
            self._get_context(session, role.id, current_user=current_user)
            for role in session.execute(select(Role).order_by(Role.name.asc())).scalars().all()
        ]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            lowered = normalized_search.lower()
            contexts = [
                context
                for context in contexts
                if lowered in context.role.name.lower()
                or lowered in context.role.code.lower()
                or (context.role.description and lowered in context.role.description.lower())
            ]

        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            contexts = [
                context for context in contexts if _role_status(context.role) == normalized_status
            ]

        normalized_surface = _normalize_optional(app_surface)
        if normalized_surface and normalized_surface != "all":
            contexts = [
                context
                for context in contexts
                if self._matches_surface(context.role, normalized_surface)
            ]

        normalized_high_privilege = _normalize_optional(high_privilege)
        if normalized_high_privilege == "yes":
            contexts = [context for context in contexts if self._is_high_privilege(context)]
        elif normalized_high_privilege == "no":
            contexts = [context for context in contexts if not self._is_high_privilege(context)]

        normalized_has_users = _normalize_optional(has_users)
        if normalized_has_users == "yes":
            contexts = [context for context in contexts if context.assigned_users]
        elif normalized_has_users == "no":
            contexts = [context for context in contexts if not context.assigned_users]

        normalized_module = _normalize_optional(permission_module)
        if normalized_module and normalized_module != "all":
            contexts = [
                context
                for context in contexts
                if any(permission.module == normalized_module for permission in context.permissions)
            ]

        normalized_system = _normalize_optional(system_state)
        if normalized_system == "system":
            contexts = [context for context in contexts if context.role.is_system]
        elif normalized_system == "custom":
            contexts = [context for context in contexts if not context.role.is_system]

        normalized_warning = _normalize_optional(warning_state)
        if normalized_warning == "with_warnings":
            contexts = [context for context in contexts if self._build_warnings(context)]
        elif normalized_warning == "without_warnings":
            contexts = [context for context in contexts if not self._build_warnings(context)]

        items = [self._to_list_item(context) for context in contexts]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminRolesListResponse(
            backend_contract=AdminRoleBackendContractView(),
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(contexts),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def list_permissions(
        self, session: Session, *, current_user: AuthenticatedUser
    ) -> AdminPermissionsResponse:
        current_user = refresh_actor(session, current_user)
        require_capability(current_user, "roles.view")
        permissions = self._fetch_all_permissions(session)
        return AdminPermissionsResponse(
            groups=self._permission_groups(permissions, enabled_codes=set()),
            sensitive_permission_codes=[
                permission.code for permission in permissions if permission.is_sensitive
            ],
        )

    def get_role_detail(
        self,
        session: Session,
        *,
        role_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> AdminRoleDetailView:
        current_user = refresh_actor(session, current_user)
        require_capability(current_user, "roles.view")
        return self._to_detail(
            session,
            self._get_context(session, role_id, current_user=current_user),
            current_user=current_user,
        )

    def create_role(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminRoleCreateRequest,
        request_id: str | None,
    ) -> AdminRoleDetailView:
        lock_privileged_lifecycle(session)
        current_user = refresh_actor(session, current_user)
        require_branches(current_user, "roles.manage", [], global_only=True)
        if command.code == SUPERADMIN_ROLE_CODE:
            raise HTTPException(
                status_code=403,
                detail="The Superadministrator role is reserved for owner provisioning.",
            )
        self._ensure_unique_code(session, command.code)
        surfaces = self._normalize_surfaces(command.surfaces)
        permissions = self._get_permissions_by_codes(session, command.permission_codes)
        self._ensure_surface_permission_compatibility(surfaces, permissions)
        if (
            self._contains_sensitive_permission(permissions)
            and not command.confirmed_high_risk_change
        ):
            raise RoleConflictError("High-risk permissions require explicit confirmation.")

        role = Role(
            code=command.code,
            name=command.name.strip(),
            description=command.description,
            surfaces=surfaces,
            is_active=command.is_active,
            is_system=False,
        )
        try:
            session.add(role)
            session.flush()
            self._replace_permissions(session, role=role, permissions=permissions)
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                role=role,
                action=AUDIT_ACTION_ADMIN_ROLE_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_ROLE_CREATED_V1,
                request_id=request_id,
                metadata=self._role_metadata(role, permissions),
            )
            ensure_superadmin_remains(session)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise RoleValidationError("Role code must be unique.") from error

        return self._to_detail(
            session, self._get_context(session, role.id), current_user=current_user
        )

    def update_role(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        role_id: uuid.UUID,
        command: AdminRoleUpdateRequest,
        request_id: str | None,
        approval_id: uuid.UUID | None = None,
    ) -> AdminRoleDetailView:
        current_user = authorize_privileged_change(
            session,
            current_user=current_user,
            operation="ROLE_UPDATE",
            target_role_id=role_id,
            payload=command.model_dump(mode="json", exclude_unset=True),
            approval_id=approval_id,
            request_id=request_id,
        )
        require_branches(current_user, "roles.manage", [], global_only=True)
        context = self._get_context(session, role_id)
        role = context.role
        if role.is_system and role.code != SUPERADMIN_ROLE_CODE:
            raise RoleConflictError("System roles are read-only.")

        own_assignment = session.scalar(
            select(UserRoleAssignment.id).where(
                UserRoleAssignment.user_id == current_user.id, UserRoleAssignment.role_id == role_id
            )
        )
        if own_assignment is not None and (
            (
                command.permission_codes is not None
                and not set(command.permission_codes) <= {item.code for item in context.permissions}
            )
            or (command.surfaces is not None and not set(command.surfaces) <= set(role.surfaces))
            or (command.is_active is True and not role.is_active)
        ):
            raise HTTPException(
                status_code=403, detail="Self-elevation through a role change is forbidden."
            )
        previous_metadata = self._role_metadata(role, context.permissions)
        surfaces = self._normalize_surfaces(role.surfaces)
        permissions = context.permissions
        previous_permission_codes = {permission.code for permission in permissions}

        if "name" in command.model_fields_set and command.name is not None:
            role.name = command.name.strip()
        if "description" in command.model_fields_set:
            role.description = command.description
        if command.surfaces is not None:
            surfaces = self._normalize_surfaces(command.surfaces)
        if command.permission_codes is not None:
            permissions = self._get_permissions_by_codes(session, command.permission_codes)
            self._ensure_surface_permission_compatibility(surfaces, permissions)

        new_permission_codes = {permission.code for permission in permissions}
        added_sensitive = bool(
            (new_permission_codes - previous_permission_codes) & set(SENSITIVE_PERMISSION_CODES)
        )
        removing_manage_roles = (
            "roles.manage" in previous_permission_codes
            and "roles.manage" not in new_permission_codes
        )
        assigned_active_users = self._assigned_active_user_count(context)
        if (
            added_sensitive
            or (command.surfaces is not None and assigned_active_users > 0)
            or (command.is_active is False and assigned_active_users > 0)
        ) and not command.confirmed_high_risk_change:
            raise RoleConflictError("Sensitive role changes require explicit confirmation.")
        if removing_manage_roles and self._is_last_active_role_with_permission(
            session,
            role,
            "roles.manage",
        ):
            raise RoleConflictError("Cannot remove roles.manage from the last active admin role.")

        role.surfaces = surfaces
        if command.is_active is not None:
            if command.is_active is False and self._is_last_active_role_with_permission(
                session,
                role,
                "roles.manage",
            ):
                raise RoleConflictError("Cannot deactivate the last role with role management.")
            role.is_active = command.is_active

        session.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        ).scalars().all()
        self._replace_permissions(session, role=role, permissions=permissions)
        session.flush()
        self._record_change(
            session,
            current_user=current_user,
            role=role,
            action=AUDIT_ACTION_ADMIN_ROLE_UPDATED,
            event_name=OUTBOX_EVENT_ADMIN_ROLE_UPDATED_V1,
            request_id=request_id,
            metadata={
                "previous": previous_metadata,
                "current": self._role_metadata(role, permissions),
            },
        )
        ensure_superadmin_remains(session)
        session.commit()
        return self._to_detail(
            session, self._get_context(session, role.id), current_user=current_user
        )

    def change_status(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        role_id: uuid.UUID,
        command: AdminRoleStatusChangeRequest,
        request_id: str | None,
        approval_id: uuid.UUID | None = None,
    ) -> AdminRoleDetailView:
        current_user = authorize_privileged_change(
            session,
            current_user=current_user,
            operation="ROLE_STATUS",
            target_role_id=role_id,
            payload=command.model_dump(mode="json", exclude_unset=True),
            approval_id=approval_id,
            request_id=request_id,
        )
        require_branches(current_user, "roles.manage", [], global_only=True)
        context = self._get_context(session, role_id)
        role = context.role
        if role.is_system and role.code != SUPERADMIN_ROLE_CODE:
            raise RoleConflictError("System roles are read-only.")
        if (
            not command.is_active
            and self._assigned_active_user_count(context) > 0
            and not command.confirmed_high_risk_change
        ):
            raise RoleConflictError("Deactivating an assigned role requires confirmation.")
        if not command.is_active and self._is_last_active_role_with_permission(
            session,
            role,
            "roles.manage",
        ):
            raise RoleConflictError("Cannot deactivate the last role with role management.")

        own_assignment = session.scalar(
            select(UserRoleAssignment.id).where(
                UserRoleAssignment.user_id == current_user.id, UserRoleAssignment.role_id == role_id
            )
        )
        if own_assignment is not None and command.is_active and not role.is_active:
            raise HTTPException(
                status_code=403, detail="Self-elevation through role activation is forbidden."
            )
        previous_status = _role_status(role)
        role.is_active = command.is_active
        session.flush()
        self._record_change(
            session,
            current_user=current_user,
            role=role,
            action=AUDIT_ACTION_ADMIN_ROLE_STATUS_CHANGED,
            event_name=OUTBOX_EVENT_ADMIN_ROLE_STATUS_CHANGED_V1,
            request_id=request_id,
            metadata={
                **self._role_metadata(role, context.permissions),
                "previous_status": previous_status,
                "new_status": _role_status(role),
            },
        )
        ensure_superadmin_remains(session)
        session.commit()
        return self._to_detail(
            session, self._get_context(session, role.id), current_user=current_user
        )

    def assign_role_to_user(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        role_id: uuid.UUID,
        user_id: uuid.UUID,
        command: AdminAssignmentScopeRequest,
        request_id: str | None,
        approval_id: uuid.UUID | None = None,
    ) -> AdminRoleDetailView:
        current_user = authorize_privileged_change(
            session,
            current_user=current_user,
            operation="ROLE_ASSIGNMENT",
            target_user_id=user_id,
            target_role_id=role_id,
            payload=command.model_dump(mode="json", exclude_unset=True),
            approval_id=approval_id,
            request_id=request_id,
        )
        role = self._get_role(session, role_id)
        if not role.is_active:
            raise RoleValidationError("Inactive roles cannot be assigned.")
        user = self._get_user(session, user_id)
        assignment_metadata = set_role_assignment(
            session, actor=current_user, user_id=user_id, role_id=role_id, scope=command
        )
        self._record_assignment_change(
            session,
            current_user=current_user,
            role=role,
            user=user,
            action=AUDIT_ACTION_ADMIN_ROLE_USER_ASSIGNED,
            request_id=request_id,
            assignment_metadata=assignment_metadata,
        )
        ensure_superadmin_remains(session)
        session.commit()
        return self._to_detail(
            session, self._get_context(session, role.id), current_user=current_user
        )

    def remove_role_from_user(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        role_id: uuid.UUID,
        user_id: uuid.UUID,
        request_id: str | None,
        approval_id: uuid.UUID | None = None,
    ) -> AdminRoleDetailView:
        current_user = authorize_privileged_change(
            session,
            current_user=current_user,
            operation="ROLE_REMOVAL",
            target_user_id=user_id,
            target_role_id=role_id,
            payload={},
            approval_id=approval_id,
            request_id=request_id,
        )
        role = self._get_role(session, role_id)
        user = self._get_user(session, user_id)
        assignment_metadata = set_role_assignment(
            session, actor=current_user, user_id=user_id, role_id=role_id, scope=None
        )
        self._record_assignment_change(
            session,
            current_user=current_user,
            role=role,
            user=user,
            action=AUDIT_ACTION_ADMIN_ROLE_USER_REMOVED,
            request_id=request_id,
            assignment_metadata=assignment_metadata,
        )
        ensure_superadmin_remains(session)
        session.commit()
        return self._to_detail(
            session, self._get_context(session, role.id), current_user=current_user
        )

    def _to_list_item(self, context: _RoleContext) -> AdminRoleListItemView:
        warnings = self._build_warnings(context)
        return AdminRoleListItemView(
            id=context.role.id,
            code=context.role.code,
            name=context.role.name,
            description=context.role.description,
            status=_role_status(context.role),
            surfaces=_LIST_IDENTITY_SURFACE_ADAPTER.validate_python(
                self._normalize_surfaces(context.role.surfaces)
            ),
            permission_count=len(context.permissions),
            assigned_user_count=len(context.assigned_users),
            is_system=context.role.is_system,
            is_high_privilege=self._is_high_privilege(context),
            scope_summary=self._scope_summary(),
            warning_state=self._readiness(context.role, warnings),
            warnings=warnings,
            updated_at=context.role.updated_at,
        )

    def _to_detail(
        self, session: Session, context: _RoleContext, *, current_user: AuthenticatedUser
    ) -> AdminRoleDetailView:
        warnings = self._build_warnings(context)
        enabled_codes = {permission.code for permission in context.permissions}
        sensitive_permissions = [
            self._permission_view(permission, is_enabled=True)
            for permission in context.permissions
            if permission.is_sensitive
        ]
        grants = {grant.capability: grant for grant in current_user.effective_grants}
        role_grant = grants.get("roles.manage")
        can_edit = (
            role_grant is not None
            and role_grant.scope_type == "GLOBAL"
            and (not context.role.is_system or context.role.code == SUPERADMIN_ROLE_CODE)
        )
        can_assign = "role_assignments.manage" in grants
        visible_users = [
            (assignment, user)
            for assignment, user in context.assigned_users
            if can_access_user(session, current_user, "users.view", user.id)
        ]
        return AdminRoleDetailView(
            overview=AdminRoleOverviewView(
                id=context.role.id,
                code=context.role.code,
                name=context.role.name,
                description=context.role.description,
                status=_role_status(context.role),
                surfaces=_LIST_IDENTITY_SURFACE_ADAPTER.validate_python(
                    self._normalize_surfaces(context.role.surfaces)
                ),
                is_system=context.role.is_system,
                is_high_privilege=self._is_high_privilege(context),
                created_at=context.role.created_at,
                updated_at=context.role.updated_at,
                warning_state=self._readiness(context.role, warnings),
            ),
            access_surfaces=AdminRoleAccessSurfacesView(
                surfaces=_LIST_IDENTITY_SURFACE_ADAPTER.validate_python(
                    self._normalize_surfaces(context.role.surfaces)
                ),
                pos_enabled=IDENTITY_SURFACE_POS in self._normalize_surfaces(context.role.surfaces),
                backoffice_enabled=IDENTITY_SURFACE_BACKOFFICE
                in self._normalize_surfaces(context.role.surfaces),
                grants_both_surfaces=(
                    IDENTITY_SURFACE_POS in self._normalize_surfaces(context.role.surfaces)
                    and IDENTITY_SURFACE_BACKOFFICE
                    in self._normalize_surfaces(context.role.surfaces)
                ),
                note=(
                    "El rol declara capacidad de superficie; la superficie inicial del usuario "
                    "se administra en Usuarios."
                ),
            ),
            permission_matrix=self._permission_groups(
                self._fetch_all_permissions(session),
                enabled_codes=enabled_codes,
            ),
            sensitive_permissions=sensitive_permissions,
            scopes=AdminRoleScopeView(scope_summary=self._scope_summary()),
            assigned_users=self._assigned_user_views(session, visible_users),
            audit_history=self._fetch_audit_history(session, context.role.id)
            if grants.get("audit.view") is not None and grants["audit.view"].scope_type == "GLOBAL"
            else [],
            available_actions=AdminRoleAvailableActionsView(
                can_edit=can_edit,
                can_activate=can_edit and not context.role.is_active,
                can_deactivate=can_edit and context.role.is_active,
                can_assign_users=can_assign and context.role.is_active,
                can_remove_users=can_assign,
            ),
            warnings=warnings,
        )

    def _build_metrics(self, contexts: list[_RoleContext]) -> AdminRoleMetricsView:
        return AdminRoleMetricsView(
            total_roles=len(contexts),
            active_roles=sum(1 for context in contexts if context.role.is_active),
            inactive_roles=sum(1 for context in contexts if not context.role.is_active),
            with_users=sum(1 for context in contexts if context.assigned_users),
            without_users=sum(1 for context in contexts if not context.assigned_users),
            high_privilege=sum(1 for context in contexts if self._is_high_privilege(context)),
            pos_roles=sum(
                1
                for context in contexts
                if IDENTITY_SURFACE_POS in self._normalize_surfaces(context.role.surfaces)
            ),
            backoffice_roles=sum(
                1
                for context in contexts
                if IDENTITY_SURFACE_BACKOFFICE in self._normalize_surfaces(context.role.surfaces)
            ),
            with_warnings=sum(1 for context in contexts if self._build_warnings(context)),
        )

    def _build_filter_options(self, session: Session) -> AdminRoleFilterOptionsView:
        modules = {
            permission.module: permission.module_label
            for permission in self._fetch_all_permissions(session)
        }
        return AdminRoleFilterOptionsView(
            statuses=[
                AdminRoleFilterOptionView(id="active", label="Activos"),
                AdminRoleFilterOptionView(id="inactive", label="Inactivos"),
            ],
            app_surfaces=[
                AdminRoleFilterOptionView(id="POS", label="POS"),
                AdminRoleFilterOptionView(id="BACKOFFICE", label="Backoffice"),
                AdminRoleFilterOptionView(id="BOTH", label="Ambos"),
            ],
            high_privilege=[
                AdminRoleFilterOptionView(id="yes", label="Alto privilegio"),
                AdminRoleFilterOptionView(id="no", label="Sin alto privilegio"),
            ],
            has_users=[
                AdminRoleFilterOptionView(id="yes", label="Con usuarios"),
                AdminRoleFilterOptionView(id="no", label="Sin usuarios"),
            ],
            permission_modules=[
                AdminRoleFilterOptionView(id=module, label=label)
                for module, label in sorted(modules.items(), key=lambda item: item[1])
            ],
            warning_states=[
                AdminRoleFilterOptionView(id="with_warnings", label="Con advertencias"),
                AdminRoleFilterOptionView(id="without_warnings", label="Sin advertencias"),
            ],
            system_states=[
                AdminRoleFilterOptionView(id="system", label="Sistema"),
                AdminRoleFilterOptionView(id="custom", label="Personalizados"),
            ],
        )

    def _build_warnings(self, context: _RoleContext) -> list[AdminRoleWarningView]:
        warnings: list[AdminRoleWarningView] = []
        surfaces = self._normalize_surfaces(context.role.surfaces)
        if not context.role.is_active:
            warnings.append(
                AdminRoleWarningView(
                    code="inactive_role",
                    message="El rol esta inactivo y no debe asignarse a nuevos usuarios.",
                    severity="info",
                )
            )
        if not surfaces:
            warnings.append(
                AdminRoleWarningView(
                    code="missing_surface",
                    message="El rol no declara acceso a POS ni Backoffice.",
                    severity="critical",
                )
            )
        if not context.permissions:
            warnings.append(
                AdminRoleWarningView(
                    code="missing_permissions",
                    message="El rol no tiene permisos asignados.",
                    severity="warning",
                )
            )
        if context.role.is_active and not context.assigned_users and not context.role.is_system:
            warnings.append(
                AdminRoleWarningView(
                    code="role_without_users",
                    message="El rol esta activo pero no tiene usuarios asignados.",
                    severity="info",
                )
            )
        if self._is_high_privilege(context):
            warnings.append(
                AdminRoleWarningView(
                    code="high_privilege_role",
                    message="El rol incluye permisos sensibles que requieren revision cuidadosa.",
                    severity="warning",
                )
            )
        return warnings

    def _readiness(
        self,
        role: Role,
        warnings: list[AdminRoleWarningView],
    ) -> AdminRoleReadinessState:
        if not role.is_active or any(warning.severity == "critical" for warning in warnings):
            return "blocked"
        if warnings:
            return "warning"
        return "ready"

    def _permission_groups(
        self,
        permissions: list[Permission],
        *,
        enabled_codes: set[str],
    ) -> list[AdminPermissionGroupView]:
        grouped: dict[str, list[Permission]] = {}
        labels: dict[str, str] = {}
        for permission in permissions:
            grouped.setdefault(permission.module, []).append(permission)
            labels[permission.module] = permission.module_label
        return [
            AdminPermissionGroupView(
                module=module,
                label=labels[module],
                permissions=[
                    self._permission_view(
                        permission,
                        is_enabled=permission.code in enabled_codes,
                    )
                    for permission in sorted(items, key=lambda item: item.code)
                ],
            )
            for module, items in sorted(grouped.items(), key=lambda item: labels[item[0]])
        ]

    def _permission_view(self, permission: Permission, *, is_enabled: bool) -> AdminPermissionView:
        return AdminPermissionView(
            id=permission.id,
            code=permission.code,
            label=permission.label,
            description=permission.description,
            module=permission.module,
            module_label=permission.module_label,
            action=permission.action,
            surfaces=_LIST_IDENTITY_SURFACE_ADAPTER.validate_python(
                self._normalize_surfaces(permission.surfaces)
            ),
            is_sensitive=permission.is_sensitive,
            is_enabled=is_enabled,
        )

    def _assigned_user_views(
        self,
        session: Session,
        assigned_users: list[tuple[UserRoleAssignment, User]],
    ) -> list[AdminRoleAssignedUserView]:
        views: list[AdminRoleAssignedUserView] = []
        for assignment, user in assigned_users:
            branch_names = (
                session.execute(
                    select(Branch.name)
                    .join(UserBranchAssignment, UserBranchAssignment.branch_id == Branch.id)
                    .where(
                        UserBranchAssignment.user_id == user.id,
                        UserBranchAssignment.is_active.is_(True),
                    )
                    .order_by(Branch.name.asc())
                )
                .scalars()
                .all()
            )
            views.append(
                AdminRoleAssignedUserView(
                    user_id=user.id,
                    full_name=user.full_name,
                    email=user.email,
                    status=_user_status(user),
                    branch_summary=", ".join(branch_names) if branch_names else "Sin sucursal",
                    surfaces=_LIST_IDENTITY_SURFACE_ADAPTER.validate_python(
                        self._normalize_surfaces(user.allowed_surfaces)
                    ),
                    assigned_at=assignment.created_at,
                    scope_type=_SCOPE_TYPE_ADAPTER.validate_python(assignment.scope_type),
                    branch_ids=assignment_branch_ids(session, assignment.id),
                )
            )
        return views

    def _fetch_audit_history(
        self,
        session: Session,
        role_id: uuid.UUID,
    ) -> list[AdminRoleAuditEventView]:
        records = (
            session.execute(
                select(AuditLog)
                .where(
                    AuditLog.resource_type == ROLE_RESOURCE_TYPE,
                    AuditLog.resource_id == str(role_id),
                )
                .order_by(AuditLog.occurred_at.desc())
                .limit(20)
            )
            .scalars()
            .all()
        )
        return [
            AdminRoleAuditEventView(
                id=record.id,
                occurred_at=record.occurred_at,
                actor_id=record.actor_id,
                action=record.action,
                metadata=record.metadata_,
            )
            for record in records
        ]

    def _get_context(
        self, session: Session, role_id: uuid.UUID, *, current_user: AuthenticatedUser | None = None
    ) -> _RoleContext:
        role = self._get_role(session, role_id)
        return _RoleContext(
            role=role,
            permissions=self._fetch_role_permissions(session, role.id),
            assigned_users=self._fetch_assigned_users(session, role.id, current_user=current_user),
        )

    def _get_role(self, session: Session, role_id: uuid.UUID) -> Role:
        role = session.get(Role, role_id)
        if role is None:
            raise RoleNotFoundError("Role was not found.")
        return role

    def _get_user(self, session: Session, user_id: uuid.UUID) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise RoleValidationError("User was not found.")
        return user

    def _fetch_role_permissions(self, session: Session, role_id: uuid.UUID) -> list[Permission]:
        return list(
            session.execute(
                select(Permission)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role_id)
                .order_by(Permission.module.asc(), Permission.code.asc())
            )
            .scalars()
            .all()
        )

    def _fetch_all_permissions(self, session: Session) -> list[Permission]:
        return list(
            session.execute(
                select(Permission)
                .where(Permission.is_active.is_(True))
                .order_by(Permission.module.asc(), Permission.code.asc())
            )
            .scalars()
            .all()
        )

    def _fetch_assigned_users(
        self,
        session: Session,
        role_id: uuid.UUID,
        *,
        current_user: AuthenticatedUser | None = None,
    ) -> list[tuple[UserRoleAssignment, User]]:
        return list(
            session.execute(
                select(UserRoleAssignment, User)
                .join(User, User.id == UserRoleAssignment.user_id)
                .where(
                    user_scope_predicate(current_user, "roles.view")
                    if current_user is not None
                    else true()
                )
                .where(
                    UserRoleAssignment.role_id == role_id,
                    UserRoleAssignment.is_active.is_(True),
                )
                .order_by(User.full_name.asc(), User.email.asc())
            )
            .tuples()
            .all()
        )

    def _get_permissions_by_codes(
        self,
        session: Session,
        codes: list[str],
    ) -> list[Permission]:
        normalized_codes = list(
            dict.fromkeys(code.strip().lower() for code in codes if code.strip())
        )
        if set(normalized_codes) - set(PERMISSION_CODES):
            raise RoleValidationError("Only canonical active capability codes can be assigned.")
        if not normalized_codes:
            raise RoleValidationError("At least one permission is required.")
        permissions = (
            session.execute(
                select(Permission).where(
                    Permission.code.in_(normalized_codes), Permission.is_active.is_(True)
                )
            )
            .scalars()
            .all()
        )
        by_code = {permission.code: permission for permission in permissions}
        missing = [code for code in normalized_codes if code not in by_code]
        if missing:
            raise RoleValidationError(f"Invalid permission code: {missing[0]}.")
        return [by_code[code] for code in normalized_codes]

    def _replace_permissions(
        self,
        session: Session,
        *,
        role: Role,
        permissions: list[Permission],
    ) -> None:
        existing = (
            session.execute(select(RolePermission).where(RolePermission.role_id == role.id))
            .scalars()
            .all()
        )
        for row in existing:
            session.delete(row)
        session.flush()
        for permission in permissions:
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    def _ensure_unique_code(
        self,
        session: Session,
        code: str,
        *,
        exclude_role_id: uuid.UUID | None = None,
    ) -> None:
        statement = select(Role.id).where(Role.code == code)
        if exclude_role_id is not None:
            statement = statement.where(Role.id != exclude_role_id)
        if session.execute(statement).scalar_one_or_none() is not None:
            raise RoleValidationError("Role code must be unique.")

    def _ensure_surface_permission_compatibility(
        self,
        surfaces: list[str],
        permissions: list[Permission],
    ) -> None:
        surface_set = set(surfaces)
        for permission in permissions:
            if not set(self._normalize_surfaces(permission.surfaces)) & surface_set:
                raise RoleValidationError(
                    f"Permission {permission.code} is not compatible with selected surfaces."
                )

    def _contains_sensitive_permission(self, permissions: list[Permission]) -> bool:
        return any(permission.is_sensitive for permission in permissions)

    def _is_high_privilege(self, context: _RoleContext) -> bool:
        return any(permission.is_sensitive for permission in context.permissions)

    def _assigned_active_user_count(self, context: _RoleContext) -> int:
        return sum(1 for _assignment, user in context.assigned_users if user.is_active)

    def _active_role_count_for_user(self, session: Session, user_id: uuid.UUID) -> int:
        return session.execute(
            select(func.count())
            .select_from(UserRoleAssignment)
            .join(Role, Role.id == UserRoleAssignment.role_id)
            .where(
                UserRoleAssignment.user_id == user_id,
                UserRoleAssignment.is_active.is_(True),
                Role.is_active.is_(True),
            )
        ).scalar_one()

    def _is_last_active_role_with_permission(
        self,
        session: Session,
        target_role: Role,
        permission_code: str,
    ) -> bool:
        permission_id = session.execute(
            select(Permission.id).where(Permission.code == permission_code)
        ).scalar_one_or_none()
        if permission_id is None or not target_role.is_active:
            return False
        other_role_id = session.execute(
            select(Role.id)
            .join(RolePermission, RolePermission.role_id == Role.id)
            .where(
                Role.id != target_role.id,
                Role.is_active.is_(True),
                RolePermission.permission_id == permission_id,
            )
            .limit(1)
        ).scalar_one_or_none()
        return other_role_id is None

    def _matches_surface(self, role: Role, app_surface: str) -> bool:
        surfaces = self._normalize_surfaces(role.surfaces)
        normalized = app_surface.strip().upper()
        if normalized == "BOTH":
            return IDENTITY_SURFACE_POS in surfaces and IDENTITY_SURFACE_BACKOFFICE in surfaces
        return normalized in surfaces

    def _scope_summary(self) -> str:
        return "Explicit GLOBAL or BRANCH_SET scope on each role assignment."

    def _record_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        role: Role,
        action: str,
        event_name: str,
        request_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=ROLE_RESOURCE_TYPE,
            resource_id=str(role.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=ROLE_RESOURCE_TYPE,
            aggregate_id=str(role.id),
            event_name=event_name,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )

    def _record_assignment_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        role: Role,
        user: User,
        action: str,
        request_id: str | None,
        assignment_metadata: dict[str, Any],
    ) -> None:
        metadata = {
            **assignment_metadata,
            "role_id": str(role.id),
            "role_code": role.code,
            "user_id": str(user.id),
            "user_email": user.email,
        }
        self._record_change(
            session,
            current_user=current_user,
            role=role,
            action=action,
            event_name=OUTBOX_EVENT_ADMIN_ROLE_USER_ASSIGNMENT_CHANGED_V1,
            request_id=request_id,
            metadata=metadata,
        )

    def _role_metadata(self, role: Role, permissions: list[Permission]) -> dict[str, Any]:
        return {
            "id": str(role.id),
            "code": role.code,
            "name": role.name,
            "status": _role_status(role),
            "surfaces": self._normalize_surfaces(role.surfaces),
            "is_system": role.is_system,
            "permission_codes": [permission.code for permission in permissions],
            "sensitive_permission_codes": [
                permission.code for permission in permissions if permission.is_sensitive
            ],
        }

    def _normalize_surfaces(self, values: Sequence[str] | None) -> list[str]:
        if values is None:
            return [IDENTITY_SURFACE_POS]
        normalized: list[str] = []
        for value in values:
            surface = str(value).strip().upper()
            if surface not in IDENTITY_ALLOWED_SURFACES:
                raise RoleValidationError("Unsupported application surface.")
            if surface not in normalized:
                normalized.append(surface)
        if not normalized:
            raise RoleValidationError("At least one application surface is required.")
        return normalized


def _role_status(role: Role) -> AdminRoleStatus:
    return "active" if role.is_active else "inactive"


def _user_status(user: User) -> str:
    if user.is_locked:
        return "locked"
    return "active" if user.is_active else "inactive"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
