from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

SanitaryStatus = Literal[
    "SCHEDULED",
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    "REQUIRES_FOLLOW_UP",
]
SanitaryResult = Literal["NOT_EVALUATED", "PASSED", "FAILED", "PARTIAL"]
SanitaryItemResult = Literal["PENDING", "PASSED", "FAILED", "NOT_APPLICABLE"]
SanitaryRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SanitaryEvidenceState = Literal["all", "with_evidence", "without_evidence"]
SanitaryIncidentState = Literal["all", "with_incident", "without_incident"]


class AdminSanitaryBackendContractView(BaseModel):
    cancel_endpoint: str = (
        "POST /v1/admin/sanitary-verifications/{verification_id}/cancel"
    )
    complete_endpoint: str = (
        "POST /v1/admin/sanitary-verifications/{verification_id}/complete"
    )
    create_endpoint: str = "POST /v1/admin/sanitary-verifications"
    detail_endpoint: str = "GET /v1/admin/sanitary-verifications/{verification_id}"
    evidence_contract: str = (
        "Evidence files are not supported yet; evidence is captured as evidence_note."
    )
    incident_contract: str = (
        "Incident creation is not supported yet; failed verifications expose action metadata."
    )
    list_endpoint: str = "GET /v1/admin/sanitary-verifications"
    start_endpoint: str = "POST /v1/admin/sanitary-verifications/{verification_id}/start"
    templates_endpoint: str = "GET /v1/admin/sanitary-verifications/templates"


class AdminSanitaryFilterOptionView(BaseModel):
    id: str
    label: str


class AdminSanitaryTemplateItemView(BaseModel):
    description: str | None = None
    display_order: int
    evidence_required_on_failure: bool
    expected_standard: str | None = None
    id: UUID
    is_required: bool
    label: str
    risk_level: SanitaryRiskLevel


class AdminSanitaryTemplateView(BaseModel):
    area_type: str
    description: str | None = None
    frequency: str
    id: UUID
    is_active: bool
    items: list[AdminSanitaryTemplateItemView]
    name: str
    pass_threshold_percent: int
    process_type: str
    requires_evidence_on_failure: bool
    risk_level: SanitaryRiskLevel


class AdminSanitaryFilterOptionsView(BaseModel):
    area_types: list[AdminSanitaryFilterOptionView]
    areas: list[AdminSanitaryFilterOptionView]
    branches: list[AdminSanitaryFilterOptionView]
    evidence_states: list[AdminSanitaryFilterOptionView]
    incident_states: list[AdminSanitaryFilterOptionView]
    inspectors: list[AdminSanitaryFilterOptionView]
    process_types: list[AdminSanitaryFilterOptionView]
    processes: list[AdminSanitaryFilterOptionView]
    results: list[AdminSanitaryFilterOptionView]
    risk_levels: list[AdminSanitaryFilterOptionView]
    statuses: list[AdminSanitaryFilterOptionView]
    templates: list[AdminSanitaryFilterOptionView]


class AdminSanitaryMetricsView(BaseModel):
    failed_count: int
    high_risk_count: int
    pending_count: int
    passed_count: int
    requires_follow_up_count: int
    total_count: int
    with_evidence_count: int
    with_incident_count: int


class AdminSanitaryWarningView(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class AdminSanitaryVerificationListItemView(BaseModel):
    area_id: UUID | None = None
    area_name: str
    branch_id: UUID
    branch_name: str
    checklist_total_count: int
    completed_at: datetime | None = None
    equipment_id: UUID | None = None
    equipment_name: str | None = None
    failed_count: int
    folio: str
    has_evidence: bool
    has_incident: bool
    id: UUID
    inspector_user_id: UUID
    inspector_user_name: str
    passed_count: int
    process_name: str | None = None
    result: SanitaryResult
    risk_level: SanitaryRiskLevel
    scheduled_at: datetime
    status: SanitaryStatus
    template_name: str
    updated_at: datetime
    warning_state: str
    warnings: list[AdminSanitaryWarningView]


class AdminSanitaryVerificationListResponse(BaseModel):
    backend_contract: AdminSanitaryBackendContractView = Field(
        default_factory=AdminSanitaryBackendContractView,
    )
    filter_options: AdminSanitaryFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminSanitaryVerificationListItemView]
    metrics: AdminSanitaryMetricsView
    page: int
    page_size: int
    total: int


class AdminSanitaryOverviewView(BaseModel):
    area_name: str
    branch_id: UUID
    branch_name: str
    completed_at: datetime | None = None
    created_at: datetime
    created_by_user_id: UUID
    created_by_user_name: str
    equipment_name: str | None = None
    folio: str
    id: UUID
    inspector_user_id: UUID
    inspector_user_name: str
    process_name: str | None = None
    result: SanitaryResult
    risk_level: SanitaryRiskLevel
    scheduled_at: datetime
    started_at: datetime | None = None
    status: SanitaryStatus
    warning_state: str


