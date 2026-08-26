from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

EquipmentOperationalStatus = Literal[
    "OPERATIONAL",
    "OUT_OF_SERVICE",
    "UNDER_MAINTENANCE",
    "RETIRED",
    "INACTIVE",
]
EquipmentRiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
MaintenanceStatus = Literal[
    "SCHEDULED",
    "PENDING",
    "IN_PROGRESS",
    "COMPLETED",
    "OVERDUE",
    "CANCELLED",
]
MaintenanceType = Literal[
    "PREVENTIVE",
    "CORRECTIVE",
    "INSPECTION",
    "CALIBRATION",
    "CLEANING_TECHNICAL",
]
MaintenanceResult = Literal[
    "NOT_COMPLETED",
    "COMPLETED_SUCCESSFULLY",
    "COMPLETED_WITH_OBSERVATIONS",
    "FAILED",
    "REQUIRES_FOLLOW_UP",
    "CANCELLED",
]


class AdminEquipmentBackendContractView(BaseModel):
    cancel_maintenance_endpoint: str = (
        "POST /v1/admin/equipment-maintenance/maintenance/{maintenance_id}/cancel"
    )
    complete_maintenance_endpoint: str = (
        "POST /v1/admin/equipment-maintenance/maintenance/{maintenance_id}/complete"
    )
    create_equipment_endpoint: str = "POST /v1/admin/equipment-maintenance/equipment"
    create_maintenance_endpoint: str = "POST /v1/admin/equipment-maintenance/maintenance"
    detail_endpoint: str = "GET /v1/admin/equipment-maintenance/equipment/{equipment_id}"
    evidence_contract: str = (
        "Evidence files are not supported yet; evidence is captured as evidence_note."
    )
    incident_contract: str = (
        "Incident backend is not available yet; incident links are stored as references."
    )
    list_endpoint: str = "GET /v1/admin/equipment-maintenance/equipment"
    start_maintenance_endpoint: str = (
        "POST /v1/admin/equipment-maintenance/maintenance/{maintenance_id}/start"
    )
    status_endpoint: str = "POST /v1/admin/equipment-maintenance/equipment/{equipment_id}/status"
    update_equipment_endpoint: str = (
        "PATCH /v1/admin/equipment-maintenance/equipment/{equipment_id}"
    )


class AdminEquipmentFilterOptionView(BaseModel):
    id: str
    label: str


class AdminEquipmentFilterOptionsView(BaseModel):
    area_types: list[AdminEquipmentFilterOptionView]
    areas: list[AdminEquipmentFilterOptionView]
    branches: list[AdminEquipmentFilterOptionView]
    equipment_types: list[AdminEquipmentFilterOptionView]
    incident_states: list[AdminEquipmentFilterOptionView]
    maintenance_statuses: list[AdminEquipmentFilterOptionView]
    maintenance_types: list[AdminEquipmentFilterOptionView]
    operational_statuses: list[AdminEquipmentFilterOptionView]
    providers: list[AdminEquipmentFilterOptionView]
    risk_levels: list[AdminEquipmentFilterOptionView]
    technicians: list[AdminEquipmentFilterOptionView]


class AdminEquipmentMetricsView(BaseModel):
    corrective_open_count: int
    high_risk_count: int
    operational_count: int
    out_of_service_count: int
    overdue_count: int
    pending_maintenance_count: int
    period_cost: Decimal
    total_equipment_count: int


class AdminEquipmentWarningView(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "critical"] = "warning"


class AdminMaintenanceRecordListItemView(BaseModel):
    completed_at: datetime | None = None
    cost: Decimal | None = None
    evidence_note: str | None = None
    folio: str
    has_evidence: bool
    id: UUID
    maintenance_type: MaintenanceType
    notes: str | None = None
    provider_name: str | None = None
    related_incident_reference: str | None = None
    result: MaintenanceResult
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    status: MaintenanceStatus
    technician_name: str | None = None
    warning_state: str


class AdminEquipmentListItemView(BaseModel):
    area_id: UUID | None = None
    area_name: str | None = None
    branch_id: UUID
    branch_name: str
    code: str
    equipment_type: str
    id: UUID
    last_maintenance_at: datetime | None = None
    maintenance_status: str
    name: str
    next_maintenance_at: datetime | None = None
    open_incident_count: int
    operational_status: EquipmentOperationalStatus
    period_cost: Decimal
    risk_level: EquipmentRiskLevel
    updated_at: datetime
    warning_state: str
    warnings: list[AdminEquipmentWarningView]


class AdminEquipmentListResponse(BaseModel):
    backend_contract: AdminEquipmentBackendContractView = Field(
        default_factory=AdminEquipmentBackendContractView,
    )
    filter_options: AdminEquipmentFilterOptionsView
    is_backend_connected: bool = True
    items: list[AdminEquipmentListItemView]
    metrics: AdminEquipmentMetricsView
    page: int
    page_size: int
    total: int


class AdminEquipmentOverviewView(BaseModel):
    branch_id: UUID
    branch_name: str
    code: str
    created_at: datetime
    equipment_type: str
    id: UUID
    name: str
    operational_status: EquipmentOperationalStatus
    risk_level: EquipmentRiskLevel
    updated_at: datetime
    warning_state: str


