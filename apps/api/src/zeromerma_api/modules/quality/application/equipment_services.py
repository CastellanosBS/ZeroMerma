from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import cast

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.quality.application.equipment_schemas import (
    AdminEquipmentAvailableActionsView,
    AdminEquipmentCostContextView,
    AdminEquipmentCreateRequest,
    AdminEquipmentCurrentMaintenanceStatusView,
    AdminEquipmentDetailView,
    AdminEquipmentEvidenceView,
    AdminEquipmentFilterOptionsView,
    AdminEquipmentFilterOptionView,
    AdminEquipmentIncidentRelatedView,
    AdminEquipmentListItemView,
    AdminEquipmentListResponse,
    AdminEquipmentLocationContextView,
    AdminEquipmentMetadataView,
    AdminEquipmentMetricsView,
    AdminEquipmentOverviewView,
    AdminEquipmentRelatedDocumentView,
    AdminEquipmentStatusRequest,
    AdminEquipmentUpdateRequest,
    AdminEquipmentWarningView,
    AdminMaintenanceCancelRequest,
    AdminMaintenanceCompleteRequest,
    AdminMaintenanceCreateRequest,
    AdminMaintenanceRecordListItemView,
    EquipmentOperationalStatus,
    EquipmentRiskLevel,
    MaintenanceResult,
    MaintenanceStatus,
    MaintenanceType,
)
from zeromerma_api.modules.quality.domain.constants import (
    AUDIT_ACTION_EQUIPMENT_CREATED,
    AUDIT_ACTION_EQUIPMENT_HIGH_RISK_NOTIFIED,
    AUDIT_ACTION_EQUIPMENT_STATUS_CHANGED,
    AUDIT_ACTION_EQUIPMENT_UPDATED,
    AUDIT_ACTION_MAINTENANCE_CANCELLED,
    AUDIT_ACTION_MAINTENANCE_COMPLETED,
    AUDIT_ACTION_MAINTENANCE_CREATED,
    AUDIT_ACTION_MAINTENANCE_STARTED,
    CLEANING_RISK_CRITICAL,
    CLEANING_RISK_HIGH,
    CLEANING_RISK_LOW,
    CLEANING_RISK_MEDIUM,
    EQUIPMENT_AREA_TYPE_CLEANING_SANITATION,
    EQUIPMENT_AREA_TYPE_DISPLAY_COUNTER,
    EQUIPMENT_AREA_TYPE_OTHER,
    EQUIPMENT_AREA_TYPE_PRODUCTION,
    EQUIPMENT_AREA_TYPE_REFRIGERATION,
    EQUIPMENT_AREA_TYPE_STORAGE,
    EQUIPMENT_RESOURCE_TYPE,
    EQUIPMENT_STATUS_INACTIVE,
    EQUIPMENT_STATUS_OPERATIONAL,
    EQUIPMENT_STATUS_OUT_OF_SERVICE,
    EQUIPMENT_STATUS_RETIRED,
    EQUIPMENT_STATUS_UNDER_MAINTENANCE,
    EQUIPMENT_TYPE_DISPLAY_CASE,
    EQUIPMENT_TYPE_MIXER,
    EQUIPMENT_TYPE_OTHER,
    EQUIPMENT_TYPE_OVEN,
    EQUIPMENT_TYPE_PACKAGING,
    EQUIPMENT_TYPE_REFRIGERATION,
    EQUIPMENT_TYPE_SANITATION,
    EQUIPMENT_TYPE_SCALE,
    EQUIPMENT_WARNING_FOLLOW_UP,
    EQUIPMENT_WARNING_HIGH_RISK,
    EQUIPMENT_WARNING_OK,
    EQUIPMENT_WARNING_OUT_OF_SERVICE,
    EQUIPMENT_WARNING_OVERDUE,
    EQUIPMENT_WARNING_UNDER_MAINTENANCE,
    MAINTENANCE_RESOURCE_TYPE,
    MAINTENANCE_RESULT_CANCELLED,
    MAINTENANCE_RESULT_COMPLETED_SUCCESSFULLY,
    MAINTENANCE_RESULT_COMPLETED_WITH_OBSERVATIONS,
    MAINTENANCE_RESULT_FAILED,
    MAINTENANCE_RESULT_REQUIRES_FOLLOW_UP,
    MAINTENANCE_STATUS_CANCELLED,
    MAINTENANCE_STATUS_COMPLETED,
    MAINTENANCE_STATUS_IN_PROGRESS,
    MAINTENANCE_STATUS_OVERDUE,
    MAINTENANCE_STATUS_PENDING,
    MAINTENANCE_STATUS_SCHEDULED,
    MAINTENANCE_TYPE_CALIBRATION,
    MAINTENANCE_TYPE_CLEANING_TECHNICAL,
    MAINTENANCE_TYPE_CORRECTIVE,
    MAINTENANCE_TYPE_INSPECTION,
    MAINTENANCE_TYPE_PREVENTIVE,
    OUTBOX_EVENT_EQUIPMENT_CREATED_V1,
    OUTBOX_EVENT_EQUIPMENT_HIGH_RISK_ALERT_V1,
    OUTBOX_EVENT_EQUIPMENT_STATUS_CHANGED_V1,
    OUTBOX_EVENT_EQUIPMENT_UPDATED_V1,
    OUTBOX_EVENT_MAINTENANCE_CANCELLED_V1,
    OUTBOX_EVENT_MAINTENANCE_COMPLETED_V1,
    OUTBOX_EVENT_MAINTENANCE_CREATED_V1,
    OUTBOX_EVENT_MAINTENANCE_STARTED_V1,
    VALID_EQUIPMENT_AREA_TYPES,
    VALID_EQUIPMENT_OPERATIONAL_STATUSES,
    VALID_EQUIPMENT_TYPES,
    VALID_MAINTENANCE_RESULTS,
    VALID_MAINTENANCE_STATUSES,
    VALID_MAINTENANCE_TYPES,
)
from zeromerma_api.modules.quality.domain.exceptions import (
    EquipmentMaintenanceValidationError,
    EquipmentNotFoundError,
    MaintenanceRecordNotFoundError,
)
from zeromerma_api.modules.quality.infrastructure.models import (
    CleaningLog,
    EquipmentAsset,
    EquipmentMaintenanceRecord,
    SanitaryVerification,
)

_EQUIPMENT_OPERATIONAL_STATUS_ADAPTER: TypeAdapter[EquipmentOperationalStatus] = TypeAdapter(
    EquipmentOperationalStatus
)
_EQUIPMENT_RISK_LEVEL_ADAPTER: TypeAdapter[EquipmentRiskLevel] = TypeAdapter(EquipmentRiskLevel)
_MAINTENANCE_RESULT_ADAPTER: TypeAdapter[MaintenanceResult] = TypeAdapter(MaintenanceResult)
_MAINTENANCE_RESULT_NONE_ADAPTER: TypeAdapter[MaintenanceResult | None] = TypeAdapter(
    MaintenanceResult | None
)
_MAINTENANCE_STATUS_ADAPTER: TypeAdapter[MaintenanceStatus] = TypeAdapter(MaintenanceStatus)
_MAINTENANCE_TYPE_ADAPTER: TypeAdapter[MaintenanceType] = TypeAdapter(MaintenanceType)
_MAINTENANCE_TYPE_NONE_ADAPTER: TypeAdapter[MaintenanceType | None] = TypeAdapter(
    MaintenanceType | None
)
EQUIPMENT_TYPE_LABELS = {
    EQUIPMENT_TYPE_OVEN: "Horno",
    EQUIPMENT_TYPE_MIXER: "Batidora / mezcladora",
    EQUIPMENT_TYPE_REFRIGERATION: "Refrigeracion",
    EQUIPMENT_TYPE_DISPLAY_CASE: "Vitrina / exhibicion",
    EQUIPMENT_TYPE_SCALE: "Bascula",
    EQUIPMENT_TYPE_PACKAGING: "Empaque",
    EQUIPMENT_TYPE_SANITATION: "Sanitizacion",
    EQUIPMENT_TYPE_OTHER: "Otro",
}

AREA_TYPE_LABELS = {
    EQUIPMENT_AREA_TYPE_PRODUCTION: "Produccion",
    EQUIPMENT_AREA_TYPE_REFRIGERATION: "Refrigeracion",
    EQUIPMENT_AREA_TYPE_DISPLAY_COUNTER: "Mostrador / exhibicion",
    EQUIPMENT_AREA_TYPE_STORAGE: "Almacen",
    EQUIPMENT_AREA_TYPE_CLEANING_SANITATION: "Limpieza / sanidad",
    EQUIPMENT_AREA_TYPE_OTHER: "Otra area",
}

OPERATIONAL_STATUS_LABELS = {
    EQUIPMENT_STATUS_OPERATIONAL: "Operativo",
    EQUIPMENT_STATUS_OUT_OF_SERVICE: "Fuera de servicio",
    EQUIPMENT_STATUS_UNDER_MAINTENANCE: "En mantenimiento",
    EQUIPMENT_STATUS_RETIRED: "Retirado",
    EQUIPMENT_STATUS_INACTIVE: "Inactivo",
}

MAINTENANCE_TYPE_LABELS = {
    MAINTENANCE_TYPE_PREVENTIVE: "Preventivo",
    MAINTENANCE_TYPE_CORRECTIVE: "Correctivo",
    MAINTENANCE_TYPE_INSPECTION: "Inspeccion",
    MAINTENANCE_TYPE_CALIBRATION: "Calibracion",
    MAINTENANCE_TYPE_CLEANING_TECHNICAL: "Limpieza tecnica",
}

MAINTENANCE_STATUS_LABELS = {
    MAINTENANCE_STATUS_SCHEDULED: "Programado",
    MAINTENANCE_STATUS_PENDING: "Pendiente",
    MAINTENANCE_STATUS_IN_PROGRESS: "En proceso",
    MAINTENANCE_STATUS_COMPLETED: "Completado",
    MAINTENANCE_STATUS_OVERDUE: "Vencido",
    MAINTENANCE_STATUS_CANCELLED: "Cancelado",
    "OK": "Al dia",
    "NO_HISTORY": "Sin historial",
}

RISK_LABELS = {
    CLEANING_RISK_LOW: "Bajo",
    CLEANING_RISK_MEDIUM: "Medio",
    CLEANING_RISK_HIGH: "Alto",
    CLEANING_RISK_CRITICAL: "Critico",
}

OPEN_MAINTENANCE_STATUSES = {
    MAINTENANCE_STATUS_SCHEDULED,
    MAINTENANCE_STATUS_PENDING,
    MAINTENANCE_STATUS_IN_PROGRESS,
    MAINTENANCE_STATUS_OVERDUE,
}


def _equipment_status(value: str) -> EquipmentOperationalStatus:
    return cast(EquipmentOperationalStatus, value)


def _equipment_risk(value: str) -> EquipmentRiskLevel:
    return cast(EquipmentRiskLevel, value)


def _maintenance_status(value: str) -> MaintenanceStatus:
    return cast(MaintenanceStatus, value)


def _maintenance_type(value: str) -> MaintenanceType:
    return cast(MaintenanceType, value)


def _maintenance_result(value: str | None) -> MaintenanceResult | None:
    return cast(MaintenanceResult, value) if value is not None else None


FINAL_MAINTENANCE_STATUSES = {
    MAINTENANCE_STATUS_COMPLETED,
    MAINTENANCE_STATUS_CANCELLED,
}


@dataclass(frozen=True)
class _EquipmentRow:
    branch: Branch
    created_by_user: User
    equipment: EquipmentAsset
    maintenance_records: list[EquipmentMaintenanceRecord]


