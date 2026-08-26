from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView


class AdminReturnCorrectionFilterOptionView(BaseModel):
    id: str
    label: str


class AdminReturnsBackendContractView(BaseModel):
    create_endpoint: str | None = None
    detail_endpoint: str
    list_endpoint: str
    reprint_endpoint: str | None = None


class AdminReturnMetricsView(BaseModel):
    returns_count: int
    refunded_amount: Decimal
    cash_refunded_amount: Decimal
    returned_line_count: int
    pending_review_count: int


class AdminReturnFilterOptionsView(BaseModel):
    branches: list[AdminReturnCorrectionFilterOptionView]
    operators: list[AdminReturnCorrectionFilterOptionView]
    refund_methods: list[AdminReturnCorrectionFilterOptionView]
    statuses: list[AdminReturnCorrectionFilterOptionView]


class AdminReturnListItemView(BaseModel):
    id: UUID
    folio: str
    original_sale_id: UUID
    original_ticket_folio: str
    created_at: datetime
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    workstation_code: str
    operator_id: UUID
    operator_name: str
    returned_line_count: int
    refunded_amount: Decimal
    refund_method: str
    status: str
    warning_state: str | None = None


class AdminReturnsListResponse(BaseModel):
    backend_contract: AdminReturnsBackendContractView
    filter_options: AdminReturnFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminReturnListItemView]
    metrics: AdminReturnMetricsView
    page: int
    page_size: int
    total: int


class AdminReturnOverviewView(BaseModel):
    id: UUID
    folio: str
    status: str
    created_at: datetime
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    workstation_code: str
    operator_id: UUID
    operator_name: str
    total_refund_amount: Decimal
    refund_method: str
    reason_code: str
    reason_name: str
    notes: str | None = None
    is_partial_return: bool


class AdminReturnOriginalTicketView(BaseModel):
    sale_id: UUID
    folio: str
    status: str
    sale_date: datetime
    total_amount: Decimal
    payment_methods_label: str
    cashier_name: str
    branch_name: str
    workstation_name: str
    cash_session_id: UUID


class AdminReturnedLineView(BaseModel):
    id: UUID
    original_sale_line_id: UUID
    product_name: str
    product_code: str
    product_class_name: str
    product_class_code: str
    original_quantity: Decimal
    returned_quantity: Decimal
    unit_price: Decimal
    refund_amount: Decimal
    disposition_code: str
    line_status: str


class AdminReturnRefundImpactView(BaseModel):
    refund_method: str
    refund_amount: Decimal
    cash_session_id: UUID
    cash_impact_amount: Decimal
    linked_cash_movement_id: UUID | None = None
    currency_code: str


class AdminReturnRelatedDocumentView(BaseModel):
    id: str
    document_type: str
    folio: str
    status: str
    amount: Decimal | None = None
    occurred_at: datetime | None = None
    route_hint: str | None = None


class AdminReturnAvailableActionsView(BaseModel):
    can_create_from_backoffice: bool = False
    can_open_original_ticket: bool = True
    can_reprint: bool = False
    creation_note: str


class AdminReturnDetailView(BaseModel):
    audit_summary: AuditSummaryView | None = None
    available_actions: AdminReturnAvailableActionsView
    backend_contract: AdminReturnsBackendContractView
    original_ticket: AdminReturnOriginalTicketView
    overview: AdminReturnOverviewView
    refund_impact: AdminReturnRefundImpactView
    related_documents: list[AdminReturnRelatedDocumentView]
    returned_lines: list[AdminReturnedLineView]
