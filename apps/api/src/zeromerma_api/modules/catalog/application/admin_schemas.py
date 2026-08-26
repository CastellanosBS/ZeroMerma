from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminProductCaptureMode = Literal["PRODUCT_DIRECT", "CLASS_CAPTURE"]
AdminProductStatus = Literal["active", "inactive"]
AdminProductClassStatus = Literal["active", "inactive"]
AdminProductClassProductPresence = Literal["all", "with_products", "without_products"]
AdminProductKind = Literal["FINISHED_GOOD", "RAW_MATERIAL", "CONSUMABLE", "DISPOSABLE"]
AdminRecipeState = Literal["all", "no_recipe", "active_recipe", "warning"]
AdminRecipeHealthStatus = Literal["healthy", "warning", "incomplete", "no_recipe"]
AdminPriceCaptureMode = Literal["PRODUCT_DIRECT", "CLASS_CAPTURE"]
AdminPriceEntityType = Literal["product", "class"]
AdminPriceHealth = Literal[
    "healthy",
    "missing_price",
    "warning",
    "low_margin",
    "negative_margin",
]
AdminPriceOwner = Literal["product_unit_price", "class_capture_unit_price"]
AdminPriceStatus = Literal["active", "inactive"]
AdminProductReadinessStatus = Literal[
    "ready",
    "requires_attention",
    "incomplete",
    "pending_integration",
    "unknown",
]
AdminProductAvailabilityState = Literal[
    "available",
    "not_available",
    "not_configured",
    "unknown",
]


class AdminProductFilterOptionView(BaseModel):
    id: UUID
    label: str


class AdminProductAvailabilitySummaryView(BaseModel):
    configured_branches_count: int | None = None
    total_branches_count: int | None = None
    state: AdminProductAvailabilityState = "unknown"


class AdminProductBranchAvailabilityView(BaseModel):
    branch_id: UUID
    branch_name: str
    brand_id: UUID | None = None
    brand_name: str | None = None
    state: AdminProductAvailabilityState
    visible_in_pos: bool
    updated_at: datetime | None = None


class AdminProductRelatedReadinessView(BaseModel):
    audit_trail: AdminProductReadinessStatus
    branch_availability: AdminProductReadinessStatus
    inventory: AdminProductReadinessStatus
    pos_visibility: AdminProductReadinessStatus
    price: AdminProductReadinessStatus
    recipe: AdminProductReadinessStatus


class AdminProductReadinessView(BaseModel):
    missing_requirements: list[str]
    related: AdminProductRelatedReadinessView
    status: AdminProductReadinessStatus


class AdminProductView(BaseModel):
    id: UUID
    code: str
    sku: str | None = None
    name: str
    quick_name: str | None = None
    description: str | None = None
    class_id: UUID
    class_name: str
    capture_mode: AdminProductCaptureMode
    status: AdminProductStatus
    product_kind: AdminProductKind = "FINISHED_GOOD"
    unit_price: Decimal
    standard_cost: Decimal | None = None
    currency_code: str
    unit_of_measure: str = "piece"
    brand_id: UUID | None = None
    brand_name: str | None = None
    visible_in_pos: bool
    availability: AdminProductAvailabilitySummaryView
    branch_availability: list[AdminProductBranchAvailabilityView]
    readiness: AdminProductReadinessView
    updated_at: datetime | None = None


class AdminProductMetricsView(BaseModel):
    active_products: int | None = None
    product_direct: int | None = None
    class_capture: int | None = None
    require_attention: int | None = None
    without_branch_availability: int | None = None


class AdminProductFilterOptionsView(BaseModel):
    branches: list[AdminProductFilterOptionView]
    brands: list[AdminProductFilterOptionView]
    classes: list[AdminProductFilterOptionView]


class AdminProductsListResponse(BaseModel):
    items: list[AdminProductView]
    total: int
    page: int
    page_size: int
    metrics: AdminProductMetricsView
    filter_options: AdminProductFilterOptionsView
    is_backend_connected: bool = True


class AdminProductCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    product_class_id: UUID
    unit_price: Decimal = Field(ge=0)
    quick_name: str | None = Field(default=None, max_length=80)
    search_aliases: str | None = None
    status: AdminProductStatus = "active"
    capture_mode: AdminProductCaptureMode | None = None

    @field_validator("code", "name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized


class AdminProductUpdateRequest(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    product_class_id: UUID | None = None
    unit_price: Decimal | None = Field(default=None, ge=0)
    quick_name: str | None = Field(default=None, max_length=80)
    search_aliases: str | None = None
    status: AdminProductStatus | None = None
    capture_mode: AdminProductCaptureMode | None = None

    @field_validator("code", "name")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized


class AdminRecipeInputView(BaseModel):
    id: UUID
    input_product_id: UUID
    input_product_code: str
    input_product_name: str
    unit_of_measure: str
    quantity: Decimal
    standard_cost: Decimal | None = None
    extended_cost: Decimal | None = None
    status: AdminProductStatus


class AdminRecipeView(BaseModel):
    id: UUID
    product_id: UUID
    version_name: str | None = None
    yield_qty: Decimal
    yield_uom: str
    is_active: bool
    input_count: int
    total_batch_cost: Decimal | None = None
    calculated_unit_cost: Decimal | None = None
    created_at: datetime
    updated_at: datetime
    inputs: list[AdminRecipeInputView]


class AdminRecipeCostWarningsView(BaseModel):
    codes: list[str]
    messages: list[str]


class AdminRecipeCostProductSummaryView(BaseModel):
    product_id: UUID
    product_code: str
    product_name: str
    class_id: UUID
    class_name: str
    brand_id: UUID
    brand_name: str
    unit_of_measure: str
    product_status: AdminProductStatus
    product_standard_cost: Decimal | None = None
    product_unit_price: Decimal
    currency_code: str
    active_recipe_id: UUID | None = None
    active_recipe_version_name: str | None = None
    active_recipe_updated_at: datetime | None = None
    recipe_input_count: int
    yield_qty: Decimal | None = None
    yield_uom: str | None = None
    total_batch_cost: Decimal | None = None
    calculated_unit_cost: Decimal | None = None
    cost_variance: Decimal | None = None
    cost_variance_percent: Decimal | None = None
    health_status: AdminRecipeHealthStatus
    warnings: AdminRecipeCostWarningsView
    updated_at: datetime | None = None


class AdminRecipeCostMetricsView(BaseModel):
    with_active_recipe: int
    without_recipe: int
    with_warnings: int
    high_variance: int
    recently_updated: int


class AdminRecipeCostFilterOptionsView(BaseModel):
    brands: list[AdminProductFilterOptionView]
    classes: list[AdminProductFilterOptionView]
    raw_materials: list[AdminProductFilterOptionView]


class AdminRecipeCostsListResponse(BaseModel):
    items: list[AdminRecipeCostProductSummaryView]
    total: int
    page: int
    page_size: int
    metrics: AdminRecipeCostMetricsView
    filter_options: AdminRecipeCostFilterOptionsView
    is_backend_connected: bool = True


class AdminRecipeCostDetailView(BaseModel):
    product: AdminRecipeCostProductSummaryView
    active_recipe: AdminRecipeView | None = None
    recipe_versions: list[AdminRecipeView]


class AdminRecipeInputCreateRequest(BaseModel):
    input_product_id: UUID
    quantity: Decimal = Field(gt=0)


class AdminRecipeCreateRequest(BaseModel):
    product_id: UUID
    version_name: str | None = Field(default=None, max_length=120)
    yield_qty: Decimal = Field(gt=0)
    yield_uom: str = Field(default="piece", min_length=1, max_length=32)
    activate: bool = True
    inputs: list[AdminRecipeInputCreateRequest] = Field(min_length=1)

    @field_validator("yield_uom")
    @classmethod
    def validate_yield_uom(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized


class AdminRecipeDuplicateRequest(BaseModel):
    version_name: str | None = Field(default=None, max_length=120)
    activate: bool = False


class AdminPriceWarningsView(BaseModel):
    codes: list[str]
    messages: list[str]


class AdminPriceRowView(BaseModel):
    entity_id: UUID
    entity_type: AdminPriceEntityType
    entity_name: str
    entity_code: str
    class_id: UUID
    class_name: str
    brand_id: UUID
    brand_name: str
    capture_mode: AdminPriceCaptureMode
    current_price: Decimal | None = None
    currency_code: str
    price_owner: AdminPriceOwner
    standard_cost: Decimal | None = None
    price_cost_delta: Decimal | None = None
    margin_percent: Decimal | None = None
    status: AdminPriceStatus
    health: AdminPriceHealth
    warnings: AdminPriceWarningsView
    related_product_id: UUID | None = None
    related_class_id: UUID
    updated_at: datetime | None = None


class AdminPriceMetricsView(BaseModel):
    total_entities: int
    product_direct: int
    class_capture: int
    missing_or_invalid: int
    high_variance: int
    recently_changed: int


class AdminPriceFilterOptionsView(BaseModel):
    brands: list[AdminProductFilterOptionView]
    classes: list[AdminProductFilterOptionView]


class AdminPricesListResponse(BaseModel):
    items: list[AdminPriceRowView]
    total: int
    page: int
    page_size: int
    metrics: AdminPriceMetricsView
    filter_options: AdminPriceFilterOptionsView
    is_backend_connected: bool = True


class AdminPriceDetailView(BaseModel):
    price: AdminPriceRowView
    history_note: str | None = None


class AdminPriceUpdateRequest(BaseModel):
    price: Decimal = Field(ge=0)


class AdminProductAvailabilityRequest(BaseModel):
    branch_ids: list[UUID] = Field(default_factory=list)
    visible_in_pos: bool = True


class AdminProductClassProductSummaryView(BaseModel):
    id: UUID
    code: str
    name: str
    status: AdminProductStatus
    unit_price: Decimal
    updated_at: datetime | None = None


class AdminProductClassWarningsView(BaseModel):
    codes: list[str]
    messages: list[str]


class AdminProductClassView(BaseModel):
    id: UUID
    brand_id: UUID
    brand_name: str
    code: str
    name: str
    quick_name: str | None = None
    search_aliases: str | None = None
    capture_mode_default: AdminProductCaptureMode
    class_capture_unit_price: Decimal | None = None
    currency_code: str
    display_order: int
    status: AdminProductClassStatus
    is_sellable: bool
    product_count: int
    active_product_count: int
    inactive_product_count: int
    linked_products: list[AdminProductClassProductSummaryView]
    warnings: AdminProductClassWarningsView
    readiness: AdminProductReadinessStatus
    updated_at: datetime | None = None


class AdminProductClassMetricsView(BaseModel):
    total_classes: int
    active_classes: int
    class_capture: int
    product_direct: int
    without_products: int
    with_warnings: int


class AdminProductClassFilterOptionsView(BaseModel):
    brands: list[AdminProductFilterOptionView]


class AdminProductClassesListResponse(BaseModel):
    items: list[AdminProductClassView]
    total: int
    page: int
    page_size: int
    metrics: AdminProductClassMetricsView
    filter_options: AdminProductClassFilterOptionsView
    is_backend_connected: bool = True


class AdminProductClassCreateRequest(BaseModel):
    brand_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    quick_name: str | None = Field(default=None, max_length=80)
    search_aliases: str | None = None
    capture_mode_default: AdminProductCaptureMode
    class_capture_unit_price: Decimal | None = Field(default=None, ge=0)
    currency_code: str = Field(default="MXN", min_length=3, max_length=3)
    display_order: int = Field(default=1000, ge=0)
    status: AdminProductClassStatus = "active"
    is_sellable: bool = True

    @field_validator("code", "name", "currency_code")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized


class AdminProductClassUpdateRequest(BaseModel):
    brand_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    quick_name: str | None = Field(default=None, max_length=80)
    search_aliases: str | None = None
    capture_mode_default: AdminProductCaptureMode | None = None
    class_capture_unit_price: Decimal | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    display_order: int | None = Field(default=None, ge=0)
    status: AdminProductClassStatus | None = None
    is_sellable: bool | None = None

    @field_validator("code", "name", "currency_code")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized
