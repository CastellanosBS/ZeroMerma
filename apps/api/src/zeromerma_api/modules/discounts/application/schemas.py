from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class OperationalDiscountMethodView(BaseModel):
    code: str
    label: str
    affects_cash_drawer: bool
    is_enabled: bool
    helper_text: str | None = None


class OperationalDiscountCategoryView(BaseModel):
    code: str
    name: str
    display_order: int


class OperationalDiscountScopeView(BaseModel):
    code: str
    label: str


class OperationalDiscountFilterOptionView(BaseModel):
    value: str
    label: str


class DiscountControlsView(BaseModel):
    high_value_amount_threshold: Decimal
    high_value_requires_acknowledgement: bool = True


class DiscountsBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None = None
    branch_brand_key: str
    discount_registration_allowed: bool
    default_scope: str
    available_scopes: list[OperationalDiscountScopeView]
    active_discount_methods: list[OperationalDiscountMethodView]
    active_categories: list[OperationalDiscountCategoryView]
    discount_controls: DiscountControlsView


class CreateOperationalDiscountRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    subject_name: str = Field(min_length=1, max_length=160)
    concept: str = Field(min_length=1, max_length=240)
    category_code: str | None = Field(default=None, max_length=40)
    payment_method_code: str = Field(min_length=1, max_length=40)
    total_amount: Decimal = Field(gt=Decimal("0.00"), max_digits=12, decimal_places=2)
    high_value_acknowledged: bool = False
    notes: str | None = None


class OperationalDiscountListItemView(BaseModel):
    id: UUID
    folio: str
    status: str
    subject_name: str
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


class DiscountsListResponse(BaseModel):
    workstation_code: str
    scope: str
    created_by_user_id: str | None = None
    query: str | None = None
    category: str | None = None
    payment_method: str | None = None
    available_users: list[OperationalDiscountFilterOptionView]
    discounts: list[OperationalDiscountListItemView]


class OperationalDiscountDetailResponse(BaseModel):
    id: UUID
    folio: str
    status: str
    branch: BranchSummary
    workstation: WorkstationSummary
    created_by: AuthenticatedUser
    active_cash_session_id: UUID
    subject_name: str
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


AdminCommercialDiscountType = Literal["PERCENTAGE", "FIXED_AMOUNT"]
AdminCommercialDiscountScope = Literal["GLOBAL", "PRODUCT", "CLASS"]
AdminCommercialDiscountStatus = Literal["ACTIVE", "INACTIVE", "ARCHIVED"]
AdminCommercialDiscountValidityStatus = Literal["current", "upcoming", "expired", "not_scheduled"]
AdminCommercialDiscountHealth = Literal["healthy", "warning", "invalid", "expired"]


class AdminCommercialDiscountFilterOptionView(BaseModel):
    id: UUID
    label: str


class AdminCommercialDiscountWarningsView(BaseModel):
    codes: list[str]
    messages: list[str]


class AdminCommercialDiscountMetricsView(BaseModel):
    total_discounts: int
    active_discounts: int
    upcoming_discounts: int
    expired_discounts: int
    with_warnings: int
    product_scoped: int
    class_scoped: int


class AdminCommercialDiscountFilterOptionsView(BaseModel):
    brands: list[AdminCommercialDiscountFilterOptionView]
    classes: list[AdminCommercialDiscountFilterOptionView]
    products: list[AdminCommercialDiscountFilterOptionView]


class AdminCommercialDiscountBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/discounts"
    detail_endpoint: str = "GET /v1/admin/discounts/{id}"
    create_endpoint: str = "POST /v1/admin/discounts"
    update_endpoint: str = "PATCH /v1/admin/discounts/{id}"
    duplicate_endpoint: str = "POST /v1/admin/discounts/{id}/duplicate"


