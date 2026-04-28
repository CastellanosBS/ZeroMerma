from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from zeromerma_api.modules.audit.application.schemas import AuditSummaryView
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.operations.application.schemas import (
    OperationDocumentView,
    TransferDestinationBranchView,
)


class CorrectionReasonView(BaseModel):
    code: str
    name: str
    display_order: int


class CorrectionControlsView(BaseModel):
    high_impact_quantity_threshold: Decimal
    high_impact_requires_acknowledgement: bool = True


class CorrectionHistoryScopeView(BaseModel):
    code: str
    label: str


class CorrectionHistoryFilterOptionView(BaseModel):
    value: str
    label: str


class CorrectionBootstrapResponse(BaseModel):
    user: AuthenticatedUser
    branch: BranchSummary
    workstation: WorkstationSummary
    local_timestamp: datetime
    current_open_cash_session: CashSessionView | None = None
    branch_brand_key: str
    correction_operations_allowed: bool
    correction_reasons: list[CorrectionReasonView]
    correction_controls: CorrectionControlsView
    destination_branches: list[TransferDestinationBranchView]


class CorrectionSearchDocumentView(BaseModel):
    id: UUID
    folio: str
    document_type: str
    status: str
    display_title: str
    source_branch_code: str
    source_branch_name: str
    destination_branch_code: str | None
    destination_branch_name: str | None
    workstation_code: str
    workstation_name: str
    committed_at_utc: datetime | None
    correction_count: int


class CorrectionSearchResponse(BaseModel):
    workstation_code: str
    document_type: str | None
    query: str | None
    documents: list[CorrectionSearchDocumentView]


class CorrectionProductOptionView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None = None
    product_class_id: UUID
    product_class_code: str
    product_class_name: str
    display_order: int


class CorrectionsProductsResponse(BaseModel):
    workstation_code: str
    query: str | None
    products: list[CorrectionProductOptionView]


class AppliedCorrectionLineSummaryView(BaseModel):
    line_number: int
    target_line_id: UUID | None
    product_code_snapshot: str
    product_name_snapshot: str
    delta_quantity: Decimal


class AppliedCorrectionSummaryView(BaseModel):
    id: UUID
    folio: str
    reason_code: str
    reason_name: str
    status: str
    committed_at_utc: datetime | None
    line_count: int
    corrected_destination_branch_code: str | None = None
    corrected_destination_branch_name: str | None = None
    audit_summary: AuditSummaryView | None = None
    lines: list[AppliedCorrectionLineSummaryView] = Field(default_factory=list)


class CorrectionTargetDetailResponse(BaseModel):
    document_title: str
    target_document: OperationDocumentView
    is_correctable: bool
    blocking_reason: str | None
    applied_corrections: list[AppliedCorrectionSummaryView]


class CorrectionCommitLineRequest(BaseModel):
    target_line_id: UUID | None = None
    product_id: UUID
    delta_quantity: Decimal = Field(max_digits=12, decimal_places=3)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("delta_quantity")
    @classmethod
    def validate_non_zero_delta(cls, value: Decimal) -> Decimal:
        if value == 0:
            raise ValueError("Correction delta quantity cannot be zero.")
        return value


class CorrectionCommitRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    target_document_id: UUID
    reason_code: str = Field(min_length=1, max_length=40)
    corrected_destination_branch_id: UUID | None = None
    high_impact_acknowledged: bool = False
    notes: str | None = Field(default=None, max_length=1000)
    lines: list[CorrectionCommitLineRequest] = Field(default_factory=list)


class CorrectionDocumentLineView(BaseModel):
    id: UUID
    line_number: int
    target_line_id: UUID | None
    product_id: UUID
    product_code_snapshot: str
    product_name_snapshot: str
    product_class_id: UUID
    product_class_code_snapshot: str
    product_class_name_snapshot: str
    delta_quantity: Decimal
    unit_of_measure_code: str
    notes: str | None


class CorrectionDocumentView(BaseModel):
    id: UUID
    folio: str
    target_document_id: UUID
    target_document_type: str
    correction_type: str
    source_branch_id: UUID
    source_branch_code: str
    source_branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    created_by_user_id: UUID
    created_by_user_email: str
    created_by_user_full_name: str
    reason_code: str
    reason_name: str
    corrected_destination_branch_id: UUID | None
    corrected_destination_branch_code: str | None
    corrected_destination_branch_name: str | None
    notes: str | None
    status: str
    created_at_utc: datetime
    committed_at_utc: datetime | None
    audit_summary: AuditSummaryView | None = None
    lines: list[CorrectionDocumentLineView]


class CorrectionHistoryListItemView(BaseModel):
    id: UUID
    folio: str
    target_document_id: UUID
    target_document_folio: str
    target_document_type: str
    correction_type: str
    status: str
    source_branch_code: str
    source_branch_name: str
    workstation_code: str
    workstation_name: str
    created_by_user_id: UUID
    created_by_user_full_name: str
    reason_code: str
    reason_name: str
    corrected_destination_branch_code: str | None = None
    corrected_destination_branch_name: str | None = None
    line_count: int
    net_effect_quantity: Decimal
    created_at_utc: datetime
    committed_at_utc: datetime | None


class CorrectionsHistoryResponse(BaseModel):
    workstation_code: str
    scope: str
    query: str | None = None
    created_by_user_id: str | None = None
    target_document_type: str | None = None
    reason_code: str | None = None
    available_scopes: list[CorrectionHistoryScopeView]
    available_users: list[CorrectionHistoryFilterOptionView]
    available_document_types: list[CorrectionHistoryFilterOptionView]
    available_reasons: list[CorrectionHistoryFilterOptionView]
    records: list[CorrectionHistoryListItemView]
