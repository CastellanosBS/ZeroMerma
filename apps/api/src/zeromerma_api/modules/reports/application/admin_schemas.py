from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminReportFilterOptionView(BaseModel):
    code: str
    label: str


class AdminReportFilterDefinitionView(BaseModel):
    key: str
    label: str
    type: str
    options_source: str | None = None
    required: bool = False
    default_value: str | None = None
    options: list[AdminReportFilterOptionView] = Field(default_factory=list)


class AdminReportDefinitionView(BaseModel):
    code: str
    name: str
    description: str
    category: str
    category_label: str
    source_modules: list[str]
    available_filters: list[AdminReportFilterDefinitionView]
    supported_exports: list[str]
    status: str
    is_sensitive: bool
    required_permissions: list[str]
    backend_endpoint: str | None = None
    preview_kind: str
    unavailable_reason: str | None = None


class AdminReportCatalogFilterOptionsView(BaseModel):
    categories: list[AdminReportFilterOptionView]
    export_formats: list[AdminReportFilterOptionView]
    sensitivities: list[AdminReportFilterOptionView]
    source_modules: list[AdminReportFilterOptionView]
    statuses: list[AdminReportFilterOptionView]


class AdminReportCatalogMetricsView(BaseModel):
    available_reports: int
    category_count: int
    exportable_reports: int
    sensitive_reports: int
    pending_backend_reports: int
    recently_generated_reports: int | None = None


class AdminReportBackendContractView(BaseModel):
    definitions_endpoint: str = "GET /v1/admin/reports"
    preview_endpoint: str = "POST /v1/admin/reports/{report_code}/preview"
    export_endpoint: str = "POST /v1/admin/reports/{report_code}/export"
    generation_history_supported: bool = False
    async_jobs_supported: bool = False
    saved_configurations_supported: bool = False
    supported_export_formats: list[str] = Field(default_factory=lambda: ["json"])


class AdminReportDefinitionsResponse(BaseModel):
    backend_contract: AdminReportBackendContractView = Field(
        default_factory=AdminReportBackendContractView,
    )
    definitions: list[AdminReportDefinitionView]
    filter_options: AdminReportCatalogFilterOptionsView
    is_backend_connected: bool = True
    metrics: AdminReportCatalogMetricsView
    total: int


class AdminReportPreviewRequest(BaseModel):
    filters: dict[str, Any] = Field(default_factory=dict)


class AdminReportExportRequest(AdminReportPreviewRequest):
    format: str = "json"


class AdminReportSummaryCardView(BaseModel):
    label: str
    value: str
    helper_text: str | None = None
    tone: str = "neutral"


class AdminReportColumnView(BaseModel):
    key: str
    label: str
    kind: str = "text"


class AdminReportRelatedLinkView(BaseModel):
    label: str
    module: str
    route_hint: str | None = None
    document_type: str | None = None
    document_id: str | None = None
    reference: str | None = None
    can_open: bool = True


class AdminReportRowView(BaseModel):
    id: str
    cells: dict[str, str | None]
    source_document_links: list[AdminReportRelatedLinkView] = Field(default_factory=list)


class AdminReportPreviewResponse(BaseModel):
    report_code: str
    report_name: str
    generated_at: datetime
    filters_applied: dict[str, str | None]
    summary_cards: list[AdminReportSummaryCardView]
    columns: list[AdminReportColumnView]
    rows: list[AdminReportRowView]
    related_links: list[AdminReportRelatedLinkView]
    warnings: list[str] = Field(default_factory=list)


class AdminReportExportResponse(BaseModel):
    format: str
    generated_at: datetime
    report_code: str
    report_name: str
    filters_applied: dict[str, str | None]
    total_rows: int
    rows: list[AdminReportRowView]
    warnings: list[str] = Field(default_factory=list)
