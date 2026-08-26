from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminBranchStatus = Literal["active", "inactive"]
AdminBranchReadinessStatus = Literal["ready", "warning", "inactive"]
AdminBranchWarningSeverity = Literal["info", "warning", "critical"]
AdminBranchHasActiveWorkstations = Literal["all", "yes", "no"]
AdminBranchWarningState = Literal["all", "with_warnings", "without_warnings"]
AdminWorkstationStatus = Literal["active", "inactive"]
AdminWorkstationReadinessStatus = Literal["ready", "warning", "blocked"]
AdminWorkstationCashSessionState = Literal["all", "open", "closed", "no_recent_session"]


class AdminBranchFilterOptionView(BaseModel):
    id: UUID
    label: str


class AdminBranchBackendContractView(BaseModel):
    create_endpoint: str = "POST /v1/admin/branches"
    detail_endpoint: str = "GET /v1/admin/branches/{id}"
    list_endpoint: str = "GET /v1/admin/branches"
    update_endpoint: str = "PATCH /v1/admin/branches/{id}"


class AdminBranchMetricsView(BaseModel):
    total_branches: int
    active_branches: int
    inactive_branches: int
    with_workstations: int
    without_active_workstation: int
    with_warnings: int


class AdminBranchFilterOptionsView(BaseModel):
    brands: list[AdminBranchFilterOptionView]


class AdminBranchWarningView(BaseModel):
    code: str
    message: str
    severity: AdminBranchWarningSeverity


class AdminBranchListItemView(BaseModel):
    id: UUID
    brand_id: UUID
    brand_name: str
    code: str
    name: str
    timezone: str
    status: AdminBranchStatus
    workstation_count: int
    active_workstation_count: int
    assigned_user_count: int
    readiness: AdminBranchReadinessStatus
    warnings: list[AdminBranchWarningView]
    updated_at: datetime | None = None


class AdminBranchesListResponse(BaseModel):
    backend_contract: AdminBranchBackendContractView = Field(
        default_factory=AdminBranchBackendContractView,
    )
    filter_options: AdminBranchFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminBranchListItemView]
    metrics: AdminBranchMetricsView
    page: int
    page_size: int
    total: int


class AdminBranchOverviewView(BaseModel):
    id: UUID
    brand_id: UUID
    brand_name: str
    code: str
    name: str
    status: AdminBranchStatus
    timezone: str
    readiness: AdminBranchReadinessStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminBranchLocationContactView(BaseModel):
    address_line: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class AdminBranchOperationalConfigView(BaseModel):
    timezone: str
    is_active: bool
    pos_ready: bool
    inventory_scope_ready: bool = True
    production_scope_ready: bool = True


class AdminBranchWorkstationView(BaseModel):
    id: UUID
    code: str
    name: str
    is_active: bool
    updated_at: datetime | None = None


class AdminBranchWorkstationsSummaryView(BaseModel):
    total: int
    active: int
    inactive: int
    items: list[AdminBranchWorkstationView]


class AdminBranchUserAssignmentView(BaseModel):
    assignment_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    is_active: bool
    updated_at: datetime | None = None


class AdminBranchUsersSummaryView(BaseModel):
    total: int
    active: int
    inactive: int
    items: list[AdminBranchUserAssignmentView]


class AdminBranchRelatedOperationsSummaryView(BaseModel):
    open_cash_sessions: int


class AdminBranchAvailableActionsView(BaseModel):
    can_edit: bool = True
    can_activate: bool
    can_deactivate: bool
    can_open_workstations: bool = True
    can_open_users: bool = True


class AdminBranchDetailView(BaseModel):
    available_actions: AdminBranchAvailableActionsView
    location_contact: AdminBranchLocationContactView
    operational_config: AdminBranchOperationalConfigView
    overview: AdminBranchOverviewView
    related_operations_summary: AdminBranchRelatedOperationsSummaryView
    user_assignments_summary: AdminBranchUsersSummaryView
    warnings: list[AdminBranchWarningView]
    workstations_summary: AdminBranchWorkstationsSummaryView


