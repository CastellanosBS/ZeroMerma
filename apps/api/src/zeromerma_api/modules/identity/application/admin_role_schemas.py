from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from zeromerma_api.modules.identity.application.admin_schemas import AdminAssignmentScopeRequest
from zeromerma_api.modules.identity.application.schemas import IdentitySurface
from zeromerma_api.modules.identity.domain.constants import IDENTITY_ALLOWED_SURFACES

AdminRoleStatus = Literal["active", "inactive"]
AdminRoleWarningSeverity = Literal["info", "warning", "critical"]
AdminRoleReadinessState = Literal["ready", "warning", "blocked"]


class AdminRoleBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/roles"
    detail_endpoint: str = "GET /v1/admin/roles/{id}"
    create_endpoint: str = "POST /v1/admin/roles"
    update_endpoint: str = "PATCH /v1/admin/roles/{id}"
    status_endpoint: str = "POST /v1/admin/roles/{id}/status"
    permissions_endpoint: str = "GET /v1/admin/roles/permissions"
    assign_user_endpoint: str = "POST /v1/admin/roles/{id}/users/{user_id}"
    remove_user_endpoint: str = "POST /v1/admin/roles/{id}/users/{user_id}/remove"
    duplicate_supported: bool = False
    scoped_roles_supported: bool = True
    destructive_delete_supported: bool = False


class AdminRoleFilterOptionView(BaseModel):
    id: str
    label: str


class AdminRoleFilterOptionsView(BaseModel):
    statuses: list[AdminRoleFilterOptionView]
    app_surfaces: list[AdminRoleFilterOptionView]
    high_privilege: list[AdminRoleFilterOptionView]
    has_users: list[AdminRoleFilterOptionView]
    permission_modules: list[AdminRoleFilterOptionView]
    warning_states: list[AdminRoleFilterOptionView]
    system_states: list[AdminRoleFilterOptionView]


class AdminRoleMetricsView(BaseModel):
    total_roles: int
    active_roles: int
    inactive_roles: int
    with_users: int
    without_users: int
    high_privilege: int
    pos_roles: int
    backoffice_roles: int
    with_warnings: int


class AdminRoleWarningView(BaseModel):
    code: str
    message: str
    severity: AdminRoleWarningSeverity


class AdminRoleListItemView(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    status: AdminRoleStatus
    surfaces: list[IdentitySurface]
    permission_count: int
    assigned_user_count: int
    is_system: bool
    is_high_privilege: bool
    scope_summary: str
    warning_state: AdminRoleReadinessState
    warnings: list[AdminRoleWarningView]
    updated_at: datetime


class AdminRolesListResponse(BaseModel):
    backend_contract: AdminRoleBackendContractView = Field(
        default_factory=AdminRoleBackendContractView,
    )
    filter_options: AdminRoleFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminRoleListItemView]
    metrics: AdminRoleMetricsView
    page: int
    page_size: int
    total: int


class AdminRoleOverviewView(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None = None
    status: AdminRoleStatus
    surfaces: list[IdentitySurface]
    is_system: bool
    is_high_privilege: bool
    created_at: datetime
    updated_at: datetime
    warning_state: AdminRoleReadinessState


class AdminRoleAccessSurfacesView(BaseModel):
    surfaces: list[IdentitySurface]
    pos_enabled: bool
    backoffice_enabled: bool
    grants_both_surfaces: bool
    note: str


class AdminPermissionView(BaseModel):
    id: UUID
    code: str
    label: str
    description: str | None = None
    module: str
    module_label: str
    action: str
    surfaces: list[IdentitySurface]
    is_sensitive: bool
    is_enabled: bool


class AdminPermissionGroupView(BaseModel):
    module: str
    label: str
    permissions: list[AdminPermissionView]


class AdminRoleScopeView(BaseModel):
    is_supported: bool = True
    scope_summary: str = "Explicit scope is configured per user role assignment."
    missing_contract_note: str = ""


class AdminRoleAssignedUserView(BaseModel):
    user_id: UUID
    full_name: str
    email: str
    status: str
    branch_summary: str
    surfaces: list[IdentitySurface]
    assigned_at: datetime
    scope_type: Literal["GLOBAL", "BRANCH_SET"]
    branch_ids: list[UUID]


class AdminRoleAuditEventView(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_id: UUID | None = None
    action: str
    metadata: dict[str, Any]


class AdminRoleAvailableActionsView(BaseModel):
    can_edit: bool
    can_activate: bool
    can_deactivate: bool
    can_assign_users: bool
    can_remove_users: bool
    can_duplicate: bool = False
    can_delete: bool = False
    can_open_audit: bool = True


class AdminRoleDetailView(BaseModel):
    overview: AdminRoleOverviewView
    access_surfaces: AdminRoleAccessSurfacesView
    permission_matrix: list[AdminPermissionGroupView]
    sensitive_permissions: list[AdminPermissionView]
    scopes: AdminRoleScopeView
    assigned_users: list[AdminRoleAssignedUserView]
    audit_history: list[AdminRoleAuditEventView]
    available_actions: AdminRoleAvailableActionsView
    warnings: list[AdminRoleWarningView]


class AdminPermissionsResponse(BaseModel):
    groups: list[AdminPermissionGroupView]
    sensitive_permission_codes: list[str]


class AdminRoleCreateRequest(BaseModel):
    code: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    surfaces: list[IdentitySurface] = Field(min_length=1)
    permission_codes: list[str] = Field(min_length=1)
    is_active: bool = True
    confirmed_high_risk_change: bool = False

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if not normalized or not normalized.replace("_", "").isalnum():
            raise ValueError("Role code must use letters, numbers or underscores.")
        return normalized

    @field_validator("name", "description")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("surfaces")
    @classmethod
    def normalize_surfaces(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            surface = str(value).strip().upper()
            if surface not in IDENTITY_ALLOWED_SURFACES:
                raise ValueError("Unsupported application surface.")
            if surface not in normalized:
                normalized.append(surface)
        if not normalized:
            raise ValueError("At least one application surface is required.")
        return normalized

    @field_validator("permission_codes")
    @classmethod
    def normalize_permission_codes(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            code = value.strip().lower()
            if code and code not in normalized:
                normalized.append(code)
        if not normalized:
            raise ValueError("At least one permission is required.")
        return normalized


class AdminRoleUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    surfaces: list[IdentitySurface] | None = None
    permission_codes: list[str] | None = None
    is_active: bool | None = None
    confirmed_high_risk_change: bool = False

    @field_validator("name", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        return normalized or None

    @field_validator("surfaces")
    @classmethod
    def normalize_optional_surfaces(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return values
        return AdminRoleCreateRequest.normalize_surfaces(values)

    @field_validator("permission_codes")
    @classmethod
    def normalize_optional_permission_codes(
        cls,
        values: list[str] | None,
    ) -> list[str] | None:
        if values is None:
            return values
        return AdminRoleCreateRequest.normalize_permission_codes(values)

    @model_validator(mode="after")
    def validate_has_change(self) -> AdminRoleUpdateRequest:
        if not self.model_fields_set:
            raise ValueError("At least one field is required.")
        return self


class AdminRoleStatusChangeRequest(BaseModel):
    is_active: bool
    confirmed_high_risk_change: bool = False


class AdminRoleUserAssignmentRequest(AdminAssignmentScopeRequest):
    pass
