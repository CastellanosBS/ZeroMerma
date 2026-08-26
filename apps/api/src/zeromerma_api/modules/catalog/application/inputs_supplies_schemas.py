from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminInputSupplyKind = Literal["RAW_MATERIAL", "CONSUMABLE", "DISPOSABLE"]
AdminInputSupplyStatus = Literal["active", "inactive"]
AdminInputSupplyStockState = Literal[
    "in_stock",
    "low_stock",
    "negative_stock",
    "out_of_stock",
    "no_inventory",
]
AdminInputSupplyWarningSeverity = Literal["info", "warning", "critical"]
AdminInputSupplyWarningState = Literal["ok", "info", "warning", "critical"]
AdminInputSupplyRecipeUsageState = Literal["all", "used", "unused"]
AdminInputSupplyCostState = Literal["all", "with_cost", "missing_cost"]


class AdminInputSupplyBackendContractView(BaseModel):
    add_supplier_relation_endpoint: str = "POST /v1/admin/inputs-supplies/{product_id}/suppliers"
    detail_endpoint: str = "GET /v1/admin/inputs-supplies/{product_id}"
    list_endpoint: str = "GET /v1/admin/inputs-supplies"
    create_endpoint: str = "POST /v1/admin/inputs-supplies"
    status_endpoint: str = "POST /v1/admin/inputs-supplies/{product_id}/status"
    update_endpoint: str = "PATCH /v1/admin/inputs-supplies/{product_id}"
    update_supplier_relation_endpoint: str = (
        "PATCH /v1/admin/inputs-supplies/{product_id}/suppliers/{relation_id}"
    )


class AdminInputSupplyFilterOptionView(BaseModel):
    id: str
    label: str


class AdminInputSupplyWarningView(BaseModel):
    code: str
    message: str
    severity: AdminInputSupplyWarningSeverity


class AdminInputSupplyMetricsView(BaseModel):
    active_raw_materials: int
    active_consumables: int
    active_disposables: int
    low_stock: int
    missing_cost: int
    used_in_recipes: int
    without_supplier: int


class AdminInputSupplyFilterOptionsView(BaseModel):
    classes: list[AdminInputSupplyFilterOptionView]
    cost_states: list[AdminInputSupplyFilterOptionView]
    product_kinds: list[AdminInputSupplyFilterOptionView]
    recipe_usage_states: list[AdminInputSupplyFilterOptionView]
    statuses: list[AdminInputSupplyFilterOptionView]
    stock_states: list[AdminInputSupplyFilterOptionView]
    suppliers: list[AdminInputSupplyFilterOptionView]
    usage_types: list[AdminInputSupplyFilterOptionView]
    warning_states: list[AdminInputSupplyFilterOptionView]


class AdminInputSupplyListItemView(BaseModel):
    base_uom: str
    category_id: UUID
    category_name: str
    code: str
    id: UUID
    is_active: bool
    is_inventory_tracked: bool
    is_purchasable: bool
    last_movement_at: datetime | None = None
    last_purchase_cost: Decimal | None = None
    name: str
    primary_supplier_name: str | None = None
    product_kind: AdminInputSupplyKind
    purchase_uom: str | None = None
    recipe_usage_count: int
    standard_cost: Decimal | None = None
    stock_state: AdminInputSupplyStockState
    supplier_count: int
    updated_at: datetime
    warning_state: AdminInputSupplyWarningState
    warnings: list[AdminInputSupplyWarningView]


class AdminInputSupplyListResponse(BaseModel):
    backend_contract: AdminInputSupplyBackendContractView = Field(
        default_factory=AdminInputSupplyBackendContractView
    )
    filter_options: AdminInputSupplyFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminInputSupplyListItemView]
    metrics: AdminInputSupplyMetricsView
    page: int
    page_size: int
    total: int


class AdminInputSupplyOverviewView(BaseModel):
    base_uom: str
    category_id: UUID
    category_name: str
    code: str
    created_at: datetime
    id: UUID
    is_active: bool
    is_inventory_tracked: bool
    is_purchasable: bool
    last_purchase_cost: Decimal | None = None
    name: str
    product_kind: AdminInputSupplyKind
    purchase_uom: str | None = None
    readiness_state: AdminInputSupplyWarningState
    standard_cost: Decimal | None = None
    updated_at: datetime
    warning_state: AdminInputSupplyWarningState


class AdminInputSupplyClassificationView(BaseModel):
    kind: AdminInputSupplyKind
    notes: str | None = None
    status: AdminInputSupplyStatus
    storage_group: str | None = None
    usage_type: str | None = None


class AdminInputSupplyUnitsConversionView(BaseModel):
    base_uom: str
    consumption_uom: str
    conversion_factor: Decimal | None = None
    minimum_purchase_quantity: Decimal | None = None
    purchase_uom: str | None = None
    unit_conversion_supported: bool


