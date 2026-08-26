from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

IncidentStatus = Literal[
    "OPEN",
    "IN_REVIEW",
    "IN_PROGRESS",
    "WAITING_ACTION",
    "RESOLVED",
    "CLOSED",
    "CANCELLED",
]
IncidentSeverity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
IncidentType = Literal[
    "SANITATION_ISSUE",
    "CLEANING_NON_COMPLIANCE",
    "EQUIPMENT_FAILURE",
    "PRODUCTION_ISSUE",
    "INVENTORY_ISSUE",
    "TRANSFER_ISSUE",
    "WASTE_ISSUE",
    "SAFETY_ISSUE",
    "CUSTOMER_COMPLAINT",
    "PROCESS_DEVIATION",
    "OTHER",
]
IncidentSourceType = Literal[
    "MANUAL",
    "CLEANING_LOG",
    "SANITARY_VERIFICATION",
    "EQUIPMENT",
    "PRODUCTION",
    "INVENTORY",
    "TRANSFER",
    "WASTE_MERMA",
    "CUSTOMER_REPORT",
    "CORRECTION",
]


class AdminIncidentBackendContractView(BaseModel):
    add_follow_up_endpoint: str = "POST /v1/admin/incidents/{incident_id}/follow-ups"
    change_status_endpoint: str = "POST /v1/admin/incidents/{incident_id}/status"
    create_endpoint: str = "POST /v1/admin/incidents"
    detail_endpoint: str = "GET /v1/admin/incidents/{incident_id}"
    evidence_contract: str = (
        "Evidence files are not supported yet; evidence is captured as evidence_note."
    )
    list_endpoint: str = "GET /v1/admin/incidents"
    reopen_endpoint: str = "POST /v1/admin/incidents/{incident_id}/reopen"
    resolve_endpoint: str = "POST /v1/admin/incidents/{incident_id}/resolve"
    update_endpoint: str = "PATCH /v1/admin/incidents/{incident_id}"


class AdminIncidentFilterOptionView(BaseModel):
    id: str
    label: str


class AdminIncidentFilterOptionsView(BaseModel):
    areas: list[AdminIncidentFilterOptionView]
    branches: list[AdminIncidentFilterOptionView]
    due_states: list[AdminIncidentFilterOptionView]
    evidence_states: list[AdminIncidentFilterOptionView]
    incident_types: list[AdminIncidentFilterOptionView]
    related_document_states: list[AdminIncidentFilterOptionView]
    reported_by_users: list[AdminIncidentFilterOptionView]
    responsible_users: list[AdminIncidentFilterOptionView]
    severities: list[AdminIncidentFilterOptionView]
    source_types: list[AdminIncidentFilterOptionView]
    statuses: list[AdminIncidentFilterOptionView]


class AdminIncidentMetricsView(BaseModel):
    high_risk_count: int
    in_progress_count: int
    open_count: int
    overdue_count: int
    resolved_count: int
    sanitary_generated_count: int
    total_count: int
    with_evidence_count: int


class AdminIncidentWarningView(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class AdminIncidentListItemView(BaseModel):
    area_name: str | None = None
    branch_id: UUID
    branch_name: str
    created_at: datetime
    due_at: datetime | None = None
    folio: str
    has_evidence: bool
    id: UUID
    incident_type: IncidentType
    related_document_count: int
    reported_by_user_id: UUID
    reported_by_user_name: str
    responsible_user_id: UUID | None = None
    responsible_user_name: str | None = None
    severity: IncidentSeverity
    source_reference: str | None = None
    source_type: IncidentSourceType
    status: IncidentStatus
    title: str
    updated_at: datetime
    warning_state: str
    warnings: list[AdminIncidentWarningView]


class AdminIncidentListResponse(BaseModel):
    backend_contract: AdminIncidentBackendContractView = Field(
        default_factory=AdminIncidentBackendContractView,
    )
    filter_options: AdminIncidentFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminIncidentListItemView]
    metrics: AdminIncidentMetricsView
    page: int
    page_size: int
    total: int


class AdminIncidentOverviewView(AdminIncidentListItemView):
    resolved_at: datetime | None = None


class AdminIncidentLocationScopeView(BaseModel):
    area_name: str | None = None
    branch_code: str
    branch_id: UUID
    branch_name: str
    equipment_name: str | None = None
    process_name: str | None = None
    product_reference: str | None = None
    production_reference: str | None = None


class AdminIncidentSourceDocumentView(BaseModel):
    empty_state: str = "Esta incidencia fue registrada manualmente y no tiene documento origen."
    route_hint: str | None = None
    source_document_id: UUID | None = None
    source_reference: str | None = None
    source_summary: str | None = None
    source_type: IncidentSourceType


