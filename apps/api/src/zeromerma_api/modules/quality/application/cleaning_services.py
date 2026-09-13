from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.actions import restrict_actions
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.application.visibility import operational_user_predicate
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.quality.application.cleaning_schemas import (
    AdminCleaningAvailableActionsView,
    AdminCleaningChecklistItemInput,
    AdminCleaningChecklistItemView,
    AdminCleaningEvidenceView,
    AdminCleaningFilterOptionsView,
    AdminCleaningFilterOptionView,
    AdminCleaningLocationAreaView,
    AdminCleaningLogCancelRequest,
    AdminCleaningLogCompleteRequest,
    AdminCleaningLogCreateRequest,
    AdminCleaningLogDetailView,
    AdminCleaningLogListItemView,
    AdminCleaningLogListResponse,
    AdminCleaningMetricsView,
    AdminCleaningObservationsView,
    AdminCleaningOverviewView,
    AdminCleaningRelatedDocumentView,
    AdminCleaningTaskTemplateView,
    AdminCleaningTemplateItemView,
    AdminCleaningTemplateView,
    AdminCleaningWarningView,
    CleaningLogStatus,
    CleaningRiskLevel,
)
from zeromerma_api.modules.quality.domain.constants import (
    AUDIT_ACTION_CLEANING_LOG_CANCELLED,
    AUDIT_ACTION_CLEANING_LOG_COMPLETED,
    AUDIT_ACTION_CLEANING_LOG_CREATED,
    AUDIT_ACTION_CLEANING_LOG_HIGH_RISK_NOTIFIED,
    CLEANING_AREA_TYPE_COUNTER,
    CLEANING_AREA_TYPE_CUSTOMER,
    CLEANING_AREA_TYPE_EQUIPMENT,
    CLEANING_AREA_TYPE_EXTERIOR,
    CLEANING_AREA_TYPE_OTHER,
    CLEANING_AREA_TYPE_PRODUCTION,
    CLEANING_AREA_TYPE_RESTROOM,
    CLEANING_AREA_TYPE_STORAGE,
    CLEANING_FREQUENCY_AS_NEEDED,
    CLEANING_FREQUENCY_DAILY,
    CLEANING_FREQUENCY_MONTHLY,
    CLEANING_FREQUENCY_PER_SHIFT,
    CLEANING_FREQUENCY_WEEKLY,
    CLEANING_LOG_STATUS_CANCELLED,
    CLEANING_LOG_STATUS_COMPLETED,
    CLEANING_LOG_STATUS_IN_PROGRESS,
    CLEANING_LOG_STATUS_MISSED,
    CLEANING_LOG_STATUS_PENDING,
    CLEANING_LOG_STATUS_REQUIRES_REVIEW,
    CLEANING_LOG_STATUS_SCHEDULED,
    CLEANING_RESOURCE_TYPE,
    CLEANING_RISK_CRITICAL,
    CLEANING_RISK_HIGH,
    CLEANING_RISK_LOW,
    CLEANING_RISK_MEDIUM,
    CLEANING_SHIFT_AFTERNOON,
    CLEANING_SHIFT_MIXED,
    CLEANING_SHIFT_MORNING,
    CLEANING_SHIFT_NIGHT,
    CLEANING_TYPE_DEEP,
    CLEANING_TYPE_EQUIPMENT,
    CLEANING_TYPE_OTHER,
    CLEANING_TYPE_ROUTINE,
    CLEANING_TYPE_SANITATION,
    CLEANING_TYPE_SPILL_RESPONSE,
    CLEANING_WARNING_HIGH_RISK,
    CLEANING_WARNING_INCOMPLETE,
    CLEANING_WARNING_OK,
    CLEANING_WARNING_OVERDUE,
    CLEANING_WARNING_REVIEW,
    OUTBOX_EVENT_CLEANING_LOG_CANCELLED_V1,
    OUTBOX_EVENT_CLEANING_LOG_COMPLETED_V1,
    OUTBOX_EVENT_CLEANING_LOG_CREATED_V1,
    OUTBOX_EVENT_CLEANING_LOG_HIGH_RISK_ALERT_V1,
    VALID_CLEANING_AREA_TYPES,
    VALID_CLEANING_RISK_LEVELS,
    VALID_CLEANING_SHIFTS,
    VALID_CLEANING_TYPES,
)
from zeromerma_api.modules.quality.domain.exceptions import (
    CleaningLogNotFoundError,
    CleaningLogValidationError,
)
from zeromerma_api.modules.quality.infrastructure.models import (
    CleaningLog,
    CleaningLogChecklistItem,
    CleaningTemplate,
    CleaningTemplateItem,
)

