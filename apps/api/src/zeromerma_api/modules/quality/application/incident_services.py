from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.actions import restrict_actions
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.quality.application.incident_schemas import (
    AdminIncidentAvailableActionsView,
    AdminIncidentCorrectiveActionView,
    AdminIncidentCreateRequest,
    AdminIncidentDescriptionClassificationView,
    AdminIncidentDetailView,
    AdminIncidentEvidenceView,
    AdminIncidentFilterOptionsView,
    AdminIncidentFilterOptionView,
    AdminIncidentFollowUpCreateRequest,
    AdminIncidentFollowUpView,
    AdminIncidentListItemView,
    AdminIncidentListResponse,
    AdminIncidentLocationScopeView,
    AdminIncidentMetricsView,
    AdminIncidentOverviewView,
    AdminIncidentRelatedDocumentView,
    AdminIncidentResolveRequest,
    AdminIncidentSourceDocumentView,
    AdminIncidentStatusRequest,
    AdminIncidentTimelineItemView,
    AdminIncidentUpdateRequest,
    AdminIncidentWarningView,
    IncidentSeverity,
    IncidentSourceType,
    IncidentStatus,
    IncidentType,
)
from zeromerma_api.modules.quality.domain.constants import (
    AUDIT_ACTION_INCIDENT_CREATED,
    AUDIT_ACTION_INCIDENT_FOLLOW_UP_ADDED,
    AUDIT_ACTION_INCIDENT_HIGH_RISK_NOTIFIED,
    AUDIT_ACTION_INCIDENT_REOPENED,
    AUDIT_ACTION_INCIDENT_RESOLVED,
    AUDIT_ACTION_INCIDENT_STATUS_CHANGED,
    AUDIT_ACTION_INCIDENT_UPDATED,
    INCIDENT_RESOURCE_TYPE,
    INCIDENT_SEVERITY_CRITICAL,
    INCIDENT_SEVERITY_HIGH,
    INCIDENT_SOURCE_CLEANING_LOG,
    INCIDENT_SOURCE_EQUIPMENT,
    INCIDENT_SOURCE_MANUAL,
    INCIDENT_SOURCE_SANITARY_VERIFICATION,
    INCIDENT_STATUS_CANCELLED,
    INCIDENT_STATUS_CLOSED,
    INCIDENT_STATUS_IN_PROGRESS,
    INCIDENT_STATUS_OPEN,
    INCIDENT_STATUS_RESOLVED,
    INCIDENT_TYPE_OTHER,
    INCIDENT_WARNING_HIGH_RISK,
    INCIDENT_WARNING_MISSING_EVIDENCE,
    INCIDENT_WARNING_OK,
    INCIDENT_WARNING_OVERDUE,
    INCIDENT_WARNING_UNASSIGNED,
    INCIDENT_WARNING_WAITING_ACTION,
    OUTBOX_EVENT_INCIDENT_CREATED_V1,
    OUTBOX_EVENT_INCIDENT_FOLLOW_UP_ADDED_V1,
    OUTBOX_EVENT_INCIDENT_HIGH_RISK_ALERT_V1,
    OUTBOX_EVENT_INCIDENT_REOPENED_V1,
    OUTBOX_EVENT_INCIDENT_RESOLVED_V1,
    OUTBOX_EVENT_INCIDENT_STATUS_CHANGED_V1,
    OUTBOX_EVENT_INCIDENT_UPDATED_V1,
    VALID_INCIDENT_SEVERITIES,
    VALID_INCIDENT_SOURCE_TYPES,
    VALID_INCIDENT_STATUSES,
    VALID_INCIDENT_TYPES,
)
from zeromerma_api.modules.quality.domain.exceptions import (
    IncidentNotFoundError,
    IncidentValidationError,
)
from zeromerma_api.modules.quality.infrastructure.models import (
    CleaningLog,
    EquipmentAsset,
    EquipmentMaintenanceRecord,
    QualityIncident,
    QualityIncidentFollowUp,
    SanitaryVerification,
)

_INCIDENT_SEVERITY_ADAPTER: TypeAdapter[IncidentSeverity] = TypeAdapter(IncidentSeverity)
_INCIDENT_SOURCE_TYPE_ADAPTER: TypeAdapter[IncidentSourceType] = TypeAdapter(IncidentSourceType)
_INCIDENT_STATUS_ADAPTER: TypeAdapter[IncidentStatus] = TypeAdapter(IncidentStatus)
_INCIDENT_TYPE_ADAPTER: TypeAdapter[IncidentType] = TypeAdapter(IncidentType)
INCIDENT_TYPE_LABELS = {
    "SANITATION_ISSUE": "Problema sanitario",
    "CLEANING_NON_COMPLIANCE": "Incumplimiento de limpieza",
    "EQUIPMENT_FAILURE": "Falla de equipo",
    "PRODUCTION_ISSUE": "Problema de produccion",
    "INVENTORY_ISSUE": "Problema de inventario",
    "TRANSFER_ISSUE": "Problema de transferencia",
    "WASTE_ISSUE": "Merma / perdida",
    "SAFETY_ISSUE": "Seguridad",
    "CUSTOMER_COMPLAINT": "Queja de cliente",
    "PROCESS_DEVIATION": "Desviacion de proceso",
    "OTHER": "Otro",
}