class AdminIncidentDescriptionClassificationView(BaseModel):
    description: str
    food_safety_impact: bool
    incident_type: IncidentType
    notes: str | None = None
    operational_impact: str | None = None
    risk_level: IncidentSeverity
    severity: IncidentSeverity


class AdminIncidentCorrectiveActionView(BaseModel):
    corrective_action: str | None = None
    current_progress: str
    due_at: datetime | None = None
    responsible_user_id: UUID | None = None
    responsible_user_name: str | None = None
    resolution_note: str | None = None
    resolution_result: str | None = None
    resolved_at: datetime | None = None


class AdminIncidentEvidenceView(BaseModel):
    empty_state: str = "Esta incidencia no tiene evidencia adjunta."
    evidence_note: str | None = None
    files: list[dict[str, str]] = Field(default_factory=list)
    has_evidence: bool = False
    is_supported: bool = True
    upload_supported: bool = False


class AdminIncidentRelatedDocumentView(BaseModel):
    document_id: str
    document_type: str
    folio: str
    route_hint: str | None = None
    status: str


class AdminIncidentTimelineItemView(BaseModel):
    label: str
    occurred_at: datetime
    user_name: str | None = None
    note: str | None = None


class AdminIncidentFollowUpView(BaseModel):
    created_at: datetime
    created_by_user_id: UUID
    created_by_user_name: str
    id: UUID
    note: str
    status_change: str | None = None


class AdminIncidentAvailableActionsView(BaseModel):
    can_add_evidence: bool
    can_add_follow_up: bool
    can_assign: bool
    can_cancel: bool
    can_create_corrective_action: bool
    can_create_maintenance: bool
    can_export: bool
    can_mark_in_progress: bool
    can_print: bool
    can_reopen: bool
    can_resolve: bool
    note: str | None = None


class AdminIncidentDetailView(BaseModel):
    available_actions: AdminIncidentAvailableActionsView
    corrective_action: AdminIncidentCorrectiveActionView
    description_classification: AdminIncidentDescriptionClassificationView
    evidence: AdminIncidentEvidenceView
    follow_ups: list[AdminIncidentFollowUpView]
    location_scope: AdminIncidentLocationScopeView
    overview: AdminIncidentOverviewView
    related_documents: list[AdminIncidentRelatedDocumentView]
    source_document: AdminIncidentSourceDocumentView
    timeline: list[AdminIncidentTimelineItemView]
    warnings: list[AdminIncidentWarningView]


class AdminIncidentCreateRequest(BaseModel):
    area_name: str | None = None
    branch_id: UUID
    corrective_action: str | None = None
    description: str
    due_at: datetime | None = None
    equipment_name: str | None = None
    evidence_note: str | None = None
    food_safety_impact: bool = False
    incident_type: IncidentType
    notes: str | None = None
    operational_impact: str | None = None
    process_name: str | None = None
    product_reference: str | None = None
    production_reference: str | None = None
    responsible_user_id: UUID | None = None
    severity: IncidentSeverity
    source_document_id: UUID | None = None
    source_reference: str | None = None
    source_summary: str | None = None
    source_type: IncidentSourceType = "MANUAL"
    title: str

    @field_validator(
        "area_name",
        "corrective_action",
        "description",
        "equipment_name",
        "evidence_note",
        "notes",
        "operational_impact",
        "process_name",
        "product_reference",
        "production_reference",
        "source_reference",
        "source_summary",
        "title",
    )
    @classmethod
    def _strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized if normalized else None


class AdminIncidentUpdateRequest(BaseModel):
    area_name: str | None = None
    corrective_action: str | None = None
    description: str | None = None
    due_at: datetime | None = None
    equipment_name: str | None = None
    evidence_note: str | None = None
    food_safety_impact: bool | None = None
    operational_impact: str | None = None
    process_name: str | None = None
    product_reference: str | None = None
    production_reference: str | None = None
    responsible_user_id: UUID | None = None
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    title: str | None = None


class AdminIncidentFollowUpCreateRequest(BaseModel):
    note: str
    status_change: IncidentStatus | None = None

    @field_validator("note")
    @classmethod
    def _strip_note(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Follow-up note is required.")
        return normalized


class AdminIncidentStatusRequest(BaseModel):
    cancellation_reason: str | None = None
    note: str | None = None
    status: IncidentStatus


class AdminIncidentResolveRequest(BaseModel):
    evidence_note: str | None = None
    resolution_note: str
    result: str
    resolved_at: datetime | None = None

    @field_validator("resolution_note", "result")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Resolution note and result are required.")
        return normalized
