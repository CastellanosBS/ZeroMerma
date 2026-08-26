from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AdminCashFlowFilterOptionView(BaseModel):
    id: str
    label: str


class AdminCashFlowBackendContractView(BaseModel):
    detail_endpoint: str
    export_endpoint: str | None = None
    list_endpoint: str
    trend_endpoint: str | None = None


class AdminCashFlowSummaryView(BaseModel):
    inflows_total: Decimal
    outflows_total: Decimal
    net_total: Decimal
    cash_total: Decimal
    card_total: Decimal
    operational_payments_total: Decimal
    refunds_total: Decimal
    pending_reconciliation_total: Decimal
    difference_total: Decimal


class AdminCashFlowTrendPointView(BaseModel):
    date: date
    inflows: Decimal
    outflows: Decimal
    net: Decimal


class AdminCashFlowFilterOptionsView(BaseModel):
    branches: list[AdminCashFlowFilterOptionView]
    categories: list[AdminCashFlowFilterOptionView]
    directions: list[AdminCashFlowFilterOptionView]
    operators: list[AdminCashFlowFilterOptionView]
    payment_methods: list[AdminCashFlowFilterOptionView]
    reconciliation_states: list[AdminCashFlowFilterOptionView]
    source_types: list[AdminCashFlowFilterOptionView]
    workstations: list[AdminCashFlowFilterOptionView]


class AdminCashFlowMovementListItemView(BaseModel):
    id: str
    occurred_at: datetime
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    operator_id: UUID | None = None
    operator_name: str
    direction: str
    source_type: str
    source_document_id: UUID
    source_reference: str
    category: str | None = None
    payment_method: str
    amount: Decimal
    currency: str
    reconciliation_status: str
    warning_state: str


class AdminCashFlowListResponse(BaseModel):
    backend_contract: AdminCashFlowBackendContractView
    filter_options: AdminCashFlowFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminCashFlowMovementListItemView]
    page: int
    page_size: int
    summary: AdminCashFlowSummaryView
    total: int
    trend: list[AdminCashFlowTrendPointView]


class AdminCashFlowMovementOverviewView(BaseModel):
    id: str
    occurred_at: datetime
    direction: str
    amount: Decimal
    currency: str
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
    category: str | None = None
    warning_state: str


class AdminCashFlowSourceContextView(BaseModel):
    source_type: str
    source_reference: str
    source_route_hint: str | None = None
    source_status: str | None = None
    source_total_amount: Decimal | None = None
    source_payment_method: str | None = None
    cash_session_id: UUID | None = None
    cash_cut_id: UUID | None = None
    cash_cut_folio: str | None = None
    cash_cut_route_hint: str | None = None
    original_ticket_folio: str | None = None
    concept: str | None = None
    expected_cash_amount: Decimal | None = None
    counted_cash_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    note: str | None = None


class AdminCashFlowFinancialClassificationView(BaseModel):
    direction: str
    source_category: str | None = None
    payment_method: str
    cash_impact: Decimal
    card_impact: Decimal
    net_effect: Decimal
    affects_cash_drawer: bool
    affects_bank_settlement: bool
    note: str | None = None


class AdminCashFlowReconciliationView(BaseModel):
    status: str
    reconciliation_id: UUID | None = None
    reconciliation_folio: str | None = None
    unresolved_amount: Decimal | None = None
    reason_label: str | None = None
    route_hint: str | None = None
    message: str


class AdminCashFlowRelatedDocumentView(BaseModel):
    id: str
    document_type: str
    folio: str
    status: str
    amount: Decimal | None = None
    occurred_at: datetime | None = None
    route_hint: str | None = None


class AdminCashFlowAvailableActionsView(BaseModel):
    can_copy_reference: bool = True
    can_export: bool = False
    can_open_cash_cut: bool = False
    can_open_reconciliation: bool = False
    can_open_source: bool = True
    note: str | None = None


class AdminCashFlowMovementDetailView(BaseModel):
    available_actions: AdminCashFlowAvailableActionsView
    backend_contract: AdminCashFlowBackendContractView
    financial_classification: AdminCashFlowFinancialClassificationView
    overview: AdminCashFlowMovementOverviewView
    reconciliation: AdminCashFlowReconciliationView
    related_documents: list[AdminCashFlowRelatedDocumentView]
    source_document_context: AdminCashFlowSourceContextView
