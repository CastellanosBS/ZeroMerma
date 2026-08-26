from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminReconciliationFilterOptionView(BaseModel):
    id: str
    label: str


class AdminReconciliationBackendContractView(BaseModel):
    create_endpoint: str
    detail_endpoint: str
    evidence_endpoint: str | None = None
    export_endpoint: str | None = None
    list_endpoint: str
    pending_endpoint: str
    resolve_endpoint: str


class AdminReconciliationMetricsView(BaseModel):
    pending_count: int
    reconciled_count: int
    net_difference_amount: Decimal
    shortage_amount: Decimal
    overage_amount: Decimal
    card_terminal_pending_count: int
    cash_pending_count: int
    with_evidence_count: int


class AdminReconciliationFilterOptionsView(BaseModel):
    branches: list[AdminReconciliationFilterOptionView]
    cashiers: list[AdminReconciliationFilterOptionView]
    discrepancy_types: list[AdminReconciliationFilterOptionView]
    evidence_states: list[AdminReconciliationFilterOptionView]
    payment_methods: list[AdminReconciliationFilterOptionView]
    reason_codes: list[AdminReconciliationFilterOptionView]
    source_types: list[AdminReconciliationFilterOptionView]
    statuses: list[AdminReconciliationFilterOptionView]
    workstations: list[AdminReconciliationFilterOptionView]


class AdminReconciliationListItemView(BaseModel):
    id: UUID
    folio: str
    source_type: str
    source_document_id: UUID
    source_reference: str
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    operator_id: UUID | None = None
    operator_name: str
    occurred_at: datetime
    payment_method: str
    expected_amount: Decimal
    actual_amount: Decimal
    difference_amount: Decimal
    difference_direction: str
    status: str
    reason_code: str | None = None
    has_evidence: bool
    warning_state: str
    updated_at: datetime


class AdminPendingDiscrepancyItemView(BaseModel):
    source_type: str
    source_document_id: UUID
    source_reference: str
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    operator_id: UUID | None = None
    operator_name: str
    payment_method: str
    expected_amount: Decimal
    actual_amount: Decimal
    difference_amount: Decimal
    difference_direction: str
    occurred_at: datetime
    suggested_warning_state: str


class AdminReconciliationListResponse(BaseModel):
    backend_contract: AdminReconciliationBackendContractView
    filter_options: AdminReconciliationFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminReconciliationListItemView]
    metrics: AdminReconciliationMetricsView
    page: int
    page_size: int
    pending_discrepancies: list[AdminPendingDiscrepancyItemView]
    total: int


class AdminPendingDiscrepanciesResponse(BaseModel):
    backend_contract: AdminReconciliationBackendContractView
    items: list[AdminPendingDiscrepancyItemView]
    total: int


class AdminReconciliationOverviewView(BaseModel):
    id: UUID
    folio: str
    status: str
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    operator_id: UUID | None = None
    operator_name: str
    source_type: str
    source_document_id: UUID
    source_reference: str
    payment_method: str
    expected_amount: Decimal
    actual_amount: Decimal
    difference_amount: Decimal
    difference_direction: str
    warning_state: str


class AdminReconciliationSourceContextView(BaseModel):
    source_type: str
    source_reference: str
    source_route_hint: str | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    expected_cash_amount: Decimal | None = None
    counted_cash_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    payment_method: str | None = None
    terminal_reference: str | None = None
    external_reported_amount: Decimal | None = None
    operational_payment_category: str | None = None
    refund_original_ticket: str | None = None
    note: str | None = None


class AdminReconciliationDifferenceBreakdownView(BaseModel):
    expected_amount: Decimal
    actual_amount: Decimal
    difference_amount: Decimal
    direction: str
    payment_method: str
    tolerance_status: str
    tolerance_note: str | None = None


class AdminReconciliationExplanationView(BaseModel):
    reason_code: str | None = None
    reason_label: str | None = None
    notes: str | None = None
    responsible_user_id: UUID | None = None
    responsible_user_name: str | None = None
    timestamp: datetime | None = None


class AdminReconciliationEvidenceView(BaseModel):
    is_supported: bool
    has_evidence: bool
    evidence_note: str | None = None
    files: list[str]
    empty_state: str


class AdminReconciliationRelatedDocumentView(BaseModel):
    id: str
    document_type: str
    folio: str
    status: str
    amount: Decimal | None = None
    occurred_at: datetime | None = None
    route_hint: str | None = None


class AdminReconciliationResolutionView(BaseModel):
    status: str
    required_fields: list[str]
    can_resolve: bool
    resolved_by_user_id: UUID | None = None
    resolved_by_user_name: str | None = None
    resolved_at: datetime | None = None
    resolution_reason: str | None = None
    final_notes: str | None = None
    evidence_summary: str | None = None


class AdminReconciliationAvailableActionsView(BaseModel):
    can_copy_folio: bool = True
    can_export_report: bool = False
    can_open_source: bool = True
    can_resolve: bool = False
    can_save_notes: bool = False
    can_attach_evidence: bool = False
    can_void: bool = False
    note: str | None = None


class AdminReconciliationDetailView(BaseModel):
    available_actions: AdminReconciliationAvailableActionsView
    backend_contract: AdminReconciliationBackendContractView
    difference_breakdown: AdminReconciliationDifferenceBreakdownView
    evidence: AdminReconciliationEvidenceView
    explanation_reason: AdminReconciliationExplanationView
    overview: AdminReconciliationOverviewView
    related_documents: list[AdminReconciliationRelatedDocumentView]
    resolution: AdminReconciliationResolutionView
    source_document_context: AdminReconciliationSourceContextView


class AdminReconciliationCreateRequest(BaseModel):
    source_type: str = Field(min_length=1)
    source_document_id: UUID
    reason_code: str = Field(min_length=1)
    notes: str | None = None
    evidence_note: str | None = None
    final_status: str = "RECONCILED"


class AdminReconciliationResolveRequest(BaseModel):
    reason_code: str = Field(min_length=1)
    notes: str | None = None
    evidence_note: str | None = None
