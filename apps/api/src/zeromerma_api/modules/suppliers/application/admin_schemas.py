from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

AdminSupplierStatus = Literal["ACTIVE", "INACTIVE", "BLOCKED"]
AdminSupplierWarningSeverity = Literal["info", "warning", "critical"]

_SUPPLIER_ACTIVITY_PENDING_NOTE = (
    "Purchase orders, receipts, invoices and supplier payments are pending "
    "canonical backend modules."
)


class AdminSupplierBackendContractView(BaseModel):
    list_endpoint: str = "GET /v1/admin/suppliers"
    detail_endpoint: str = "GET /v1/admin/suppliers/{supplier_id}"
    create_endpoint: str = "POST /v1/admin/suppliers"
    update_endpoint: str = "PATCH /v1/admin/suppliers/{supplier_id}"
    status_endpoint: str = "POST /v1/admin/suppliers/{supplier_id}/status"
    contact_endpoint: str = "POST /v1/admin/suppliers/{supplier_id}/contacts"
    product_endpoint: str = "POST /v1/admin/suppliers/{supplier_id}/products"


class AdminSupplierFilterOptionView(BaseModel):
    id: str
    label: str


class AdminSupplierFilterOptionsView(BaseModel):
    branches: list[AdminSupplierFilterOptionView]
    categories: list[AdminSupplierFilterOptionView]
    product_kinds: list[AdminSupplierFilterOptionView]
    products: list[AdminSupplierFilterOptionView]
    statuses: list[AdminSupplierFilterOptionView]
    warning_states: list[AdminSupplierFilterOptionView]


class AdminSupplierMetricsView(BaseModel):
    active_suppliers: int
    blocked_suppliers: int
    inactive_suppliers: int
    suppliers_with_recent_activity: int
    suppliers_with_warnings: int
    suppliers_without_products: int
    total_suppliers: int


class AdminSupplierWarningView(BaseModel):
    code: str
    message: str
    severity: AdminSupplierWarningSeverity = "warning"


class AdminSupplierListItemView(BaseModel):
    branch_count: int
    category: str
    code: str
    commercial_name: str | None = None
    id: UUID
    legal_name: str
    primary_contact_email: str | None = None
    primary_contact_name: str | None = None
    primary_contact_phone: str | None = None
    product_count: int
    status: AdminSupplierStatus
    tax_id: str | None = None
    terms_summary: str
    updated_at: datetime
    warning_state: AdminSupplierWarningSeverity | None = None
    warnings: list[AdminSupplierWarningView]


class AdminSupplierListResponse(BaseModel):
    backend_contract: AdminSupplierBackendContractView = Field(
        default_factory=AdminSupplierBackendContractView
    )
    filter_options: AdminSupplierFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminSupplierListItemView]
    metrics: AdminSupplierMetricsView
    page: int
    page_size: int
    total: int


class AdminSupplierOverviewView(BaseModel):
    category: str
    code: str
    commercial_name: str | None = None
    created_at: datetime
    id: UUID
    legal_name: str
    readiness_state: AdminSupplierWarningSeverity | None = None
    status: AdminSupplierStatus
    tax_id: str | None = None
    updated_at: datetime


class AdminSupplierFiscalLegalView(BaseModel):
    fiscal_address: str | None = None
    fiscal_regime: str | None = None
    legal_name: str
    notes: str | None = None
    payment_fiscal_email: str | None = None
    tax_id: str | None = None


class AdminSupplierContactView(BaseModel):
    email: str | None = None
    id: UUID
    is_active: bool
    is_primary: bool
    name: str
    notes: str | None = None
    phone: str | None = None
    role: str | None = None
    whatsapp: str | None = None


class AdminSupplierCommercialTermsView(BaseModel):
    credit_days: int
    default_currency: str
    delivery_notes: str | None = None
    lead_time_days: int
    minimum_order_amount: Decimal | None = None
    payment_terms_type: str
    purchase_notes: str | None = None
    summary: str


class AdminSupplierProductAssociationView(BaseModel):
    conversion_factor: Decimal | None = None
    currency: str
    id: UUID
    is_active: bool
    last_known_price: Decimal | None = None
    lead_time_days: int
    minimum_order_qty: Decimal | None = None
    notes: str | None = None
    product_code: str
    product_id: UUID
    product_kind: str
    product_name: str
    purchase_uom: str
    supplier_sku: str | None = None


class AdminSupplierBranchApplicabilityView(BaseModel):
    branch_code: str
    branch_id: UUID
    branch_name: str
    branch_status: str
    delivery_notes: str | None = None
    is_active: bool


