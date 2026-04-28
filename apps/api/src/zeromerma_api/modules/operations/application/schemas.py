from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.operations.domain.constants import OPERATION_BUCKET_COUNTER


class WasteReasonView(BaseModel):
    code: str
    name: str
    display_order: int
    requires_note: bool = False


class WasteControlsView(BaseModel):
    attachment_evidence_supported: bool = False
    high_impact_quantity_threshold: Decimal
    high_impact_requires_acknowledgement: bool = True
    high_impact_requires_note: bool = True
    stock_validated_source_bucket_codes: list[str]


class OperationBranchSummary(BranchSummary):
    brand_key: str | None = None


class TransferDestinationBranchView(BaseModel):
    id: UUID
    code: str
    name: str
    timezone: str
    brand_key: str | None = None


class OperationsBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: OperationBranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    branch_brand_key: str | None = None
    waste_reasons: list[WasteReasonView]
    waste_controls: WasteControlsView
    destination_branches: list[TransferDestinationBranchView]


class OperationsCatalogClassView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None
    display_order: int
    product_count: int


class OperationsCatalogResponse(BaseModel):
    workstation_code: str
    module: str
    query: str | None
    classes: list[OperationsCatalogClassView]


class OperationsCatalogProductView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None
    display_order: int
    unit_price: Decimal
    currency_code: str


class OperationsClassProductsResponse(BaseModel):
    class_id: UUID
    class_code: str
    class_name: str
    module: str
    query: str | None
    products: list[OperationsCatalogProductView]


class OperationCommitLineRequest(BaseModel):
    product_id: UUID
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=500)


class CounterTransferCommitRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    lines: list[OperationCommitLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class WasteCommitRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    source_bucket_code: str = Field(default=OPERATION_BUCKET_COUNTER, min_length=1, max_length=32)
    reason_code: str = Field(min_length=1, max_length=40)
    high_impact_acknowledged: bool = False
    lines: list[OperationCommitLineRequest] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=1000)


class OperationDocumentLineView(BaseModel):
    id: UUID
    line_number: int
    product_id: UUID
    product_code_snapshot: str
    product_name_snapshot: str
    product_class_id: UUID
    product_class_code_snapshot: str
    product_class_name_snapshot: str
    quantity: Decimal
    expected_quantity: Decimal | None
    received_quantity: Decimal | None
    unit_of_measure_code: str
    variance_reason: str | None
    notes: str | None


class OperationDocumentView(BaseModel):
    id: UUID
    folio: str
    document_type: str
    status: str
    source_branch_id: UUID
    source_branch_code: str
    source_branch_name: str
    destination_branch_id: UUID | None
    destination_branch_code: str | None
    destination_branch_name: str | None
    source_bucket_code: str | None
    destination_bucket_code: str | None
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    created_by_user_id: UUID
    created_by_user_email: str
    created_by_user_full_name: str
    reason_code: str | None
    reason_name: str | None
    notes: str | None
    reference_document_id: UUID | None
    created_at_utc: datetime
    committed_at_utc: datetime | None
    audit_summary: AuditSummaryView | None = None
    lines: list[OperationDocumentLineView]


class OperationHistoryScopeView(BaseModel):
    code: str
    label: str


class OperationHistoryFilterOptionView(BaseModel):
    value: str
    label: str


class OperationHistoryListItemView(BaseModel):
    id: UUID
    folio: str
    document_type: str
    status: str
    source_branch_code: str
    source_branch_name: str
    destination_branch_code: str | None
    destination_branch_name: str | None
    source_bucket_code: str | None
    destination_bucket_code: str | None
    workstation_code: str
    workstation_name: str
    created_by_user_id: UUID
    created_by_user_full_name: str
    reason_code: str | None = None
    reason_name: str | None = None
    line_count: int
    total_quantity: Decimal
    created_at_utc: datetime
    committed_at_utc: datetime | None


class OperationHistoryResponse(BaseModel):
    workstation_code: str
    document_type: str
    scope: str
    created_by_user_id: str | None = None
    reason_code: str | None = None
    product_id: str | None = None
    source_bucket_code: str | None = None
    destination_bucket_code: str | None = None
    available_scopes: list[OperationHistoryScopeView]
    available_users: list[OperationHistoryFilterOptionView]
    available_reasons: list[OperationHistoryFilterOptionView]
    available_products: list[OperationHistoryFilterOptionView]
    available_source_buckets: list[OperationHistoryFilterOptionView]
    available_destination_buckets: list[OperationHistoryFilterOptionView]
    records: list[OperationHistoryListItemView]