class AdminSanitaryScopeView(BaseModel):
    area_name: str
    area_type: str
    branch_code: str
    branch_id: UUID
    branch_name: str
    equipment_name: str | None = None
    process_name: str | None = None
    process_type: str


class AdminSanitaryChecklistTemplateView(BaseModel):
    area_type: str
    description: str | None = None
    failed_items: int
    frequency: str | None = None
    passed_items: int
    pass_threshold_percent: int
    process_type: str
    risk_level: SanitaryRiskLevel
    template_id: UUID | None = None
    template_name: str
    total_items: int


class AdminSanitaryChecklistItemView(BaseModel):
    display_order: int
    evidence_required_on_failure: bool
    expected_standard: str | None = None
    id: UUID
    is_required: bool
    label: str
    notes: str | None = None
    result: SanitaryItemResult
    risk_level: SanitaryRiskLevel


class AdminSanitaryScoreResultView(BaseModel):
    max_score: int | None = None
    percentage: int | None = None
    result: SanitaryResult
    score: int | None = None
    threshold_percent: int


class AdminSanitaryEvidenceView(BaseModel):
    empty_state: str = "Esta verificacion no tiene evidencia adjunta."
    evidence_note: str | None = None
    files: list[dict[str, str]] = Field(default_factory=list)
    has_evidence: bool = False
    is_supported: bool = True
    upload_supported: bool = False


class AdminSanitaryFindingsView(BaseModel):
    cancellation_reason: str | None = None
    failed_required_count: int
    findings_notes: str | None = None
    follow_up_due_at: datetime | None = None
    follow_up_required: bool
    notes: str | None = None


class AdminSanitaryRelatedCleaningLogView(BaseModel):
    completed_at: datetime | None = None
    folio: str
    id: UUID
    responsible_user_name: str
    route_hint: str | None = "/admin/bitacoras-limpieza"
    status: str


class AdminSanitaryRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    route_hint: str | None = None
    status: str


class AdminSanitaryAvailableActionsView(BaseModel):
    can_add_evidence: bool
    can_cancel: bool
    can_complete: bool
    can_create_incident: bool
    can_edit: bool
    can_export: bool
    can_print: bool
    can_start: bool
    note: str | None = None


class AdminSanitaryVerificationDetailView(BaseModel):
    available_actions: AdminSanitaryAvailableActionsView
    checklist_results: list[AdminSanitaryChecklistItemView]
    checklist_template: AdminSanitaryChecklistTemplateView
    evidence: AdminSanitaryEvidenceView
    findings_observations: AdminSanitaryFindingsView
    overview: AdminSanitaryOverviewView
    related_cleaning_logs: list[AdminSanitaryRelatedCleaningLogView]
    related_documents: list[AdminSanitaryRelatedDocumentView]
    scope: AdminSanitaryScopeView
    score_result: AdminSanitaryScoreResultView
    warnings: list[AdminSanitaryWarningView]


class AdminSanitaryChecklistItemInput(BaseModel):
    expected_standard: str | None = None
    id: UUID | None = None
    is_required: bool = True
    label: str = Field(min_length=1, max_length=240)
    notes: str | None = None
    result: SanitaryItemResult = "PENDING"
    risk_level: SanitaryRiskLevel = "MEDIUM"
    evidence_required_on_failure: bool = False

    @field_validator("expected_standard", "label", "notes", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminSanitaryVerificationCreateRequest(BaseModel):
    area_name: str = Field(min_length=1, max_length=160)
    area_type: str = "OTHER"
    branch_id: UUID
    checklist_results: list[AdminSanitaryChecklistItemInput] = Field(default_factory=list)
    complete_immediately: bool = False
    completed_at: datetime | None = None
    equipment_name: str | None = None
    evidence_note: str | None = None
    findings_notes: str | None = None
    inspector_user_id: UUID
    notes: str | None = None
    process_name: str | None = None
    process_type: str = "OTHER"
    risk_level: SanitaryRiskLevel = "MEDIUM"
    scheduled_at: datetime
    template_id: UUID | None = None
    template_name: str | None = None

    @field_validator(
        "area_name",
        "equipment_name",
        "evidence_note",
        "findings_notes",
        "notes",
        "process_name",
        "template_name",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminSanitaryVerificationCompleteRequest(BaseModel):
    checklist_results: list[AdminSanitaryChecklistItemInput] = Field(default_factory=list)
    completed_at: datetime | None = None
    evidence_note: str | None = None
    findings_notes: str | None = None
    notes: str | None = None

    @field_validator("evidence_note", "findings_notes", "notes", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminSanitaryVerificationCancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def _strip_reason(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value
