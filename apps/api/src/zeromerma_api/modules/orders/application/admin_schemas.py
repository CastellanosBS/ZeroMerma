from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class AdminOrderFilterOptionView(BaseModel):
    id: str
    label: str


class AdminOrdersBackendContractView(BaseModel):
    list_endpoint: str
    detail_endpoint: str
    mark_ready_endpoint: str
    deliver_endpoint: str
    cancel_endpoint: str
    create_endpoint: str | None = None
    financial_capture_endpoint: str | None = None


class AdminOrderMetricsView(BaseModel):
    active_orders: int
    ready_orders: int
    due_today: int
    deposits_received_amount: Decimal
    outstanding_balance_amount: Decimal
    canceled_orders: int


class AdminOrderFilterOptionsView(BaseModel):
    branches: list[AdminOrderFilterOptionView]
    cashiers: list[AdminOrderFilterOptionView]
    payment_states: list[AdminOrderFilterOptionView]
    statuses: list[AdminOrderFilterOptionView]
    workstations: list[AdminOrderFilterOptionView]


class AdminOrderListItemView(BaseModel):
    id: UUID
    folio: str
    customer_name: str
    customer_phone: str | None = None
    requested_for_at: datetime | None = None
    status: str
    payment_state: str
    total_amount: Decimal
    advance_amount: Decimal
    remaining_balance_amount: Decimal
    currency_code: str
    branch_id: UUID
    branch_name: str
    workstation_id: UUID
    workstation_name: str
    workstation_code: str
    created_by_user_id: UUID
    created_by_user_full_name: str
    line_count: int
    total_units: Decimal
    cancellation_refund_eligible: bool
    cancellation_refund_amount: Decimal
    warning_state: str | None = None
    created_at_utc: datetime
    updated_at_utc: datetime


class AdminOrdersListResponse(BaseModel):
    backend_contract: AdminOrdersBackendContractView
    filter_options: AdminOrderFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminOrderListItemView]
    metrics: AdminOrderMetricsView
    page: int
    page_size: int
    total: int


class AdminOrderOverviewView(BaseModel):
    id: UUID
    folio: str
    status: str
    payment_state: str
    customer_name: str
    customer_phone: str | None = None
    requested_for_at: datetime | None = None
    branch_id: UUID
    branch_name: str
    total_amount: Decimal
    advance_amount: Decimal
    remaining_balance_amount: Decimal
    currency_code: str
    cancellation_refund_eligible: bool
    cancellation_refund_amount: Decimal
    created_at_utc: datetime
    updated_at_utc: datetime
    delivered_at: datetime | None = None
    canceled_at: datetime | None = None
    cancellation_reason: str | None = None


class AdminOrderCustomerView(BaseModel):
    name: str
    phone: str | None = None
    notes: str | None = None


class AdminOrderLineView(BaseModel):
    id: UUID
    line_number: int
    product_id: UUID
    product_code: str
    product_name: str
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal


class AdminOrderPaymentView(BaseModel):
    id: UUID
    sequence: int
    payment_type: str
    payment_method_code: str
    amount: Decimal
    currency_code: str
    recorded_at_utc: datetime
    recorded_by_user_id: UUID
    recorded_by_user_full_name: str


class AdminOrderTimelineEventView(BaseModel):
    key: str
    label: str
    occurred_at: datetime
    description: str | None = None


class AdminOrderRelatedDocumentView(BaseModel):
    id: str
    document_type: str
    folio: str
    status: str
    occurred_at: datetime | None = None
    amount: Decimal | None = None
    route_hint: str | None = None


class AdminOrderAvailableActionsView(BaseModel):
    can_mark_ready: bool
    can_deliver: bool
    can_cancel: bool
    can_capture_balance: bool
    can_create_from_backoffice: bool
    requires_settlement_on_delivery: bool
    requires_cash_session_for_financial_action: bool
    financial_action_note: str | None = None


class AdminOrderDetailView(BaseModel):
    available_actions: AdminOrderAvailableActionsView
    backend_contract: AdminOrdersBackendContractView
    customer: AdminOrderCustomerView
    lines: list[AdminOrderLineView]
    operational_context: dict[str, str | UUID | None]
    overview: AdminOrderOverviewView
    payments: list[AdminOrderPaymentView]
    related_documents: list[AdminOrderRelatedDocumentView]
    timeline: list[AdminOrderTimelineEventView]


class AdminOrderActionRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=120)
