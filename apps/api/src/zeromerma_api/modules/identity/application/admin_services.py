from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_OPEN
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.application.admin_schemas import (
    AdminUserAccountStatusView,
    AdminUserAppAccessView,
    AdminUserAuditTimelineEventView,
    AdminUserAvailableActionsView,
    AdminUserBranchAssignmentCommand,
    AdminUserBranchAssignmentView,
    AdminUserBranchFilterOptionView,
    AdminUserCreateRequest,
    AdminUserDetailView,
    AdminUserFilterOptionsView,
    AdminUserFilterOptionView,
    AdminUserListItemView,
    AdminUserLockRequest,
    AdminUserMetricsView,
    AdminUserOperationalContextView,
    AdminUserOverviewView,
    AdminUserProfileView,
    AdminUserReadinessState,
    AdminUserRoleAssignmentsView,
    AdminUserRoleAssignmentView,
    AdminUserSecurityActionsView,
    AdminUsersListResponse,
    AdminUserStatus,
    AdminUserStatusChangeRequest,
    AdminUserUpdateRequest,
    AdminUserWarningView,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.security import PasswordHasher
from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_ALLOWED_SURFACES,
    IDENTITY_SURFACE_BACKOFFICE,
    IDENTITY_SURFACE_POS,
)
from zeromerma_api.modules.identity.domain.exceptions import (
    UserConflictError,
    UserNotFoundError,
    UserValidationError,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Role,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.sales.infrastructure.models import Sale

AUDIT_ACTION_ADMIN_USER_CREATED = "admin.user.created"
AUDIT_ACTION_ADMIN_USER_UPDATED = "admin.user.updated"
AUDIT_ACTION_ADMIN_USER_STATUS_CHANGED = "admin.user.status_changed"
AUDIT_ACTION_ADMIN_USER_LOCKED = "admin.user.locked"
AUDIT_ACTION_ADMIN_USER_UNLOCKED = "admin.user.unlocked"
AUDIT_ACTION_ADMIN_USER_BRANCH_ASSIGNMENT_CHANGED = "admin.user.branch_assignment_changed"
AUDIT_ACTION_ADMIN_USER_ROLE_ASSIGNMENT_CHANGED = "admin.user.role_assignment_changed"

OUTBOX_EVENT_ADMIN_USER_CREATED_V1 = "admin.user.created.v1"
OUTBOX_EVENT_ADMIN_USER_UPDATED_V1 = "admin.user.updated.v1"
OUTBOX_EVENT_ADMIN_USER_SECURITY_CHANGED_V1 = "admin.user.security_changed.v1"
OUTBOX_EVENT_ADMIN_USER_BRANCH_ASSIGNMENT_CHANGED_V1 = (
    "admin.user.branch_assignment_changed.v1"
)
OUTBOX_EVENT_ADMIN_USER_ROLE_ASSIGNMENT_CHANGED_V1 = "admin.user.role_assignment_changed.v1"

USER_RESOURCE_TYPE = "user"


@dataclass(frozen=True)
class _UserContext:
    user: User
    assignments: list[tuple[UserBranchAssignment, Branch]]
    roles: list[tuple[UserRoleAssignment, Role]]


class AdminUserService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        password_hasher: PasswordHasher | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._password_hasher = password_hasher or PasswordHasher()

    def list_users(
        self,
        session: Session,
        *,
        search: str | None,
        status_filter: str | None,
        app_access: str | None,
        branch_id: uuid.UUID | None,
        role_id: str | None,
        last_login_state: str | None,
        warning_state: str | None,
        page: int,
        page_size: int,
    ) -> AdminUsersListResponse:
        users = (
            session.execute(select(User).order_by(User.full_name.asc(), User.email.asc()))
            .scalars()
            .all()
        )
        contexts = [
            _UserContext(
                user=user,
                assignments=self._fetch_assignments(session, user.id),
                roles=self._fetch_role_assignments(session, user.id),
            )
            for user in users
        ]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            lowered = normalized_search.lower()
            contexts = [
                context
                for context in contexts
                if lowered in context.user.full_name.lower()
                or lowered in context.user.email.lower()
            ]

        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            contexts = [
                context for context in contexts if _user_status(context.user) == normalized_status
            ]

        normalized_access = _normalize_optional(app_access)
        if normalized_access and normalized_access != "all":
            contexts = [
                context
                for context in contexts
                if self._matches_app_access(context.user, normalized_access)
            ]

        if branch_id is not None:
            contexts = [
                context
                for context in contexts
                if any(
                    assignment.branch_id == branch_id and assignment.is_active
                    for assignment, _branch in context.assignments
                )
            ]

        normalized_last_login = _normalize_optional(last_login_state)
        if normalized_last_login == "with_login":
            contexts = [context for context in contexts if context.user.last_login_at is not None]
        elif normalized_last_login == "without_login":
            contexts = [context for context in contexts if context.user.last_login_at is None]

        normalized_role_id = _normalize_optional(role_id)
        if normalized_role_id not in (None, "all"):
            role_uuid = self._parse_uuid(normalized_role_id, "Role id must be valid.")
            contexts = [
                context
                for context in contexts
                if self._user_has_role(session, context.user.id, role_uuid)
            ]

        normalized_warning_state = _normalize_optional(warning_state)
        if normalized_warning_state == "with_warnings":
            contexts = [context for context in contexts if self._build_warnings(context)]
        elif normalized_warning_state == "without_warnings":
            contexts = [context for context in contexts if not self._build_warnings(context)]

        items = [self._to_list_item(context) for context in contexts]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminUsersListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(contexts),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_user_detail(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        current_user: AuthenticatedUser,
    ) -> AdminUserDetailView:
        context = self._get_context(session, user_id)
        return self._to_detail(session, context, current_user=current_user)

    def create_user(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminUserCreateRequest,
        request_id: str | None,
    ) -> AdminUserDetailView:
        if command.send_invitation:
            raise UserValidationError("Invitation flow is not available in this backend.")
        if command.temporary_password is None:
            raise UserValidationError(
                "Temporary password is required until invitation flow exists."
            )
        email = self._normalize_email(command.email)
        self._ensure_unique_email(session, email)
        surfaces = self._normalize_surfaces(command.allowed_surfaces)
        default_surface = self._resolve_default_surface(surfaces, command.default_surface)
        branch_commands = self._deduplicate_branch_commands(command.branch_assignments)
        roles = self._get_roles_by_ids(session, command.role_ids)
        self._ensure_roles_are_active(roles)
        if IDENTITY_SURFACE_POS in surfaces and not branch_commands:
            raise UserValidationError("POS users require at least one branch assignment.")

        branches = [
            self._get_branch(session, assignment.branch_id)
            for assignment in branch_commands
        ]
        user = User(
            email=email,
            full_name=command.full_name.strip(),
            password_hash=self._password_hasher.hash_password(command.temporary_password),
            allowed_surfaces=surfaces,
            default_surface=default_surface,
            is_active=True,
            phone=command.phone,
            notes=command.notes,
        )

        try:
            session.add(user)
            session.flush()
            self._replace_assignments(
                session,
                user=user,
                branch_commands=branch_commands,
                branches=branches,
            )
            self._replace_role_assignments(
                session,
                current_user=current_user,
                user=user,
                roles=roles,
            )
            session.flush()
            for role in roles:
                self._record_role_assignment_change(
                    session,
                    current_user=current_user,
                    user=user,
                    role=role,
                    request_id=request_id,
                    metadata={"action": "assigned_on_create", **self._user_metadata(user)},
                )
            self._record_change(
                session,
                current_user=current_user,
                user=user,
                action=AUDIT_ACTION_ADMIN_USER_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_USER_CREATED_V1,
                request_id=request_id,
                metadata=self._user_metadata(user),
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise UserValidationError("Email must be unique.") from error

        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def update_user(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        command: AdminUserUpdateRequest,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        previous_metadata = self._user_metadata(user)

        if "email" in command.model_fields_set and command.email is not None:
            email = self._normalize_email(command.email)
            self._ensure_unique_email(session, email, exclude_user_id=user.id)
            user.email = email

        if "full_name" in command.model_fields_set and command.full_name is not None:
            user.full_name = command.full_name.strip()
        if "phone" in command.model_fields_set:
            user.phone = command.phone
        if "notes" in command.model_fields_set:
            user.notes = command.notes

        surfaces = self._normalize_surfaces(user.allowed_surfaces)
        if command.allowed_surfaces is not None:
            surfaces = self._normalize_surfaces(command.allowed_surfaces)
            if (
                user.id == current_user.id
                and IDENTITY_SURFACE_BACKOFFICE not in surfaces
            ):
                raise UserConflictError("You cannot remove your own Backoffice access.")
            if (
                user.is_active
                and not user.is_locked
                and IDENTITY_SURFACE_BACKOFFICE in self._normalize_surfaces(user.allowed_surfaces)
                and IDENTITY_SURFACE_BACKOFFICE not in surfaces
                and self._is_last_backoffice_user(session, user)
            ):
                raise UserConflictError("Cannot remove Backoffice access from the last admin user.")
            user.allowed_surfaces = surfaces

        default_surface = command.default_surface
        if default_surface is not None:
            user.default_surface = self._resolve_default_surface(surfaces, default_surface)
        elif command.allowed_surfaces is not None:
            user.default_surface = self._resolve_default_surface(surfaces, user.default_surface)

        if (
            IDENTITY_SURFACE_POS in surfaces
            and self._active_assignment_count(session, user.id) == 0
        ):
            raise UserValidationError("POS users require at least one branch assignment.")

        try:
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                user=user,
                action=AUDIT_ACTION_ADMIN_USER_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_USER_UPDATED_V1,
                request_id=request_id,
                metadata={
                    "previous": previous_metadata,
                    "current": self._user_metadata(user),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise UserValidationError("Email must be unique.") from error

        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def change_status(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        command: AdminUserStatusChangeRequest,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        if user.id == current_user.id and not command.is_active:
            raise UserConflictError("You cannot deactivate your own account.")
        if (
            user.is_active
            and not command.is_active
            and self._is_last_backoffice_user(session, user)
        ):
            raise UserConflictError("Cannot deactivate the last active Backoffice user.")

        previous_status = _user_status(user)
        user.is_active = command.is_active
        session.flush()
        self._record_change(
            session,
            current_user=current_user,
            user=user,
            action=AUDIT_ACTION_ADMIN_USER_STATUS_CHANGED,
            event_name=OUTBOX_EVENT_ADMIN_USER_SECURITY_CHANGED_V1,
            request_id=request_id,
            metadata={
                **self._user_metadata(user),
                "previous_status": previous_status,
                "new_status": _user_status(user),
            },
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def lock_user(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        command: AdminUserLockRequest,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        if user.id == current_user.id:
            raise UserConflictError("You cannot lock your own account.")
        if not user.is_locked and self._is_last_backoffice_user(session, user):
            raise UserConflictError("Cannot lock the last active Backoffice user.")

        user.is_locked = True
        user.lock_reason = command.reason
        session.flush()
        self._record_change(
            session,
            current_user=current_user,
            user=user,
            action=AUDIT_ACTION_ADMIN_USER_LOCKED,
            event_name=OUTBOX_EVENT_ADMIN_USER_SECURITY_CHANGED_V1,
            request_id=request_id,
            metadata=self._user_metadata(user),
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def unlock_user(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        user.is_locked = False
        user.lock_reason = None
        session.flush()
        self._record_change(
            session,
            current_user=current_user,
            user=user,
            action=AUDIT_ACTION_ADMIN_USER_UNLOCKED,
            event_name=OUTBOX_EVENT_ADMIN_USER_SECURITY_CHANGED_V1,
            request_id=request_id,
            metadata=self._user_metadata(user),
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def add_branch_assignment(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        command: AdminUserBranchAssignmentCommand,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        branch = self._get_branch(session, command.branch_id)
        had_active_assignments = self._active_assignment_count(session, user.id) > 0
        assignment = session.execute(
            select(UserBranchAssignment).where(
                UserBranchAssignment.user_id == user.id,
                UserBranchAssignment.branch_id == branch.id,
            )
        ).scalar_one_or_none()
        if assignment is None:
            assignment = UserBranchAssignment(
                user_id=user.id,
                branch_id=branch.id,
                is_active=True,
                is_default=False,
            )
            session.add(assignment)
        else:
            assignment.is_active = True

        if command.is_default or not had_active_assignments:
            session.flush()
            self._set_default_assignment(session, user=user, branch_id=branch.id)

        session.flush()
        self._record_branch_assignment_change(
            session,
            current_user=current_user,
            user=user,
            branch=branch,
            request_id=request_id,
            metadata={"action": "assigned", **self._user_metadata(user)},
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def deactivate_branch_assignment(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        branch_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        branch = self._get_branch(session, branch_id)
        assignment = self._get_assignment(session, user_id=user.id, branch_id=branch.id)
        if IDENTITY_SURFACE_POS in self._normalize_surfaces(user.allowed_surfaces):
            active_count = self._active_assignment_count(session, user.id)
            if assignment.is_active and active_count <= 1:
                raise UserConflictError("Cannot remove the last branch from a POS user.")

        assignment.is_active = False
        assignment.is_default = False
        self._ensure_default_assignment(session, user=user)
        session.flush()
        self._record_branch_assignment_change(
            session,
            current_user=current_user,
            user=user,
            branch=branch,
            request_id=request_id,
            metadata={"action": "deactivated", **self._user_metadata(user)},
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def set_default_branch_assignment(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        branch_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        branch = self._get_branch(session, branch_id)
        assignment = self._get_assignment(session, user_id=user.id, branch_id=branch.id)
        if not assignment.is_active:
            raise UserValidationError("Default branch assignment must be active.")

        self._set_default_assignment(session, user=user, branch_id=branch.id)
        session.flush()
        self._record_branch_assignment_change(
            session,
            current_user=current_user,
            user=user,
            branch=branch,
            request_id=request_id,
            metadata={"action": "default_changed", **self._user_metadata(user)},
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def assign_role(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        role = self._get_role(session, role_id)
        if not role.is_active:
            raise UserValidationError("Inactive roles cannot be assigned.")
        assignment = session.execute(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.role_id == role.id,
            )
        ).scalar_one_or_none()
        if assignment is None:
            assignment = UserRoleAssignment(
                user_id=user.id,
                role_id=role.id,
                is_active=True,
                assigned_by_user_id=current_user.id,
            )
            session.add(assignment)
        else:
            assignment.is_active = True
            assignment.assigned_by_user_id = current_user.id
        session.flush()
        self._record_role_assignment_change(
            session,
            current_user=current_user,
            user=user,
            role=role,
            request_id=request_id,
            metadata={"action": "assigned", **self._user_metadata(user)},
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def remove_role(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminUserDetailView:
        user = self._get_user(session, user_id)
        role = self._get_role(session, role_id)
        assignment = session.execute(
            select(UserRoleAssignment).where(
                UserRoleAssignment.user_id == user.id,
                UserRoleAssignment.role_id == role.id,
                UserRoleAssignment.is_active.is_(True),
            )
        ).scalar_one_or_none()
        if assignment is None:
            raise UserNotFoundError("Role assignment was not found.")
        if user.is_active and self._active_role_count(session, user.id) <= 1:
            raise UserConflictError("Cannot remove the last active role from an active user.")
        assignment.is_active = False
        session.flush()
        self._record_role_assignment_change(
            session,
            current_user=current_user,
            user=user,
            role=role,
            request_id=request_id,
            metadata={"action": "removed", **self._user_metadata(user)},
        )
        session.commit()
        return self.get_user_detail(session, user_id=user.id, current_user=current_user)

    def _to_list_item(self, context: _UserContext) -> AdminUserListItemView:
        warnings = self._build_warnings(context)
        active_branch_names = [
            branch.name for assignment, branch in context.assignments if assignment.is_active
        ]
        surfaces = self._normalize_surfaces(context.user.allowed_surfaces)
        role_names = [role.name for assignment, role in context.roles if assignment.is_active]
        return AdminUserListItemView(
            id=context.user.id,
            full_name=context.user.full_name,
            email=context.user.email,
            status=_user_status(context.user),
            allowed_surfaces=surfaces,
            default_surface=self._resolve_default_surface(surfaces, context.user.default_surface),
            branch_count=len(active_branch_names),
            branch_names=active_branch_names,
            role_count=len(role_names),
            role_names=role_names,
            last_login_at=context.user.last_login_at,
            created_at=context.user.created_at,
            updated_at=context.user.updated_at,
            warning_state=self._readiness(context.user, warnings),
            warnings=warnings,
        )

    def _to_detail(
        self,
        session: Session,
        context: _UserContext,
        *,
        current_user: AuthenticatedUser,
    ) -> AdminUserDetailView:
        user = context.user
        warnings = self._build_warnings(context)
        surfaces = self._normalize_surfaces(user.allowed_surfaces)
        status_value = _user_status(user)
        can_lock = user.is_active and not user.is_locked and user.id != current_user.id
        can_deactivate = user.is_active and user.id != current_user.id
        can_activate = not user.is_active
        can_unlock = user.is_locked
        readiness = self._readiness(user, warnings)

        return AdminUserDetailView(
            overview=AdminUserOverviewView(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                status=status_value,
                allowed_surfaces=surfaces,
                default_surface=self._resolve_default_surface(surfaces, user.default_surface),
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_login_at=user.last_login_at,
                warning_state=readiness,
            ),
            profile=AdminUserProfileView(
                full_name=user.full_name,
                email=user.email,
                phone=user.phone,
                notes=user.notes,
            ),
            account_status=AdminUserAccountStatusView(
                is_active=user.is_active,
                is_locked=user.is_locked,
                lock_reason=user.lock_reason,
                password_reset_required=user.password_reset_required,
                last_login_at=user.last_login_at,
            ),
            app_access=AdminUserAppAccessView(
                allowed_surfaces=surfaces,
                default_surface=self._resolve_default_surface(surfaces, user.default_surface),
                pos_enabled=IDENTITY_SURFACE_POS in surfaces,
                backoffice_enabled=IDENTITY_SURFACE_BACKOFFICE in surfaces,
                has_both_surfaces=(
                    IDENTITY_SURFACE_POS in surfaces
                    and IDENTITY_SURFACE_BACKOFFICE in surfaces
                ),
            ),
            branch_assignments=[
                AdminUserBranchAssignmentView(
                    assignment_id=assignment.id,
                    branch_id=branch.id,
                    branch_name=branch.name,
                    branch_code=branch.code,
                    is_active=assignment.is_active,
                    is_default=assignment.is_default,
                    assigned_at=assignment.created_at,
                    updated_at=assignment.updated_at,
                )
                for assignment, branch in sorted(
                    context.assignments,
                    key=lambda item: (not item[0].is_default, item[1].name, item[1].code),
                )
            ],
            role_assignments=AdminUserRoleAssignmentsView(
                is_supported=True,
                items=[
                    AdminUserRoleAssignmentView(
                        role_id=str(role.id),
                        role_name=role.name,
                        role_description=role.description,
                        scope="Sin restricciones",
                        assigned_at=assignment.created_at,
                    )
                    for assignment, role in context.roles
                    if assignment.is_active
                ],
                missing_contract_note="",
            ),
            security_actions=AdminUserSecurityActionsView(
                can_lock=can_lock,
                can_unlock=can_unlock,
                can_activate=can_activate,
                can_deactivate=can_deactivate,
            ),
            operational_context=self._build_operational_context(session, user),
            audit_timeline=self._fetch_audit_timeline(session, user.id),
            available_actions=AdminUserAvailableActionsView(
                can_edit_role_assignments=True,
                can_activate=can_activate,
                can_deactivate=can_deactivate,
                can_lock=can_lock,
                can_unlock=can_unlock,
            ),
            warnings=warnings,
        )

    def _build_metrics(self, contexts: list[_UserContext]) -> AdminUserMetricsView:
        return AdminUserMetricsView(
            total_users=len(contexts),
            active_users=sum(
                1
                for context in contexts
                if context.user.is_active and not context.user.is_locked
            ),
            inactive_users=sum(1 for context in contexts if not context.user.is_active),
            locked_users=sum(1 for context in contexts if context.user.is_locked),
            pos_users=sum(
                1
                for context in contexts
                if IDENTITY_SURFACE_POS in self._normalize_surfaces(context.user.allowed_surfaces)
            ),
            backoffice_users=sum(
                1
                for context in contexts
                if IDENTITY_SURFACE_BACKOFFICE
                in self._normalize_surfaces(context.user.allowed_surfaces)
            ),
            without_branch=sum(
                1
                for context in contexts
                if (
                    context.user.is_active
                    and IDENTITY_SURFACE_POS
                    in self._normalize_surfaces(context.user.allowed_surfaces)
                    and not any(assignment.is_active for assignment, _branch in context.assignments)
                )
            ),
        )

    def _build_filter_options(self, session: Session) -> AdminUserFilterOptionsView:
        branches = session.execute(
            select(Branch).order_by(Branch.name.asc(), Branch.code.asc())
        ).scalars().all()
        roles = session.execute(select(Role).order_by(Role.name.asc())).scalars().all()
        return AdminUserFilterOptionsView(
            branches=[
                AdminUserBranchFilterOptionView(
                    id=branch.id,
                    label=f"{branch.name} - {branch.code}",
                )
                for branch in branches
            ],
            roles=[
                AdminUserFilterOptionView(id=str(role.id), label=role.name)
                for role in roles
                if role.is_active
            ],
            statuses=[
                AdminUserFilterOptionView(id="active", label="Activos"),
                AdminUserFilterOptionView(id="inactive", label="Inactivos"),
                AdminUserFilterOptionView(id="locked", label="Bloqueados"),
            ],
            app_access=[
                AdminUserFilterOptionView(id="POS", label="POS"),
                AdminUserFilterOptionView(id="BACKOFFICE", label="Backoffice"),
                AdminUserFilterOptionView(id="BOTH", label="Ambos"),
            ],
            warning_states=[
                AdminUserFilterOptionView(id="with_warnings", label="Con advertencias"),
                AdminUserFilterOptionView(id="without_warnings", label="Sin advertencias"),
            ],
            last_login_states=[
                AdminUserFilterOptionView(id="with_login", label="Con acceso"),
                AdminUserFilterOptionView(id="without_login", label="Sin acceso registrado"),
            ],
        )

    def _build_warnings(self, context: _UserContext) -> list[AdminUserWarningView]:
        warnings: list[AdminUserWarningView] = []
        surfaces = self._normalize_surfaces(context.user.allowed_surfaces)
        if not context.user.is_active:
            warnings.append(
                AdminUserWarningView(
                    code="inactive_user",
                    message="El usuario esta inactivo y no puede autenticarse.",
                    severity="info",
                )
            )
        if context.user.is_locked:
            warnings.append(
                AdminUserWarningView(
                    code="locked_user",
                    message="La cuenta esta bloqueada hasta que se desbloquee desde Backoffice.",
                    severity="critical",
                )
            )
        if not surfaces:
            warnings.append(
                AdminUserWarningView(
                    code="missing_app_access",
                    message="El usuario no tiene acceso a POS ni Backoffice configurado.",
                    severity="critical",
                )
            )
        if (
            IDENTITY_SURFACE_POS in surfaces
            and context.user.is_active
            and not any(assignment.is_active for assignment, _branch in context.assignments)
        ):
            warnings.append(
                AdminUserWarningView(
                    code="pos_without_branch",
                    message="El usuario tiene acceso POS pero no tiene sucursal asignada.",
                    severity="critical",
                )
            )
        if len(surfaces) > 1 and context.user.default_surface not in surfaces:
            warnings.append(
                AdminUserWarningView(
                    code="invalid_default_surface",
                    message="La superficie inicial no coincide con el acceso configurado.",
                    severity="warning",
                )
            )
        if context.user.password_reset_required:
            warnings.append(
                AdminUserWarningView(
                    code="password_reset_required",
                    message="El usuario debe restablecer su contrasena en el proximo acceso.",
                    severity="warning",
                )
            )
        if context.user.is_active and not context.roles:
            warnings.append(
                AdminUserWarningView(
                    code="missing_role_assignment",
                    message="El usuario esta activo pero no tiene roles asignados.",
                    severity="warning",
                )
            )
        return warnings

    def _readiness(
        self,
        user: User,
        warnings: list[AdminUserWarningView],
    ) -> AdminUserReadinessState:
        if not user.is_active or user.is_locked or any(
            warning.severity == "critical" for warning in warnings
        ):
            return "blocked"
        if warnings:
            return "warning"
        return "ready"

    def _build_operational_context(
        self,
        session: Session,
        user: User,
    ) -> AdminUserOperationalContextView:
        open_sessions_count = session.execute(
            select(func.count())
            .select_from(CashSession)
            .where(
                CashSession.user_id == user.id,
                CashSession.status == CASH_SESSION_STATUS_OPEN,
            )
        ).scalar_one()
        recent_pos_activity_count = session.execute(
            select(func.count()).select_from(Sale).where(Sale.operator_id == user.id)
        ).scalar_one()
        recent_backoffice_activity_count = session.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.actor_id == user.id)
        ).scalar_one()
        branch_names = session.execute(
            select(Branch.name)
            .join(Sale, Sale.branch_id == Branch.id)
            .where(Sale.operator_id == user.id)
            .distinct()
            .order_by(Branch.name.asc())
            .limit(5)
        ).scalars().all()
        last_workstation_used = session.execute(
            select(Workstation.name)
            .join(Sale, Sale.workstation_id == Workstation.id)
            .where(Sale.operator_id == user.id)
            .order_by(Sale.confirmed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        return AdminUserOperationalContextView(
            open_cash_sessions_count=open_sessions_count,
            recent_pos_activity_count=recent_pos_activity_count,
            recent_backoffice_activity_count=recent_backoffice_activity_count,
            recently_operated_branches=list(branch_names),
            last_workstation_used=last_workstation_used,
        )

    def _fetch_audit_timeline(
        self,
        session: Session,
        user_id: uuid.UUID,
    ) -> list[AdminUserAuditTimelineEventView]:
        records = session.execute(
            select(AuditLog)
            .where(
                AuditLog.resource_type == USER_RESOURCE_TYPE,
                AuditLog.resource_id == str(user_id),
            )
            .order_by(AuditLog.occurred_at.desc())
            .limit(20)
        ).scalars().all()
        return [
            AdminUserAuditTimelineEventView(
                id=record.id,
                occurred_at=record.occurred_at,
                actor_id=record.actor_id,
                action=record.action,
                metadata=record.metadata_,
            )
            for record in records
        ]

    def _fetch_assignments(
        self,
        session: Session,
        user_id: uuid.UUID,
    ) -> list[tuple[UserBranchAssignment, Branch]]:
        return list(
            session.execute(
                select(UserBranchAssignment, Branch)
                .join(Branch, Branch.id == UserBranchAssignment.branch_id)
                .where(UserBranchAssignment.user_id == user_id)
                .order_by(Branch.name.asc(), Branch.code.asc())
            ).all()
        )

    def _fetch_role_assignments(
        self,
        session: Session,
        user_id: uuid.UUID,
    ) -> list[tuple[UserRoleAssignment, Role]]:
        return list(
            session.execute(
                select(UserRoleAssignment, Role)
                .join(Role, Role.id == UserRoleAssignment.role_id)
                .where(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.is_active.is_(True),
                )
                .order_by(Role.name.asc(), Role.code.asc())
            ).all()
        )

    def _get_context(self, session: Session, user_id: uuid.UUID) -> _UserContext:
        user = self._get_user(session, user_id)
        return _UserContext(
            user=user,
            assignments=self._fetch_assignments(session, user.id),
            roles=self._fetch_role_assignments(session, user.id),
        )

    def _get_user(self, session: Session, user_id: uuid.UUID) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise UserNotFoundError("User was not found.")
        return user

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise UserValidationError("Branch was not found.")
        return branch

    def _get_role(self, session: Session, role_id: uuid.UUID) -> Role:
        role = session.get(Role, role_id)
        if role is None:
            raise UserValidationError("Role was not found.")
        return role

    def _get_roles_by_ids(self, session: Session, role_ids: list[str]) -> list[Role]:
        if not role_ids:
            return []
        parsed_ids = list(
            dict.fromkeys(
                self._parse_uuid(role_id, "Role id must be valid.") for role_id in role_ids
            )
        )
        roles = session.execute(select(Role).where(Role.id.in_(parsed_ids))).scalars().all()
        by_id = {role.id: role for role in roles}
        missing = [role_id for role_id in parsed_ids if role_id not in by_id]
        if missing:
            raise UserValidationError("Role was not found.")
        return [by_id[role_id] for role_id in parsed_ids]

    def _ensure_roles_are_active(self, roles: list[Role]) -> None:
        if any(not role.is_active for role in roles):
            raise UserValidationError("Inactive roles cannot be assigned.")

    def _get_assignment(
        self,
        session: Session,
        *,
        user_id: uuid.UUID,
        branch_id: uuid.UUID,
    ) -> UserBranchAssignment:
        assignment = session.execute(
            select(UserBranchAssignment).where(
                UserBranchAssignment.user_id == user_id,
                UserBranchAssignment.branch_id == branch_id,
            )
        ).scalar_one_or_none()
        if assignment is None:
            raise UserNotFoundError("Branch assignment was not found.")
        return assignment

    def _active_assignment_count(self, session: Session, user_id: uuid.UUID) -> int:
        return session.execute(
            select(func.count())
            .select_from(UserBranchAssignment)
            .where(
                UserBranchAssignment.user_id == user_id,
                UserBranchAssignment.is_active.is_(True),
            )
        ).scalar_one()

    def _active_role_count(self, session: Session, user_id: uuid.UUID) -> int:
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

    def _user_has_role(
        self,
        session: Session,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
    ) -> bool:
        return (
            session.execute(
                select(UserRoleAssignment.id).where(
                    UserRoleAssignment.user_id == user_id,
                    UserRoleAssignment.role_id == role_id,
                    UserRoleAssignment.is_active.is_(True),
                )
            ).scalar_one_or_none()
            is not None
        )

    def _replace_assignments(
        self,
        session: Session,
        *,
        user: User,
        branch_commands: list[AdminUserBranchAssignmentCommand],
        branches: list[Branch],
    ) -> None:
        default_index = next(
            (index for index, command in enumerate(branch_commands) if command.is_default),
            0,
        )
        for index, branch in enumerate(branches):
            session.add(
                UserBranchAssignment(
                    user_id=user.id,
                    branch_id=branch.id,
                    is_active=True,
                    is_default=index == default_index,
                )
            )

    def _replace_role_assignments(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user: User,
        roles: list[Role],
    ) -> None:
        for role in roles:
            session.add(
                UserRoleAssignment(
                    user_id=user.id,
                    role_id=role.id,
                    is_active=True,
                    assigned_by_user_id=current_user.id,
                )
            )

    def _set_default_assignment(
        self,
        session: Session,
        *,
        user: User,
        branch_id: uuid.UUID,
    ) -> None:
        assignments = session.execute(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == user.id)
        ).scalars().all()
        for assignment in assignments:
            assignment.is_default = assignment.branch_id == branch_id and assignment.is_active

    def _ensure_default_assignment(self, session: Session, *, user: User) -> None:
        assignments = session.execute(
            select(UserBranchAssignment)
            .where(
                UserBranchAssignment.user_id == user.id,
                UserBranchAssignment.is_active.is_(True),
            )
            .order_by(UserBranchAssignment.created_at.asc())
        ).scalars().all()
        if assignments and not any(assignment.is_default for assignment in assignments):
            assignments[0].is_default = True

    def _record_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user: User,
        action: str,
        event_name: str,
        request_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=USER_RESOURCE_TYPE,
            resource_id=str(user.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=USER_RESOURCE_TYPE,
            aggregate_id=str(user.id),
            event_name=event_name,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )

    def _record_branch_assignment_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user: User,
        branch: Branch,
        request_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_ADMIN_USER_BRANCH_ASSIGNMENT_CHANGED,
            resource_type=USER_RESOURCE_TYPE,
            resource_id=str(user.id),
            branch_id=branch.id,
            request_id=request_id,
            metadata={**metadata, "branch_id": str(branch.id), "branch_code": branch.code},
        )
        self._outbox_writer.append(
            session,
            aggregate_type=USER_RESOURCE_TYPE,
            aggregate_id=str(user.id),
            event_name=OUTBOX_EVENT_ADMIN_USER_BRANCH_ASSIGNMENT_CHANGED_V1,
            payload={**metadata, "branch_id": str(branch.id), "branch_code": branch.code},
            headers={"request_id": request_id} if request_id else {},
        )

    def _record_role_assignment_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        user: User,
        role: Role,
        request_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        payload = {
            **metadata,
            "role_id": str(role.id),
            "role_code": role.code,
            "role_name": role.name,
        }
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_ADMIN_USER_ROLE_ASSIGNMENT_CHANGED,
            resource_type=USER_RESOURCE_TYPE,
            resource_id=str(user.id),
            branch_id=None,
            request_id=request_id,
            metadata=payload,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=USER_RESOURCE_TYPE,
            aggregate_id=str(user.id),
            event_name=OUTBOX_EVENT_ADMIN_USER_ROLE_ASSIGNMENT_CHANGED_V1,
            payload=payload,
            headers={"request_id": request_id} if request_id else {},
        )

    def _user_metadata(self, user: User) -> dict[str, Any]:
        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "status": _user_status(user),
            "allowed_surfaces": self._normalize_surfaces(user.allowed_surfaces),
            "default_surface": user.default_surface,
            "is_active": user.is_active,
            "is_locked": user.is_locked,
        }

    def _ensure_unique_email(
        self,
        session: Session,
        email: str,
        *,
        exclude_user_id: uuid.UUID | None = None,
    ) -> None:
        statement = select(User.id).where(User.email == email)
        if exclude_user_id is not None:
            statement = statement.where(User.id != exclude_user_id)
        existing = session.execute(statement).scalar_one_or_none()
        if existing is not None:
            raise UserValidationError("Email must be unique.")

    def _deduplicate_branch_commands(
        self,
        commands: list[AdminUserBranchAssignmentCommand],
    ) -> list[AdminUserBranchAssignmentCommand]:
        by_branch: dict[uuid.UUID, AdminUserBranchAssignmentCommand] = {}
        for command in commands:
            by_branch[command.branch_id] = command
        return list(by_branch.values())

    def _parse_uuid(self, value: str | None, message: str) -> uuid.UUID:
        if value is None:
            raise UserValidationError(message)
        try:
            return uuid.UUID(str(value))
        except ValueError as error:
            raise UserValidationError(message) from error

    def _is_last_backoffice_user(self, session: Session, target_user: User) -> bool:
        if (
            not target_user.is_active
            or target_user.is_locked
            or IDENTITY_SURFACE_BACKOFFICE
            not in self._normalize_surfaces(target_user.allowed_surfaces)
        ):
            return False
        users = session.execute(
            select(User).where(
                User.id != target_user.id,
                User.is_active.is_(True),
                User.is_locked.is_(False),
            )
        ).scalars().all()
        return not any(
            IDENTITY_SURFACE_BACKOFFICE in self._normalize_surfaces(user.allowed_surfaces)
            for user in users
        )

    def _matches_app_access(self, user: User, app_access: str) -> bool:
        surfaces = self._normalize_surfaces(user.allowed_surfaces)
        normalized = app_access.strip().upper()
        if normalized == "BOTH":
            return (
                IDENTITY_SURFACE_POS in surfaces
                and IDENTITY_SURFACE_BACKOFFICE in surfaces
            )
        return normalized in surfaces

    def _normalize_email(self, email: str) -> str:
        normalized = email.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", maxsplit=1)[-1]:
            raise UserValidationError("Email must be valid.")
        return normalized

    def _normalize_surfaces(self, values: list[str] | tuple[str, ...] | None) -> list[str]:
        if values is None:
            return [IDENTITY_SURFACE_POS]
        normalized: list[str] = []
        for value in values:
            surface = str(value).strip().upper()
            if surface not in IDENTITY_ALLOWED_SURFACES:
                raise UserValidationError("Unsupported application access.")
            if surface not in normalized:
                normalized.append(surface)
        if not normalized:
            raise UserValidationError("Application access is required.")
        return normalized

    def _resolve_default_surface(
        self,
        surfaces: list[str],
        default_surface: str | None,
    ) -> str:
        if default_surface is None:
            return surfaces[0]
        resolved = default_surface.strip().upper()
        if resolved not in surfaces:
            raise UserValidationError("Default surface must be included in application access.")
        return resolved


def _user_status(user: User) -> AdminUserStatus:
    if user.is_locked:
        return "locked"
    return "active" if user.is_active else "inactive"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
