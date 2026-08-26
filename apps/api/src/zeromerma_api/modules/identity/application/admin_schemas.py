from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from zeromerma_api.modules.identity.application.schemas import IdentitySurface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_ALLOWED_SURFACES

AdminUserStatus = Literal["active", "inactive", "locked"]
AdminUserWarningSeverity = Literal["info", "warning", "critical"]
AdminUserReadinessState = Literal["ready", "warning", "blocked"]


class AdminUserBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/users"
    detail_endpoint: str = "GET /v1/admin/users/{id}"
    create_endpoint: str = "POST /v1/admin/users"
    update_endpoint: str = "PATCH /v1/admin/users/{id}"
    status_endpoint: str = "POST /v1/admin/users/{id}/status"
    lock_endpoint: str = "POST /v1/admin/users/{id}/lock"
    unlock_endpoint: str = "POST /v1/admin/users/{id}/unlock"
    branch_assignment_endpoint: str = "POST /v1/admin/users/{id}/branch-assignments"
    role_assignment_supported: bool = True
    invitation_supported: bool = False
    password_reset_supported: bool = False
    session_revocation_supported: bool = False


class AdminUserFilterOptionView(BaseModel):
    id: str
    label: str


class AdminUserBranchFilterOptionView(BaseModel):
    id: UUID
    label: str


class AdminUserFilterOptionsView(BaseModel):
    branches: list[AdminUserBranchFilterOptionView]
    roles: list[AdminUserFilterOptionView] = Field(default_factory=list)
    statuses: list[AdminUserFilterOptionView]
    app_access: list[AdminUserFilterOptionView]
    warning_states: list[AdminUserFilterOptionView]
    last_login_states: list[AdminUserFilterOptionView]


class AdminUserMetricsView(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    locked_users: int
    pending_users: int = 0
    pos_users: int
    backoffice_users: int
    without_branch: int


class AdminUserWarningView(BaseModel):
    code: str
    message: str
    severity: AdminUserWarningSeverity


class AdminUserListItemView(BaseModel):
    id: UUID
    full_name: str
    email: str
    status: AdminUserStatus
    allowed_surfaces: list[IdentitySurface]
    default_surface: IdentitySurface
    branch_count: int
    branch_names: list[str]
    role_count: int = 0
    role_names: list[str] = Field(default_factory=list)
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    warning_state: AdminUserReadinessState
    warnings: list[AdminUserWarningView]


class AdminUsersListResponse(BaseModel):
    backend_contract: AdminUserBackendContractView = Field(
        default_factory=AdminUserBackendContractView,
    )
    filter_options: AdminUserFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminUserListItemView]
    metrics: AdminUserMetricsView
    page: int
    page_size: int
    total: int


class AdminUserOverviewView(BaseModel):
    id: UUID
    full_name: str
    email: str
    status: AdminUserStatus
    allowed_surfaces: list[IdentitySurface]
    default_surface: IdentitySurface
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    warning_state: AdminUserReadinessState