class AdminSupplierOperationalActivityView(BaseModel):
    integration_available: bool = False
    notes: str = _SUPPLIER_ACTIVITY_PENDING_NOTE
    open_purchase_orders: int | None = None
    recent_purchase_orders: int | None = None


class AdminSupplierRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    status: str


class AdminSupplierAvailableActionsView(BaseModel):
    can_add_contact: bool = True
    can_add_product: bool = True
    can_block: bool = True
    can_deactivate: bool = True
    can_edit: bool = True


class AdminSupplierDetailView(BaseModel):
    available_actions: AdminSupplierAvailableActionsView
    branch_applicability: list[AdminSupplierBranchApplicabilityView]
    commercial_terms: AdminSupplierCommercialTermsView
    contacts: list[AdminSupplierContactView]
    fiscal_legal: AdminSupplierFiscalLegalView
    operational_activity: AdminSupplierOperationalActivityView
    overview: AdminSupplierOverviewView
    product_associations: list[AdminSupplierProductAssociationView]
    related_documents: list[AdminSupplierRelatedDocumentView]
    warnings: list[AdminSupplierWarningView]


class AdminSupplierContactRequest(BaseModel):
    email: str | None = Field(default=None, max_length=320)
    is_primary: bool = False
    name: str = Field(min_length=1, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)
    phone: str | None = Field(default=None, max_length=40)
    role: str | None = Field(default=None, max_length=120)
    whatsapp: str | None = Field(default=None, max_length=40)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str | None) -> str | None:
        normalized = _blank_to_none(value)
        if normalized is not None and "@" not in normalized:
            raise ValueError("Email must be valid.")
        return normalized

    @field_validator("name")
    @classmethod
    def _normalize_required_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Contact name is required.")
        return normalized

    @field_validator("phone", "role", "whatsapp", "notes")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminSupplierProductRequest(BaseModel):
    conversion_factor: Decimal | None = Field(default=None, gt=0)
    currency: str = Field(default="MXN", min_length=3, max_length=3)
    is_active: bool = True
    last_known_price: Decimal | None = Field(default=None, ge=0)
    lead_time_days: int = Field(default=0, ge=0)
    minimum_order_qty: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    product_id: UUID
    purchase_uom: str | None = Field(default=None, max_length=32)
    supplier_sku: str | None = Field(default=None, max_length=80)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("notes", "purchase_uom", "supplier_sku")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminSupplierBranchRequest(BaseModel):
    branch_id: UUID
    delivery_notes: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    @field_validator("delivery_notes")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminSupplierCreateRequest(BaseModel):
    branch_ids: list[UUID] = Field(default_factory=list)
    category: str = "OTHER"
    code: str | None = Field(default=None, max_length=64)
    commercial_name: str | None = Field(default=None, max_length=200)
    contacts: list[AdminSupplierContactRequest] = Field(default_factory=list)
    credit_days: int = Field(default=0, ge=0)
    default_currency: str = Field(default="MXN", min_length=3, max_length=3)
    delivery_notes: str | None = Field(default=None, max_length=1000)
    fiscal_address: str | None = Field(default=None, max_length=320)
    fiscal_regime: str | None = Field(default=None, max_length=120)
    lead_time_days: int = Field(default=0, ge=0)
    legal_name: str = Field(min_length=1, max_length=200)
    minimum_order_amount: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    payment_fiscal_email: str | None = Field(default=None, max_length=320)
    payment_terms_type: str = "CASH"
    product_relations: list[AdminSupplierProductRequest] = Field(default_factory=list)
    purchase_notes: str | None = Field(default=None, max_length=1000)
    status: AdminSupplierStatus = "ACTIVE"
    tax_id: str | None = Field(default=None, max_length=40)

    @field_validator("category", "payment_terms_type", "status")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("default_currency")
    @classmethod
    def _normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("legal_name")
    @classmethod
    def _normalize_legal_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Supplier legal name is required.")
        return normalized

    @field_validator(
        "code",
        "commercial_name",
        "delivery_notes",
        "fiscal_address",
        "fiscal_regime",
        "notes",
        "payment_fiscal_email",
        "purchase_notes",
        "tax_id",
    )
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class AdminSupplierUpdateRequest(AdminSupplierCreateRequest):
    pass


class AdminSupplierStatusRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=1000)
    status: AdminSupplierStatus

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("notes")
    @classmethod
    def _normalize_text(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
