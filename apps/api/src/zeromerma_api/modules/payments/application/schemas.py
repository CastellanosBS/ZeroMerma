from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class OperationalPaymentMethodView(BaseModel):
    code: str
    label: str
    affects_cash_drawer: bool
    is_enabled: bool
    helper_text: str | None = None


class OperationalPaymentCategoryView(BaseModel):
    code: str
    name: str
    display_order: int


class OperationalPaymentScopeView(BaseModel):
    code: str
    label: str


class OperationalPaymentFilterOptionView(BaseModel):
    value: str
    label: str


class PaymentsBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None = None
    branch_brand_key: str
    payment_registration_allowed: bool
    default_scope: str
    available_scopes: list[OperationalPaymentScopeView]
    active_payment_methods: list[OperationalPaymentMethodView]
    active_categories: list[OperationalPaymentCategoryView]


class CreateOperationalPaymentRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    payee_name: str = Field(min_length=1, max_length=160)
    concept: str = Field(min_length=1, max_length=240)
    category_code: str | None = Field(default=None, max_length=40)
    payment_method_code: str = Field(min_length=1, max_length=40)
    total_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=12, decimal_places=2)
    notes: str | None = None


class OperationalPaymentListItemView(BaseModel):
    id: UUID
    folio: str
    status: str
    payee_name: str
    concept: str
    category_code: str | None = None
    category_name: str | None = None
    payment_method_code: str
    total_amount: Decimal
    cash_amount: Decimal
    non_cash_amount: Decimal
    currency_code: str
    created_at_utc: datetime
    operator_full_name: str
    branch_code: str
    branch_name: str
    workstation_code: str
    workstation_name: str
    affects_cash_drawer: bool


class PaymentsListResponse(BaseModel):
    workstation_code: str
    scope: str
    created_by_user_id: str | None = None
    query: str | None = None
    category: str | None = None
    payment_method: str | None = None
    available_users: list[OperationalPaymentFilterOptionView]
    payments: list[OperationalPaymentListItemView]


class OperationalPaymentDetailResponse(BaseModel):
    id: UUID
    folio: str
    status: str
    branch: BranchSummary
    workstation: WorkstationSummary
    created_by: AuthenticatedUser
    active_cash_session_id: UUID
    payee_name: str
    concept: str
    category_code: str | None = None
    category_name: str | None = None
    notes: str | None = None
    payment_method_code: str
    currency_code: str
    total_amount: Decimal
    cash_amount: Decimal
    non_cash_amount: Decimal
    created_at_utc: datetime
    committed_at_utc: datetime
    affects_cash_drawer: bool
    audit_summary: AuditSummaryView | None = None
