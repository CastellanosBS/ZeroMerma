from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

CleaningLogStatus = Literal[
    "SCHEDULED",
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "MISSED",
    "CANCELLED",
    "REQUIRES_REVIEW",
]
CleaningRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
CleaningEvidenceState = Literal["all", "with_evidence", "without_evidence"]
CleaningObservationState = Literal["all", "with_observations", "without_observations"]


class AdminCleaningBackendContractView(BaseModel):
    cancel_endpoint: str = "POST /v1/admin/cleaning-logs/{cleaning_log_id}/cancel"
    complete_endpoint: str = "POST /v1/admin/cleaning-logs/{cleaning_log_id}/complete"
    create_endpoint: str = "POST /v1/admin/cleaning-logs"
    detail_endpoint: str = "GET /v1/admin/cleaning-logs/{cleaning_log_id}"
    evidence_contract: str = (
        "Evidence files are not supported yet; evidence is captured as evidence_note."
    )
    list_endpoint: str = "GET /v1/admin/cleaning-logs"
    templates_endpoint: str = "GET /v1/admin/cleaning-logs/templates"


class AdminCleaningFilterOptionView(BaseModel):
    id: str
    label: str


class AdminCleaningTemplateItemView(BaseModel):
    description: str | None = None
    display_order: int
    id: UUID
    is_required: bool
    label: str


class AdminCleaningTemplateView(BaseModel):
    area_type: str
    cleaning_type: str
    description: str | None = None
    estimated_duration_minutes: int | None = None
    frequency: str
    id: UUID
    is_active: bool
    items: list[AdminCleaningTemplateItemView]
    method_summary: str | None = None
    name: str
    requires_evidence: bool
    required_tools: str | None = None
    risk_level: CleaningRiskLevel


class AdminCleaningFilterOptionsView(BaseModel):
    area_types: list[AdminCleaningFilterOptionView]
    areas: list[AdminCleaningFilterOptionView]
    branches: list[AdminCleaningFilterOptionView]
    cleaning_types: list[AdminCleaningFilterOptionView]
    evidence_states: list[AdminCleaningFilterOptionView]
    observation_states: list[AdminCleaningFilterOptionView]
    responsible_users: list[AdminCleaningFilterOptionView]
    risk_levels: list[AdminCleaningFilterOptionView]
    shifts: list[AdminCleaningFilterOptionView]
    statuses: list[AdminCleaningFilterOptionView]
    templates: list[AdminCleaningFilterOptionView]


class AdminCleaningMetricsView(BaseModel):
    completed_count: int
    high_risk_count: int
    overdue_count: int
    pending_count: int
    requires_review_count: int
    total_count: int
    with_evidence_count: int
    with_observations_count: int


class AdminCleaningWarningView(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class AdminCleaningLogListItemView(BaseModel):
    area_id: UUID | None = None
    area_name: str
    branch_id: UUID
    branch_name: str
    checklist_completed_count: int
    checklist_total_count: int
    cleaning_type: str
    completed_at: datetime | None = None
    equipment_id: UUID | None = None
    equipment_name: str | None = None
    folio: str
    has_evidence: bool
    has_observations: bool
    id: UUID
    responsible_user_id: UUID
    responsible_user_name: str
    risk_level: CleaningRiskLevel
    scheduled_at: datetime
    shift_code: str
    status: CleaningLogStatus
    task_name: str
    updated_at: datetime
    warning_state: str
    warnings: list[AdminCleaningWarningView]


class AdminCleaningLogListResponse(BaseModel):
    backend_contract: AdminCleaningBackendContractView = Field(
        default_factory=AdminCleaningBackendContractView,
    )
    filter_options: AdminCleaningFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminCleaningLogListItemView]
    metrics: AdminCleaningMetricsView
    page: int
    page_size: int
    total: int