class AdminInputSupplySupplierRelationView(BaseModel):
    conversion_factor: Decimal | None = None
    currency: str
    id: UUID
    is_active: bool
    last_known_price: Decimal | None = None
    lead_time_days: int
    minimum_order_qty: Decimal | None = None
    notes: str | None = None
    purchase_uom: str | None = None
    supplier_id: UUID
    supplier_name: str
    supplier_sku: str | None = None


class AdminInputSupplyCostView(BaseModel):
    cost_updated_at: datetime | None = None
    currency: str
    last_purchase_cost: Decimal | None = None
    standard_cost: Decimal | None = None
    supplier_price_max: Decimal | None = None
    supplier_price_min: Decimal | None = None
    warnings: list[AdminInputSupplyWarningView]


class AdminInputSupplyInventoryBranchView(BaseModel):
    branch_id: UUID
    branch_name: str
    last_movement_at: datetime | None = None
    quantity_on_hand: Decimal
    stock_state: AdminInputSupplyStockState


class AdminInputSupplyInventoryStatusView(BaseModel):
    integration_available: bool
    last_movement_at: datetime | None = None
    minimum_stock: Decimal | None = None
    preferred_order_quantity: Decimal | None = None
    reorder_point: Decimal | None = None
    stock_by_branch: list[AdminInputSupplyInventoryBranchView]
    stock_state: AdminInputSupplyStockState
    total_stock: Decimal | None = None
    unit_of_measure: str


class AdminInputSupplyRecipeUsageView(BaseModel):
    finished_product_code: str
    finished_product_id: UUID
    finished_product_name: str
    quantity: Decimal
    recipe_id: UUID
    recipe_version_name: str | None = None
    unit_of_measure: str


class AdminInputSupplyRelatedDocumentView(BaseModel):
    document_id: UUID | str
    document_type: str
    folio: str
    status: str


class AdminInputSupplyAvailableActionsView(BaseModel):
    can_add_supplier: bool = True
    can_deactivate: bool = True
    can_edit: bool = True
    can_open_inventory: bool = True
    can_open_product: bool = True
    can_open_recipes: bool = True


class AdminInputSupplyDetailView(BaseModel):
    available_actions: AdminInputSupplyAvailableActionsView = Field(
        default_factory=AdminInputSupplyAvailableActionsView
    )
    classification: AdminInputSupplyClassificationView
    cost: AdminInputSupplyCostView
    inventory_status: AdminInputSupplyInventoryStatusView
    overview: AdminInputSupplyOverviewView
    procurement_warnings: list[AdminInputSupplyWarningView]
    recipe_usage: list[AdminInputSupplyRecipeUsageView]
    related_documents: list[AdminInputSupplyRelatedDocumentView]
    suppliers: list[AdminInputSupplySupplierRelationView]
    units_conversion: AdminInputSupplyUnitsConversionView


class AdminInputSupplySupplierRelationRequest(BaseModel):
    conversion_factor: Decimal | None = Field(default=None, gt=0)
    currency: str = Field(default="MXN", min_length=3, max_length=3)
    is_active: bool = True
    last_known_price: Decimal | None = Field(default=None, ge=0)
    lead_time_days: int = Field(default=0, ge=0)
    minimum_order_qty: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    purchase_uom: str | None = Field(default=None, max_length=32)
    supplier_id: UUID
    supplier_sku: str | None = Field(default=None, max_length=80)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("notes", "purchase_uom", "supplier_sku")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminInputSupplyCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    is_active: bool = True
    is_inventory_tracked: bool = True
    is_purchasable: bool = True
    minimum_stock: Decimal | None = Field(default=None, ge=0)
    name: str = Field(min_length=1, max_length=160)
    preferred_order_quantity: Decimal | None = Field(default=None, ge=0)
    procurement_notes: str | None = Field(default=None, max_length=1000)
    product_class_id: UUID
    product_kind: AdminInputSupplyKind
    purchase_conversion_factor: Decimal | None = Field(default=None, gt=0)
    purchase_uom: str | None = Field(default=None, max_length=32)
    reorder_point: Decimal | None = Field(default=None, ge=0)
    standard_cost: Decimal | None = Field(default=None, ge=0)
    supplier_relations: list[AdminInputSupplySupplierRelationRequest] = Field(default_factory=list)
    unit_of_measure: str = Field(min_length=1, max_length=32)
    usage_type: str | None = Field(default=None, max_length=40)

    @field_validator("code", "name", "unit_of_measure")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank.")
        return normalized

    @field_validator("procurement_notes", "purchase_uom", "usage_type")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminInputSupplyUpdateRequest(AdminInputSupplyCreateRequest):
    pass


class AdminInputSupplyStatusRequest(BaseModel):
    is_active: bool
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def _normalize_notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
