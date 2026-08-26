from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminWasteStatus = Literal["COMMITTED", "CANCELLED"]
AdminWasteImpactLevel = Literal["normal", "high"]
AdminWasteEvidenceState = Literal["all", "with_evidence", "without_evidence"]
AdminWasteWarningSeverity = Literal["info", "warning", "critical"]
AdminWasteLocationCode = Literal["BACKROOM", "COUNTER", "IN_TRANSIT"]
AdminWasteProductKind = Literal["FINISHED_GOOD", "RAW_MATERIAL", "CONSUMABLE", "DISPOSABLE"]


class AdminWasteBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/waste"
    detail_endpoint: str = "GET /v1/admin/waste/{waste_id}"
    create_endpoint: str = "POST /v1/admin/waste"
    reasons_endpoint: str = "GET /v1/admin/waste/reasons"
    inventory_movement_contract: str = "Confirmed waste creates WASTE_RECORD inventory movement."


class AdminWasteFilterOptionView(BaseModel):
    id: str
    label: str


class AdminWasteReasonView(BaseModel):
    code: str
    label: str
    display_order: int
    requires_note: bool
    requires_evidence: bool = False
    high_impact_default: bool = False


class AdminWasteFilterOptionsView(BaseModel):
    branches: list[AdminWasteFilterOptionView]
    classes: list[AdminWasteFilterOptionView]
    evidence_states: list[AdminWasteFilterOptionView]
    impact_levels: list[AdminWasteFilterOptionView]
    locations: list[AdminWasteFilterOptionView]
    operators: list[AdminWasteFilterOptionView]
    product_kinds: list[AdminWasteFilterOptionView]
    products: list[AdminWasteFilterOptionView]
    reasons: list[AdminWasteReasonView]
    statuses: list[AdminWasteFilterOptionView]


class AdminWasteMetricsView(BaseModel):
    contaminated_or_damaged: int
    evidence_records: int
    estimated_value: Decimal | None = None
    expired_records: int
    high_impact_records: int
    total_quantity: Decimal
    total_records: int


class AdminWasteWarningView(BaseModel):
    code: str
    message: str
    severity: AdminWasteWarningSeverity = "warning"


class AdminWasteListItemView(BaseModel):
    branch_id: UUID
    branch_name: str
    created_at: datetime
    estimated_value: Decimal | None = None
    folio: str
    has_evidence: bool = False
    id: UUID
    impact_level: AdminWasteImpactLevel
    line_count: int
    location_code: AdminWasteLocationCode
    location_name: str
    operator_name: str
    product_code: str
    product_id: UUID
    product_kind: AdminWasteProductKind
    product_name: str
    quantity: Decimal
    reason_code: str
    reason_label: str
    status: AdminWasteStatus
    uom: str
    warning_state: AdminWasteWarningSeverity | None = None
    warnings: list[AdminWasteWarningView]


class AdminWasteListResponse(BaseModel):
    backend_contract: AdminWasteBackendContractView = Field(default_factory=AdminWasteBackendContractView)
    filter_options: AdminWasteFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminWasteListItemView]
    metrics: AdminWasteMetricsView
    page: int
    page_size: int
    total: int


class AdminWasteOverviewView(BaseModel):
    branch_id: UUID
    branch_name: str
    confirmed_at: datetime | None = None
    created_at: datetime
    folio: str
    has_evidence: bool = False
    id: UUID
    impact_level: AdminWasteImpactLevel
    location_code: AdminWasteLocationCode
    location_name: str
    notes: str | None = None
    operator_id: UUID
    operator_name: str
    quantity: Decimal
    reason_code: str
    reason_label: str
    status: AdminWasteStatus
    uom: str
    warning_state: AdminWasteWarningSeverity | None = None
    workstation_code: str | None = None
    workstation_name: str | None = None


class AdminWasteProductInventoryContextView(BaseModel):
    branch_id: UUID
    branch_name: str
    class_id: UUID
    class_name: str
    current_stock: Decimal | None = None
    product_code: str
    product_id: UUID
    product_is_active: bool
    product_kind: AdminWasteProductKind
    product_name: str
    stock_after: Decimal | None = None
    stock_before: Decimal | None = None
    uom: str


class AdminWasteLineView(BaseModel):
    estimated_value: Decimal | None = None
    line_number: int
    product_code: str
    product_id: UUID
    product_kind: AdminWasteProductKind
    product_name: str
    quantity: Decimal
    uom: str


class AdminWasteReasonClassificationView(BaseModel):
    category: str
    description: str | None = None
    label: str
    requires_evidence: bool = False
    requires_note: bool


class AdminWasteEvidenceView(BaseModel):
    attachment_supported: bool = False
    evidence_items: list[dict[str, str]] = Field(default_factory=list)
    notes: str | None = None


class AdminWasteInventoryMovementView(BaseModel):
    balance_after: Decimal | None = None
    direction: str
    id: UUID
    location_code: str
    movement_type: str
    product_id: UUID
    quantity: Decimal
    source_document_id: UUID | None = None
    source_document_type: str | None = None
    unit_of_measure: str


class AdminWasteInventoryImpactView(BaseModel):
    integration_available: bool = True
    movements: list[AdminWasteInventoryMovementView]
    notes: str | None = None


class AdminWasteRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    status: str


class AdminWasteAvailableActionsView(BaseModel):
    can_create_correction: bool = True
    can_edit: bool = False
    can_open_inventory_movement: bool = True
    can_print: bool = False


class AdminWasteDetailView(BaseModel):
    available_actions: AdminWasteAvailableActionsView
    evidence: AdminWasteEvidenceView
    inventory_impact: AdminWasteInventoryImpactView
    lines: list[AdminWasteLineView]
    overview: AdminWasteOverviewView
    product_inventory_context: AdminWasteProductInventoryContextView
    reason_classification: AdminWasteReasonClassificationView
    related_documents: list[AdminWasteRelatedDocumentView]
    warnings: list[AdminWasteWarningView]


class AdminWasteCreateRequest(BaseModel):
    branch_id: UUID
    location_code: AdminWasteLocationCode = "BACKROOM"
    notes: str | None = Field(default=None, max_length=1000)
    product_id: UUID
    quantity: Decimal = Field(gt=0)
    reason_code: str = Field(min_length=1, max_length=40)

    @field_validator("notes")
    @classmethod
    def _blank_notes_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("reason_code")
    @classmethod
    def _normalize_reason_code(cls, value: str) -> str:
        return value.strip().upper()