class AdminEquipmentLocationContextView(BaseModel):
    area_name: str | None = None
    area_type: str
    branch_code: str
    branch_id: UUID
    branch_name: str
    food_safety_critical: bool
    is_critical: bool


class AdminEquipmentMetadataView(BaseModel):
    brand: str | None = None
    maintenance_frequency_days: int | None = None
    model: str | None = None
    notes: str | None = None
    provider_name: str | None = None
    purchase_date: date | None = None
    serial_number: str | None = None
    warranty_expires_at: date | None = None


class AdminEquipmentCurrentMaintenanceStatusView(BaseModel):
    current_open_maintenance: AdminMaintenanceRecordListItemView | None = None
    current_linked_incident: str | None = None
    downtime_state: str
    last_maintenance_at: datetime | None = None
    last_maintenance_result: MaintenanceResult | None = None
    last_maintenance_type: MaintenanceType | None = None
    next_scheduled_maintenance_at: datetime | None = None
    overdue: bool


class AdminEquipmentIncidentRelatedView(BaseModel):
    folio: str
    route_hint: str | None = "/admin/incidencias"
    severity: str = "UNKNOWN"
    status: str = "REFERENCE_ONLY"


class AdminEquipmentEvidenceView(BaseModel):
    empty_state: str = "Este mantenimiento no tiene evidencia adjunta."
    files: list[dict[str, str]] = Field(default_factory=list)
    has_evidence: bool = False
    is_supported: bool = True
    latest_evidence_note: str | None = None
    upload_supported: bool = False


class AdminEquipmentCostContextView(BaseModel):
    last_service_cost: Decimal | None = None
    period_cost: Decimal
    total_lifetime_cost: Decimal
    warranty_note: str | None = None


class AdminEquipmentRelatedDocumentView(BaseModel):
    document_id: UUID
    document_type: str
    folio: str
    route_hint: str | None = None
    status: str


class AdminEquipmentAvailableActionsView(BaseModel):
    can_cancel_maintenance: bool
    can_complete_maintenance: bool
    can_create_corrective: bool
    can_create_preventive: bool
    can_edit_equipment: bool
    can_export: bool
    can_mark_operational: bool
    can_mark_out_of_service: bool
    can_print: bool
    can_start_maintenance: bool
    note: str | None = None


class AdminEquipmentDetailView(BaseModel):
    available_actions: AdminEquipmentAvailableActionsView
    cost_context: AdminEquipmentCostContextView
    current_maintenance_status: AdminEquipmentCurrentMaintenanceStatusView
    evidence: AdminEquipmentEvidenceView
    incidents_related: list[AdminEquipmentIncidentRelatedView]
    location_context: AdminEquipmentLocationContextView
    maintenance_history: list[AdminMaintenanceRecordListItemView]
    metadata: AdminEquipmentMetadataView
    overview: AdminEquipmentOverviewView
    related_documents: list[AdminEquipmentRelatedDocumentView]
    warnings: list[AdminEquipmentWarningView]


class AdminEquipmentCreateRequest(BaseModel):
    area_name: str | None = None
    area_type: str = "OTHER"
    branch_id: UUID
    brand: str | None = None
    code: str = Field(min_length=1, max_length=64)
    equipment_type: str = "OTHER"
    food_safety_critical: bool = False
    is_critical: bool = False
    maintenance_frequency_days: int | None = None
    model: str | None = None
    name: str = Field(min_length=1, max_length=180)
    notes: str | None = None
    operational_status: EquipmentOperationalStatus = "OPERATIONAL"
    provider_name: str | None = None
    purchase_date: date | None = None
    risk_level: EquipmentRiskLevel = "MEDIUM"
    serial_number: str | None = None
    warranty_expires_at: date | None = None

    @field_validator(
        "area_name",
        "brand",
        "code",
        "model",
        "name",
        "notes",
        "provider_name",
        "serial_number",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminEquipmentUpdateRequest(AdminEquipmentCreateRequest):
    pass


class AdminEquipmentStatusRequest(BaseModel):
    operational_status: EquipmentOperationalStatus
    reason: str | None = None

    @field_validator("reason", mode="before")
    @classmethod
    def _strip_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminMaintenanceCreateRequest(BaseModel):
    description: str = Field(min_length=1, max_length=1000)
    equipment_id: UUID
    expected_cost: Decimal | None = None
    maintenance_type: MaintenanceType
    provider_name: str | None = None
    related_incident_reference: str | None = None
    scheduled_at: datetime | None = None
    source_document_reference: str | None = None
    source_document_type: str | None = None
    start_immediately: bool = False
    status: MaintenanceStatus = "PENDING"
    technician_name: str | None = None

    @field_validator(
        "description",
        "provider_name",
        "related_incident_reference",
        "source_document_reference",
        "source_document_type",
        "technician_name",
        mode="before",
    )
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminMaintenanceCompleteRequest(BaseModel):
    completed_at: datetime | None = None
    cost: Decimal | None = None
    equipment_status_after_service: EquipmentOperationalStatus | None = None
    evidence_note: str | None = None
    notes: str | None = None
    result: MaintenanceResult
    technician_name: str | None = None

    @field_validator("evidence_note", "notes", "technician_name", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class AdminMaintenanceCancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason", mode="before")
    @classmethod
    def _strip_reason(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value