class AdminBranchCreateRequest(BaseModel):
    brand_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    timezone: str = Field(min_length=1, max_length=64)
    is_active: bool = True
    address_line: str | None = Field(default=None, max_length=240)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=40)
    contact_email: str | None = Field(default=None, max_length=320)
    notes: str | None = None

    @field_validator(
        "code",
        "name",
        "timezone",
        "address_line",
        "city",
        "state",
        "country",
        "postal_code",
        "phone",
        "notes",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("code", "name", "timezone")
    @classmethod
    def validate_required_text(cls, value: str | None) -> str:
        normalized = "" if value is None else value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        if "@" not in normalized:
            raise ValueError("Contact email must be valid.")
        return normalized


class AdminBranchUpdateRequest(BaseModel):
    brand_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    is_active: bool | None = None
    address_line: str | None = Field(default=None, max_length=240)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    country: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=40)
    contact_email: str | None = Field(default=None, max_length=320)
    notes: str | None = None

    @field_validator(
        "code",
        "name",
        "timezone",
        "address_line",
        "city",
        "state",
        "country",
        "postal_code",
        "phone",
        "notes",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @field_validator("code", "name", "timezone")
    @classmethod
    def validate_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Value cannot be blank.")
        return value

    @field_validator("contact_email")
    @classmethod
    def validate_optional_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            return None
        if "@" not in normalized:
            raise ValueError("Contact email must be valid.")
        return normalized


class AdminWorkstationBackendContractView(BaseModel):
    create_endpoint: str = "POST /v1/admin/workstations"
    detail_endpoint: str = "GET /v1/admin/workstations/{id}"
    list_endpoint: str = "GET /v1/admin/workstations"
    update_endpoint: str = "PATCH /v1/admin/workstations/{id}"


class AdminWorkstationMetricsView(BaseModel):
    total_workstations: int
    active_workstations: int
    inactive_workstations: int
    with_open_cash_session: int
    without_active_branch: int
    with_warnings: int


class AdminWorkstationFilterOptionsView(BaseModel):
    branches: list[AdminBranchFilterOptionView]


class AdminWorkstationCashSessionSummaryView(BaseModel):
    id: UUID
    status: str
    opening_amount: str
    opened_at: datetime
    closed_at: datetime | None = None
    opened_by_user_id: UUID | None = None
    opened_by_user_name: str | None = None


class AdminWorkstationListItemView(BaseModel):
    id: UUID
    branch_id: UUID
    branch_code: str
    branch_name: str
    branch_is_active: bool
    code: str
    name: str
    status: AdminWorkstationStatus
    has_active_cash_session: bool
    active_cash_session_id: UUID | None = None
    last_opened_at: datetime | None = None
    last_closed_at: datetime | None = None
    readiness: AdminWorkstationReadinessStatus
    warnings: list[AdminBranchWarningView]
    updated_at: datetime | None = None


class AdminWorkstationsListResponse(BaseModel):
    backend_contract: AdminWorkstationBackendContractView = Field(
        default_factory=AdminWorkstationBackendContractView,
    )
    filter_options: AdminWorkstationFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminWorkstationListItemView]
    metrics: AdminWorkstationMetricsView
    page: int
    page_size: int
    total: int


class AdminWorkstationOverviewView(BaseModel):
    id: UUID
    code: str
    name: str
    status: AdminWorkstationStatus
    readiness: AdminWorkstationReadinessStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminWorkstationBranchRelationshipView(BaseModel):
    branch_id: UUID
    branch_code: str
    branch_name: str
    branch_timezone: str
    branch_is_active: bool


class AdminWorkstationOperationalConfigView(BaseModel):
    is_active: bool
    pos_enabled: bool


class AdminWorkstationCashSessionContextView(BaseModel):
    active_session: AdminWorkstationCashSessionSummaryView | None = None
    last_closed_session: AdminWorkstationCashSessionSummaryView | None = None


class AdminWorkstationAccessUserView(BaseModel):
    user_id: UUID
    user_name: str
    user_email: str
    is_active: bool


class AdminWorkstationAccessContextView(BaseModel):
    assigned_user_count: int
    active_assigned_user_count: int
    users: list[AdminWorkstationAccessUserView]


class AdminWorkstationAvailableActionsView(BaseModel):
    can_edit: bool = True
    can_activate: bool
    can_deactivate: bool
    can_open_branch: bool = True
    can_open_cash_session: bool


class AdminWorkstationDetailView(BaseModel):
    access_context: AdminWorkstationAccessContextView
    available_actions: AdminWorkstationAvailableActionsView
    branch_relationship: AdminWorkstationBranchRelationshipView
    cash_session_context: AdminWorkstationCashSessionContextView
    operational_config: AdminWorkstationOperationalConfigView
    overview: AdminWorkstationOverviewView
    warnings: list[AdminBranchWarningView]


class AdminWorkstationCreateRequest(BaseModel):
    branch_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    is_active: bool = True

    @field_validator("code", "name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized


class AdminWorkstationUpdateRequest(BaseModel):
    branch_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None

    @field_validator("code", "name")
    @classmethod
    def validate_optional_required_text(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Value cannot be blank.")
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized
