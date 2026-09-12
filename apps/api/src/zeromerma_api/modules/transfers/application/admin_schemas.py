from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

AdminTransferStatus = Literal[
    "DRAFT",
    "IN_TRANSIT",
    "RECEIVED",
    "RECEIVED_WITH_VARIANCE",
    "CANCELLED",
]
AdminTransferWarningSeverity = Literal["info", "warning", "critical"]
AdminTransferDiscrepancyState = Literal["all", "with_discrepancy", "without_discrepancy"]


class AdminTransferFilterOptionView(BaseModel):
    id: UUID | str
    label: str


class AdminTransferBackendContractView(BaseModel):
    cancel_endpoint: str = "POST /v1/admin/transfers/{transfer_id}/cancel"
    create_endpoint: str = "POST /v1/admin/transfers"
    detail_endpoint: str = "GET /v1/admin/transfers/{transfer_id}"
    dispatch_endpoint: str = "POST /v1/admin/transfers/{transfer_id}/dispatch"
    list_endpoint: str = "GET /v1/admin/transfers"
    receive_endpoint: str = "POST /v1/admin/transfers/{transfer_id}/receive"
    update_endpoint: str = "PATCH /v1/admin/transfers/{transfer_id}"


class AdminTransferMetricsView(BaseModel):
    cancelled_transfers: int
    in_transit_transfers: int
    pending_receipt_transfers: int
    received_transfers: int
    total_transfers: int
    units_in_transit: Decimal
    with_discrepancies: int


class AdminTransferFilterOptionsView(BaseModel):
    branches: list[AdminTransferFilterOptionView]
    operators: list[AdminTransferFilterOptionView]
    products: list[AdminTransferFilterOptionView]
    statuses: list[AdminTransferFilterOptionView]


class AdminTransferWarningView(BaseModel):
    code: str
    message: str
    severity: AdminTransferWarningSeverity


class AdminTransferListItemView(BaseModel):
    created_at: datetime
    destination_branch_code: str
    destination_branch_id: UUID
    destination_branch_name: str
    dispatched_at: datetime | None = None
    folio: str
    has_discrepancy: bool
    id: UUID
    line_count: int
    operator_name: str
    origin_branch_code: str
    origin_branch_id: UUID
    origin_branch_name: str
    received_at: datetime | None = None
    received_unit_count: Decimal | None = None
    requested_unit_count: Decimal
    sent_unit_count: Decimal
    status: AdminTransferStatus
    warning_state: AdminTransferWarningSeverity | None = None
    warnings: list[AdminTransferWarningView]


class AdminTransferListResponse(BaseModel):
    backend_contract: AdminTransferBackendContractView = Field(
        default_factory=AdminTransferBackendContractView
    )
    filter_options: AdminTransferFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminTransferListItemView]
    metrics: AdminTransferMetricsView
    page: int
    page_size: int
    total: int


class AdminTransferOverviewView(BaseModel):
    created_at: datetime
    created_by_user_id: UUID
    created_by_user_name: str
    dispatched_at: datetime | None = None
    folio: str
    id: UUID
    line_count: int
    received_at: datetime | None = None
    received_by_user_id: UUID | None = None
    received_by_user_name: str | None = None
    received_unit_count: Decimal | None = None
    requested_unit_count: Decimal
    sent_unit_count: Decimal
    status: AdminTransferStatus
    has_discrepancy: bool
    notes: str | None = None


class AdminTransferBranchView(BaseModel):
    branch_code: str
    branch_id: UUID
    branch_is_active: bool
    branch_name: str
    timezone: str


class AdminTransferLineView(BaseModel):
    difference: Decimal | None = None
    line_status: str
    notes: str | None = None
    product_code: str
    product_id: UUID
    product_kind: str
    product_name: str
    received_quantity: Decimal | None = None
    requested_quantity: Decimal
    sent_quantity: Decimal
    shipment_line_id: UUID
    unit_of_measure: str
    variance_reason: str | None = None


class AdminTransferReceiptView(BaseModel):
    difference: Decimal | None = None
    discrepancy_reason_required: bool
    expected_total_quantity: Decimal
    has_discrepancy: bool
    receipt_document_id: UUID | None = None
    received_total_quantity: Decimal | None = None
    state: str


class AdminTransferInventoryMovementView(BaseModel):
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


class AdminTransferInventoryImpactView(BaseModel):
    integration_available: bool
    movements: list[AdminTransferInventoryMovementView]
    notes: str | None = None


class AdminTransferRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    status: str


class AdminTransferAvailableActionsView(BaseModel):
    can_cancel: bool
    can_dispatch: bool
    can_edit: bool
    can_receive: bool
    can_view_movements: bool


class AdminTransferDetailView(BaseModel):
    available_actions: AdminTransferAvailableActionsView
    destination: AdminTransferBranchView
    inventory_impact: AdminTransferInventoryImpactView
    lines: list[AdminTransferLineView]
    origin: AdminTransferBranchView
    overview: AdminTransferOverviewView
    receipt: AdminTransferReceiptView
    related_documents: list[AdminTransferRelatedDocumentView]
    warnings: list[AdminTransferWarningView]


class AdminTransferLineInput(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminTransferCreateRequest(BaseModel):
    destination_branch_id: UUID
    lines: list[AdminTransferLineInput] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)
    origin_branch_id: UUID

    @model_validator(mode="after")
    def validate_distinct_branches(self) -> AdminTransferCreateRequest:
        if self.origin_branch_id == self.destination_branch_id:
            raise ValueError("Origin and destination branches must differ.")
        return self

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminTransferUpdateRequest(BaseModel):
    destination_branch_id: UUID | None = None
    lines: list[AdminTransferLineInput] | None = None
    notes: str | None = Field(default=None, max_length=1000)
    origin_branch_id: UUID | None = None

    @model_validator(mode="after")
    def validate_distinct_branches(self) -> AdminTransferUpdateRequest:
        if (
            self.origin_branch_id is not None
            and self.destination_branch_id is not None
            and self.origin_branch_id == self.destination_branch_id
        ):
            raise ValueError("Origin and destination branches must differ.")
        return self

    @field_validator("lines")
    @classmethod
    def validate_lines(
        cls, value: list[AdminTransferLineInput] | None
    ) -> list[AdminTransferLineInput] | None:
        if value is not None and len(value) == 0:
            raise ValueError("Transfer must contain at least one line.")
        return value

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminTransferDispatchRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminTransferReceiptLineInput(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    received_quantity: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=3)
    shipment_line_id: UUID
    variance_reason: str | None = Field(default=None, max_length=120)

    @field_validator("notes", "variance_reason")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminTransferReceiveRequest(BaseModel):
    lines: list[AdminTransferReceiptLineInput] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AdminTransferCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=160)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None