SOURCE_TYPE_LABELS = {
    INCIDENT_SOURCE_MANUAL: "Manual",
    INCIDENT_SOURCE_CLEANING_LOG: "Bitacora de limpieza",
    INCIDENT_SOURCE_SANITARY_VERIFICATION: "Verificacion sanitaria",
    INCIDENT_SOURCE_EQUIPMENT: "Equipo",
    "PRODUCTION": "Produccion",
    "INVENTORY": "Inventario",
    "TRANSFER": "Transferencia",
    "WASTE_MERMA": "Merma",
    "CUSTOMER_REPORT": "Reporte cliente",
    "CORRECTION": "Correccion",
}

STATUS_LABELS = {
    INCIDENT_STATUS_OPEN: "Abierta",
    "IN_REVIEW": "En revision",
    INCIDENT_STATUS_IN_PROGRESS: "En seguimiento",
    "WAITING_ACTION": "Esperando accion",
    INCIDENT_STATUS_RESOLVED: "Resuelta",
    INCIDENT_STATUS_CLOSED: "Cerrada",
    INCIDENT_STATUS_CANCELLED: "Cancelada",
}

SEVERITY_LABELS = {
    "LOW": "Baja",
    "MEDIUM": "Media",
    "HIGH": "Alta",
    "CRITICAL": "Critica",
}

FINAL_STATUSES = {INCIDENT_STATUS_RESOLVED, INCIDENT_STATUS_CLOSED, INCIDENT_STATUS_CANCELLED}


@dataclass(frozen=True)
class _IncidentRow:
    branch: Branch
    follow_ups: list[QualityIncidentFollowUp]
    incident: QualityIncident
    reported_by: User
    responsible: User | None


