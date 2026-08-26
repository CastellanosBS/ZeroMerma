from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView


class AdminReturnCorrectionFilterOptionView(BaseModel):
    id: str
    label: str


class AdminCorrectionsBackendContractView(BaseModel):
    create_endpoint: str | None = None
    detail_endpoint: str
    list_endpoint: str
    print_endpoint: str | None = None


class AdminCorrectionMetricsView(BaseModel):
    corrections_count: int
    total_units_affected: Decimal
    positive_effect_count: int
    negative_effect_count: int
    pending_review_count: int


class AdminCorrectionFilterOptionsView(BaseModel):
    branches: list[AdminReturnCorrectionFilterOptionView]
    correction_types: list[AdminReturnCorrectionFilterOptionView]
    operators: list[AdminReturnCorrectionFilterOptionView]
    reasons: list[AdminReturnCorrectionFilterOptionView]
    statuses: list[AdminReturnCorrectionFilterOptionView]
    target_document_types: list[AdminReturnCorrectionFilterOptionView]


class AdminCorrectionListItemView(BaseModel):
    id: UUID
    folio: str
    original_document_id: UUID
    original_document_folio: str
    original_document_type: str
    correction_type: str
    created_at: datetime
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    workstation_code: str
    operator_id: UUID
    operator_name: str
    reason_code: str
    reason_name: str
    line_count: int
    net_effect_quantity: Decimal
    total_units_affected: Decimal
    net_effect: str
    status: str
    warning_state: str | None = None


class AdminCorrectionsListResponse(BaseModel):
    backend_contract: AdminCorrectionsBackendContractView
    filter_options: AdminCorrectionFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminCorrectionListItemView]
    metrics: AdminCorrectionMetricsView
    page: int
    page_size: int
    total: int


class AdminCorrectionOverviewView(BaseModel):
    id: UUID
    folio: str
    status: str
    created_at: datetime
    committed_at: datetime | None = None
    operator_id: UUID
    operator_name: str
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    workstation_code: str
    correction_type: str
    original_document_id: UUID
    original_document_folio: str
    original_document_type: str
    net_effect: str
    net_effect_quantity: Decimal
    total_units_affected: Decimal


class AdminCorrectionOriginalDocumentView(BaseModel):
    id: UUID
    folio: str
    document_type: str
    status: str
    occurred_at: datetime | None = None
    operator_name: str
    branch_name: str
    workstation_name: str
    route_hint: str | None = None


class AdminCorrectionAffectedLineView(BaseModel):
    id: UUID
    target_line_id: UUID | None = None
    product_name: str
    product_code: str
    product_class_name: str
    product_class_code: str
    original_quantity: Decimal | None = None
    corrected_quantity: Decimal | None = None
    difference_quantity: Decimal
    unit_of_measure_code: str
    notes: str | None = None


class AdminCorrectionReasonNotesView(BaseModel):
    reason_code: str
    reason_name: str
    notes: str | None = None
    audit_summary: AuditSummaryView | None = None


class AdminCorrectionNetEffectView(BaseModel):
    total_units_affected: Decimal
    total_amount_affected: Decimal | None = None
    inventory_effect: str
    cash_effect: str
    net_effect: str


class AdminCorrectionRelatedDocumentView(BaseModel):
    id: str
    document_type: str
    folio: str
    status: str
    occurred_at: datetime | None = None
    route_hint: str | None = None


class AdminCorrectionAvailableActionsView(BaseModel):
    can_create_from_backoffice: bool = False
    can_open_original_document: bool = True
    can_print: bool = False
    creation_note: str


class AdminCorrectionDetailView(BaseModel):
    affected_lines: list[AdminCorrectionAffectedLineView]
    available_actions: AdminCorrectionAvailableActionsView
    backend_contract: AdminCorrectionsBackendContractView
    net_effect: AdminCorrectionNetEffectView
    original_document: AdminCorrectionOriginalDocumentView
    overview: AdminCorrectionOverviewView
    reason_notes: AdminCorrectionReasonNotesView
    related_documents: list[AdminCorrectionRelatedDocumentView]