_CLEANING_LOG_STATUS_ADAPTER: TypeAdapter[CleaningLogStatus] = TypeAdapter(CleaningLogStatus)
_CLEANING_RISK_LEVEL_ADAPTER: TypeAdapter[CleaningRiskLevel] = TypeAdapter(CleaningRiskLevel)
AREA_TYPE_LABELS = {
    CLEANING_AREA_TYPE_PRODUCTION: "Produccion",
    CLEANING_AREA_TYPE_COUNTER: "Mostrador / exhibicion",
    CLEANING_AREA_TYPE_STORAGE: "Almacen",
    CLEANING_AREA_TYPE_RESTROOM: "Sanitario",
    CLEANING_AREA_TYPE_CUSTOMER: "Area de clientes",
    CLEANING_AREA_TYPE_EQUIPMENT: "Equipo",
    CLEANING_AREA_TYPE_EXTERIOR: "Exterior",
    CLEANING_AREA_TYPE_OTHER: "Otra area",
}

FREQUENCY_LABELS = {
    CLEANING_FREQUENCY_PER_SHIFT: "Por turno",
    CLEANING_FREQUENCY_DAILY: "Diaria",
    CLEANING_FREQUENCY_WEEKLY: "Semanal",
    CLEANING_FREQUENCY_MONTHLY: "Mensual",
    CLEANING_FREQUENCY_AS_NEEDED: "Segun necesidad",
}

CLEANING_TYPE_LABELS = {
    CLEANING_TYPE_ROUTINE: "Limpieza rutinaria",
    CLEANING_TYPE_DEEP: "Limpieza profunda",
    CLEANING_TYPE_EQUIPMENT: "Equipo",
    CLEANING_TYPE_SANITATION: "Sanitizacion",
    CLEANING_TYPE_SPILL_RESPONSE: "Derrame / emergencia",
    CLEANING_TYPE_OTHER: "Otra",
}

RISK_LABELS = {
    CLEANING_RISK_LOW: "Bajo",
    CLEANING_RISK_MEDIUM: "Medio",
    CLEANING_RISK_HIGH: "Alto",
    CLEANING_RISK_CRITICAL: "Critico",
}

SHIFT_LABELS = {
    CLEANING_SHIFT_MORNING: "Matutino",
    CLEANING_SHIFT_AFTERNOON: "Vespertino",
    CLEANING_SHIFT_NIGHT: "Nocturno",
    CLEANING_SHIFT_MIXED: "Mixto",
}

STATUS_LABELS = {
    CLEANING_LOG_STATUS_SCHEDULED: "Programada",
    CLEANING_LOG_STATUS_PENDING: "Pendiente",
    CLEANING_LOG_STATUS_IN_PROGRESS: "En proceso",
    CLEANING_LOG_STATUS_COMPLETED: "Completada",
    CLEANING_LOG_STATUS_MISSED: "Vencida / no realizada",
    CLEANING_LOG_STATUS_CANCELLED: "Cancelada",
    CLEANING_LOG_STATUS_REQUIRES_REVIEW: "Por revisar",
}

OPEN_STATUSES = {
    CLEANING_LOG_STATUS_SCHEDULED,
    CLEANING_LOG_STATUS_PENDING,
    CLEANING_LOG_STATUS_IN_PROGRESS,
}

FINAL_STATUSES = {
    CLEANING_LOG_STATUS_COMPLETED,
    CLEANING_LOG_STATUS_CANCELLED,
    CLEANING_LOG_STATUS_MISSED,
}


@dataclass(frozen=True)
class _CleaningRow:
    branch: Branch
    checklist_items: list[CleaningLogChecklistItem]
    created_by_user: User
    log: CleaningLog
    responsible_user: User
    template: CleaningTemplate | None


