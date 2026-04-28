from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class OrderStatusCounterView(BaseModel):
    status: str
    count: int


class OrdersBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None = None
    branch_brand_key: str
    status_counters: list[OrderStatusCounterView]
    can_create_order: bool


class OrdersCatalogClassView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None = None
    display_order: int
    product_count: int


class OrdersCatalogResponse(BaseModel):
    workstation_code: str
    query: str | None = None
    classes: list[OrdersCatalogClassView]


class OrdersCatalogProductView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None = None
    display_order: int
    unit_price: Decimal
    currency_code: str


class OrdersClassProductsResponse(BaseModel):
    class_id: UUID
    class_code: str
    class_name: str
    query: str | None = None
    products: list[OrdersCatalogProductView]


class CreateCustomerOrderItemRequest(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=Decimal("0.000"), max_digits=12, decimal_places=3)


class CreateCustomerOrderAdvancePaymentRequest(BaseModel):
    payment_method_code: str = Field(min_length=1, max_length=40)
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=12, decimal_places=2)


class DeliverCustomerOrderSettlementPaymentRequest(BaseModel):
    payment_method_code: str = Field(min_length=1, max_length=40)
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=12, decimal_places=2)


class CreateCustomerOrderRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    customer_name: str = Field(min_length=1, max_length=160)
    customer_phone: str | None = Field(default=None, max_length=32)
    requested_for_at: datetime | None = None
    notes: str | None = None
    items: list[CreateCustomerOrderItemRequest] = Field(min_length=1)
    advance_amount: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), max_digits=12, decimal_places=2
    )
    advance_payment_method_code: str | None = Field(default=None, max_length=40)
    advance_payments: list[CreateCustomerOrderAdvancePaymentRequest] = Field(default_factory=list)


class OrderActionRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)


class DeliverCustomerOrderRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    settlement_amount: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), max_digits=12, decimal_places=2
    )
    settlement_payment_method_code: str | None = Field(default=None, max_length=40)
    settlement_payments: list[DeliverCustomerOrderSettlementPaymentRequest] = Field(
        default_factory=list
    )


class CancelCustomerOrderRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    cancellation_reason: str = Field(min_length=4, max_length=240)


class CustomerOrderListItemView(BaseModel):
    id: UUID
    folio: str
    status: str
    customer_name: str
    customer_phone: str | None = None
    requested_for_at: datetime | None = None
    created_at_utc: datetime
    line_count: int
    total_units: Decimal
    total_amount: Decimal
    advance_amount: Decimal
    remaining_balance_amount: Decimal
    currency_code: str


class OrdersListResponse(BaseModel):
    workstation_code: str
    status: str | None = None
    query: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    orders: list[CustomerOrderListItemView]


class CustomerOrderItemView(BaseModel):
    id: UUID
    line_number: int
    product_id: UUID
    product_code_snapshot: str
    product_name_snapshot: str
    product_class_id: UUID
    product_class_code_snapshot: str
    product_class_name_snapshot: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal


class CustomerOrderPaymentView(BaseModel):
    id: UUID
    sequence: int
    payment_type: str
    payment_method_code: str
    amount: Decimal
    currency_code: str
    recorded_at_utc: datetime
    recorded_by_user_id: UUID
    recorded_by_user_full_name: str


class CustomerOrderDetailResponse(BaseModel):
    id: UUID
    folio: str
    status: str
    branch: BranchSummary
    workstation_created: WorkstationSummary
    created_by: AuthenticatedUser
    delivered_by: AuthenticatedUser | None = None
    canceled_by: AuthenticatedUser | None = None
    active_cash_session_id: UUID
    customer_name: str
    customer_phone: str | None = None
    requested_for_at: datetime | None = None
    notes: str | None = None
    currency_code: str
    subtotal_amount: Decimal
    total_amount: Decimal
    advance_amount: Decimal
    remaining_balance_amount: Decimal
    delivered_at: datetime | None = None
    canceled_at: datetime | None = None
    cancellation_reason: str | None = None
    cancellation_refund_eligible: bool
    cancellation_refund_amount: Decimal
    created_at_utc: datetime
    updated_at_utc: datetime
    items: list[CustomerOrderItemView]
    payments: list[CustomerOrderPaymentView]
    can_mark_ready: bool
    can_deliver: bool
    can_cancel: bool
    requires_settlement_on_delivery: bool
