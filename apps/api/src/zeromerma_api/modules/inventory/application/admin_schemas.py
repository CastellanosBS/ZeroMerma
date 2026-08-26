from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminInventoryLocationCode = Literal["BACKROOM", "COUNTER", "IN_TRANSIT", "WASTE"]
AdminInventoryProductKind = Literal["FINISHED_GOOD", "RAW_MATERIAL", "CONSUMABLE", "DISPOSABLE"]
AdminInventoryProductStatus = Literal["active", "inactive"]
AdminInventoryStockState = Literal["in_stock", "out_of_stock", "low_stock", "negative_stock"]
AdminInventoryWarningSeverity = Literal["info", "warning", "critical"]
AdminInventoryAdjustmentType = Literal["INCREASE", "DECREASE", "SET_COUNTED"]
AdminInventoryMovementDirection = Literal["IN", "OUT"]


class AdminInventoryFilterOptionView(BaseModel):
    id: UUID | str
    label: str


class AdminInventoryBackendContractView(BaseModel):
    adjustment_endpoint: str = "POST /v1/admin/inventory/adjustments"
    detail_endpoint: str = "GET /v1/admin/inventory/{balance_id}"
    list_endpoint: str = "GET /v1/admin/inventory"
    movements_endpoint: str = "GET /v1/admin/inventory/{balance_id}/movements"


class AdminInventoryMetricsView(BaseModel):
    products_with_stock: int
    negative_stock: int
    stale_stock: int
    total_records: int
    estimated_value: Decimal | None = None


class AdminInventoryFilterOptionsView(BaseModel):
    branches: list[AdminInventoryFilterOptionView]
    classes: list[AdminInventoryFilterOptionView]
    locations: list[AdminInventoryFilterOptionView]
    products: list[AdminInventoryFilterOptionView]
    product_kinds: list[AdminInventoryFilterOptionView]


class AdminInventoryWarningView(BaseModel):
    code: str
    message: str
    severity: AdminInventoryWarningSeverity


class AdminInventoryListItemView(BaseModel):
    available_quantity: Decimal | None = None
    balance_id: UUID
    branch_id: UUID
    branch_is_active: bool
    branch_name: str
    class_id: UUID
    class_name: str
    in_transit_quantity: Decimal | None = None
    last_movement_at: datetime | None = None
    location_code: AdminInventoryLocationCode
    location_name: str
    product_code: str
    product_id: UUID
    product_is_active: bool
    product_kind: AdminInventoryProductKind
    product_name: str
    quantity_on_hand: Decimal
    reserved_quantity: Decimal | None = None
    stock_state: AdminInventoryStockState
    unit_of_measure: str
    warning_state: AdminInventoryWarningSeverity | None = None
    warnings: list[AdminInventoryWarningView]


class AdminInventoryListResponse(BaseModel):
    backend_contract: AdminInventoryBackendContractView = Field(default_factory=AdminInventoryBackendContractView)
    filter_options: AdminInventoryFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminInventoryListItemView]
    metrics: AdminInventoryMetricsView
    page: int
    page_size: int
    total: int


class AdminInventoryProductView(BaseModel):
    class_id: UUID
    class_name: str
    code: str
    id: UUID
    is_active: bool
    is_sellable: bool
    name: str
    product_kind: AdminInventoryProductKind
    standard_cost: Decimal | None = None
    unit_of_measure: str


class AdminInventoryBranchLocationView(BaseModel):
    branch_id: UUID
    branch_is_active: bool
    branch_name: str
    location_code: AdminInventoryLocationCode
    location_name: str
    location_model_supported: bool = True


class AdminInventoryStockBreakdownView(BaseModel):
    available_quantity: Decimal | None = None
    estimated_value: Decimal | None = None
    in_transit_quantity: Decimal | None = None
    quantity_on_hand: Decimal
    reserved_quantity: Decimal | None = None
    unit_of_measure: str


class AdminInventoryMovementSummaryView(BaseModel):
    last_adjustment_at: datetime | None = None
    last_inbound_at: datetime | None = None
    last_movement_at: datetime | None = None
    last_outbound_at: datetime | None = None


class AdminInventoryRelatedActionsView(BaseModel):
    can_create_adjustment: bool = True
    can_open_branch: bool = True
    can_open_product: bool = True
    can_start_count: bool = False
    count_endpoint_available: bool = False


class AdminInventoryMovementView(BaseModel):
    balance_after: Decimal | None = None
    branch_id: UUID
    branch_name: str
    direction: AdminInventoryMovementDirection
    id: UUID
    location_code: AdminInventoryLocationCode
    movement_type: str
    notes: str | None = None
    occurred_at: datetime
    operator_name: str | None = None
    product_id: UUID
    quantity: Decimal
    reason: str | None = None
    source_document_id: UUID | None = None
    source_document_type: str | None = None
    unit_of_measure: str


class AdminInventoryDetailView(BaseModel):
    balance_id: UUID
    branch_location: AdminInventoryBranchLocationView
    movement_summary: AdminInventoryMovementSummaryView
    movements: list[AdminInventoryMovementView]
    product: AdminInventoryProductView
    related_actions: AdminInventoryRelatedActionsView
    stock_breakdown: AdminInventoryStockBreakdownView
    stock_state: AdminInventoryStockState
    warnings: list[AdminInventoryWarningView]


class AdminInventoryMovementsResponse(BaseModel):
    items: list[AdminInventoryMovementView]
    page: int
    page_size: int
    total: int


class AdminInventoryAdjustmentRequest(BaseModel):
    adjustment_type: AdminInventoryAdjustmentType
    branch_id: UUID
    location_code: AdminInventoryLocationCode = "BACKROOM"
    notes: str | None = Field(default=None, max_length=500)
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    reason: str = Field(min_length=1, max_length=160)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Adjustment reason is required.")
        return normalized

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminInventoryAdjustmentView(BaseModel):
    id: UUID
    adjustment_type: AdminInventoryAdjustmentType
    balance_id: UUID
    branch_id: UUID
    created_at: datetime
    created_by_user_id: UUID
    location_code: AdminInventoryLocationCode
    new_quantity: Decimal
    notes: str | None = None
    previous_quantity: Decimal
    product_id: UUID
    quantity: Decimal
    reason: str
