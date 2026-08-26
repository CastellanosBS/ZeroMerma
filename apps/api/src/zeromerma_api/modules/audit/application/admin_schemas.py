from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminAuditFilterOptionView(BaseModel):
    code: str
    label: str


class AdminAuditBackendContractView(BaseModel):
    export_supported: bool = True
    request_context_supported: bool = True
    related_timeline_supported: bool = True
    immutable_events: bool = True
    mutation_supported: bool = False


class AdminAuditFilterOptionsView(BaseModel):
    actions: list[AdminAuditFilterOptionView]
    branches: list[AdminAuditFilterOptionView]
    entity_types: list[AdminAuditFilterOptionView]
    modules: list[AdminAuditFilterOptionView]
    results: list[AdminAuditFilterOptionView]
    sensitivities: list[AdminAuditFilterOptionView]
    severities: list[AdminAuditFilterOptionView]
    source_apps: list[AdminAuditFilterOptionView]
    users: list[AdminAuditFilterOptionView]
    warning_states: list[AdminAuditFilterOptionView]


class AdminAuditSummaryView(BaseModel):
    access_events: int
    active_actors: int
    failed_events: int
    financial_events: int
    inventory_events: int
    sensitive_events: int
    system_events: int
    total_events: int


class AdminAuditEventListItemView(BaseModel):
    id: UUID
    occurred_at: datetime
    actor_user_id: UUID | None = None
    actor_name: str
    actor_email: str | None = None
    actor_type: str
    source_app: str
    module: str
    module_label: str
    action: str
    action_label: str
    entity_type: str
    entity_id: str | None = None
    entity_reference: str | None = None
    result: str
    severity: str
    is_sensitive: bool
    branch_id: UUID | None = None
    branch_name: str | None = None
    workstation_id: str | None = None
    workstation_name: str | None = None
    warning_state: str


class AdminAuditEventsListResponse(BaseModel):
    backend_contract: AdminAuditBackendContractView = Field(
        default_factory=AdminAuditBackendContractView,
    )
    filter_options: AdminAuditFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminAuditEventListItemView]
    metrics: AdminAuditSummaryView
    page: int
    page_size: int
    total: int


class AdminAuditOverviewView(AdminAuditEventListItemView):
    request_id: str | None = None


class AdminAuditActorContextView(BaseModel):
    user_id: UUID | None = None
    full_name: str
    email: str | None = None
    user_status: str | None = None
    roles_summary: str | None = None
    branch_assignments_summary: str | None = None
    can_open_user: bool = False


class AdminAuditEntityContextView(BaseModel):
    entity_type: str
    entity_id: str | None = None
    entity_reference: str | None = None
    branch_id: UUID | None = None
    branch_name: str | None = None
    workstation_id: str | None = None
    workstation_name: str | None = None
    cash_session_id: str | None = None
    related_module: str
    can_open_related_document: bool = False


class AdminAuditChangeItemView(BaseModel):
    field: str
    old_value_masked: str | None = None
    new_value_masked: str | None = None
    change_type: str


class AdminAuditRequestContextView(BaseModel):
    request_id: str | None = None
    correlation_id: str | None = None
    endpoint: str | None = None
    method: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    status_code: int | None = None
    error_code: str | None = None
    duration_ms: int | None = None


class AdminAuditRelatedDocumentView(BaseModel):
    document_type: str
    document_id: str | None = None
    reference: str | None = None
    label: str
    module: str
    can_open: bool = False


class AdminAuditTimelineEventView(BaseModel):
    id: UUID
    occurred_at: datetime
    action: str
    action_label: str
    actor_name: str
    result: str
    is_sensitive: bool


class AdminAuditAvailableActionsView(BaseModel):
    can_copy_event_id: bool = True
    can_copy_correlation_id: bool = False
    can_export_event: bool = True
    can_open_related_document: bool = False
    can_open_user: bool = False
    can_search_related_events: bool = True


class AdminAuditEventDetailView(BaseModel):
    overview: AdminAuditOverviewView
    actor_context: AdminAuditActorContextView
    entity_context: AdminAuditEntityContextView
    change_summary: list[AdminAuditChangeItemView]
    request_context: AdminAuditRequestContextView | None = None
    related_documents: list[AdminAuditRelatedDocumentView]
    timeline_related_events: list[AdminAuditTimelineEventView]
    available_actions: AdminAuditAvailableActionsView


class AdminAuditExportRowView(BaseModel):
    occurred_at: datetime
    actor: str
    actor_email: str | None = None
    source_app: str
    module: str
    action: str
    entity_type: str
    entity_id: str | None = None
    entity_reference: str | None = None
    result: str
    branch_name: str | None = None
    workstation_name: str | None = None
    is_sensitive: bool


class AdminAuditExportResponse(BaseModel):
    format: str = "json"
    generated_at: datetime
    total: int
    rows: list[AdminAuditExportRowView]
