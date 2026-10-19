from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

AdminProductionStatus = Literal[
    "DRAFT", "RELEASED", "PENDING_RECONCILIATION", "COMPLETED", "CANCELLED"
]
AdminProductionWarningSeverity = Literal["info", "warning", "critical"]
AdminProductionInputStatus = Literal["available", "insufficient", "unavailable"]
ProductionPlanStatus = Literal["DRAFT", "RELEASED", "CANCELLED"]
ProductionRunStatus = Literal["OPEN", "PENDING_RECONCILIATION", "COMPLETED", "CANCELLED"]
ProductionReconciliationEvidence = Literal["MANUAL_CONFIRMED"]
ProductionCommandCode = Literal["create", "update", "release", "complete", "cancel"]


class ProductionCommandResultView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    folio: str
    branch_id: UUID
    product_id: UUID
    recipe_id: UUID
    status: AdminProductionStatus
    planned_output_qty: Decimal
    actual_output_qty: Decimal | None
    variance_qty: Decimal | None
    variance_percent: Decimal | None
    created_at: datetime
    updated_at: datetime


class AdminProductionBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/production"
    detail_endpoint: str = "GET /v1/admin/production/{production_id}"
    create_endpoint: str = "POST /v1/admin/production"
    update_endpoint: str = "PATCH /v1/admin/production/{production_id}"
    release_endpoint: str = "POST /v1/admin/production/{production_id}/release"
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
    released_at: datetime | None = None
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
    plan_status: ProductionPlanStatus
    run_id: UUID | None
    run_status: ProductionRunStatus | None
    reconciliation_evidence: ProductionReconciliationEvidence | None
    output_lot_code: str | None = None
    output_expires_at: datetime | None = None
    reconciliation_finish_as: Literal["COMPLETED", "CANCELLED"] | None = None
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
    released_at: datetime | None = None
    released_by_user_id: UUID | None = None
    released_by_user_name: str | None = None
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
    id: UUID
    reservation_id: UUID | None
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
    returned_qty: Decimal | None = None
    waste_qty: Decimal | None = None
    remainder_qty: Decimal | None = None
    reconciliation_reason: str | None = None
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
    integration_available: bool = True
    notes: str = "Only explicitly reconciled input waste is recorded; yield variance is not waste."
    records: list[dict[str, str]] = Field(default_factory=list)


class AdminProductionInventoryMovementView(BaseModel):
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
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
    can_release: bool
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
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    notes: str | None = None
    planned_at: AwareDatetime | None = None
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
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None
    planned_at: AwareDatetime | None = None
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


class AdminProductionReleaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None


class AdminProductionInputReconciliation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_product_id: UUID
    consumed_qty: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    returned_qty: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    waste_qty: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    remainder_qty: Decimal = Field(ge=0, max_digits=12, decimal_places=3)
    reason: str | None = Field(default=None, max_length=500)


class AdminProductionCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_output_qty: Decimal = Field(ge=0)
    output_lot_code: str | None = Field(default=None, min_length=1, max_length=120)
    output_expires_at: AwareDatetime | None = None
    notes: str | None = None
    variance_reason: str | None = None
    confirm_without_differences: bool = False
    inputs: list[AdminProductionInputReconciliation] = Field(default_factory=list)
    finish_as: Literal["COMPLETED", "CANCELLED"] = "COMPLETED"

    @field_validator("variance_reason")
    @classmethod
    def _blank_reason_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminProductionCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = None
    no_physical_effects_confirmed: bool = False
