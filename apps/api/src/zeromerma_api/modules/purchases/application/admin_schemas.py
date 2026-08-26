from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

AdminPurchaseStatus = Literal["DRAFT", "ORDERED", "PARTIALLY_RECEIVED", "RECEIVED", "CANCELLED"]
AdminPurchaseType = Literal["PURCHASE", "DIRECT_ENTRY"]
AdminPurchaseWarningSeverity = Literal["info", "warning", "critical"]


class AdminPurchaseBackendContractView(BaseModel):
    cancel_endpoint: str = "POST /v1/admin/purchases/{purchase_id}/cancel"
    confirm_endpoint: str = "POST /v1/admin/purchases/{purchase_id}/confirm"
    create_direct_entry_endpoint: str = "POST /v1/admin/purchases/direct-entry"
    create_endpoint: str = "POST /v1/admin/purchases"
    detail_endpoint: str = "GET /v1/admin/purchases/{purchase_id}"
    list_endpoint: str = "GET /v1/admin/purchases"
    receive_endpoint: str = "POST /v1/admin/purchases/{purchase_id}/receive"
    update_endpoint: str = "PATCH /v1/admin/purchases/{purchase_id}"


class AdminPurchaseFilterOptionView(BaseModel):
    id: UUID | str
    label: str


class AdminPurchaseFilterOptionsView(BaseModel):
    branches: list[AdminPurchaseFilterOptionView]
    operators: list[AdminPurchaseFilterOptionView]
    product_kinds: list[AdminPurchaseFilterOptionView]
    products: list[AdminPurchaseFilterOptionView]
    statuses: list[AdminPurchaseFilterOptionView]
    suppliers: list[AdminPurchaseFilterOptionView]


class AdminPurchaseMetricsView(BaseModel):
    active_suppliers_used: int
    confirmed_entries: int
    partially_received: int
    pending_receipt: int
    total_amount: Decimal
    total_documents: int
    with_discrepancies: int


class AdminPurchaseWarningView(BaseModel):
    code: str
    message: str
    severity: AdminPurchaseWarningSeverity


class AdminPurchaseListItemView(BaseModel):
    branch_id: UUID
    branch_name: str
    created_at: datetime
    document_date: datetime
    document_type: AdminPurchaseType
    external_document_number: str | None = None
    folio: str
    has_discrepancy: bool
    id: UUID
    line_count: int
    operator_name: str
    received_at: datetime | None = None
    received_unit_count: Decimal
    status: AdminPurchaseStatus
    supplier_id: UUID
    supplier_name: str
    total_amount: Decimal
    warning_state: AdminPurchaseWarningSeverity | None = None
    warnings: list[AdminPurchaseWarningView]


class AdminPurchaseListResponse(BaseModel):
    backend_contract: AdminPurchaseBackendContractView = Field(
        default_factory=AdminPurchaseBackendContractView
    )
    filter_options: AdminPurchaseFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminPurchaseListItemView]
    metrics: AdminPurchaseMetricsView
    page: int
    page_size: int
    total: int


class AdminPurchaseOverviewView(BaseModel):
    branch_id: UUID
    branch_name: str
    confirmed_at: datetime | None = None
    created_at: datetime
    created_by_user_id: UUID
    created_by_user_name: str
    document_date: datetime
    document_type: AdminPurchaseType
    external_document_number: str | None = None
    external_document_type: str | None = None
    folio: str
    has_discrepancy: bool
    id: UUID
    line_count: int
    notes: str | None = None
    received_at: datetime | None = None
    received_unit_count: Decimal
    status: AdminPurchaseStatus
    supplier_id: UUID
    supplier_name: str
    total_amount: Decimal
    warning_state: AdminPurchaseWarningSeverity | None = None


class AdminPurchaseSupplierContextView(BaseModel):
    commercial_name: str | None = None
    lead_time_days: int
    payment_terms_summary: str
    primary_contact: str | None = None
    status: str
    supplier_id: UUID
    supplier_name: str


class AdminPurchaseBranchView(BaseModel):
    branch_code: str
    branch_id: UUID
    branch_is_active: bool
    branch_name: str
    timezone: str


class AdminPurchaseLineView(BaseModel):
    discrepancy: Decimal
    discrepancy_reason: str | None = None
    line_status: str
    line_total: Decimal
    notes: str | None = None
    ordered_quantity: Decimal
    pending_quantity: Decimal
    product_code: str
    product_id: UUID
    product_kind: str
    product_name: str
    purchase_line_id: UUID
    received_quantity: Decimal
    standard_cost: Decimal | None = None
    supplier_last_known_price: Decimal | None = None
    unit_cost: Decimal
    unit_of_measure: str


