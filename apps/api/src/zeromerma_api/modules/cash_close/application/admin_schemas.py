from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AdminCashCutFilterOptionView(BaseModel):
    id: str
    label: str


class AdminCashCutBackendContractView(BaseModel):
    detail_endpoint: str
    export_endpoint: str | None = None
    list_endpoint: str
    print_endpoint: str | None = None


class AdminCashCutMetricsView(BaseModel):
    closed_cuts_count: int
    net_sales_amount: Decimal
    expected_cash_amount: Decimal
    counted_cash_amount: Decimal
    net_difference_amount: Decimal
    cuts_with_difference_count: int
    pending_close_count: int
    operational_payments_amount: Decimal


class AdminCashCutFilterOptionsView(BaseModel):
    branches: list[AdminCashCutFilterOptionView]
    cashiers: list[AdminCashCutFilterOptionView]
    difference_states: list[AdminCashCutFilterOptionView]
    payment_methods: list[AdminCashCutFilterOptionView]
    statuses: list[AdminCashCutFilterOptionView]
    workstations: list[AdminCashCutFilterOptionView]


class AdminCashCutListItemView(BaseModel):
    id: UUID
    folio: str
    cash_session_id: UUID
    close_id: UUID | None = None
    opened_at: datetime
    closed_at: datetime | None = None
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    cashier_id: UUID
    cashier_name: str
    opening_amount: Decimal
    expected_cash_amount: Decimal
    counted_cash_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    total_sales_amount: Decimal
    payment_methods_summary: str
    status: str
    difference_state: str
    warning_state: str
    warning_count: int
    has_refunds: bool
    has_operational_payments: bool


class AdminCashCutsListResponse(BaseModel):
    backend_contract: AdminCashCutBackendContractView
    filter_options: AdminCashCutFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminCashCutListItemView]
    metrics: AdminCashCutMetricsView
    page: int
    page_size: int
    total: int


class AdminCashCutOverviewView(BaseModel):
    id: UUID
    folio: str
    cash_session_id: UUID
    close_id: UUID | None = None
    status: str
    branch_id: UUID
    branch_name: str
    branch_code: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    cashier_id: UUID
    cashier_name: str
    opened_at: datetime
    closed_at: datetime | None = None
    opening_amount: Decimal
    closing_notes: str | None = None
    total_duration_minutes: int | None = None
    warning_state: str


class AdminCashCutExpectedVsCountedView(BaseModel):
    opening_amount: Decimal
    cash_sales_amount: Decimal
    cash_refunds_amount: Decimal
    cash_operational_payments_amount: Decimal
    cash_operational_discounts_amount: Decimal
    cash_adjustments_amount: Decimal
    expected_cash_amount: Decimal
    counted_cash_amount: Decimal | None = None
    difference_amount: Decimal | None = None
    difference_state: str
    is_counted_cash_available: bool
    note: str | None = None


class AdminCashCutPaymentBreakdownView(BaseModel):
    payment_method_code: str
    currency_code: str
    sales_amount: Decimal
    refund_amount: Decimal
    operational_payment_amount: Decimal
    operational_discount_amount: Decimal
    expected_amount: Decimal | None = None
    counted_amount: Decimal | None = None
    variance_amount: Decimal | None = None
    net_amount: Decimal
    is_counted_supported: bool


class AdminCashCutTicketItemView(BaseModel):
    ticket_id: UUID
    folio: str
    occurred_at: datetime
    total_amount: Decimal
    currency_code: str
    payment_method_summary: str
    cashier_name: str
    status: str
    route_hint: str


class AdminCashCutRefundItemView(BaseModel):
    id: UUID
    folio: str
    original_ticket_folio: str
    amount: Decimal
    payment_method_code: str
    occurred_at: datetime
    operator_name: str
    reason_name: str
    status: str
    route_hint: str


class AdminCashCutOperationalPaymentItemView(BaseModel):
    id: UUID
    folio: str
    category_code: str | None = None
    category_name: str | None = None
    amount: Decimal
    cash_amount: Decimal
    payment_method_code: str
    occurred_at: datetime
    operator_name: str
    notes: str | None = None
    route_hint: str


class AdminCashCutCorrectionAdjustmentItemView(BaseModel):
    id: UUID
    folio: str
    document_type: str
    amount: Decimal | None = None
    occurred_at: datetime | None = None
    operator_name: str | None = None
    notes: str | None = None
    route_hint: str | None = None


class AdminCashCutDenominationLineView(BaseModel):
    denomination: Decimal
    quantity: int
    subtotal: Decimal


class AdminCashCutDenominationCountView(BaseModel):
    is_supported: bool
    lines: list[AdminCashCutDenominationLineView]
    total_counted: Decimal | None = None
    note: str | None = None


class AdminCashCutReconciliationStatusView(BaseModel):
    status: str
    reconciled_at: datetime | None = None
    reconciled_by_name: str | None = None
    related_document_id: UUID | None = None
    route_hint: str | None = None
    note: str | None = None


class AdminCashCutTimelineItemView(BaseModel):
    event_code: str
    label: str
    occurred_at: datetime
    actor_name: str | None = None
    summary: str | None = None


class AdminCashCutRelatedDocumentView(BaseModel):
    id: str
    document_type: str
    folio: str
    status: str
    amount: Decimal | None = None
    occurred_at: datetime | None = None
    route_hint: str | None = None


class AdminCashCutAvailableActionsView(BaseModel):
    can_copy_folio: bool = True
    can_export_report: bool = False
    can_print_report: bool = False
    can_open_tickets: bool = True
    can_open_returns: bool = True
    can_open_operational_payments: bool = True
    can_remote_close: bool = False
    remote_close_note: str | None = None


class AdminCashCutDetailView(BaseModel):
    available_actions: AdminCashCutAvailableActionsView
    audit_timeline: list[AdminCashCutTimelineItemView]
    backend_contract: AdminCashCutBackendContractView
    corrections_adjustments: list[AdminCashCutCorrectionAdjustmentItemView]
    denomination_count: AdminCashCutDenominationCountView
    expected_vs_counted: AdminCashCutExpectedVsCountedView
    included_tickets: list[AdminCashCutTicketItemView]
    operational_payments: list[AdminCashCutOperationalPaymentItemView]
    overview: AdminCashCutOverviewView
    payment_breakdown: list[AdminCashCutPaymentBreakdownView]
    reconciliation_status: AdminCashCutReconciliationStatusView
    related_documents: list[AdminCashCutRelatedDocumentView]
    returns_refunds: list[AdminCashCutRefundItemView]