class AdminEquipmentMaintenanceService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_equipment(
        self,
        session: Session,
        *,
        area_name: str | None,
        area_type: str | None,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        equipment_type: str | None,
        incident_state: str | None,
        maintenance_status: str | None,
        maintenance_type: str | None,
        operational_status: str | None,
        overdue_state: str | None,
        page: int,
        page_size: int,
        provider_name: str | None,
        risk_level: str | None,
        search: str | None,
        technician_name: str | None,
    ) -> AdminEquipmentListResponse:
        rows = self._fetch_rows(session)

        if branch_id is not None:
            rows = [row for row in rows if row.equipment.branch_id == branch_id]
        rows = self._filter_by_text(rows, area_name, lambda row: row.equipment.area_name or "")
        rows = self._filter_by_code(rows, area_type, lambda row: row.equipment.area_type)
        rows = self._filter_by_code(rows, equipment_type, lambda row: row.equipment.equipment_type)
        rows = self._filter_by_code(
            rows, operational_status, lambda row: row.equipment.operational_status
        )
        rows = self._filter_by_code(rows, risk_level, lambda row: row.equipment.risk_level)

        normalized_maintenance_status = _normalize_optional(maintenance_status)
        if normalized_maintenance_status and normalized_maintenance_status != "all":
            rows = [
                row
                for row in rows
                if self._maintenance_state(row) == normalized_maintenance_status
                or any(
                    record.status == normalized_maintenance_status
                    for record in row.maintenance_records
                )
            ]

        normalized_maintenance_type = _normalize_optional(maintenance_type)
        if normalized_maintenance_type and normalized_maintenance_type != "all":
            rows = [
                row
                for row in rows
                if any(
                    record.maintenance_type == normalized_maintenance_type
                    for record in row.maintenance_records
                )
            ]

        normalized_provider = _normalize_optional(provider_name)
        if normalized_provider and normalized_provider != "all":
            rows = [
                row
                for row in rows
                if (row.equipment.provider_name or "").casefold() == normalized_provider.casefold()
                or any(
                    (record.provider_name or "").casefold() == normalized_provider.casefold()
                    for record in row.maintenance_records
                )
            ]

        normalized_technician = _normalize_optional(technician_name)
        if normalized_technician and normalized_technician != "all":
            rows = [
                row
                for row in rows
                if any(
                    (record.technician_name or "").casefold() == normalized_technician.casefold()
                    for record in row.maintenance_records
                )
            ]

        if date_from is not None or date_to is not None:
            rows = [
                row
                for row in rows
                if any(
                    self._record_in_range(record, date_from=date_from, date_to=date_to)
                    for record in row.maintenance_records
                )
            ]

        normalized_overdue = _normalize_optional(overdue_state)
        if normalized_overdue == "overdue":
            rows = [row for row in rows if self._is_overdue(row)]
        elif normalized_overdue == "not_overdue":
            rows = [row for row in rows if not self._is_overdue(row)]

        normalized_incident = _normalize_optional(incident_state)
        if normalized_incident == "with_incident":
            rows = [row for row in rows if self._open_incident_count(row) > 0]
        elif normalized_incident == "without_incident":
            rows = [row for row in rows if self._open_incident_count(row) == 0]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            rows = [row for row in rows if self._matches_search(row, normalized_search)]

        items = [self._to_list_item(row, date_from=date_from, date_to=date_to) for row in rows]
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        total = len(items)
        offset = (safe_page - 1) * safe_page_size

        return AdminEquipmentListResponse(
            filter_options=self._build_filter_options(rows),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows, date_from=date_from, date_to=date_to),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_detail(
        self,
        session: Session,
        *,
        equipment_id: uuid.UUID,
    ) -> AdminEquipmentDetailView:
        return self._to_detail(session, self._get_row(session, equipment_id))

    def create_equipment(
        self,
        session: Session,
        *,
        command: AdminEquipmentCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        branch = self._get_branch(session, command.branch_id)
        if not branch.is_active:
            raise EquipmentMaintenanceValidationError("Equipment branch is inactive.")
        self._get_user(session, current_user.id)
        self._validate_equipment_command(command)
        self._ensure_unique_code(session, command.code)

        equipment = EquipmentAsset(
            area_name=command.area_name,
            area_type=command.area_type,
            branch_id=branch.id,
            brand=command.brand,
            code=command.code,
            created_by_user_id=current_user.id,
            equipment_type=command.equipment_type,
            food_safety_critical=command.food_safety_critical,
            is_critical=command.is_critical,
            maintenance_frequency_days=command.maintenance_frequency_days,
            model=command.model,
            name=command.name,
            notes=command.notes,
            operational_status=command.operational_status,
            provider_name=command.provider_name,
            purchase_date=command.purchase_date,
            risk_level=command.risk_level,
            serial_number=command.serial_number,
            warranty_expires_at=command.warranty_expires_at,
        )
        session.add(equipment)
        session.flush()
        self._record_equipment_change(
            session,
            action=AUDIT_ACTION_EQUIPMENT_CREATED,
            actor_id=current_user.id,
            branch_id=branch.id,
            equipment=equipment,
            request_id=request_id,
        )
        self._append_equipment_event(
            session,
            event_name=OUTBOX_EVENT_EQUIPMENT_CREATED_V1,
            equipment=equipment,
            branch=branch,
        )
        if self._is_high_risk_equipment(equipment):
            self._record_high_risk_alert(session, current_user.id, branch.id, equipment, request_id)

        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise EquipmentMaintenanceValidationError("Equipment code already exists.") from error

        return self._to_detail(session, self._get_row(session, equipment.id))

    def update_equipment(
        self,
        session: Session,
        *,
        equipment_id: uuid.UUID,
        command: AdminEquipmentUpdateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        row = self._get_row(session, equipment_id)
        branch = self._get_branch(session, command.branch_id)
        if not branch.is_active:
            raise EquipmentMaintenanceValidationError("Equipment branch is inactive.")
        self._validate_equipment_command(command)
        self._ensure_unique_code(session, command.code, current_equipment_id=equipment_id)

        equipment = row.equipment
        equipment.area_name = command.area_name
        equipment.area_type = command.area_type
        equipment.branch_id = branch.id
        equipment.brand = command.brand
        equipment.code = command.code
        equipment.equipment_type = command.equipment_type
        equipment.food_safety_critical = command.food_safety_critical
        equipment.is_critical = command.is_critical
        equipment.maintenance_frequency_days = command.maintenance_frequency_days
        equipment.model = command.model
        equipment.name = command.name
        equipment.notes = command.notes
        equipment.operational_status = command.operational_status
        equipment.provider_name = command.provider_name
        equipment.purchase_date = command.purchase_date
        equipment.risk_level = command.risk_level
        equipment.serial_number = command.serial_number
        equipment.warranty_expires_at = command.warranty_expires_at

        self._record_equipment_change(
            session,
            action=AUDIT_ACTION_EQUIPMENT_UPDATED,
            actor_id=current_user.id,
            branch_id=branch.id,
            equipment=equipment,
            request_id=request_id,
        )
        self._append_equipment_event(
            session,
            event_name=OUTBOX_EVENT_EQUIPMENT_UPDATED_V1,
            equipment=equipment,
            branch=branch,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, equipment.id))

    def change_equipment_status(
        self,
        session: Session,
        *,
        equipment_id: uuid.UUID,
        command: AdminEquipmentStatusRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        row = self._get_row(session, equipment_id)
        if command.operational_status not in VALID_EQUIPMENT_OPERATIONAL_STATUSES:
            raise EquipmentMaintenanceValidationError("Equipment status is not supported.")
        if command.operational_status in {
            EQUIPMENT_STATUS_OUT_OF_SERVICE,
            EQUIPMENT_STATUS_RETIRED,
            EQUIPMENT_STATUS_INACTIVE,
        } and not _has_text(command.reason):
            raise EquipmentMaintenanceValidationError("Status change reason is required.")
        if (
            command.operational_status == EQUIPMENT_STATUS_OPERATIONAL
            and self._has_unresolved_failed_maintenance(row)
            and self._is_high_risk_equipment(row.equipment)
        ):
            raise EquipmentMaintenanceValidationError(
                "Critical equipment cannot be marked operational after failed maintenance."
            )

        row.equipment.operational_status = command.operational_status
        row.equipment.out_of_service_reason = (
            command.reason
            if command.operational_status == EQUIPMENT_STATUS_OUT_OF_SERVICE
            else None
        )
        self._record_equipment_change(
            session,
            action=AUDIT_ACTION_EQUIPMENT_STATUS_CHANGED,
            actor_id=current_user.id,
            branch_id=row.equipment.branch_id,
            equipment=row.equipment,
            request_id=request_id,
        )
        self._append_equipment_event(
            session,
            event_name=OUTBOX_EVENT_EQUIPMENT_STATUS_CHANGED_V1,
            equipment=row.equipment,
            branch=row.branch,
        )
        if self._is_high_risk_equipment(row.equipment):
            self._record_high_risk_alert(
                session,
                current_user.id,
                row.equipment.branch_id,
                row.equipment,
                request_id,
            )
        session.commit()
        return self._to_detail(session, self._get_row(session, equipment_id))

    def create_maintenance(
        self,
        session: Session,
        *,
        command: AdminMaintenanceCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        row = self._get_row(session, command.equipment_id)
        self._validate_maintenance_create(command)
        now = _utc_now()
        status: str = command.status
        if command.start_immediately:
            status = MAINTENANCE_STATUS_IN_PROGRESS
        elif (
            command.scheduled_at
            and _as_utc(command.scheduled_at) < now
            and status
            in {
                MAINTENANCE_STATUS_SCHEDULED,
                MAINTENANCE_STATUS_PENDING,
            }
        ):
            status = MAINTENANCE_STATUS_OVERDUE

        record = EquipmentMaintenanceRecord(
            created_by_user_id=current_user.id,
            description=command.description,
            equipment_id=row.equipment.id,
            expected_cost=command.expected_cost,
            folio=self._generate_maintenance_folio(session),
            maintenance_type=command.maintenance_type,
            provider_name=command.provider_name,
            related_incident_reference=command.related_incident_reference,
            scheduled_at=_as_utc(command.scheduled_at) if command.scheduled_at else None,
            source_document_reference=command.source_document_reference,
            source_document_type=command.source_document_type,
            started_at=now if command.start_immediately else None,
            status=status,
            technician_name=command.technician_name,
        )
        session.add(record)
        if command.start_immediately:
            row.equipment.operational_status = EQUIPMENT_STATUS_UNDER_MAINTENANCE
        self._record_maintenance_change(
            session,
            action=AUDIT_ACTION_MAINTENANCE_CREATED,
            actor_id=current_user.id,
            branch_id=row.equipment.branch_id,
            equipment=row.equipment,
            record=record,
            request_id=request_id,
        )
        self._append_maintenance_event(
            session,
            event_name=OUTBOX_EVENT_MAINTENANCE_CREATED_V1,
            equipment=row.equipment,
            record=record,
            branch=row.branch,
        )
        if command.start_immediately:
            self._record_maintenance_change(
                session,
                action=AUDIT_ACTION_MAINTENANCE_STARTED,
                actor_id=current_user.id,
                branch_id=row.equipment.branch_id,
                equipment=row.equipment,
                record=record,
                request_id=request_id,
            )
            self._append_maintenance_event(
                session,
                event_name=OUTBOX_EVENT_MAINTENANCE_STARTED_V1,
                equipment=row.equipment,
                record=record,
                branch=row.branch,
            )
        if self._is_high_risk_equipment(row.equipment):
            self._record_high_risk_alert(
                session,
                current_user.id,
                row.equipment.branch_id,
                row.equipment,
                request_id,
            )
        session.commit()
        return self._to_detail(session, self._get_row(session, row.equipment.id))

    def start_maintenance(
        self,
        session: Session,
        *,
        maintenance_id: uuid.UUID,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        record = self._get_maintenance_record(session, maintenance_id)
        row = self._get_row(session, record.equipment_id)
        if record.status in FINAL_MAINTENANCE_STATUSES:
            raise EquipmentMaintenanceValidationError(
                "Maintenance cannot be started from its current status."
            )
        record.status = MAINTENANCE_STATUS_IN_PROGRESS
        record.started_at = record.started_at or _utc_now()
        row.equipment.operational_status = EQUIPMENT_STATUS_UNDER_MAINTENANCE
        self._record_maintenance_change(
            session,
            action=AUDIT_ACTION_MAINTENANCE_STARTED,
            actor_id=current_user.id,
            branch_id=row.equipment.branch_id,
            equipment=row.equipment,
            record=record,
            request_id=request_id,
        )
        self._append_maintenance_event(
            session,
            event_name=OUTBOX_EVENT_MAINTENANCE_STARTED_V1,
            equipment=row.equipment,
            record=record,
            branch=row.branch,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, row.equipment.id))

    def complete_maintenance(
        self,
        session: Session,
        *,
        maintenance_id: uuid.UUID,
        command: AdminMaintenanceCompleteRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        record = self._get_maintenance_record(session, maintenance_id)
        row = self._get_row(session, record.equipment_id)
        if record.status in FINAL_MAINTENANCE_STATUSES:
            raise EquipmentMaintenanceValidationError(
                "Maintenance cannot be completed from its current status."
            )
        self._validate_maintenance_completion(row, command)

        record.status = MAINTENANCE_STATUS_COMPLETED
        record.completed_at = _as_utc(command.completed_at) if command.completed_at else _utc_now()
        record.cost = command.cost
        record.evidence_note = command.evidence_note
        record.has_evidence = _has_text(command.evidence_note)
        record.notes = command.notes
        record.result = command.result
        record.technician_name = command.technician_name or record.technician_name
        row.equipment.operational_status = self._status_after_completion(row, command)
        row.equipment.out_of_service_reason = (
            command.notes
            if row.equipment.operational_status == EQUIPMENT_STATUS_OUT_OF_SERVICE
            else None
        )
        self._record_maintenance_change(
            session,
            action=AUDIT_ACTION_MAINTENANCE_COMPLETED,
            actor_id=current_user.id,
            branch_id=row.equipment.branch_id,
            equipment=row.equipment,
            record=record,
            request_id=request_id,
        )
        self._append_maintenance_event(
            session,
            event_name=OUTBOX_EVENT_MAINTENANCE_COMPLETED_V1,
            equipment=row.equipment,
            record=record,
            branch=row.branch,
        )
        if self._is_high_risk_equipment(row.equipment):
            self._record_high_risk_alert(
                session,
                current_user.id,
                row.equipment.branch_id,
                row.equipment,
                request_id,
            )
        session.commit()
        return self._to_detail(session, self._get_row(session, row.equipment.id))

    def cancel_maintenance(
        self,
        session: Session,
        *,
        maintenance_id: uuid.UUID,
        command: AdminMaintenanceCancelRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminEquipmentDetailView:
        record = self._get_maintenance_record(session, maintenance_id)
        row = self._get_row(session, record.equipment_id)
        if record.status in FINAL_MAINTENANCE_STATUSES:
            raise EquipmentMaintenanceValidationError(
                "Maintenance cannot be cancelled from its current status."
            )
        record.status = MAINTENANCE_STATUS_CANCELLED
        record.result = MAINTENANCE_RESULT_CANCELLED
        record.cancellation_reason = command.reason
        self._record_maintenance_change(
            session,
            action=AUDIT_ACTION_MAINTENANCE_CANCELLED,
            actor_id=current_user.id,
            branch_id=row.equipment.branch_id,
            equipment=row.equipment,
            record=record,
            request_id=request_id,
        )
        self._append_maintenance_event(
            session,
            event_name=OUTBOX_EVENT_MAINTENANCE_CANCELLED_V1,
            equipment=row.equipment,
            record=record,
            branch=row.branch,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, row.equipment.id))

    def _fetch_rows(self, session: Session) -> list[_EquipmentRow]:
        equipment = (
            session.execute(select(EquipmentAsset).order_by(EquipmentAsset.updated_at.desc()))
            .scalars()
            .all()
        )
        return [self._row_from_equipment(session, asset) for asset in equipment]

    def _row_from_equipment(self, session: Session, equipment: EquipmentAsset) -> _EquipmentRow:
        branch = session.get(Branch, equipment.branch_id)
        created_by_user = session.get(User, equipment.created_by_user_id)
        records = (
            session.execute(
                select(EquipmentMaintenanceRecord)
                .where(EquipmentMaintenanceRecord.equipment_id == equipment.id)
                .order_by(
                    EquipmentMaintenanceRecord.scheduled_at.desc().nullslast(),
                    EquipmentMaintenanceRecord.created_at.desc(),
                )
            )
            .scalars()
            .all()
        )
        if branch is None or created_by_user is None:
            raise EquipmentMaintenanceValidationError("Equipment references invalid data.")
        return _EquipmentRow(
            branch=branch,
            created_by_user=created_by_user,
            equipment=equipment,
            maintenance_records=list(records),
        )

    def _get_row(self, session: Session, equipment_id: uuid.UUID) -> _EquipmentRow:
        equipment = session.get(EquipmentAsset, equipment_id)
        if equipment is None:
            raise EquipmentNotFoundError("Equipment does not exist.")
        return self._row_from_equipment(session, equipment)

    def _get_maintenance_record(
        self,
        session: Session,
        maintenance_id: uuid.UUID,
    ) -> EquipmentMaintenanceRecord:
        record = session.get(EquipmentMaintenanceRecord, maintenance_id)
        if record is None:
            raise MaintenanceRecordNotFoundError("Maintenance record does not exist.")
        return record

    def _to_detail(self, session: Session, row: _EquipmentRow) -> AdminEquipmentDetailView:
        list_item = self._to_list_item(row, date_from=None, date_to=None)
        last_completed = self._last_completed(row)
        latest_evidence = next(
            (record.evidence_note for record in row.maintenance_records if record.evidence_note),
            None,
        )
        lifetime_cost = sum(
            ((record.cost or Decimal("0")) for record in row.maintenance_records),
            Decimal("0"),
        )
        current_open = self._current_open_record(row)
        return AdminEquipmentDetailView(
            available_actions=self._available_actions(row),
            cost_context=AdminEquipmentCostContextView(
                last_service_cost=last_completed.cost if last_completed else None,
                period_cost=list_item.period_cost,
                total_lifetime_cost=lifetime_cost,
                warranty_note=self._warranty_note(row.equipment),
            ),
            current_maintenance_status=AdminEquipmentCurrentMaintenanceStatusView(
                current_open_maintenance=self._maintenance_view(current_open)
                if current_open
                else None,
                current_linked_incident=current_open.related_incident_reference
                if current_open
                else None,
                downtime_state=(
                    "out_of_service"
                    if row.equipment.operational_status == EQUIPMENT_STATUS_OUT_OF_SERVICE
                    else "under_maintenance"
                    if row.equipment.operational_status == EQUIPMENT_STATUS_UNDER_MAINTENANCE
                    else "operational"
                ),
                last_maintenance_at=last_completed.completed_at if last_completed else None,
                last_maintenance_result=_MAINTENANCE_RESULT_NONE_ADAPTER.validate_python(
                    last_completed.result if last_completed else None
                ),
                last_maintenance_type=_MAINTENANCE_TYPE_NONE_ADAPTER.validate_python(
                    last_completed.maintenance_type if last_completed else None
                ),
                next_scheduled_maintenance_at=self._next_scheduled_maintenance_at(row),
                overdue=self._is_overdue(row),
            ),
            evidence=AdminEquipmentEvidenceView(
                has_evidence=latest_evidence is not None,
                latest_evidence_note=latest_evidence,
            ),
            incidents_related=self._incident_references(row),
            location_context=AdminEquipmentLocationContextView(
                area_name=row.equipment.area_name,
                area_type=row.equipment.area_type,
                branch_code=row.branch.code,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                food_safety_critical=row.equipment.food_safety_critical,
                is_critical=row.equipment.is_critical,
            ),
            maintenance_history=[
                self._maintenance_view(record) for record in row.maintenance_records
            ],
            metadata=AdminEquipmentMetadataView(
                brand=row.equipment.brand,
                maintenance_frequency_days=row.equipment.maintenance_frequency_days,
                model=row.equipment.model,
                notes=row.equipment.notes,
                provider_name=row.equipment.provider_name,
                purchase_date=row.equipment.purchase_date,
                serial_number=row.equipment.serial_number,
                warranty_expires_at=row.equipment.warranty_expires_at,
            ),
            overview=AdminEquipmentOverviewView(
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                code=row.equipment.code,
                created_at=row.equipment.created_at,
                equipment_type=row.equipment.equipment_type,
                id=row.equipment.id,
                name=row.equipment.name,
                operational_status=_EQUIPMENT_OPERATIONAL_STATUS_ADAPTER.validate_python(
                    row.equipment.operational_status
                ),
                risk_level=_EQUIPMENT_RISK_LEVEL_ADAPTER.validate_python(row.equipment.risk_level),
                updated_at=row.equipment.updated_at,
                warning_state=list_item.warning_state,
            ),
            related_documents=self._related_documents(session, row),
            warnings=list_item.warnings,
        )

    def _to_list_item(
        self,
        row: _EquipmentRow,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> AdminEquipmentListItemView:
        last_completed = self._last_completed(row)
        return AdminEquipmentListItemView(
            area_name=row.equipment.area_name,
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            code=row.equipment.code,
            equipment_type=row.equipment.equipment_type,
            id=row.equipment.id,
            last_maintenance_at=(last_completed.completed_at if last_completed else None),
            maintenance_status=self._maintenance_state(row),
            name=row.equipment.name,
            next_maintenance_at=self._next_scheduled_maintenance_at(row),
            open_incident_count=self._open_incident_count(row),
            operational_status=_EQUIPMENT_OPERATIONAL_STATUS_ADAPTER.validate_python(
                row.equipment.operational_status
            ),
            period_cost=self._period_cost(row, date_from=date_from, date_to=date_to),
            risk_level=_EQUIPMENT_RISK_LEVEL_ADAPTER.validate_python(row.equipment.risk_level),
            updated_at=row.equipment.updated_at,
            warning_state=self._warning_state(row),
            warnings=self._warnings(row),
        )

    def _maintenance_view(
        self,
        record: EquipmentMaintenanceRecord,
    ) -> AdminMaintenanceRecordListItemView:
        return AdminMaintenanceRecordListItemView(
            completed_at=record.completed_at,
            cost=record.cost,
            evidence_note=record.evidence_note,
            folio=record.folio,
            has_evidence=record.has_evidence,
            id=record.id,
            maintenance_type=_MAINTENANCE_TYPE_ADAPTER.validate_python(record.maintenance_type),
            notes=record.notes,
            provider_name=record.provider_name,
            related_incident_reference=record.related_incident_reference,
            result=_MAINTENANCE_RESULT_ADAPTER.validate_python(record.result),
            scheduled_at=record.scheduled_at,
            started_at=record.started_at,
            status=_MAINTENANCE_STATUS_ADAPTER.validate_python(
                self._effective_record_status(record)
            ),
            technician_name=record.technician_name,
            warning_state=self._record_warning_state(record),
        )

    def _build_filter_options(self, rows: list[_EquipmentRow]) -> AdminEquipmentFilterOptionsView:
        return AdminEquipmentFilterOptionsView(
            area_types=[
                AdminEquipmentFilterOptionView(id=key, label=value)
                for key, value in AREA_TYPE_LABELS.items()
            ],
            areas=_dedupe_options(
                AdminEquipmentFilterOptionView(
                    id=row.equipment.area_name, label=row.equipment.area_name
                )
                for row in rows
                if row.equipment.area_name
            ),
            branches=_dedupe_options(
                AdminEquipmentFilterOptionView(id=str(row.branch.id), label=row.branch.name)
                for row in rows
            ),
            equipment_types=[
                AdminEquipmentFilterOptionView(id=key, label=value)
                for key, value in EQUIPMENT_TYPE_LABELS.items()
            ],
            incident_states=[
                AdminEquipmentFilterOptionView(id="with_incident", label="Con incidencia"),
                AdminEquipmentFilterOptionView(id="without_incident", label="Sin incidencia"),
            ],
            maintenance_statuses=[
                AdminEquipmentFilterOptionView(id=key, label=value)
                for key, value in MAINTENANCE_STATUS_LABELS.items()
            ],
            maintenance_types=[
                AdminEquipmentFilterOptionView(id=key, label=value)
                for key, value in MAINTENANCE_TYPE_LABELS.items()
            ],
            operational_statuses=[
                AdminEquipmentFilterOptionView(id=key, label=value)
                for key, value in OPERATIONAL_STATUS_LABELS.items()
            ],
            providers=_dedupe_options(
                AdminEquipmentFilterOptionView(id=provider, label=provider)
                for provider in [
                    *(row.equipment.provider_name for row in rows if row.equipment.provider_name),
                    *(
                        record.provider_name
                        for row in rows
                        for record in row.maintenance_records
                        if record.provider_name
                    ),
                ]
            ),
            risk_levels=[
                AdminEquipmentFilterOptionView(id=key, label=value)
                for key, value in RISK_LABELS.items()
            ],
            technicians=_dedupe_options(
                AdminEquipmentFilterOptionView(
                    id=record.technician_name, label=record.technician_name
                )
                for row in rows
                for record in row.maintenance_records
                if record.technician_name
            ),
        )

    def _build_metrics(
        self,
        rows: list[_EquipmentRow],
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> AdminEquipmentMetricsView:
        return AdminEquipmentMetricsView(
            corrective_open_count=sum(
                1
                for row in rows
                for record in row.maintenance_records
                if record.maintenance_type == MAINTENANCE_TYPE_CORRECTIVE
                and self._effective_record_status(record) in OPEN_MAINTENANCE_STATUSES
            ),
            high_risk_count=sum(1 for row in rows if self._is_high_risk_equipment(row.equipment)),
            operational_count=sum(
                1
                for row in rows
                if row.equipment.operational_status == EQUIPMENT_STATUS_OPERATIONAL
            ),
            out_of_service_count=sum(
                1
                for row in rows
                if row.equipment.operational_status == EQUIPMENT_STATUS_OUT_OF_SERVICE
            ),
            overdue_count=sum(1 for row in rows if self._is_overdue(row)),
            pending_maintenance_count=sum(
                1 for row in rows if self._maintenance_state(row) in OPEN_MAINTENANCE_STATUSES
            ),
            period_cost=sum(
                (self._period_cost(row, date_from=date_from, date_to=date_to) for row in rows),
                Decimal("0"),
            ),
            total_equipment_count=len(rows),
        )

    def _related_documents(
        self,
        session: Session,
        row: _EquipmentRow,
    ) -> list[AdminEquipmentRelatedDocumentView]:
        documents: list[AdminEquipmentRelatedDocumentView] = []
        for record in row.maintenance_records[:5]:
            documents.append(
                AdminEquipmentRelatedDocumentView(
                    document_id=record.id,
                    document_type="MAINTENANCE_RECORD",
                    folio=record.folio,
                    status=self._effective_record_status(record),
                )
            )
        for log in self._related_cleaning_logs(session, row):
            documents.append(
                AdminEquipmentRelatedDocumentView(
                    document_id=log.id,
                    document_type="CLEANING_LOG",
                    folio=log.folio,
                    route_hint="/admin/bitacoras-limpieza",
                    status=log.status,
                )
            )
        for verification in self._related_sanitary_verifications(session, row):
            documents.append(
                AdminEquipmentRelatedDocumentView(
                    document_id=verification.id,
                    document_type="SANITARY_VERIFICATION",
                    folio=verification.folio,
                    route_hint="/admin/verificaciones-sanitarias",
                    status=verification.status,
                )
            )
        return documents[:12]

    def _related_cleaning_logs(
        self,
        session: Session,
        row: _EquipmentRow,
    ) -> list[CleaningLog]:
        logs = (
            session.execute(
                select(CleaningLog)
                .where(CleaningLog.branch_id == row.equipment.branch_id)
                .order_by(CleaningLog.scheduled_at.desc(), CleaningLog.created_at.desc())
            )
            .scalars()
            .all()
        )
        return [
            log
            for log in logs
            if self._matches_area_or_equipment(
                area_name=log.area_name,
                equipment_name=log.equipment_name,
                row=row,
            )
        ][:5]

    def _related_sanitary_verifications(
        self,
        session: Session,
        row: _EquipmentRow,
    ) -> list[SanitaryVerification]:
        verifications = (
            session.execute(
                select(SanitaryVerification)
                .where(SanitaryVerification.branch_id == row.equipment.branch_id)
                .order_by(
                    SanitaryVerification.scheduled_at.desc(),
                    SanitaryVerification.created_at.desc(),
                )
            )
            .scalars()
            .all()
        )
        return [
            verification
            for verification in verifications
            if self._matches_area_or_equipment(
                area_name=verification.area_name,
                equipment_name=verification.equipment_name,
                row=row,
            )
        ][:5]

    def _matches_area_or_equipment(
        self,
        *,
        area_name: str | None,
        equipment_name: str | None,
        row: _EquipmentRow,
    ) -> bool:
        equipment_names = {row.equipment.name.casefold(), row.equipment.code.casefold()}
        if equipment_name and equipment_name.casefold() in equipment_names:
            return True
        if row.equipment.area_name and area_name:
            return row.equipment.area_name.casefold() == area_name.casefold()
        return False

    def _incident_references(self, row: _EquipmentRow) -> list[AdminEquipmentIncidentRelatedView]:
        seen: set[str] = set()
        references: list[AdminEquipmentIncidentRelatedView] = []
        for record in row.maintenance_records:
            if record.related_incident_reference and record.related_incident_reference not in seen:
                seen.add(record.related_incident_reference)
                references.append(
                    AdminEquipmentIncidentRelatedView(folio=record.related_incident_reference)
                )
        return references

    def _available_actions(self, row: _EquipmentRow) -> AdminEquipmentAvailableActionsView:
        current_open = self._current_open_record(row)
        is_editable = row.equipment.operational_status not in {
            EQUIPMENT_STATUS_RETIRED,
            EQUIPMENT_STATUS_INACTIVE,
        }
        return AdminEquipmentAvailableActionsView(
            can_cancel_maintenance=bool(current_open),
            can_complete_maintenance=bool(current_open),
            can_create_corrective=is_editable,
            can_create_preventive=is_editable,
            can_edit_equipment=is_editable,
            can_export=False,
            can_mark_operational=row.equipment.operational_status
            in {EQUIPMENT_STATUS_OUT_OF_SERVICE, EQUIPMENT_STATUS_UNDER_MAINTENANCE},
            can_mark_out_of_service=row.equipment.operational_status
            == EQUIPMENT_STATUS_OPERATIONAL,
            can_print=False,
            can_start_maintenance=bool(
                current_open and current_open.status != MAINTENANCE_STATUS_IN_PROGRESS
            ),
            note=(
                "Incidencias, adjuntos de archivo y exportacion requieren contratos backend "
                "dedicados."
            ),
        )

    def _warnings(self, row: _EquipmentRow) -> list[AdminEquipmentWarningView]:
        warnings: list[AdminEquipmentWarningView] = []
        if row.equipment.operational_status == EQUIPMENT_STATUS_OUT_OF_SERVICE:
            warnings.append(
                AdminEquipmentWarningView(
                    code="out_of_service",
                    message="El equipo esta fuera de servicio.",
                    severity="critical",
                )
            )
        if self._is_overdue(row):
            warnings.append(
                AdminEquipmentWarningView(
                    code="overdue",
                    message="El mantenimiento preventivo o una tarea abierta esta vencida.",
                    severity="critical"
                    if self._is_high_risk_equipment(row.equipment)
                    else "warning",
                )
            )
        if row.equipment.operational_status == EQUIPMENT_STATUS_UNDER_MAINTENANCE:
            warnings.append(
                AdminEquipmentWarningView(
                    code="under_maintenance",
                    message="El equipo esta en mantenimiento.",
                    severity="warning",
                )
            )
        if any(
            record.result
            in {
                MAINTENANCE_RESULT_FAILED,
                MAINTENANCE_RESULT_REQUIRES_FOLLOW_UP,
                MAINTENANCE_RESULT_COMPLETED_WITH_OBSERVATIONS,
            }
            for record in row.maintenance_records
            if record.status == MAINTENANCE_STATUS_COMPLETED
        ):
            warnings.append(
                AdminEquipmentWarningView(
                    code="follow_up",
                    message="El historial contiene mantenimiento fallido o con observaciones.",
                    severity="warning",
                )
            )
        if self._is_high_risk_equipment(row.equipment):
            warnings.append(
                AdminEquipmentWarningView(
                    code="high_risk",
                    message="Equipo critico o de alto riesgo operativo/sanitario.",
                    severity="warning",
                )
            )
        return warnings

    def _warning_state(self, row: _EquipmentRow) -> str:
        if row.equipment.operational_status == EQUIPMENT_STATUS_OUT_OF_SERVICE:
            return EQUIPMENT_WARNING_OUT_OF_SERVICE
        if self._is_overdue(row):
            return EQUIPMENT_WARNING_OVERDUE
        if row.equipment.operational_status == EQUIPMENT_STATUS_UNDER_MAINTENANCE:
            return EQUIPMENT_WARNING_UNDER_MAINTENANCE
        if self._has_unresolved_failed_maintenance(row):
            return EQUIPMENT_WARNING_FOLLOW_UP
        if self._is_high_risk_equipment(row.equipment):
            return EQUIPMENT_WARNING_HIGH_RISK
        return EQUIPMENT_WARNING_OK

    def _maintenance_state(self, row: _EquipmentRow) -> str:
        current_open = self._current_open_record(row)
        if current_open:
            return self._effective_record_status(current_open)
        if self._next_scheduled_maintenance_at(row) and self._is_overdue(row):
            return MAINTENANCE_STATUS_OVERDUE
        if self._last_completed(row):
            return "OK"
        return "NO_HISTORY"

    def _current_open_record(
        self,
        row: _EquipmentRow,
    ) -> EquipmentMaintenanceRecord | None:
        open_records = [
            record
            for record in row.maintenance_records
            if self._effective_record_status(record) in OPEN_MAINTENANCE_STATUSES
        ]
        return open_records[0] if open_records else None

    def _last_completed(self, row: _EquipmentRow) -> EquipmentMaintenanceRecord | None:
        completed = [
            (record, record.completed_at)
            for record in row.maintenance_records
            if record.status == MAINTENANCE_STATUS_COMPLETED and record.completed_at is not None
        ]
        return max(completed, key=lambda item: _as_utc(item[1]))[0] if completed else None

    def _next_scheduled_maintenance_at(self, row: _EquipmentRow) -> datetime | None:
        open_scheduled = [
            record.scheduled_at
            for record in row.maintenance_records
            if record.status in OPEN_MAINTENANCE_STATUSES and record.scheduled_at is not None
        ]
        if open_scheduled:
            return min(_as_utc(value) for value in open_scheduled)
        last_completed = self._last_completed(row)
        if (
            last_completed is not None
            and last_completed.completed_at is not None
            and row.equipment.maintenance_frequency_days
        ):
            return _as_utc(last_completed.completed_at) + timedelta(
                days=row.equipment.maintenance_frequency_days
            )
        return None

    def _effective_record_status(self, record: EquipmentMaintenanceRecord) -> str:
        if (
            record.status in {MAINTENANCE_STATUS_SCHEDULED, MAINTENANCE_STATUS_PENDING}
            and record.scheduled_at is not None
            and _as_utc(record.scheduled_at) < _utc_now()
        ):
            return MAINTENANCE_STATUS_OVERDUE
        return record.status

    def _record_warning_state(self, record: EquipmentMaintenanceRecord) -> str:
        effective_status = self._effective_record_status(record)
        if effective_status == MAINTENANCE_STATUS_OVERDUE:
            return EQUIPMENT_WARNING_OVERDUE
        if record.result in {MAINTENANCE_RESULT_FAILED, MAINTENANCE_RESULT_REQUIRES_FOLLOW_UP}:
            return EQUIPMENT_WARNING_FOLLOW_UP
        return EQUIPMENT_WARNING_OK

    def _is_overdue(self, row: _EquipmentRow) -> bool:
        next_at = self._next_scheduled_maintenance_at(row)
        return next_at is not None and next_at < _utc_now()

    def _is_high_risk_equipment(self, equipment: EquipmentAsset) -> bool:
        return (
            equipment.risk_level in {CLEANING_RISK_HIGH, CLEANING_RISK_CRITICAL}
            or equipment.is_critical
            or equipment.food_safety_critical
            or equipment.equipment_type
            in {
                EQUIPMENT_TYPE_OVEN,
                EQUIPMENT_TYPE_MIXER,
                EQUIPMENT_TYPE_REFRIGERATION,
                EQUIPMENT_TYPE_SANITATION,
            }
        )

    def _has_unresolved_failed_maintenance(self, row: _EquipmentRow) -> bool:
        last_completed = self._last_completed(row)
        return bool(
            last_completed
            and last_completed.result
            in {MAINTENANCE_RESULT_FAILED, MAINTENANCE_RESULT_REQUIRES_FOLLOW_UP}
        )

    def _period_cost(
        self,
        row: _EquipmentRow,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> Decimal:
        total = Decimal("0")
        for record in row.maintenance_records:
            if record.cost is None:
                continue
            if self._record_in_range(record, date_from=date_from, date_to=date_to):
                total += record.cost
        return total

    def _record_in_range(
        self,
        record: EquipmentMaintenanceRecord,
        *,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> bool:
        occurred_at = record.completed_at or record.scheduled_at or record.created_at
        occurred_at = _as_utc(occurred_at)
        if date_from is not None and occurred_at < date_from:
            return False
        if date_to is not None and occurred_at > date_to:
            return False
        return True

    def _open_incident_count(self, row: _EquipmentRow) -> int:
        return len(
            {
                record.related_incident_reference
                for record in row.maintenance_records
                if record.related_incident_reference
            }
        )

    def _warranty_note(self, equipment: EquipmentAsset) -> str | None:
        if equipment.warranty_expires_at is None:
            return None
        now_date = _utc_now().date()
        if equipment.warranty_expires_at >= now_date:
            return f"Garantia vigente hasta {equipment.warranty_expires_at.isoformat()}."
        return f"Garantia vencida el {equipment.warranty_expires_at.isoformat()}."

    def _status_after_completion(
        self,
        row: _EquipmentRow,
        command: AdminMaintenanceCompleteRequest,
    ) -> str:
        if command.equipment_status_after_service:
            return command.equipment_status_after_service
        if command.result == MAINTENANCE_RESULT_COMPLETED_SUCCESSFULLY:
            return EQUIPMENT_STATUS_OPERATIONAL
        if command.result in {MAINTENANCE_RESULT_FAILED, MAINTENANCE_RESULT_REQUIRES_FOLLOW_UP}:
            return EQUIPMENT_STATUS_OUT_OF_SERVICE
        if command.result == MAINTENANCE_RESULT_COMPLETED_WITH_OBSERVATIONS:
            return row.equipment.operational_status
        return row.equipment.operational_status

    def _validate_equipment_command(
        self,
        command: AdminEquipmentCreateRequest | AdminEquipmentUpdateRequest,
    ) -> None:
        if command.equipment_type not in VALID_EQUIPMENT_TYPES:
            raise EquipmentMaintenanceValidationError("Equipment type is not supported.")
        if command.area_type not in VALID_EQUIPMENT_AREA_TYPES:
            raise EquipmentMaintenanceValidationError("Equipment area type is not supported.")
        if command.operational_status not in VALID_EQUIPMENT_OPERATIONAL_STATUSES:
            raise EquipmentMaintenanceValidationError("Equipment status is not supported.")
        if (
            command.maintenance_frequency_days is not None
            and command.maintenance_frequency_days <= 0
        ):
            raise EquipmentMaintenanceValidationError(
                "Maintenance frequency must be greater than zero."
            )
        if (
            command.purchase_date is not None
            and command.warranty_expires_at is not None
            and command.warranty_expires_at < command.purchase_date
        ):
            raise EquipmentMaintenanceValidationError(
                "Warranty expiration must be after purchase date."
            )

    def _validate_maintenance_create(self, command: AdminMaintenanceCreateRequest) -> None:
        if command.maintenance_type not in VALID_MAINTENANCE_TYPES:
            raise EquipmentMaintenanceValidationError("Maintenance type is not supported.")
        if command.status not in VALID_MAINTENANCE_STATUSES:
            raise EquipmentMaintenanceValidationError("Maintenance status is not supported.")
        if command.status == MAINTENANCE_STATUS_SCHEDULED and command.scheduled_at is None:
            raise EquipmentMaintenanceValidationError("Scheduled maintenance needs a date.")
        if command.expected_cost is not None and command.expected_cost < 0:
            raise EquipmentMaintenanceValidationError("Expected cost cannot be negative.")

    def _validate_maintenance_completion(
        self,
        row: _EquipmentRow,
        command: AdminMaintenanceCompleteRequest,
    ) -> None:
        if command.result not in VALID_MAINTENANCE_RESULTS:
            raise EquipmentMaintenanceValidationError("Maintenance result is not supported.")
        if command.result in {
            MAINTENANCE_RESULT_FAILED,
            MAINTENANCE_RESULT_REQUIRES_FOLLOW_UP,
            MAINTENANCE_RESULT_COMPLETED_WITH_OBSERVATIONS,
        } and not _has_text(command.notes):
            raise EquipmentMaintenanceValidationError(
                "Notes are required for failed or partial maintenance."
            )
        if command.cost is not None and command.cost < 0:
            raise EquipmentMaintenanceValidationError("Maintenance cost cannot be negative.")
        if (
            command.result == MAINTENANCE_RESULT_FAILED
            and command.equipment_status_after_service == EQUIPMENT_STATUS_OPERATIONAL
            and self._is_high_risk_equipment(row.equipment)
        ):
            raise EquipmentMaintenanceValidationError(
                "Critical equipment cannot be marked operational after failed maintenance."
            )

    def _ensure_unique_code(
        self,
        session: Session,
        code: str,
        *,
        current_equipment_id: uuid.UUID | None = None,
    ) -> None:
        existing = session.execute(
            select(EquipmentAsset).where(EquipmentAsset.code == code)
        ).scalar_one_or_none()
        if existing is not None and existing.id != current_equipment_id:
            raise EquipmentMaintenanceValidationError("Equipment code already exists.")

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise EquipmentMaintenanceValidationError("Equipment branch does not exist.")
        return branch

    def _get_user(self, session: Session, user_id: uuid.UUID) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise EquipmentMaintenanceValidationError("Equipment user does not exist.")
        return user

    def _generate_maintenance_folio(self, session: Session) -> str:
        count = session.execute(select(EquipmentMaintenanceRecord.id)).scalars().all()
        return f"MTN-{len(count) + 1:06d}"

    def _matches_search(self, row: _EquipmentRow, search: str) -> bool:
        haystack = " ".join(
            [
                row.equipment.code,
                row.equipment.name,
                row.equipment.equipment_type,
                row.branch.name,
                row.equipment.area_name or "",
                row.equipment.brand or "",
                row.equipment.model or "",
                row.equipment.serial_number or "",
                row.equipment.provider_name or "",
                *(
                    " ".join(
                        [
                            record.folio,
                            record.provider_name or "",
                            record.technician_name or "",
                            record.related_incident_reference or "",
                            record.description,
                        ]
                    )
                    for record in row.maintenance_records
                ),
            ]
        ).casefold()
        return search.casefold() in haystack

    def _filter_by_code(
        self,
        rows: list[_EquipmentRow],
        value: str | None,
        getter: Callable[[_EquipmentRow], str | None],
    ) -> list[_EquipmentRow]:
        normalized = _normalize_optional(value)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if getter(row) == normalized]

    def _filter_by_text(
        self,
        rows: list[_EquipmentRow],
        value: str | None,
        getter: Callable[[_EquipmentRow], str],
    ) -> list[_EquipmentRow]:
        normalized = _normalize_optional(value)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if getter(row).casefold() == normalized.casefold()]

    def _record_equipment_change(
        self,
        session: Session,
        *,
        action: str,
        actor_id: uuid.UUID,
        branch_id: uuid.UUID,
        equipment: EquipmentAsset,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            action=action,
            actor_id=actor_id,
            branch_id=branch_id,
            metadata={
                "code": equipment.code,
                "equipment_type": equipment.equipment_type,
                "name": equipment.name,
                "operational_status": equipment.operational_status,
                "risk_level": equipment.risk_level,
            },
            request_id=request_id,
            resource_id=str(equipment.id),
            resource_type=EQUIPMENT_RESOURCE_TYPE,
        )

    def _record_maintenance_change(
        self,
        session: Session,
        *,
        action: str,
        actor_id: uuid.UUID,
        branch_id: uuid.UUID,
        equipment: EquipmentAsset,
        record: EquipmentMaintenanceRecord,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            action=action,
            actor_id=actor_id,
            branch_id=branch_id,
            metadata={
                "equipment_code": equipment.code,
                "equipment_id": str(equipment.id),
                "folio": record.folio,
                "maintenance_type": record.maintenance_type,
                "result": record.result,
                "status": record.status,
            },
            request_id=request_id,
            resource_id=str(record.id),
            resource_type=MAINTENANCE_RESOURCE_TYPE,
        )

    def _append_equipment_event(
        self,
        session: Session,
        *,
        event_name: str,
        equipment: EquipmentAsset,
        branch: Branch,
    ) -> None:
        self._outbox_writer.append(
            session,
            aggregate_id=str(equipment.id),
            aggregate_type=EQUIPMENT_RESOURCE_TYPE,
            event_name=event_name,
            payload={
                "branch_code": branch.code,
                "branch_id": str(branch.id),
                "code": equipment.code,
                "equipment_type": equipment.equipment_type,
                "name": equipment.name,
                "operational_status": equipment.operational_status,
                "risk_level": equipment.risk_level,
            },
        )

    def _append_maintenance_event(
        self,
        session: Session,
        *,
        event_name: str,
        equipment: EquipmentAsset,
        record: EquipmentMaintenanceRecord,
        branch: Branch,
    ) -> None:
        self._outbox_writer.append(
            session,
            aggregate_id=str(record.id),
            aggregate_type=MAINTENANCE_RESOURCE_TYPE,
            event_name=event_name,
            payload={
                "branch_code": branch.code,
                "equipment_code": equipment.code,
                "equipment_id": str(equipment.id),
                "folio": record.folio,
                "maintenance_type": record.maintenance_type,
                "result": record.result,
                "status": record.status,
            },
        )

    def _record_high_risk_alert(
        self,
        session: Session,
        actor_id: uuid.UUID,
        branch_id: uuid.UUID,
        equipment: EquipmentAsset,
        request_id: str | None,
    ) -> None:
        self._record_equipment_change(
            session,
            action=AUDIT_ACTION_EQUIPMENT_HIGH_RISK_NOTIFIED,
            actor_id=actor_id,
            branch_id=branch_id,
            equipment=equipment,
            request_id=request_id,
        )
        self._outbox_writer.append(
            session,
            aggregate_id=str(equipment.id),
            aggregate_type=EQUIPMENT_RESOURCE_TYPE,
            event_name=OUTBOX_EVENT_EQUIPMENT_HIGH_RISK_ALERT_V1,
            payload={
                "code": equipment.code,
                "name": equipment.name,
                "operational_status": equipment.operational_status,
                "risk_level": equipment.risk_level,
            },
        )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized if normalized else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _dedupe_options(
    options: Iterable[AdminEquipmentFilterOptionView],
) -> list[AdminEquipmentFilterOptionView]:
    result: dict[str, AdminEquipmentFilterOptionView] = {}
    for option in options:
        if option.id not in result:
            result[option.id] = option
    return sorted(result.values(), key=lambda option: option.label)