class AdminUserProfileView(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    display_name: str | None = None
    employee_code: str | None = None
    notes: str | None = None


class AdminUserAccountStatusView(BaseModel):
    is_active: bool
    is_locked: bool
    lock_reason: str | None = None
    pending_invitation: bool = False
    password_reset_required: bool
    failed_login_count: int | None = None
    last_login_at: datetime | None = None
    active_sessions_count: int | None = None
    active_sessions_supported: bool = False


class AdminUserAppAccessView(BaseModel):
    allowed_surfaces: list[IdentitySurface]
    default_surface: IdentitySurface
    pos_enabled: bool
    backoffice_enabled: bool
    has_both_surfaces: bool


class AdminUserBranchAssignmentView(BaseModel):
    assignment_id: UUID
    branch_id: UUID
    branch_name: str
    branch_code: str
    is_active: bool
    is_default: bool
    assigned_at: datetime
    updated_at: datetime


class AdminUserRoleAssignmentView(BaseModel):
    role_id: str
    role_name: str
    role_description: str | None = None
    scope: str | None = None
    assigned_at: datetime | None = None


class AdminUserRoleAssignmentsView(BaseModel):
    is_supported: bool = False
    items: list[AdminUserRoleAssignmentView] = Field(default_factory=list)
    missing_contract_note: str = "Role assignment backend support is not available yet."


class AdminUserSecurityActionsView(BaseModel):
    supports_locking: bool = True
    supports_password_reset: bool = False
    supports_invitation: bool = False
    supports_session_revocation: bool = False
    can_lock: bool
    can_unlock: bool
    can_activate: bool
    can_deactivate: bool
    can_revoke_sessions: bool = False
    can_send_invitation: bool = False
    can_send_password_reset: bool = False


class AdminUserOperationalContextView(BaseModel):
    open_cash_sessions_count: int
    recent_pos_activity_count: int
    recent_backoffice_activity_count: int
    recently_operated_branches: list[str]
    last_workstation_used: str | None = None
    active_sessions_supported: bool = False


class AdminUserAuditTimelineEventView(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_id: UUID | None = None
    action: str
    metadata: dict[str, Any]


class AdminUserAvailableActionsView(BaseModel):
    can_edit_profile: bool = True
    can_edit_app_access: bool = True
    can_edit_branch_assignments: bool = True
    can_edit_role_assignments: bool = False
    can_activate: bool
    can_deactivate: bool
    can_lock: bool
    can_unlock: bool
    can_open_audit: bool = True


class AdminUserDetailView(BaseModel):
    overview: AdminUserOverviewView
    profile: AdminUserProfileView
    account_status: AdminUserAccountStatusView
    app_access: AdminUserAppAccessView
    branch_assignments: list[AdminUserBranchAssignmentView]
    role_assignments: AdminUserRoleAssignmentsView
    security_actions: AdminUserSecurityActionsView
    operational_context: AdminUserOperationalContextView
    audit_timeline: list[AdminUserAuditTimelineEventView]
    available_actions: AdminUserAvailableActionsView
    warnings: list[AdminUserWarningView]


class AdminUserBranchAssignmentCommand(BaseModel):
    branch_id: UUID
    is_default: bool = False


class AdminUserCreateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=320)
    temporary_password: str | None = Field(default=None, min_length=8, max_length=128)
    allowed_surfaces: list[IdentitySurface] = Field(min_length=1)
    default_surface: IdentitySurface | None = None
    branch_assignments: list[AdminUserBranchAssignmentCommand] = Field(default_factory=list)
    role_ids: list[str] = Field(default_factory=list)
    send_invitation: bool = False
    phone: str | None = Field(default=None, max_length=40)
    notes: str | None = None

    @field_validator("full_name", "email", "phone", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str:
        normalized = "" if value is None else value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", maxsplit=1)[-1]:
            raise ValueError("Email must be valid.")
        return normalized

    @field_validator("allowed_surfaces")
    @classmethod
    def normalize_surfaces(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for surface in values:
            resolved = str(surface).strip().upper()
            if resolved not in IDENTITY_ALLOWED_SURFACES:
                raise ValueError("Unsupported application access.")
            if resolved not in normalized:
                normalized.append(resolved)
        if not normalized:
            raise ValueError("Application access is required.")
        return normalized

    @model_validator(mode="after")
    def validate_default_surface(self) -> AdminUserCreateRequest:
        if len(self.allowed_surfaces) > 1 and self.default_surface is None:
            raise ValueError(
                "Default surface is required when the user has POS and Backoffice access."
            )
        if self.default_surface is not None and self.default_surface not in self.allowed_surfaces:
            raise ValueError("Default surface must be included in application access.")
        return self


class AdminUserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    phone: str | None = Field(default=None, max_length=40)
    allowed_surfaces: list[IdentitySurface] | None = None
    default_surface: IdentitySurface | None = None
    notes: str | None = None

    @field_validator("full_name", "email", "phone", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("email")
    @classmethod
    def validate_optional_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", maxsplit=1)[-1]:
            raise ValueError("Email must be valid.")
        return normalized

    @field_validator("allowed_surfaces")
    @classmethod
    def normalize_optional_surfaces(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return values
        normalized: list[str] = []
        for surface in values:
            resolved = str(surface).strip().upper()
            if resolved not in IDENTITY_ALLOWED_SURFACES:
                raise ValueError("Unsupported application access.")
            if resolved not in normalized:
                normalized.append(resolved)
        if not normalized:
            raise ValueError("Application access is required.")
        return normalized


class AdminUserStatusChangeRequest(BaseModel):
    is_active: bool


class AdminUserLockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=320)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None


class AdminUserRoleAssignmentRequest(BaseModel):
    role_id: str = Field(min_length=1, max_length=120)
