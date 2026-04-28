from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class ReturnScopeView(BaseModel):
    code: str
    label: str


class ReturnReasonView(BaseModel):
    code: str
    label: str


class ReturnFilterOptionView(BaseModel):
    value: str
    label: str


class ReturnRefundMethodView(BaseModel):
    code: str
    label: str
    is_enabled: bool
    availability_note: str | None = None


class ReturnControlsView(BaseModel):
    high_refund_amount_threshold: Decimal
    old_sale_days_threshold: int
    high_risk_requires_acknowledgement: bool = True


class ReturnsBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None = None
    branch_brand_key: str
    return_operations_allowed: bool
    default_scope: str
    available_scopes: list[ReturnScopeView]
    return_reasons: list[ReturnReasonView]
    refund_methods: list[ReturnRefundMethodView]
    return_controls: ReturnControlsView


class ReturnSaleSearchItemView(BaseModel):
    id: UUID
    folio: str
    confirmed_at: datetime
    total_amount: Decimal
    currency_code: str
    operator_full_name: str
    item_count: int
    total_quantity: Decimal
    return_count: int
    returned_amount: Decimal
    return_status: str
    has_returnable_quantity: bool


class ReturnsSearchSalesResponse(BaseModel):
    workstation_code: str
    scope: str
    query: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    sales: list[ReturnSaleSearchItemView]


class ReturnHistoryListItemView(BaseModel):
    id: UUID
    folio: str
    original_sale_id: UUID
    original_sale_folio: str
    status: str
    branch_code: str
    branch_name: str
    workstation_code: str
    workstation_name: str
    created_by_user_id: UUID
    created_by_user_full_name: str
    reason_code: str
    reason_name: str
    refund_method_code: str
    total_refund_amount: Decimal
    currency_code: str
    line_count: int
    created_at_utc: datetime


class ReturnsHistoryResponse(BaseModel):
    workstation_code: str
    scope: str
    query: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    created_by_user_id: str | None = None
    reason_code: str | None = None
    available_scopes: list[ReturnScopeView]
    available_users: list[ReturnFilterOptionView]
    available_reasons: list[ReturnFilterOptionView]
    records: list[ReturnHistoryListItemView]


class ReturnProductOptionView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None = None
    display_order: int


class ReturnsClassProductsResponse(BaseModel):
    class_id: UUID
    class_code: str
    class_name: str
    query: str | None = None
    products: list[ReturnProductOptionView]


class ReturnPaymentSummaryView(BaseModel):
    payment_method_code: str
    tendered_amount: Decimal
    applied_amount: Decimal
    change_amount: Decimal
    currency_code: str
    received_at: datetime


class ReturnableSaleLineView(BaseModel):
    id: UUID
    sequence: int
    capture_mode: str
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    product_id: UUID | None = None
    product_code: str | None = None
    product_name: str | None = None
    catalog_code_snapshot: str
    catalog_name_snapshot: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal
    already_returned_quantity: Decimal
    remaining_returnable_quantity: Decimal
    requires_exact_product_selection: bool


class ReturnOriginalSaleDetailResponse(BaseModel):
    id: UUID
    folio: str
    status: str
    confirmed_at: datetime
    branch: BranchSummary
    workstation: WorkstationSummary
    operator: AuthenticatedUser
    cash_session_id: UUID
    currency_code: str
    subtotal_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    return_count: int
    returned_amount: Decimal
    return_status: str
    has_returnable_lines: bool
    lines: list[ReturnableSaleLineView]
    payments: list[ReturnPaymentSummaryView]


class ReturnCommitLineRequest(BaseModel):
    original_sale_line_id: UUID
    returned_quantity: Decimal = Field(gt=Decimal("0.000"), max_digits=12, decimal_places=3)
    disposition_code: str = Field(min_length=1, max_length=32)
    exact_product_id: UUID | None = None


class ReturnCommitRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    original_sale_id: UUID
    reason_code: str = Field(min_length=1, max_length=40)
    high_risk_acknowledged: bool = False
    notes: str | None = None
    refund_method_code: str = Field(min_length=1, max_length=40)
    lines: list[ReturnCommitLineRequest] = Field(min_length=1)


class SaleReturnCommittedLineView(BaseModel):
    id: UUID
    line_number: int
    original_sale_line_id: UUID
    original_catalog_name_snapshot: str
    returned_product_name_snapshot: str
    returned_quantity: Decimal
    refund_unit_price: Decimal
    refund_line_total_amount: Decimal
    disposition_code: str


class SaleReturnDetailResponse(BaseModel):
    id: UUID
    folio: str
    original_sale_id: UUID
    original_sale_folio: str
    branch: BranchSummary
    workstation: WorkstationSummary
    created_by: AuthenticatedUser
    cash_session_id: UUID
    reason_code: str
    reason_name: str
    refund_method_code: str
    currency_code: str
    total_refund_amount: Decimal
    notes: str | None = None
    created_at_utc: datetime
    audit_summary: AuditSummaryView | None = None
    lines: list[SaleReturnCommittedLineView]
