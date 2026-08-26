from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class AdminSalesTicketFilterOptionView(BaseModel):
    id: str
    label: str


class AdminSalesTicketPaymentSummaryView(BaseModel):
    payment_method_code: str
    amount: Decimal
    currency_code: str


class AdminSalesTicketMetricsView(BaseModel):
    total_sales_amount: Decimal
    ticket_count: int
    average_ticket_amount: Decimal
    cash_amount: Decimal
    card_amount: Decimal
    tickets_with_returns: int


class AdminSalesTicketFilterOptionsView(BaseModel):
    branches: list[AdminSalesTicketFilterOptionView]
    cashiers: list[AdminSalesTicketFilterOptionView]
    payment_methods: list[AdminSalesTicketFilterOptionView]
    statuses: list[AdminSalesTicketFilterOptionView]
    workstations: list[AdminSalesTicketFilterOptionView]


class AdminSalesTicketBackendContractView(BaseModel):
    detail_endpoint: str
    list_endpoint: str
    reprint_endpoint: str | None = None


class AdminSalesTicketListItemView(BaseModel):
    id: UUID
    folio: str
    sale_id: UUID
    occurred_at: datetime
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    cashier_id: UUID
    cashier_name: str
    item_count: int
    unit_count: Decimal
    total_amount: Decimal
    currency_code: str
    payment_summary: list[AdminSalesTicketPaymentSummaryView]
    payment_methods_label: str
    status: str
    return_status: str
    return_count: int
    has_returns: bool


class AdminSalesTicketsListResponse(BaseModel):
    backend_contract: AdminSalesTicketBackendContractView
    filter_options: AdminSalesTicketFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminSalesTicketListItemView]
    metrics: AdminSalesTicketMetricsView
    page: int
    page_size: int
    total: int


class AdminSalesTicketOverviewView(BaseModel):
    id: UUID
    folio: str
    status: str
    confirmed_at: datetime
    currency_code: str
    subtotal_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    item_count: int
    unit_count: Decimal
    return_count: int
    returned_amount: Decimal
    return_status: str


class AdminSalesTicketOperationalContextView(BaseModel):
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    cashier_id: UUID
    cashier_email: str
    cashier_name: str
    cash_session_id: UUID
    sale_id: UUID
    created_at: datetime
    confirmed_at: datetime


class AdminSalesTicketLineView(BaseModel):
    id: UUID
    sequence: int
    capture_mode: str
    catalog_code: str
    catalog_name: str
    product_id: UUID | None = None
    product_class_id: UUID | None = None
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal
    discount_amount: Decimal
    physical_attribution_status: str


class AdminSalesTicketPaymentView(BaseModel):
    id: UUID
    sequence: int
    payment_method_code: str
    tendered_amount: Decimal
    applied_amount: Decimal
    change_amount: Decimal
    currency_code: str
    received_at: datetime


class AdminSalesTicketRelatedDocumentView(BaseModel):
    id: UUID
    document_type: str
    folio: str
    status: str
    amount: Decimal | None = None
    occurred_at: datetime | None = None
    route_hint: str | None = None


class AdminSalesTicketPrintableView(BaseModel):
    can_reprint: bool
    preview_available: bool
    note: str | None = None


class AdminSalesTicketDetailView(BaseModel):
    overview: AdminSalesTicketOverviewView
    operational_context: AdminSalesTicketOperationalContextView
    lines: list[AdminSalesTicketLineView]
    payments: list[AdminSalesTicketPaymentView]
    related_documents: list[AdminSalesTicketRelatedDocumentView]
    printable_ticket: AdminSalesTicketPrintableView
