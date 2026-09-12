from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminProductionStatus = Literal["DRAFT", "IN_PROGRESS", "COMPLETED", "CANCELLED"]
AdminProductionWarningSeverity = Literal["info", "warning", "critical"]
AdminProductionInputStatus = Literal["available", "insufficient", "unavailable"]


class AdminProductionBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/production"
    detail_endpoint: str = "GET /v1/admin/production/{production_id}"
    create_endpoint: str = "POST /v1/admin/production"
    update_endpoint: str = "PATCH /v1/admin/production/{production_id}"
    start_endpoint: str = "POST /v1/admin/production/{production_id}/start"
    complete_endpoint: str = "POST /v1/admin/production/{production_id}/complete"
    cancel_endpoint: str = "POST /v1/admin/production/{production_id}/cancel"


class AdminProductionFilterOptionView(BaseModel):
    id: str
    label: str


class AdminProductionFilterOptionsView(BaseModel):
    branches: list[AdminProductionFilterOptionView]
    operators: list[AdminProductionFilterOptionView]
    products: list[AdminProductionFilterOptionView]
    recipes: list[AdminProductionFilterOptionView]
    statuses: list[AdminProductionFilterOptionView]


class AdminProductionMetricsView(BaseModel):
    completed_batches: int
    in_progress_batches: int
    pending_batches: int
    produced_units: Decimal
    total_batches: int
    with_shortages: int
    with_variance: int


class AdminProductionWarningView(BaseModel):
    code: str
    message: str
    severity: AdminProductionWarningSeverity = "warning"


class AdminProductionListItemView(BaseModel):
    actual_output_qty: Decimal | None = None
    branch_id: UUID
    branch_name: str
    completed_at: datetime | None = None
    folio: str
    id: UUID
    operator_name: str
    planned_at: datetime | None = None
    planned_output_qty: Decimal
    product_code: str
    product_id: UUID
    product_name: str
    recipe_id: UUID
    recipe_name: str
    started_at: datetime | None = None
    status: AdminProductionStatus
    variance_percent: Decimal | None = None
    variance_qty: Decimal | None = None
    warning_state: AdminProductionWarningSeverity | None = None
    warnings: list[AdminProductionWarningView]


class AdminProductionListResponse(BaseModel):
    backend_contract: AdminProductionBackendContractView = Field(
        default_factory=AdminProductionBackendContractView
    )
    filter_options: AdminProductionFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminProductionListItemView]
    metrics: AdminProductionMetricsView
    page: int
    page_size: int
    total: int


class AdminProductionOverviewView(BaseModel):
    actual_output_qty: Decimal | None = None
    branch_id: UUID
    branch_name: str
    cancelled_at: datetime | None = None
    completed_at: datetime | None = None
    completed_by_user_id: UUID | None = None
    completed_by_user_name: str | None = None
    created_at: datetime
    created_by_user_id: UUID
    created_by_user_name: str
    folio: str
    id: UUID
    notes: str | None = None
    planned_at: datetime | None = None
    planned_output_qty: Decimal
    started_at: datetime | None = None
    started_by_user_id: UUID | None = None
    started_by_user_name: str | None = None
    status: AdminProductionStatus
    variance_percent: Decimal | None = None
    variance_qty: Decimal | None = None
    variance_reason: str | None = None
    warning_state: AdminProductionWarningSeverity | None = None


class AdminProductionProductRecipeView(BaseModel):
    product_code: str
    product_id: UUID
    product_is_active: bool
    product_kind: str
    product_name: str
    product_unit_of_measure: str
    recipe_id: UUID
    recipe_is_active: bool
    recipe_name: str
    recipe_yield_qty: Decimal
    recipe_yield_uom: str


class AdminProductionInputLineView(BaseModel):
    available_qty: Decimal | None = None
    input_product_code: str
    input_product_id: UUID
    input_product_name: str
    required_qty: Decimal
    shortage_qty: Decimal | None = None
    standard_cost: Decimal | None = None
    status: AdminProductionInputStatus
    uom: str


class AdminProductionActualConsumptionLineView(BaseModel):
    consumed_qty: Decimal | None = None
    difference_qty: Decimal | None = None
    expected_qty: Decimal
    input_product_code: str
    input_product_id: UUID
    input_product_name: str
    uom: str


class AdminProductionOutputYieldView(BaseModel):
    actual_output_qty: Decimal | None = None
    planned_output_qty: Decimal
    uom: str
    variance_percent: Decimal | None = None
    variance_qty: Decimal | None = None
    variance_reason: str | None = None


class AdminProductionWasteScrapView(BaseModel):
    integration_available: bool = False
    notes: str = (
        "Waste/scrap is represented as production yield variance; "
        "dedicated merma documents are pending contract."
    )
    records: list[dict[str, str]] = Field(default_factory=list)


class AdminProductionInventoryMovementView(BaseModel):
    balance_after: Decimal | None = None
    branch_id: UUID
    direction: str
    id: UUID
    location_code: str
    movement_type: str
    product_id: UUID
    quantity: Decimal
    source_document_id: UUID | None = None
    source_document_type: str | None = None
    unit_of_measure: str


class AdminProductionInventoryImpactView(BaseModel):
    integration_available: bool = True
    movements: list[AdminProductionInventoryMovementView]
    notes: str | None = None


class AdminProductionRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    status: str


class AdminProductionAvailableActionsView(BaseModel):
    can_cancel: bool
    can_complete: bool
    can_edit: bool
    can_start: bool
    can_view_movements: bool


class AdminProductionDetailView(BaseModel):
    actual_consumption: list[AdminProductionActualConsumptionLineView]
    available_actions: AdminProductionAvailableActionsView
    inventory_impact: AdminProductionInventoryImpactView
    output_yield: AdminProductionOutputYieldView
    overview: AdminProductionOverviewView
    planned_inputs: list[AdminProductionInputLineView]
    product_recipe: AdminProductionProductRecipeView
    related_documents: list[AdminProductionRelatedDocumentView]
    warnings: list[AdminProductionWarningView]
    waste_scrap: AdminProductionWasteScrapView


class AdminProductionCreateRequest(BaseModel):
    branch_id: UUID
    notes: str | None = None
    planned_at: datetime | None = None
    planned_output_qty: Decimal = Field(gt=0)
    product_id: UUID
    recipe_id: UUID | None = None

    @field_validator("notes")
    @classmethod
    def _blank_notes_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminProductionUpdateRequest(BaseModel):
    notes: str | None = None
    planned_at: datetime | None = None
    planned_output_qty: Decimal | None = Field(default=None, gt=0)
    product_id: UUID | None = None
    recipe_id: UUID | None = None

    @field_validator("notes")
    @classmethod
    def _blank_notes_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminProductionStartRequest(BaseModel):
    notes: str | None = None


class AdminProductionCompleteRequest(BaseModel):
    actual_output_qty: Decimal = Field(ge=0)
    notes: str | None = None
    variance_reason: str | None = None

    @field_validator("variance_reason")
    @classmethod
    def _blank_reason_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminProductionCancelRequest(BaseModel):
    reason: str | None = None