class AdminIncidentService:
    def __init__(
        self,
        *,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_incidents(
        self,
        session: Session,
        *,
        area_name: str | None,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        due_state: str | None,
        evidence_state: str | None,
        incident_type: str | None,
        page: int,
        page_size: int,
        related_document_state: str | None,
        reported_by_user_id: uuid.UUID | None,
        responsible_user_id: uuid.UUID | None,
        search: str | None,
        severity: str | None,
        source_type: str | None,
        status_filter: str | None,
        warning_state: str | None,
    ) -> AdminIncidentListResponse:
        rows = self._load_rows(session)
        rows = self._filter_by_text(rows, area_name, lambda row: row.incident.area_name or "")
        rows = self._filter_by_code(rows, branch_id, lambda row: row.branch.id)
        rows = self._filter_by_date(rows, date_from, date_to)
        rows = self._filter_by_code(rows, incident_type, lambda row: row.incident.incident_type)
        rows = self._filter_by_code(
            rows,
            reported_by_user_id,
            lambda row: row.incident.reported_by_user_id,
        )
        rows = self._filter_by_code(
            rows,
            responsible_user_id,
            lambda row: row.incident.responsible_user_id,
        )
        rows = self._filter_by_code(rows, severity, lambda row: row.incident.severity)
        rows = self._filter_by_code(rows, source_type, lambda row: row.incident.source_type)
        rows = self._filter_by_code(rows, status_filter, lambda row: row.incident.status)
        rows = self._filter_by_search(rows, search)

        normalized_due = _normalize_optional(due_state)
        if normalized_due == "overdue":
            rows = [row for row in rows if self._is_overdue(row.incident)]
        elif normalized_due == "not_overdue":
            rows = [row for row in rows if not self._is_overdue(row.incident)]

        normalized_evidence = _normalize_optional(evidence_state)
        if normalized_evidence == "with_evidence":
            rows = [row for row in rows if row.incident.has_evidence]
        elif normalized_evidence == "without_evidence":
            rows = [row for row in rows if not row.incident.has_evidence]

        normalized_related = _normalize_optional(related_document_state)
        if normalized_related == "with_related":
            rows = [row for row in rows if self._related_document_count(session, row) > 0]
        elif normalized_related == "without_related":
            rows = [row for row in rows if self._related_document_count(session, row) == 0]

        normalized_warning = _normalize_optional(warning_state)
        if normalized_warning and normalized_warning != "all":
            rows = [row for row in rows if self._warning_state(row.incident) == normalized_warning]

        rows.sort(key=lambda row: row.incident.created_at, reverse=True)
        total = len(rows)
        start = (page - 1) * page_size
        paged = rows[start : start + page_size]

        return AdminIncidentListResponse(
            filter_options=self._filter_options(rows),
            is_backend_connected=True,
            items=[self._to_list_item(session, row) for row in paged],
            metrics=self._metrics(rows),
            page=page,
            page_size=page_size,
            total=total,
        )

    def get_detail(self, session: Session, *, incident_id: uuid.UUID) -> AdminIncidentDetailView:
        return self._to_detail(session, self._get_row(session, incident_id))

    def create_incident(
        self,
        session: Session,
        *,
        command: AdminIncidentCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminIncidentDetailView:
        self._validate_create(command)
        branch = self._get_branch(session, command.branch_id)
        responsible = self._get_user(session, command.responsible_user_id, required=False)
        source_context = self._source_context(session, command)
        self._validate_source_branch(branch, source_context)

        now = _utc_now()
        incident = QualityIncident(
            area_name=command.area_name or source_context.area_name,
            branch_id=branch.id,
            corrective_action=command.corrective_action,
            created_at=now,
            description=command.description,
            due_at=_as_utc(command.due_at) if command.due_at else None,
            equipment_name=command.equipment_name or source_context.equipment_name,
            evidence_note=command.evidence_note,
            folio=self._generate_folio(session),
            food_safety_impact=command.food_safety_impact,
            has_evidence=_has_text(command.evidence_note),
            incident_type=command.incident_type,
            operational_impact=command.operational_impact,
            process_name=command.process_name or source_context.process_name,
            product_reference=command.product_reference,
            production_reference=command.production_reference,
            reported_by_user_id=current_user.id,
            responsible_user_id=responsible.id if responsible else None,
            risk_level=command.severity,
            severity=command.severity,
            source_document_id=source_context.document_id,
            source_reference=command.source_reference or source_context.reference,
            source_summary=command.source_summary or source_context.summary,
            source_type=command.source_type,
            status=INCIDENT_STATUS_OPEN,
            title=command.title,
            updated_at=now,
        )
        session.add(incident)
        try:
            session.flush()
        except IntegrityError as error:
            raise IncidentValidationError("Incident folio could not be generated.") from error

        if command.notes:
            session.add(
                QualityIncidentFollowUp(
                    created_at=now,
                    created_by_user_id=current_user.id,
                    incident_id=incident.id,
                    note=command.notes,
                )
            )

        self._sync_source_incident_reference(session, incident)
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_CREATED,
            actor_id=current_user.id,
            incident=incident,
            request_id=request_id,
        )
        self._append_event(session, event_name=OUTBOX_EVENT_INCIDENT_CREATED_V1, incident=incident)
        if self._is_high_risk(incident):
            self._record_high_risk_alert(session, current_user.id, incident, request_id)
        session.commit()
        return self._to_detail(session, self._get_row(session, incident.id))

    def update_incident(
        self,
        session: Session,
        *,
        incident_id: uuid.UUID,
        command: AdminIncidentUpdateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminIncidentDetailView:
        row = self._get_row(session, incident_id)
        incident = row.incident
        self._ensure_editable(incident)
        if command.severity and command.severity not in VALID_INCIDENT_SEVERITIES:
            raise IncidentValidationError("Unsupported incident severity.")
        if command.status and command.status not in VALID_INCIDENT_STATUSES:
            raise IncidentValidationError("Unsupported incident status.")
        responsible = self._get_user(session, command.responsible_user_id, required=False)
        for field_name in (
            "area_name",
            "corrective_action",
            "description",
            "equipment_name",
            "operational_impact",
            "process_name",
            "product_reference",
            "production_reference",
            "title",
        ):
            value = getattr(command, field_name)
            if value is not None:
                setattr(incident, field_name, value)
        if command.due_at is not None:
            incident.due_at = _as_utc(command.due_at)
        if command.evidence_note is not None:
            incident.evidence_note = command.evidence_note
            incident.has_evidence = _has_text(command.evidence_note)
        if command.food_safety_impact is not None:
            incident.food_safety_impact = command.food_safety_impact
        if command.responsible_user_id is not None:
            incident.responsible_user_id = responsible.id if responsible else None
        if command.severity is not None:
            incident.severity = command.severity
            incident.risk_level = command.severity
        if command.status is not None:
            incident.status = command.status
        incident.updated_at = _utc_now()
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_UPDATED,
            actor_id=current_user.id,
            incident=incident,
            request_id=request_id,
        )
        self._append_event(session, event_name=OUTBOX_EVENT_INCIDENT_UPDATED_V1, incident=incident)
        if self._is_high_risk(incident):
            self._record_high_risk_alert(session, current_user.id, incident, request_id)
        session.commit()
        return self._to_detail(session, self._get_row(session, incident_id))

    def add_follow_up(
        self,
        session: Session,
        *,
        incident_id: uuid.UUID,
        command: AdminIncidentFollowUpCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminIncidentDetailView:
        row = self._get_row(session, incident_id)
        incident = row.incident
        self._ensure_editable(incident)
        if command.status_change and command.status_change not in VALID_INCIDENT_STATUSES:
            raise IncidentValidationError("Unsupported incident status.")
        now = _utc_now()
        if command.status_change:
            incident.status = command.status_change
            incident.updated_at = now
        follow_up = QualityIncidentFollowUp(
            created_at=now,
            created_by_user_id=current_user.id,
            incident_id=incident.id,
            note=command.note,
            status_change=command.status_change,
        )
        session.add(follow_up)
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_FOLLOW_UP_ADDED,
            actor_id=current_user.id,
            incident=incident,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_INCIDENT_FOLLOW_UP_ADDED_V1,
            incident=incident,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, incident_id))

    def change_status(
        self,
        session: Session,
        *,
        incident_id: uuid.UUID,
        command: AdminIncidentStatusRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminIncidentDetailView:
        row = self._get_row(session, incident_id)
        incident = row.incident
        self._ensure_editable(incident)
        if command.status == INCIDENT_STATUS_RESOLVED:
            raise IncidentValidationError("Use the resolve endpoint to resolve an incident.")
        if command.status == INCIDENT_STATUS_CANCELLED and not _has_text(
            command.cancellation_reason
        ):
            raise IncidentValidationError("Cancellation requires a reason.")
        now = _utc_now()
        incident.status = command.status
        incident.cancellation_reason = command.cancellation_reason
        incident.updated_at = now
        if command.note:
            session.add(
                QualityIncidentFollowUp(
                    created_at=now,
                    created_by_user_id=current_user.id,
                    incident_id=incident.id,
                    note=command.note,
                    status_change=command.status,
                )
            )
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_STATUS_CHANGED,
            actor_id=current_user.id,
            incident=incident,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_INCIDENT_STATUS_CHANGED_V1,
            incident=incident,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, incident_id))

    def resolve_incident(
        self,
        session: Session,
        *,
        incident_id: uuid.UUID,
        command: AdminIncidentResolveRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminIncidentDetailView:
        row = self._get_row(session, incident_id)
        incident = row.incident
        if incident.status in {INCIDENT_STATUS_RESOLVED, INCIDENT_STATUS_CLOSED}:
            raise IncidentValidationError("Incident is already resolved or closed.")
        if incident.status == INCIDENT_STATUS_CANCELLED:
            raise IncidentValidationError("Cancelled incidents cannot be resolved.")
        now = _utc_now()
        incident.evidence_note = command.evidence_note or incident.evidence_note
        incident.has_evidence = incident.has_evidence or _has_text(command.evidence_note)
        incident.resolution_note = command.resolution_note
        incident.resolution_result = command.result
        incident.resolved_at = _as_utc(command.resolved_at) if command.resolved_at else now
        incident.status = INCIDENT_STATUS_RESOLVED
        incident.updated_at = now
        session.add(
            QualityIncidentFollowUp(
                created_at=now,
                created_by_user_id=current_user.id,
                incident_id=incident.id,
                note=command.resolution_note,
                status_change=INCIDENT_STATUS_RESOLVED,
            )
        )
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_RESOLVED,
            actor_id=current_user.id,
            incident=incident,
            request_id=request_id,
        )
        self._append_event(session, event_name=OUTBOX_EVENT_INCIDENT_RESOLVED_V1, incident=incident)
        session.commit()
        return self._to_detail(session, self._get_row(session, incident_id))

    def reopen_incident(
        self,
        session: Session,
        *,
        incident_id: uuid.UUID,
        command: AdminIncidentFollowUpCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminIncidentDetailView:
        row = self._get_row(session, incident_id)
        incident = row.incident
        if incident.status not in {INCIDENT_STATUS_RESOLVED, INCIDENT_STATUS_CLOSED}:
            raise IncidentValidationError("Only resolved or closed incidents can be reopened.")
        now = _utc_now()
        incident.status = INCIDENT_STATUS_OPEN
        incident.resolved_at = None
        incident.updated_at = now
        session.add(
            QualityIncidentFollowUp(
                created_at=now,
                created_by_user_id=current_user.id,
                incident_id=incident.id,
                note=command.note,
                status_change=INCIDENT_STATUS_OPEN,
            )
        )
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_REOPENED,
            actor_id=current_user.id,
            incident=incident,
            request_id=request_id,
        )
        self._append_event(session, event_name=OUTBOX_EVENT_INCIDENT_REOPENED_V1, incident=incident)
        session.commit()
        return self._to_detail(session, self._get_row(session, incident_id))

    def _load_rows(self, session: Session) -> list[_IncidentRow]:
        incidents = session.scalars(select(QualityIncident)).all()
        branch_ids = {incident.branch_id for incident in incidents}
        user_ids = {incident.reported_by_user_id for incident in incidents} | {
            incident.responsible_user_id
            for incident in incidents
            if incident.responsible_user_id is not None
        }
        branches = (
            {
                branch.id: branch
                for branch in session.scalars(select(Branch).where(Branch.id.in_(branch_ids))).all()
            }
            if branch_ids
            else {}
        )
        users = (
            {
                user.id: user
                for user in session.scalars(select(User).where(User.id.in_(user_ids))).all()
            }
            if user_ids
            else {}
        )
        follow_ups = session.scalars(select(QualityIncidentFollowUp)).all()
        follow_up_map: dict[uuid.UUID, list[QualityIncidentFollowUp]] = {}
        for follow_up in follow_ups:
            follow_up_map.setdefault(follow_up.incident_id, []).append(follow_up)
        return [
            _IncidentRow(
                branch=branches[incident.branch_id],
                follow_ups=sorted(
                    follow_up_map.get(incident.id, []),
                    key=lambda item: item.created_at,
                    reverse=True,
                ),
                incident=incident,
                reported_by=users[incident.reported_by_user_id],
                responsible=users.get(incident.responsible_user_id)
                if incident.responsible_user_id
                else None,
            )
            for incident in incidents
        ]

    def _get_row(self, session: Session, incident_id: uuid.UUID) -> _IncidentRow:
        rows = [row for row in self._load_rows(session) if row.incident.id == incident_id]
        if not rows:
            raise IncidentNotFoundError("Incident does not exist.")
        return rows[0]

    def _to_detail(self, session: Session, row: _IncidentRow) -> AdminIncidentDetailView:
        list_item = self._to_list_item(session, row)
        incident = row.incident
        return AdminIncidentDetailView(
            available_actions=self._available_actions(session, incident),
            corrective_action=AdminIncidentCorrectiveActionView(
                corrective_action=incident.corrective_action,
                current_progress=incident.status,
                due_at=incident.due_at,
                responsible_user_id=incident.responsible_user_id,
                responsible_user_name=row.responsible.full_name if row.responsible else None,
                resolution_note=incident.resolution_note,
                resolution_result=incident.resolution_result,
                resolved_at=incident.resolved_at,
            ),
            description_classification=AdminIncidentDescriptionClassificationView(
                description=incident.description,
                food_safety_impact=incident.food_safety_impact,
                incident_type=_INCIDENT_TYPE_ADAPTER.validate_python(incident.incident_type),
                notes=self._latest_note(row),
                operational_impact=incident.operational_impact,
                risk_level=_INCIDENT_SEVERITY_ADAPTER.validate_python(incident.risk_level),
                severity=_INCIDENT_SEVERITY_ADAPTER.validate_python(incident.severity),
            ),
            evidence=AdminIncidentEvidenceView(
                evidence_note=incident.evidence_note,
                has_evidence=incident.has_evidence,
            ),
            follow_ups=[self._follow_up_view(session, item) for item in row.follow_ups],
            location_scope=AdminIncidentLocationScopeView(
                area_name=incident.area_name,
                branch_code=row.branch.code,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                equipment_name=incident.equipment_name,
                process_name=incident.process_name,
                product_reference=incident.product_reference,
                production_reference=incident.production_reference,
            ),
            overview=AdminIncidentOverviewView(
                **list_item.model_dump(),
                resolved_at=incident.resolved_at,
            ),
            related_documents=self._related_documents(session, row),
            source_document=self._source_document_view(incident),
            timeline=self._timeline(session, row),
            warnings=list_item.warnings,
        )

    def _to_list_item(self, session: Session, row: _IncidentRow) -> AdminIncidentListItemView:
        incident = row.incident
        return AdminIncidentListItemView(
            area_name=incident.area_name,
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            created_at=incident.created_at,
            due_at=incident.due_at,
            folio=incident.folio,
            has_evidence=incident.has_evidence,
            id=incident.id,
            incident_type=_INCIDENT_TYPE_ADAPTER.validate_python(incident.incident_type),
            related_document_count=self._related_document_count(session, row),
            reported_by_user_id=incident.reported_by_user_id,
            reported_by_user_name=row.reported_by.full_name,
            responsible_user_id=incident.responsible_user_id,
            responsible_user_name=row.responsible.full_name if row.responsible else None,
            severity=_INCIDENT_SEVERITY_ADAPTER.validate_python(incident.severity),
            source_reference=incident.source_reference,
            source_type=_INCIDENT_SOURCE_TYPE_ADAPTER.validate_python(incident.source_type),
            status=_INCIDENT_STATUS_ADAPTER.validate_python(incident.status),
            title=incident.title,
            updated_at=incident.updated_at,
            warning_state=self._warning_state(incident),
            warnings=self._warnings(incident),
        )

    def _filter_options(self, rows: list[_IncidentRow]) -> AdminIncidentFilterOptionsView:
        return AdminIncidentFilterOptionsView(
            areas=_dedupe_options(
                AdminIncidentFilterOptionView(
                    id=row.incident.area_name,
                    label=row.incident.area_name,
                )
                for row in rows
                if row.incident.area_name
            ),
            branches=_dedupe_options(
                AdminIncidentFilterOptionView(id=str(row.branch.id), label=row.branch.name)
                for row in rows
            ),
            due_states=[
                AdminIncidentFilterOptionView(id="overdue", label="Vencidas"),
                AdminIncidentFilterOptionView(id="not_overdue", label="No vencidas"),
            ],
            evidence_states=[
                AdminIncidentFilterOptionView(id="with_evidence", label="Con evidencia"),
                AdminIncidentFilterOptionView(id="without_evidence", label="Sin evidencia"),
            ],
            incident_types=[
                AdminIncidentFilterOptionView(id=key, label=value)
                for key, value in INCIDENT_TYPE_LABELS.items()
            ],
            related_document_states=[
                AdminIncidentFilterOptionView(id="with_related", label="Con documentos"),
                AdminIncidentFilterOptionView(id="without_related", label="Sin documentos"),
            ],
            reported_by_users=_dedupe_options(
                AdminIncidentFilterOptionView(
                    id=str(row.reported_by.id),
                    label=row.reported_by.full_name,
                )
                for row in rows
            ),
            responsible_users=_dedupe_options(
                AdminIncidentFilterOptionView(
                    id=str(row.responsible.id),
                    label=row.responsible.full_name,
                )
                for row in rows
                if row.responsible
            ),
            severities=[
                AdminIncidentFilterOptionView(id=key, label=value)
                for key, value in SEVERITY_LABELS.items()
            ],
            source_types=[
                AdminIncidentFilterOptionView(id=key, label=value)
                for key, value in SOURCE_TYPE_LABELS.items()
            ],
            statuses=[
                AdminIncidentFilterOptionView(id=key, label=value)
                for key, value in STATUS_LABELS.items()
            ],
        )

    def _metrics(self, rows: list[_IncidentRow]) -> AdminIncidentMetricsView:
        return AdminIncidentMetricsView(
            high_risk_count=sum(1 for row in rows if self._is_high_risk(row.incident)),
            in_progress_count=sum(
                1
                for row in rows
                if row.incident.status in {INCIDENT_STATUS_IN_PROGRESS, "WAITING_ACTION"}
            ),
            open_count=sum(1 for row in rows if row.incident.status == INCIDENT_STATUS_OPEN),
            overdue_count=sum(1 for row in rows if self._is_overdue(row.incident)),
            resolved_count=sum(
                1 for row in rows if row.incident.status == INCIDENT_STATUS_RESOLVED
            ),
            sanitary_generated_count=sum(
                1
                for row in rows
                if row.incident.source_type == INCIDENT_SOURCE_SANITARY_VERIFICATION
            ),
            total_count=len(rows),
            with_evidence_count=sum(1 for row in rows if row.incident.has_evidence),
        )

    def _validate_create(self, command: AdminIncidentCreateRequest) -> None:
        if command.incident_type not in VALID_INCIDENT_TYPES:
            raise IncidentValidationError("Unsupported incident type.")
        if command.severity not in VALID_INCIDENT_SEVERITIES:
            raise IncidentValidationError("Unsupported incident severity.")
        if command.source_type not in VALID_INCIDENT_SOURCE_TYPES:
            raise IncidentValidationError("Unsupported incident source type.")
        if command.incident_type == INCIDENT_TYPE_OTHER and not _has_text(command.notes):
            raise IncidentValidationError("Other incident type requires notes.")
        if not _has_text(command.title):
            raise IncidentValidationError("Incident title is required.")
        if not _has_text(command.description):
            raise IncidentValidationError("Incident description is required.")

    def _source_context(
        self,
        session: Session,
        command: AdminIncidentCreateRequest,
    ) -> _SourceContext:
        if command.source_type == INCIDENT_SOURCE_MANUAL:
            return _SourceContext()
        if command.source_document_id is None:
            raise IncidentValidationError("Source document id is required for this source type.")
        if command.source_type == INCIDENT_SOURCE_CLEANING_LOG:
            log = session.get(CleaningLog, command.source_document_id)
            if log is None:
                raise IncidentValidationError("Cleaning log source does not exist.")
            return _SourceContext(
                area_name=log.area_name,
                branch_id=log.branch_id,
                document_id=log.id,
                equipment_name=log.equipment_name,
                reference=log.folio,
                summary=log.task_name,
            )
        if command.source_type == INCIDENT_SOURCE_SANITARY_VERIFICATION:
            verification = session.get(SanitaryVerification, command.source_document_id)
            if verification is None:
                raise IncidentValidationError("Sanitary verification source does not exist.")
            return _SourceContext(
                area_name=verification.area_name,
                branch_id=verification.branch_id,
                document_id=verification.id,
                equipment_name=verification.equipment_name,
                process_name=verification.process_name,
                reference=verification.folio,
                summary=verification.template_name,
            )
        if command.source_type == INCIDENT_SOURCE_EQUIPMENT:
            equipment = session.get(EquipmentAsset, command.source_document_id)
            if equipment is None:
                raise IncidentValidationError("Equipment source does not exist.")
            return _SourceContext(
                area_name=equipment.area_name,
                branch_id=equipment.branch_id,
                document_id=equipment.id,
                equipment_name=equipment.name,
                reference=equipment.code,
                summary=equipment.name,
            )
        return _SourceContext(
            document_id=command.source_document_id,
            reference=command.source_reference,
            summary=command.source_summary,
        )

    def _sync_source_incident_reference(self, session: Session, incident: QualityIncident) -> None:
        if (
            incident.source_type == INCIDENT_SOURCE_SANITARY_VERIFICATION
            and incident.source_document_id
        ):
            verification = session.get(SanitaryVerification, incident.source_document_id)
            if verification:
                verification.has_incident = True
                verification.incident_reference = incident.folio
                verification.updated_at = _utc_now()
        if incident.source_type == INCIDENT_SOURCE_EQUIPMENT and incident.source_document_id:
            record = session.scalars(
                select(EquipmentMaintenanceRecord).where(
                    EquipmentMaintenanceRecord.related_incident_reference == incident.folio
                )
            ).first()
            if record:
                record.related_incident_reference = incident.folio

    def _source_document_view(self, incident: QualityIncident) -> AdminIncidentSourceDocumentView:
        return AdminIncidentSourceDocumentView(
            route_hint=self._route_for_source(incident.source_type),
            source_document_id=incident.source_document_id,
            source_reference=incident.source_reference,
            source_summary=incident.source_summary,
            source_type=_INCIDENT_SOURCE_TYPE_ADAPTER.validate_python(incident.source_type),
        )

    def _related_documents(
        self,
        session: Session,
        row: _IncidentRow,
    ) -> list[AdminIncidentRelatedDocumentView]:
        incident = row.incident
        documents: list[AdminIncidentRelatedDocumentView] = []
        if incident.source_document_id and incident.source_reference:
            documents.append(
                AdminIncidentRelatedDocumentView(
                    document_id=str(incident.source_document_id),
                    document_type=incident.source_type.lower(),
                    folio=incident.source_reference,
                    route_hint=self._route_for_source(incident.source_type),
                    status="SOURCE",
                )
            )
        for verification in session.scalars(
            select(SanitaryVerification).where(
                SanitaryVerification.incident_reference == incident.folio
            )
        ).all():
            documents.append(
                AdminIncidentRelatedDocumentView(
                    document_id=str(verification.id),
                    document_type="sanitary_verification",
                    folio=verification.folio,
                    route_hint="/admin/verificaciones-sanitarias",
                    status=verification.status,
                )
            )
        for record in session.scalars(
            select(EquipmentMaintenanceRecord).where(
                EquipmentMaintenanceRecord.related_incident_reference == incident.folio
            )
        ).all():
            documents.append(
                AdminIncidentRelatedDocumentView(
                    document_id=str(record.id),
                    document_type="equipment_maintenance",
                    folio=record.folio,
                    route_hint="/admin/mantenimiento-equipos",
                    status=record.status,
                )
            )
        return documents

    def _related_document_count(self, session: Session, row: _IncidentRow) -> int:
        return len(self._related_documents(session, row))

    def _timeline(self, session: Session, row: _IncidentRow) -> list[AdminIncidentTimelineItemView]:
        incident = row.incident
        items = [
            AdminIncidentTimelineItemView(
                label="Incidencia creada",
                note=incident.title,
                occurred_at=incident.created_at,
                user_name=row.reported_by.full_name,
            )
        ]
        for follow_up in reversed(row.follow_ups):
            user = self._get_user(session, follow_up.created_by_user_id, required=True)
            items.append(
                AdminIncidentTimelineItemView(
                    label="Seguimiento agregado",
                    note=follow_up.note,
                    occurred_at=follow_up.created_at,
                    user_name=user.full_name if user else None,
                )
            )
        if incident.resolved_at:
            items.append(
                AdminIncidentTimelineItemView(
                    label="Incidencia resuelta",
                    note=incident.resolution_note,
                    occurred_at=incident.resolved_at,
                    user_name=None,
                )
            )
        return sorted(items, key=lambda item: item.occurred_at)

    def _available_actions(
        self, session: Session, incident: QualityIncident
    ) -> AdminIncidentAvailableActionsView:
        is_final = incident.status in FINAL_STATUSES
        is_resolved_or_closed = incident.status in {
            INCIDENT_STATUS_RESOLVED,
            INCIDENT_STATUS_CLOSED,
        }
        return restrict_actions(
            session,
            AdminIncidentAvailableActionsView(
                can_add_evidence=not is_final,
                can_add_follow_up=not is_final,
                can_assign=not is_final,
                can_cancel=incident.status not in FINAL_STATUSES,
                can_create_corrective_action=not is_final,
                can_create_maintenance=incident.incident_type == "EQUIPMENT_FAILURE"
                and not is_final,
                can_export=False,
                can_mark_in_progress=not is_final,
                can_print=False,
                can_reopen=is_resolved_or_closed,
                can_resolve=incident.status not in FINAL_STATUSES,
                note=(
                    "Adjuntos de archivo, exportacion y creacion directa de mantenimiento "
                    "requieren "
                    "contratos backend dedicados; los documentos origen permanecen inmutables."
                ),
            ),
            {
                "can_add_evidence": "quality_hygiene.manage",
                "can_add_follow_up": "quality_hygiene.manage",
                "can_assign": "quality_hygiene.manage",
                "can_cancel": "quality_hygiene.manage",
                "can_create_corrective_action": "quality_hygiene.manage",
                "can_create_maintenance": "quality_hygiene.manage",
                "can_mark_in_progress": "quality_hygiene.manage",
                "can_reopen": "quality_hygiene.manage",
                "can_resolve": "quality_hygiene.manage",
            },
            branch_ids=(incident.branch_id,),
            global_only=False,
        )

    def _follow_up_view(
        self,
        session: Session,
        follow_up: QualityIncidentFollowUp,
    ) -> AdminIncidentFollowUpView:
        user = self._get_user(session, follow_up.created_by_user_id, required=True)
        return AdminIncidentFollowUpView(
            created_at=follow_up.created_at,
            created_by_user_id=follow_up.created_by_user_id,
            created_by_user_name=user.full_name if user else "Usuario",
            id=follow_up.id,
            note=follow_up.note,
            status_change=follow_up.status_change,
        )

    def _warnings(self, incident: QualityIncident) -> list[AdminIncidentWarningView]:
        warnings: list[AdminIncidentWarningView] = []
        if self._is_high_risk(incident) and incident.status not in FINAL_STATUSES:
            warnings.append(
                AdminIncidentWarningView(
                    code=INCIDENT_WARNING_HIGH_RISK,
                    message="Incidencia de alto riesgo.",
                    severity=(
                        "critical" if incident.severity == INCIDENT_SEVERITY_CRITICAL else "warning"
                    ),
                )
            )
        if self._is_overdue(incident):
            warnings.append(
                AdminIncidentWarningView(
                    code=INCIDENT_WARNING_OVERDUE,
                    message="La incidencia esta vencida.",
                    severity="critical",
                )
            )
        if self._is_high_risk(incident) and incident.responsible_user_id is None:
            warnings.append(
                AdminIncidentWarningView(
                    code=INCIDENT_WARNING_UNASSIGNED,
                    message="Incidencia de alto riesgo sin responsable asignado.",
                    severity="warning",
                )
            )
        if self._is_high_risk(incident) and not incident.has_evidence:
            warnings.append(
                AdminIncidentWarningView(
                    code=INCIDENT_WARNING_MISSING_EVIDENCE,
                    message="Incidencia de alto riesgo sin evidencia adjunta.",
                    severity="warning",
                )
            )
        if incident.status == "WAITING_ACTION":
            warnings.append(
                AdminIncidentWarningView(
                    code=INCIDENT_WARNING_WAITING_ACTION,
                    message="La incidencia esta esperando accion correctiva.",
                    severity="warning",
                )
            )
        return warnings or [
            AdminIncidentWarningView(
                code=INCIDENT_WARNING_OK,
                message="Sin advertencias.",
                severity="info",
            )
        ]

    def _warning_state(self, incident: QualityIncident) -> str:
        warnings = self._warnings(incident)
        return warnings[0].code if warnings else INCIDENT_WARNING_OK

    def _latest_note(self, row: _IncidentRow) -> str | None:
        return row.follow_ups[0].note if row.follow_ups else None

    def _is_high_risk(self, incident: QualityIncident) -> bool:
        return incident.severity in {INCIDENT_SEVERITY_HIGH, INCIDENT_SEVERITY_CRITICAL}

    def _is_overdue(self, incident: QualityIncident) -> bool:
        return (
            incident.due_at is not None
            and _as_utc(incident.due_at) < _utc_now()
            and incident.status not in FINAL_STATUSES
        )

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise IncidentValidationError("Branch does not exist.")
        return branch

    def _get_user(
        self,
        session: Session,
        user_id: uuid.UUID | None,
        *,
        required: bool,
    ) -> User | None:
        if user_id is None:
            if required:
                raise IncidentValidationError("User is required.")
            return None
        user = session.get(User, user_id)
        if user is None and required:
            raise IncidentValidationError("User does not exist.")
        return user

    def _validate_source_branch(self, branch: Branch, source_context: _SourceContext) -> None:
        if source_context.branch_id is not None and source_context.branch_id != branch.id:
            raise IncidentValidationError("Source document belongs to a different branch.")

    def _ensure_editable(self, incident: QualityIncident) -> None:
        if incident.status in {INCIDENT_STATUS_CLOSED, INCIDENT_STATUS_CANCELLED}:
            raise IncidentValidationError("Closed or cancelled incidents are read-only.")

    def _generate_folio(self, session: Session) -> str:
        count = session.scalar(select(func.count()).select_from(QualityIncident)) or 0
        return f"INC-{count + 1:06d}"

    def _route_for_source(self, source_type: str) -> str | None:
        routes = {
            INCIDENT_SOURCE_CLEANING_LOG: "/admin/bitacoras-limpieza",
            INCIDENT_SOURCE_SANITARY_VERIFICATION: "/admin/verificaciones-sanitarias",
            INCIDENT_SOURCE_EQUIPMENT: "/admin/mantenimiento-equipos",
            "PRODUCTION": "/admin/produccion",
            "INVENTORY": "/admin/inventario",
            "TRANSFER": "/admin/transferencias",
            "WASTE_MERMA": "/admin/merma",
            "CORRECTION": "/admin/devoluciones-correcciones",
        }
        return routes.get(source_type)

    def _filter_by_code(
        self,
        rows: list[_IncidentRow],
        value: object,
        getter: Callable[[_IncidentRow], str | uuid.UUID | None],
    ) -> list[_IncidentRow]:
        normalized = _normalize_optional(str(value) if value is not None else None)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if str(getter(row)) == normalized]

    def _filter_by_text(
        self,
        rows: list[_IncidentRow],
        value: str | None,
        getter: Callable[[_IncidentRow], str],
    ) -> list[_IncidentRow]:
        normalized = _normalize_optional(value)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if getter(row).casefold() == normalized.casefold()]

    def _filter_by_date(
        self,
        rows: list[_IncidentRow],
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> list[_IncidentRow]:
        if date_from:
            rows = [row for row in rows if _as_utc(row.incident.created_at) >= _as_utc(date_from)]
        if date_to:
            rows = [row for row in rows if _as_utc(row.incident.created_at) <= _as_utc(date_to)]
        return rows

    def _filter_by_search(self, rows: list[_IncidentRow], search: str | None) -> list[_IncidentRow]:
        normalized = _normalize_optional(search)
        if not normalized:
            return rows
        needle = normalized.casefold()
        return [
            row
            for row in rows
            if needle
            in " ".join(
                [
                    row.incident.folio,
                    row.incident.title,
                    row.incident.description,
                    row.incident.source_reference or "",
                    row.incident.area_name or "",
                    row.responsible.full_name if row.responsible else "",
                ]
            ).casefold()
        ]

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        actor_id: uuid.UUID,
        incident: QualityIncident,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            action=action,
            actor_id=actor_id,
            branch_id=incident.branch_id,
            metadata={
                "folio": incident.folio,
                "severity": incident.severity,
                "source_type": incident.source_type,
                "status": incident.status,
                "title": incident.title,
            },
            request_id=request_id,
            resource_id=str(incident.id),
            resource_type=INCIDENT_RESOURCE_TYPE,
        )

    def _append_event(
        self,
        session: Session,
        *,
        event_name: str,
        incident: QualityIncident,
    ) -> None:
        self._outbox_writer.append(
            session,
            aggregate_id=str(incident.id),
            aggregate_type=INCIDENT_RESOURCE_TYPE,
            event_name=event_name,
            payload={
                "branch_id": str(incident.branch_id),
                "folio": incident.folio,
                "severity": incident.severity,
                "source_reference": incident.source_reference,
                "source_type": incident.source_type,
                "status": incident.status,
                "title": incident.title,
            },
        )

    def _record_high_risk_alert(
        self,
        session: Session,
        actor_id: uuid.UUID,
        incident: QualityIncident,
        request_id: str | None,
    ) -> None:
        self._record_change(
            session,
            action=AUDIT_ACTION_INCIDENT_HIGH_RISK_NOTIFIED,
            actor_id=actor_id,
            incident=incident,
            request_id=request_id,
        )
        self._outbox_writer.append(
            session,
            aggregate_id=str(incident.id),
            aggregate_type=INCIDENT_RESOURCE_TYPE,
            event_name=OUTBOX_EVENT_INCIDENT_HIGH_RISK_ALERT_V1,
            payload={
                "branch_id": str(incident.branch_id),
                "folio": incident.folio,
                "severity": incident.severity,
                "source_type": incident.source_type,
                "title": incident.title,
            },
        )


@dataclass(frozen=True)
class _SourceContext:
    area_name: str | None = None
    branch_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    equipment_name: str | None = None
    process_name: str | None = None
    reference: str | None = None
    summary: str | None = None


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
    options: Iterable[AdminIncidentFilterOptionView],
) -> list[AdminIncidentFilterOptionView]:
    result: dict[str, AdminIncidentFilterOptionView] = {}
    for option in options:
        if option.id not in result:
            result[option.id] = option
    return sorted(result.values(), key=lambda option: option.label)