class AdminCleaningOverviewView(BaseModel):
    area_name: str
    branch_id: UUID
    branch_name: str
    cleaning_type: str
    completed_at: datetime | None = None
    created_at: datetime
    created_by_user_id: UUID
    created_by_user_name: str
    equipment_name: str | None = None
    folio: str
    id: UUID
    responsible_user_id: UUID
    responsible_user_name: str
    risk_level: CleaningRiskLevel
    scheduled_at: datetime
    shift_code: str
    started_at: datetime | None = None
    status: CleaningLogStatus
    task_name: str
    warning_state: str


class AdminCleaningLocationAreaView(BaseModel):
    area_name: str
    area_type: str
    branch_code: str
    branch_id: UUID
    branch_name: str
    equipment_name: str | None = None


class AdminCleaningTaskTemplateView(BaseModel):
    cleaning_type: str
    estimated_duration_minutes: int | None = None
    frequency: str | None = None
    method_summary: str | None = None
    required_tools: str | None = None
    risk_level: CleaningRiskLevel
    task_template_id: UUID | None = None
    task_template_name: str | None = None
    task_name: str


class AdminCleaningChecklistItemView(BaseModel):
    display_order: int
    id: UUID
    is_completed: bool
    is_required: bool
    label: str
    notes: str | None = None


class AdminCleaningEvidenceView(BaseModel):
    empty_state: str = "Esta bitacora no tiene evidencia adjunta."
    evidence_note: str | None = None
    files: list[dict[str, str]] = Field(default_factory=list)
    has_evidence: bool = False
    is_supported: bool = True
    upload_supported: bool = False


class AdminCleaningObservationsView(BaseModel):
    cancellation_reason: str | None = None
    corrective_note: str | None = None
    incomplete_required_count: int
    issue_notes: str | None = None
    notes: str | None = None


class AdminCleaningRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    route_hint: str | None = None
    status: str


class AdminCleaningAvailableActionsView(BaseModel):
    can_add_evidence: bool
    can_cancel: bool
    can_complete: bool
    can_create_incident: bool
    can_edit: bool
    can_export: bool
    can_print: bool
    note: str | None = None


class AdminCleaningLogDetailView(BaseModel):
    available_actions: AdminCleaningAvailableActionsView
    checklist: list[AdminCleaningChecklistItemView]
    evidence: AdminCleaningEvidenceView
    location_area: AdminCleaningLocationAreaView
    observations_issues: AdminCleaningObservationsView
    overview: AdminCleaningOverviewView
    related_documents: list[AdminCleaningRelatedDocumentView]
    task_template: AdminCleaningTaskTemplateView
    warnings: list[AdminCleaningWarningView]


class AdminCleaningChecklistItemInput(BaseModel):
    id: UUID | None = None
    is_completed: bool = False
    is_required: bool = True
    label: str = Field(min_length=1, max_length=240)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("label")
    @classmethod
    def _strip_label(cls, value: str) -> str:
        return value.strip()


class AdminCleaningLogCreateRequest(BaseModel):
    area_name: str = Field(min_length=1, max_length=160)
    area_type: str = "OTHER"
    branch_id: UUID
    checklist_items: list[AdminCleaningChecklistItemInput] = Field(default_factory=list)
    cleaning_type: str = "ROUTINE"
    complete_immediately: bool = False
    completed_at: datetime | None = None
    equipment_name: str | None = Field(default=None, max_length=160)
    evidence_note: str | None = Field(default=None, max_length=1000)
    issue_notes: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=1000)
    responsible_user_id: UUID
    risk_level: CleaningRiskLevel = "MEDIUM"
    scheduled_at: datetime
    shift_code: str = "MORNING"
    task_name: str | None = Field(default=None, max_length=160)
    task_template_id: UUID | None = None

    @field_validator("area_name", "task_name")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class AdminCleaningLogCompleteRequest(BaseModel):
    checklist_items: list[AdminCleaningChecklistItemInput] = Field(default_factory=list)
    completed_at: datetime | None = None
    evidence_note: str | None = Field(default=None, max_length=1000)
    issue_notes: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=1000)


class AdminCleaningLogCancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