class AdminCleaningLogService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_logs(
        self,
        session: Session,
        *,
        area_name: str | None,
        area_type: str | None,
        branch_id: uuid.UUID | None,
        cleaning_type: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        evidence_state: str | None,
        observation_state: str | None,
        page: int,
        page_size: int,
        responsible_user_id: uuid.UUID | None,
        risk_level: str | None,
        search: str | None,
        shift_code: str | None,
        status_filter: str | None,
        template_id: uuid.UUID | None,
        warning_state: str | None,
    ) -> AdminCleaningLogListResponse:
        rows = self._fetch_rows(session)

        if branch_id is not None:
            rows = [row for row in rows if row.log.branch_id == branch_id]
        if responsible_user_id is not None:
            rows = [row for row in rows if row.log.responsible_user_id == responsible_user_id]
        if template_id is not None:
            rows = [row for row in rows if row.log.task_template_id == template_id]

        rows = self._filter_by_text(rows, area_name, lambda row: row.log.area_name)
        rows = self._filter_by_code(rows, area_type, lambda row: row.log.area_type)
        rows = self._filter_by_code(rows, cleaning_type, lambda row: row.log.cleaning_type)
        rows = self._filter_by_code(rows, risk_level, lambda row: row.log.risk_level)
        rows = self._filter_by_code(rows, shift_code, lambda row: row.log.shift_code)
        rows = self._filter_by_code(rows, status_filter, lambda row: row.log.status)

        if date_from is not None:
            rows = [row for row in rows if _as_utc(row.log.scheduled_at) >= date_from]
        if date_to is not None:
            rows = [row for row in rows if _as_utc(row.log.scheduled_at) <= date_to]

        normalized_evidence = _normalize_optional(evidence_state)
        if normalized_evidence == "with_evidence":
            rows = [row for row in rows if row.log.has_evidence]
        elif normalized_evidence == "without_evidence":
            rows = [row for row in rows if not row.log.has_evidence]

        normalized_observations = _normalize_optional(observation_state)
        if normalized_observations == "with_observations":
            rows = [row for row in rows if self._has_observations(row)]
        elif normalized_observations == "without_observations":
            rows = [row for row in rows if not self._has_observations(row)]

        normalized_warning = _normalize_optional(warning_state)
        if normalized_warning and normalized_warning != "all":
            rows = [row for row in rows if self._warning_state(row) == normalized_warning]

        normalized_search = _normalize_optional(search)
        if normalized_search:
            rows = [row for row in rows if self._matches_search(row, normalized_search)]

        items = [self._to_list_item(row) for row in rows]
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        total = len(items)
        offset = (safe_page - 1) * safe_page_size

        return AdminCleaningLogListResponse(
            filter_options=self._build_filter_options(session, rows),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def list_templates(self, session: Session) -> list[AdminCleaningTemplateView]:
        templates = (
            session.execute(
                select(CleaningTemplate)
                .where(CleaningTemplate.is_active.is_(True))
                .order_by(CleaningTemplate.name.asc()),
            )
            .scalars()
            .all()
        )
        return [self._template_view(session, template) for template in templates]

    def get_detail(
        self,
        session: Session,
        *,
        cleaning_log_id: uuid.UUID,
    ) -> AdminCleaningLogDetailView:
        return self._to_detail(session, self._get_row(session, cleaning_log_id))

    def create_log(
        self,
        session: Session,
        *,
        command: AdminCleaningLogCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminCleaningLogDetailView:
        branch = self._get_branch(session, command.branch_id)
        if not branch.is_active:
            raise CleaningLogValidationError("Cleaning log branch is inactive.")
        responsible_user = self._get_user(session, command.responsible_user_id)
        if not responsible_user.is_active:
            raise CleaningLogValidationError("Responsible user is inactive.")
        created_by_user = self._get_user(session, current_user.id)
        template = (
            self._get_template(session, command.task_template_id)
            if command.task_template_id
            else None
        )

        self._validate_codes(
            area_type=command.area_type,
            cleaning_type=command.cleaning_type,
            risk_level=command.risk_level,
            shift_code=command.shift_code,
        )

        checklist_inputs = self._resolve_checklist_inputs(session, command, template)
        if not checklist_inputs:
            raise CleaningLogValidationError("Cleaning checklist must include at least one item.")

        now = _utc_now()
        should_complete = command.complete_immediately
        completed_at = _as_utc(command.completed_at) if command.completed_at else now
        task_name = command.task_name or (template.name if template else None)
        if not _has_text(task_name):
            raise CleaningLogValidationError("Cleaning task name is required.")

        risk_level = template.risk_level if template else command.risk_level
        requires_evidence = self._requires_evidence(template, risk_level)
        if should_complete:
            self._validate_completion(
                checklist_inputs=checklist_inputs,
                evidence_note=command.evidence_note,
                issue_notes=command.issue_notes,
                requires_evidence=requires_evidence,
            )

        status = CLEANING_LOG_STATUS_COMPLETED if should_complete else CLEANING_LOG_STATUS_PENDING
        if should_complete and command.issue_notes:
            status = CLEANING_LOG_STATUS_REQUIRES_REVIEW

        log = CleaningLog(
            area_name=command.area_name,
            area_type=command.area_type,
            branch_id=branch.id,
            cleaning_type=template.cleaning_type if template else command.cleaning_type,
            completed_at=completed_at if should_complete else None,
            created_by_user_id=current_user.id,
            equipment_name=command.equipment_name,
            evidence_note=command.evidence_note,
            folio=self._generate_folio(session),
            frequency=template.frequency if template else None,
            has_evidence=_has_text(command.evidence_note),
            issue_notes=command.issue_notes,
            notes=command.notes,
            responsible_user_id=responsible_user.id,
            risk_level=risk_level,
            scheduled_at=_as_utc(command.scheduled_at),
            shift_code=command.shift_code,
            started_at=now if should_complete else None,
            status=status,
            task_name=str(task_name),
            task_template_id=template.id if template else None,
        )
        session.add(log)
        session.flush()

        self._replace_checklist(session, log.id, checklist_inputs)
        self._record_change(
            session,
            action=AUDIT_ACTION_CLEANING_LOG_CREATED,
            actor_id=current_user.id,
            branch_id=branch.id,
            log=log,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_CLEANING_LOG_CREATED_V1,
            log=log,
            branch=branch,
        )
        if self._is_high_risk_log(log):
            self._record_high_risk_alert(session, current_user.id, branch.id, log, request_id)
        if should_complete:
            self._record_change(
                session,
                action=AUDIT_ACTION_CLEANING_LOG_COMPLETED,
                actor_id=current_user.id,
                branch_id=branch.id,
                log=log,
                request_id=request_id,
            )
            self._append_event(
                session,
                event_name=OUTBOX_EVENT_CLEANING_LOG_COMPLETED_V1,
                log=log,
                branch=branch,
            )

        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise CleaningLogValidationError("Cleaning log could not be saved.") from error

        return self._to_detail(
            session,
            _CleaningRow(
                branch=branch,
                checklist_items=self._get_checklist(session, log.id),
                created_by_user=created_by_user,
                log=log,
                responsible_user=responsible_user,
                template=template,
            ),
        )

    def complete_log(
        self,
        session: Session,
        *,
        cleaning_log_id: uuid.UUID,
        command: AdminCleaningLogCompleteRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminCleaningLogDetailView:
        row = self._get_row(session, cleaning_log_id)
        if row.log.status in {CLEANING_LOG_STATUS_COMPLETED, CLEANING_LOG_STATUS_CANCELLED}:
            raise CleaningLogValidationError(
                "Cleaning log cannot be completed from its current status."
            )

        checklist_inputs = (
            command.checklist_items
            if command.checklist_items
            else [
                AdminCleaningChecklistItemInput(
                    id=item.id,
                    is_completed=item.is_completed,
                    is_required=item.is_required,
                    label=item.label,
                    notes=item.notes,
                )
                for item in row.checklist_items
            ]
        )
        evidence_note = (
            command.evidence_note if command.evidence_note is not None else row.log.evidence_note
        )
        issue_notes = (
            command.issue_notes if command.issue_notes is not None else row.log.issue_notes
        )
        self._validate_completion(
            checklist_inputs=checklist_inputs,
            evidence_note=evidence_note,
            issue_notes=issue_notes,
            requires_evidence=self._requires_evidence(row.template, row.log.risk_level),
        )

        now = _utc_now()
        row.log.started_at = row.log.started_at or now
        row.log.completed_at = _as_utc(command.completed_at) if command.completed_at else now
        row.log.evidence_note = evidence_note
        row.log.has_evidence = _has_text(evidence_note)
        row.log.issue_notes = issue_notes
        row.log.notes = command.notes if command.notes is not None else row.log.notes
        row.log.status = (
            CLEANING_LOG_STATUS_REQUIRES_REVIEW
            if issue_notes or any(not item.is_completed for item in checklist_inputs)
            else CLEANING_LOG_STATUS_COMPLETED
        )
        self._replace_checklist(session, row.log.id, checklist_inputs)
        session.flush()

        self._record_change(
            session,
            action=AUDIT_ACTION_CLEANING_LOG_COMPLETED,
            actor_id=current_user.id,
            branch_id=row.log.branch_id,
            log=row.log,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_CLEANING_LOG_COMPLETED_V1,
            log=row.log,
            branch=row.branch,
        )
        if self._is_high_risk_log(row.log):
            self._record_high_risk_alert(
                session, current_user.id, row.log.branch_id, row.log, request_id
            )

        session.commit()
        return self._to_detail(session, self._get_row(session, cleaning_log_id))

    def cancel_log(
        self,
        session: Session,
        *,
        cleaning_log_id: uuid.UUID,
        command: AdminCleaningLogCancelRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminCleaningLogDetailView:
        row = self._get_row(session, cleaning_log_id)
        if row.log.status in FINAL_STATUSES:
            raise CleaningLogValidationError(
                "Completed or cancelled cleaning logs cannot be cancelled."
            )

        row.log.status = CLEANING_LOG_STATUS_CANCELLED
        row.log.cancellation_reason = command.reason
        self._record_change(
            session,
            action=AUDIT_ACTION_CLEANING_LOG_CANCELLED,
            actor_id=current_user.id,
            branch_id=row.log.branch_id,
            log=row.log,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_CLEANING_LOG_CANCELLED_V1,
            log=row.log,
            branch=row.branch,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, cleaning_log_id))

    def _fetch_rows(self, session: Session) -> list[_CleaningRow]:
        logs = (
            session.execute(
                select(CleaningLog).order_by(
                    CleaningLog.scheduled_at.desc(), CleaningLog.created_at.desc()
                ),
            )
            .scalars()
            .all()
        )
        return [self._row_from_log(session, log) for log in logs]

    def _get_row(self, session: Session, cleaning_log_id: uuid.UUID) -> _CleaningRow:
        log = session.get(CleaningLog, cleaning_log_id)
        if log is None:
            raise CleaningLogNotFoundError("Cleaning log was not found.")
        return self._row_from_log(session, log)

    def _row_from_log(self, session: Session, log: CleaningLog) -> _CleaningRow:
        branch = session.get(Branch, log.branch_id)
        responsible_user = session.get(User, log.responsible_user_id)
        created_by_user = session.get(User, log.created_by_user_id)
        if branch is None or responsible_user is None or created_by_user is None:
            raise CleaningLogValidationError("Cleaning log references unavailable branch or user.")
        template = (
            session.get(CleaningTemplate, log.task_template_id) if log.task_template_id else None
        )
        return _CleaningRow(
            branch=branch,
            checklist_items=self._get_checklist(session, log.id),
            created_by_user=created_by_user,
            log=log,
            responsible_user=responsible_user,
            template=template,
        )

    def _to_list_item(self, row: _CleaningRow) -> AdminCleaningLogListItemView:
        completed_count = sum(1 for item in row.checklist_items if item.is_completed)
        return AdminCleaningLogListItemView(
            area_name=row.log.area_name,
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            checklist_completed_count=completed_count,
            checklist_total_count=len(row.checklist_items),
            cleaning_type=row.log.cleaning_type,
            completed_at=row.log.completed_at,
            equipment_name=row.log.equipment_name,
            folio=row.log.folio,
            has_evidence=row.log.has_evidence,
            has_observations=self._has_observations(row),
            id=row.log.id,
            responsible_user_id=row.responsible_user.id,
            responsible_user_name=row.responsible_user.full_name,
            risk_level=_CLEANING_RISK_LEVEL_ADAPTER.validate_python(row.log.risk_level),
            scheduled_at=row.log.scheduled_at,
            shift_code=row.log.shift_code,
            status=_CLEANING_LOG_STATUS_ADAPTER.validate_python(row.log.status),
            task_name=row.log.task_name,
            updated_at=row.log.updated_at,
            warning_state=self._warning_state(row),
            warnings=self._warnings(row),
        )

    def _to_detail(self, session: Session, row: _CleaningRow) -> AdminCleaningLogDetailView:
        checklist = [self._checklist_view(item) for item in row.checklist_items]
        incomplete_required = sum(
            1 for item in row.checklist_items if item.is_required and not item.is_completed
        )
        return AdminCleaningLogDetailView(
            available_actions=self._available_actions(session, row),
            checklist=checklist,
            evidence=AdminCleaningEvidenceView(
                evidence_note=row.log.evidence_note,
                has_evidence=row.log.has_evidence,
            ),
            location_area=AdminCleaningLocationAreaView(
                area_name=row.log.area_name,
                area_type=row.log.area_type,
                branch_code=row.branch.code,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                equipment_name=row.log.equipment_name,
            ),
            observations_issues=AdminCleaningObservationsView(
                cancellation_reason=row.log.cancellation_reason,
                corrective_note=None,
                incomplete_required_count=incomplete_required,
                issue_notes=row.log.issue_notes,
                notes=row.log.notes,
            ),
            overview=AdminCleaningOverviewView(
                area_name=row.log.area_name,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                cleaning_type=row.log.cleaning_type,
                completed_at=row.log.completed_at,
                created_at=row.log.created_at,
                created_by_user_id=row.created_by_user.id,
                created_by_user_name=row.created_by_user.full_name,
                equipment_name=row.log.equipment_name,
                folio=row.log.folio,
                id=row.log.id,
                responsible_user_id=row.responsible_user.id,
                responsible_user_name=row.responsible_user.full_name,
                risk_level=_CLEANING_RISK_LEVEL_ADAPTER.validate_python(row.log.risk_level),
                scheduled_at=row.log.scheduled_at,
                shift_code=row.log.shift_code,
                started_at=row.log.started_at,
                status=_CLEANING_LOG_STATUS_ADAPTER.validate_python(row.log.status),
                task_name=row.log.task_name,
                warning_state=self._warning_state(row),
            ),
            related_documents=self._related_documents(row),
            task_template=AdminCleaningTaskTemplateView(
                cleaning_type=row.log.cleaning_type,
                estimated_duration_minutes=(
                    row.template.estimated_duration_minutes if row.template else None
                ),
                frequency=row.log.frequency,
                method_summary=row.template.method_summary if row.template else None,
                required_tools=row.template.required_tools if row.template else None,
                risk_level=_CLEANING_RISK_LEVEL_ADAPTER.validate_python(row.log.risk_level),
                task_name=row.log.task_name,
                task_template_id=row.template.id if row.template else None,
                task_template_name=row.template.name if row.template else None,
            ),
            warnings=self._warnings(row),
        )

    def _build_filter_options(
        self,
        session: Session,
        rows: list[_CleaningRow],
    ) -> AdminCleaningFilterOptionsView:
        branches = session.execute(select(Branch).order_by(Branch.name.asc())).scalars().all()
        users = session.scalars(
            select(User).where(operational_user_predicate(session)).order_by(User.full_name.asc())
        ).all()
        templates = (
            session.execute(
                select(CleaningTemplate)
                .where(CleaningTemplate.is_active.is_(True))
                .order_by(CleaningTemplate.name.asc()),
            )
            .scalars()
            .all()
        )
        return AdminCleaningFilterOptionsView(
            area_types=[
                AdminCleaningFilterOptionView(id=key, label=value)
                for key, value in AREA_TYPE_LABELS.items()
            ],
            areas=_dedupe_options(
                AdminCleaningFilterOptionView(id=row.log.area_name, label=row.log.area_name)
                for row in rows
            ),
            branches=[
                AdminCleaningFilterOptionView(
                    id=str(branch.id), label=f"{branch.name} - {branch.code}"
                )
                for branch in branches
            ],
            cleaning_types=[
                AdminCleaningFilterOptionView(id=key, label=value)
                for key, value in CLEANING_TYPE_LABELS.items()
            ],
            evidence_states=[
                AdminCleaningFilterOptionView(id="with_evidence", label="Con evidencia"),
                AdminCleaningFilterOptionView(id="without_evidence", label="Sin evidencia"),
            ],
            observation_states=[
                AdminCleaningFilterOptionView(id="with_observations", label="Con observaciones"),
                AdminCleaningFilterOptionView(id="without_observations", label="Sin observaciones"),
            ],
            responsible_users=[
                AdminCleaningFilterOptionView(id=str(user.id), label=user.full_name)
                for user in users
                if user.is_active
            ],
            risk_levels=[
                AdminCleaningFilterOptionView(id=key, label=value)
                for key, value in RISK_LABELS.items()
            ],
            shifts=[
                AdminCleaningFilterOptionView(id=key, label=value)
                for key, value in SHIFT_LABELS.items()
            ],
            statuses=[
                AdminCleaningFilterOptionView(id=key, label=value)
                for key, value in STATUS_LABELS.items()
            ],
            templates=[
                AdminCleaningFilterOptionView(id=str(template.id), label=template.name)
                for template in templates
            ],
        )

    def _build_metrics(self, rows: list[_CleaningRow]) -> AdminCleaningMetricsView:
        return AdminCleaningMetricsView(
            completed_count=sum(
                1 for row in rows if row.log.status == CLEANING_LOG_STATUS_COMPLETED
            ),
            high_risk_count=sum(1 for row in rows if self._is_high_risk_log(row.log)),
            overdue_count=sum(1 for row in rows if self._is_overdue(row.log)),
            pending_count=sum(1 for row in rows if row.log.status in OPEN_STATUSES),
            requires_review_count=sum(
                1 for row in rows if row.log.status == CLEANING_LOG_STATUS_REQUIRES_REVIEW
            ),
            total_count=len(rows),
            with_evidence_count=sum(1 for row in rows if row.log.has_evidence),
            with_observations_count=sum(1 for row in rows if self._has_observations(row)),
        )

    def _template_view(
        self, session: Session, template: CleaningTemplate
    ) -> AdminCleaningTemplateView:
        items = (
            session.execute(
                select(CleaningTemplateItem)
                .where(CleaningTemplateItem.template_id == template.id)
                .order_by(CleaningTemplateItem.display_order.asc()),
            )
            .scalars()
            .all()
        )
        return AdminCleaningTemplateView(
            area_type=template.area_type,
            cleaning_type=template.cleaning_type,
            description=template.description,
            estimated_duration_minutes=template.estimated_duration_minutes,
            frequency=template.frequency,
            id=template.id,
            is_active=template.is_active,
            items=[
                AdminCleaningTemplateItemView(
                    description=item.description,
                    display_order=item.display_order,
                    id=item.id,
                    is_required=item.is_required,
                    label=item.label,
                )
                for item in items
            ],
            method_summary=template.method_summary,
            name=template.name,
            requires_evidence=template.requires_evidence,
            required_tools=template.required_tools,
            risk_level=_CLEANING_RISK_LEVEL_ADAPTER.validate_python(template.risk_level),
        )

    def _resolve_checklist_inputs(
        self,
        session: Session,
        command: AdminCleaningLogCreateRequest,
        template: CleaningTemplate | None,
    ) -> list[AdminCleaningChecklistItemInput]:
        if command.checklist_items:
            return command.checklist_items
        if template is None:
            return []
        template_items = (
            session.execute(
                select(CleaningTemplateItem)
                .where(CleaningTemplateItem.template_id == template.id)
                .order_by(CleaningTemplateItem.display_order.asc()),
            )
            .scalars()
            .all()
        )
        return [
            AdminCleaningChecklistItemInput(
                is_completed=command.complete_immediately,
                is_required=item.is_required,
                label=item.label,
            )
            for item in template_items
        ]

    def _replace_checklist(
        self,
        session: Session,
        cleaning_log_id: uuid.UUID,
        checklist_items: list[AdminCleaningChecklistItemInput],
    ) -> None:
        existing = (
            session.execute(
                select(CleaningLogChecklistItem).where(
                    CleaningLogChecklistItem.cleaning_log_id == cleaning_log_id,
                ),
            )
            .scalars()
            .all()
        )
        for existing_item in existing:
            session.delete(existing_item)
        session.flush()

        for index, item in enumerate(checklist_items, start=1):
            session.add(
                CleaningLogChecklistItem(
                    cleaning_log_id=cleaning_log_id,
                    display_order=index,
                    is_completed=item.is_completed,
                    is_required=item.is_required,
                    label=item.label,
                    notes=item.notes,
                )
            )

    def _get_checklist(
        self, session: Session, cleaning_log_id: uuid.UUID
    ) -> list[CleaningLogChecklistItem]:
        return list(
            session.execute(
                select(CleaningLogChecklistItem)
                .where(CleaningLogChecklistItem.cleaning_log_id == cleaning_log_id)
                .order_by(CleaningLogChecklistItem.display_order.asc()),
            )
            .scalars()
            .all()
        )

    def _checklist_view(self, item: CleaningLogChecklistItem) -> AdminCleaningChecklistItemView:
        return AdminCleaningChecklistItemView(
            display_order=item.display_order,
            id=item.id,
            is_completed=item.is_completed,
            is_required=item.is_required,
            label=item.label,
            notes=item.notes,
        )

    def _validate_completion(
        self,
        *,
        checklist_inputs: list[AdminCleaningChecklistItemInput],
        evidence_note: str | None,
        issue_notes: str | None,
        requires_evidence: bool,
    ) -> None:
        if any(item.is_required and not item.is_completed for item in checklist_inputs):
            raise CleaningLogValidationError("Required checklist items must be completed.")
        if any(not item.is_completed for item in checklist_inputs) and not _has_text(issue_notes):
            raise CleaningLogValidationError(
                "Notes are required when checklist items are incomplete."
            )
        if requires_evidence and not _has_text(evidence_note):
            raise CleaningLogValidationError(
                "Evidence note is required for this high-risk cleaning log."
            )

    def _validate_codes(
        self,
        *,
        area_type: str,
        cleaning_type: str,
        risk_level: str,
        shift_code: str,
    ) -> None:
        if area_type not in VALID_CLEANING_AREA_TYPES:
            raise CleaningLogValidationError("Cleaning area type is not supported.")
        if cleaning_type not in VALID_CLEANING_TYPES:
            raise CleaningLogValidationError("Cleaning type is not supported.")
        if risk_level not in VALID_CLEANING_RISK_LEVELS:
            raise CleaningLogValidationError("Cleaning risk level is not supported.")
        if shift_code not in VALID_CLEANING_SHIFTS:
            raise CleaningLogValidationError("Cleaning shift is not supported.")

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise CleaningLogValidationError("Cleaning branch does not exist.")
        return branch

    def _get_user(self, session: Session, user_id: uuid.UUID) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise CleaningLogValidationError("Cleaning user does not exist.")
        return user

    def _get_template(self, session: Session, template_id: uuid.UUID | None) -> CleaningTemplate:
        template = session.get(CleaningTemplate, template_id)
        if template is None or not template.is_active:
            raise CleaningLogValidationError("Cleaning template does not exist or is inactive.")
        return template

    def _generate_folio(self, session: Session) -> str:
        count = session.execute(select(CleaningLog.id)).scalars().all()
        return f"CLN-{len(count) + 1:06d}"

    def _has_observations(self, row: _CleaningRow) -> bool:
        return any(
            [
                _has_text(row.log.notes),
                _has_text(row.log.issue_notes),
                _has_text(row.log.cancellation_reason),
                any(not item.is_completed for item in row.checklist_items),
            ]
        )

    def _warning_state(self, row: _CleaningRow) -> str:
        if row.log.status == CLEANING_LOG_STATUS_REQUIRES_REVIEW:
            return CLEANING_WARNING_REVIEW
        if self._is_overdue(row.log):
            return CLEANING_WARNING_OVERDUE
        if any(item.is_required and not item.is_completed for item in row.checklist_items):
            return CLEANING_WARNING_INCOMPLETE
        if self._is_high_risk_log(row.log):
            return CLEANING_WARNING_HIGH_RISK
        return CLEANING_WARNING_OK

    def _warnings(self, row: _CleaningRow) -> list[AdminCleaningWarningView]:
        warnings: list[AdminCleaningWarningView] = []
        if self._is_overdue(row.log):
            warnings.append(
                AdminCleaningWarningView(
                    code="overdue",
                    message="La bitacora esta vencida y requiere seguimiento.",
                    severity="critical" if self._is_high_risk_log(row.log) else "warning",
                )
            )
        if any(item.is_required and not item.is_completed for item in row.checklist_items):
            warnings.append(
                AdminCleaningWarningView(
                    code="required_checklist_incomplete",
                    message="Hay puntos obligatorios del checklist sin completar.",
                    severity="critical",
                )
            )
        if self._is_high_risk_log(row.log):
            warnings.append(
                AdminCleaningWarningView(
                    code="high_risk",
                    message="La bitacora corresponde a zona, equipo o tarea de alto riesgo.",
                    severity="warning",
                )
            )
        if row.log.status == CLEANING_LOG_STATUS_REQUIRES_REVIEW:
            warnings.append(
                AdminCleaningWarningView(
                    code="requires_review",
                    message="La bitacora tiene observaciones y requiere seguimiento.",
                    severity="warning",
                )
            )
        return warnings

    def _available_actions(
        self, session: Session, row: _CleaningRow
    ) -> AdminCleaningAvailableActionsView:
        is_final = row.log.status in FINAL_STATUSES
        return restrict_actions(
            session,
            AdminCleaningAvailableActionsView(
                can_add_evidence=row.log.status in OPEN_STATUSES,
                can_cancel=row.log.status in OPEN_STATUSES,
                can_complete=row.log.status in OPEN_STATUSES or self._is_overdue(row.log),
                can_create_incident=True,
                can_edit=row.log.status in OPEN_STATUSES,
                can_export=False,
                can_print=False,
                note=(
                    "Incidencias, adjuntos de archivo y exportacion requieren "
                    "contratos backend dedicados."
                    if not is_final
                    else "Bitacora cerrada; el checklist es de solo lectura."
                ),
            ),
            {
                "can_add_evidence": "quality_hygiene.manage",
                "can_cancel": "quality_hygiene.manage",
                "can_complete": "quality_hygiene.manage",
                "can_create_incident": "quality_hygiene.manage",
                "can_edit": "quality_hygiene.manage",
            },
            branch_ids=(row.log.branch_id,),
            global_only=False,
        )

    def _related_documents(self, row: _CleaningRow) -> list[AdminCleaningRelatedDocumentView]:
        documents: list[AdminCleaningRelatedDocumentView] = []
        if row.template is not None:
            documents.append(
                AdminCleaningRelatedDocumentView(
                    document_id=row.template.id,
                    document_type="CLEANING_TEMPLATE",
                    folio=row.template.code,
                    status="ACTIVE" if row.template.is_active else "INACTIVE",
                )
            )
        return documents

    def _is_overdue(self, log: CleaningLog) -> bool:
        return log.status in OPEN_STATUSES and _as_utc(log.scheduled_at) < _utc_now()

    def _is_high_risk_log(self, log: CleaningLog) -> bool:
        return log.risk_level in {CLEANING_RISK_HIGH, CLEANING_RISK_CRITICAL} or log.area_type in {
            CLEANING_AREA_TYPE_PRODUCTION,
            CLEANING_AREA_TYPE_EQUIPMENT,
        }

    def _requires_evidence(self, template: CleaningTemplate | None, risk_level: str) -> bool:
        return bool(template and template.requires_evidence) or risk_level in {
            CLEANING_RISK_HIGH,
            CLEANING_RISK_CRITICAL,
        }

    def _matches_search(self, row: _CleaningRow, search: str) -> bool:
        haystack = " ".join(
            [
                row.log.folio,
                row.branch.name,
                row.log.area_name,
                row.log.equipment_name or "",
                row.log.task_name,
                row.responsible_user.full_name,
                row.log.notes or "",
                row.log.issue_notes or "",
            ]
        ).casefold()
        return search.casefold() in haystack

    def _filter_by_code(
        self,
        rows: list[_CleaningRow],
        value: str | None,
        getter: Callable[[_CleaningRow], str | None],
    ) -> list[_CleaningRow]:
        normalized = _normalize_optional(value)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if getter(row) == normalized]

    def _filter_by_text(
        self,
        rows: list[_CleaningRow],
        value: str | None,
        getter: Callable[[_CleaningRow], str],
    ) -> list[_CleaningRow]:
        normalized = _normalize_optional(value)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if getter(row).casefold() == normalized.casefold()]

    def _record_change(
        self,
        session: Session,
        *,
        action: str,
        actor_id: uuid.UUID,
        branch_id: uuid.UUID,
        log: CleaningLog,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            action=action,
            actor_id=actor_id,
            branch_id=branch_id,
            metadata={
                "folio": log.folio,
                "risk_level": log.risk_level,
                "status": log.status,
                "task_name": log.task_name,
            },
            request_id=request_id,
            resource_id=str(log.id),
            resource_type=CLEANING_RESOURCE_TYPE,
        )

    def _append_event(
        self,
        session: Session,
        *,
        event_name: str,
        log: CleaningLog,
        branch: Branch,
    ) -> None:
        self._outbox_writer.append(
            session,
            aggregate_id=str(log.id),
            aggregate_type=CLEANING_RESOURCE_TYPE,
            event_name=event_name,
            payload={
                "area_name": log.area_name,
                "branch_code": branch.code,
                "branch_id": str(branch.id),
                "folio": log.folio,
                "risk_level": log.risk_level,
                "status": log.status,
                "task_name": log.task_name,
            },
        )

    def _record_high_risk_alert(
        self,
        session: Session,
        actor_id: uuid.UUID,
        branch_id: uuid.UUID,
        log: CleaningLog,
        request_id: str | None,
    ) -> None:
        self._record_change(
            session,
            action=AUDIT_ACTION_CLEANING_LOG_HIGH_RISK_NOTIFIED,
            actor_id=actor_id,
            branch_id=branch_id,
            log=log,
            request_id=request_id,
        )
        self._outbox_writer.append(
            session,
            aggregate_id=str(log.id),
            aggregate_type=CLEANING_RESOURCE_TYPE,
            event_name=OUTBOX_EVENT_CLEANING_LOG_HIGH_RISK_ALERT_V1,
            payload={
                "area_name": log.area_name,
                "folio": log.folio,
                "risk_level": log.risk_level,
                "scheduled_at": log.scheduled_at.isoformat(),
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
    options: Iterable[AdminCleaningFilterOptionView],
) -> list[AdminCleaningFilterOptionView]:
    result: dict[str, AdminCleaningFilterOptionView] = {}
    for option in options:
        if option.id not in result:
            result[option.id] = option
    return sorted(result.values(), key=lambda option: option.label)