class AdminCommercialDiscountView(BaseModel):
    id: UUID
    code: str | None = None
    name: str
    description: str | None = None
    discount_type: AdminCommercialDiscountType
    target_scope: AdminCommercialDiscountScope
    target_id: UUID | None = None
    target_code: str | None = None
    target_name: str | None = None
    target_status: str | None = None
    target_class_id: UUID | None = None
    target_class_name: str | None = None
    brand_id: UUID | None = None
    brand_name: str | None = None
    value: Decimal
    currency_code: str
    base_price: Decimal | None = None
    preview_price: Decimal | None = None
    status: AdminCommercialDiscountStatus
    validity_status: AdminCommercialDiscountValidityStatus
    valid_from_utc: datetime | None = None
    valid_to_utc: datetime | None = None
    priority: int
    is_pos_eligible: bool
    health: AdminCommercialDiscountHealth
    warnings: AdminCommercialDiscountWarningsView
    created_at: datetime
    updated_at: datetime


class AdminCommercialDiscountsListResponse(BaseModel):
    backend_contract: AdminCommercialDiscountBackendContractView
    is_backend_connected: bool = True
    items: list[AdminCommercialDiscountView]
    total: int
    page: int
    page_size: int
    metrics: AdminCommercialDiscountMetricsView
    filter_options: AdminCommercialDiscountFilterOptionsView


class AdminCommercialDiscountCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    discount_type: AdminCommercialDiscountType
    target_scope: AdminCommercialDiscountScope
    target_id: UUID | None = None
    brand_id: UUID | None = None
    value: Decimal = Field(gt=Decimal("0.0000"), max_digits=12, decimal_places=4)
    currency_code: str = Field(default="MXN", min_length=3, max_length=3)
    valid_from_utc: datetime | None = None
    valid_to_utc: datetime | None = None
    priority: int = Field(default=1000, ge=0)
    is_pos_eligible: bool = True
    status: AdminCommercialDiscountStatus = "INACTIVE"

    @model_validator(mode="after")
    def validate_shape(self) -> AdminCommercialDiscountCreateRequest:
        if self.discount_type == "PERCENTAGE" and self.value > Decimal("100"):
            raise ValueError("Percentage discounts must be less than or equal to 100.")
        if self.discount_type == "FIXED_AMOUNT" and len(self.currency_code.strip()) != 3:
            raise ValueError("Fixed discounts require a three-letter currency code.")
        if self.target_scope in {"PRODUCT", "CLASS"} and self.target_id is None:
            raise ValueError("Target entity is required for product or class discount scope.")
        if self.target_scope == "GLOBAL" and self.target_id is not None:
            raise ValueError("Global discounts cannot reference a product or class target.")
        if self.valid_from_utc and self.valid_to_utc and self.valid_from_utc >= self.valid_to_utc:
            raise ValueError("Validity range must end after it starts.")
        return self


class AdminCommercialDiscountUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=64)
    description: str | None = None
    discount_type: AdminCommercialDiscountType | None = None
    target_scope: AdminCommercialDiscountScope | None = None
    target_id: UUID | None = None
    brand_id: UUID | None = None
    value: Decimal | None = Field(
        default=None, gt=Decimal("0.0000"), max_digits=12, decimal_places=4
    )
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    valid_from_utc: datetime | None = None
    valid_to_utc: datetime | None = None
    priority: int | None = Field(default=None, ge=0)
    is_pos_eligible: bool | None = None
    status: AdminCommercialDiscountStatus | None = None

    @model_validator(mode="after")
    def validate_values(self) -> AdminCommercialDiscountUpdateRequest:
        if (
            self.discount_type == "PERCENTAGE"
            and self.value is not None
            and self.value > Decimal("100")
        ):
            raise ValueError("Percentage discounts must be less than or equal to 100.")
        if self.valid_from_utc and self.valid_to_utc and self.valid_from_utc >= self.valid_to_utc:
            raise ValueError("Validity range must end after it starts.")
        return self


class AdminCommercialDiscountDuplicateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    code: str | None = Field(default=None, max_length=64)