class AdminPurchaseReceiptSummaryView(BaseModel):
    expected_quantity: Decimal
    has_discrepancy: bool
    pending_quantity: Decimal
    receipt_count: int
    received_quantity: Decimal
    state: str


class AdminPurchaseCostSummaryView(BaseModel):
    currency: str
    received_total: Decimal
    subtotal: Decimal
    taxes: Decimal | None = None
    total: Decimal


class AdminPurchaseInventoryMovementView(BaseModel):
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


class AdminPurchaseInventoryImpactView(BaseModel):
    integration_available: bool
    movements: list[AdminPurchaseInventoryMovementView]
    notes: str | None = None


class AdminPurchaseRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    status: str


class AdminPurchaseAvailableActionsView(BaseModel):
    can_cancel: bool
    can_confirm: bool
    can_edit: bool
    can_receive: bool
    can_view_movements: bool


class AdminPurchaseDetailView(BaseModel):
    available_actions: AdminPurchaseAvailableActionsView
    cost_summary: AdminPurchaseCostSummaryView
    inventory_impact: AdminPurchaseInventoryImpactView
    lines: list[AdminPurchaseLineView]
    overview: AdminPurchaseOverviewView
    receipt: AdminPurchaseReceiptSummaryView
    receiving_branch: AdminPurchaseBranchView
    related_documents: list[AdminPurchaseRelatedDocumentView]
    supplier_context: AdminPurchaseSupplierContextView
    warnings: list[AdminPurchaseWarningView]


class AdminPurchaseLineInput(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    ordered_quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    product_id: UUID
    unit_cost: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=4)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminPurchaseCreateRequest(BaseModel):
    branch_id: UUID
    confirm_now: bool = False
    document_date: datetime | None = None
    external_document_date: datetime | None = None
    external_document_number: str | None = Field(default=None, max_length=120)
    external_document_type: str | None = Field(default=None, max_length=32)
    lines: list[AdminPurchaseLineInput] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)
    supplier_id: UUID

    @field_validator("external_document_number", "external_document_type", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminPurchaseUpdateRequest(BaseModel):
    branch_id: UUID | None = None
    document_date: datetime | None = None
    external_document_date: datetime | None = None
    external_document_number: str | None = Field(default=None, max_length=120)
    external_document_type: str | None = Field(default=None, max_length=32)
    lines: list[AdminPurchaseLineInput] | None = None
    notes: str | None = Field(default=None, max_length=1000)
    supplier_id: UUID | None = None

    @field_validator("lines")
    @classmethod
    def validate_lines(
        cls, value: list[AdminPurchaseLineInput] | None
    ) -> list[AdminPurchaseLineInput] | None:
        if value is not None and len(value) == 0:
            raise ValueError("Purchase must contain at least one line.")
        return value

    @field_validator("external_document_number", "external_document_type", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminPurchaseDirectEntryLineInput(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    product_id: UUID
    received_quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    unit_cost: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=4)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminPurchaseDirectEntryRequest(BaseModel):
    branch_id: UUID
    document_date: datetime | None = None
    external_document_date: datetime | None = None
    external_document_number: str | None = Field(default=None, max_length=120)
    external_document_type: str | None = Field(default=None, max_length=32)
    lines: list[AdminPurchaseDirectEntryLineInput] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)
    supplier_id: UUID

    @field_validator("external_document_number", "external_document_type", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminPurchaseReceiptLineInput(BaseModel):
    discrepancy_reason: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=500)
    purchase_line_id: UUID
    received_quantity: Decimal = Field(ge=Decimal("0"), max_digits=12, decimal_places=3)
    unit_cost: Decimal | None = Field(
        default=None, ge=Decimal("0"), max_digits=12, decimal_places=4
    )

    @field_validator("discrepancy_reason", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminPurchaseReceiveRequest(BaseModel):
    lines: list[AdminPurchaseReceiptLineInput] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _blank_to_none(value)

    @model_validator(mode="after")
    def validate_unique_lines(self) -> AdminPurchaseReceiveRequest:
        line_ids = [line.purchase_line_id for line in self.lines]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("Receipt lines must be unique.")
        return self


class AdminPurchaseCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=160)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
