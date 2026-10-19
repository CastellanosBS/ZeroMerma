from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.financial_ledger.application.refund_schemas import FinancialRefundView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.tickets.application.receipt_schemas import OperationalReceiptView


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

    @field_validator("payment_method_code")
    @classmethod
    def normalize_payment_method(cls, value: str) -> str:
        return value.strip().upper()


class DeliverCustomerOrderSettlementPaymentRequest(BaseModel):
    payment_method_code: str = Field(min_length=1, max_length=40)
    amount: Decimal = Field(gt=Decimal("0.00"), max_digits=12, decimal_places=2)

    @field_validator("payment_method_code")
    @classmethod
    def normalize_payment_method(cls, value: str) -> str:
        return value.strip().upper()


class CreateCustomerOrderRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID
    customer_name: str = Field(min_length=1, max_length=160)
    customer_phone: str | None = Field(default=None, max_length=32)
    requested_for_at: AwareDatetime | None = None
    notes: str | None = None
    items: list[CreateCustomerOrderItemRequest] = Field(min_length=1)
    advance_amount: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), max_digits=12, decimal_places=2
    )
    advance_payment_method_code: str | None = Field(default=None, max_length=40)
    advance_payments: list[CreateCustomerOrderAdvancePaymentRequest] = Field(default_factory=list)
    quote_fingerprint: str = Field(min_length=64, max_length=64)

    @field_validator("customer_name")
    @classmethod
    def normalize_customer_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Customer name must not be empty.")
        return normalized

    @field_validator("customer_phone", "notes", "advance_payment_method_code")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip() or None
        return normalized

    @field_validator("advance_payment_method_code")
    @classmethod
    def normalize_advance_method(cls, value: str | None) -> str | None:
        return value.upper() if value is not None else None


class OrderActionRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID


class DeliverCustomerOrderRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID
    settlement_amount: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), max_digits=12, decimal_places=2
    )
    settlement_payment_method_code: str | None = Field(default=None, max_length=40)
    settlement_payments: list[DeliverCustomerOrderSettlementPaymentRequest] = Field(
        default_factory=list
    )

    @field_validator("settlement_payment_method_code")
    @classmethod
    def normalize_settlement_method(cls, value: str | None) -> str | None:
        return value.strip().upper() or None if value is not None else None


class CancelCustomerOrderRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    cash_session_id: UUID
    cancellation_reason: str = Field(min_length=4, max_length=240)
    cancellation_responsibility: Literal["CUSTOMER", "MERCHANT"]
    terminal_status: Literal["CANCELED", "EXPIRED", "NO_SHOW"] = "CANCELED"

    @field_validator("cancellation_reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 4:
            raise ValueError("Cancellation reason requires at least four characters.")
        return normalized


OrderCommandCode = Literal["create", "mark-ready", "deliver", "cancel", "pay", "amend"]
AdminOrderCommandCode = Literal["mark-ready", "deliver", "cancel"]


class OrderCommandPaymentView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    sequence: int
    payment_type: Literal["ADVANCE", "SETTLEMENT", "REFUND"]
    payment_method_code: str
    amount: Decimal
    currency_code: str
    workstation_id: UUID
    cash_session_id: UUID
    recorded_at_utc: datetime


class OrderCommandResultView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    folio: str
    status: Literal["PENDING", "READY", "DELIVERED", "CANCELED", "EXPIRED", "NO_SHOW"]
    branch_id: UUID
    currency_code: str
    subtotal_amount: Decimal
    total_amount: Decimal
    advance_amount: Decimal
    remaining_balance_amount: Decimal
    updated_at_utc: datetime
    payments: list[OrderCommandPaymentView]
    financial_refund: FinancialRefundView | None = None


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
    receipt: OperationalReceiptView | None = None
    id: UUID
    sequence: int
    payment_type: str
    payment_method_code: str
    amount: Decimal
    currency_code: str
    cash_session_id: UUID
    workstation_id: UUID
    financial_operation_id: UUID | None = None
    financial_entry_id: UUID | None = None
    recorded_at_utc: datetime
    recorded_by_user_id: UUID
    recorded_by_user_full_name: str


class CustomerOrderDetailResponse(BaseModel):
    financial_refund: FinancialRefundView | None = None
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
    version: int = 0
    production_commit_at: datetime | None = None
    production_committed_at: datetime | None = None
    cancellation_responsibility: str | None = None
    can_amend: bool = False
    can_pay: bool = False
    recognized_revenue_amount: Decimal = Decimal("0.00")
    retained_amount: Decimal = Decimal("0.00")
    unapplied_amount: Decimal = Decimal("0.00")


class OrderQuoteRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    requested_for_at: AwareDatetime
    items: list[CreateCustomerOrderItemRequest] = Field(min_length=1)


class OrderQuoteLineView(BaseModel):
    product_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal


class OrderQuoteView(BaseModel):
    quote_fingerprint: str
    policy_id: UUID
    policy_version: int
    lead_time_minutes: int
    branch_id: UUID
    branch_timezone: str
    requested_for_at: datetime
    production_commit_at: datetime
    currency_code: str
    total_amount: Decimal
    minimum_advance_amount: Decimal
    items: list[OrderQuoteLineView]


class PayCustomerOrderRequest(OrderActionRequest):
    payments: list[CreateCustomerOrderAdvancePaymentRequest] = Field(min_length=1)


class AmendCustomerOrderRequest(OrderQuoteRequest):
    model_config = ConfigDict(str_strip_whitespace=True)
    cash_session_id: UUID
    expected_version: int = Field(ge=1)
    quote_fingerprint: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=4, max_length=240)
    additional_payments: list[CreateCustomerOrderAdvancePaymentRequest] = Field(
        default_factory=list
    )


class OrderPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    lead_time_minutes: int = Field(ge=0, le=525600)
    reason: str = Field(min_length=4, max_length=240)


class OrderPolicyView(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    branch_id: UUID
    version: int
    lead_time_minutes: int
    reason: str
