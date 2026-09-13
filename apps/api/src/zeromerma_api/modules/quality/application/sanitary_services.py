from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TypedDict

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
from zeromerma_api.modules.quality.application.sanitary_schemas import (
    AdminSanitaryAvailableActionsView,
    AdminSanitaryChecklistItemInput,
    AdminSanitaryChecklistItemView,
    AdminSanitaryChecklistTemplateView,
    AdminSanitaryEvidenceView,
    AdminSanitaryFilterOptionsView,
    AdminSanitaryFilterOptionView,
    AdminSanitaryFindingsView,
    AdminSanitaryMetricsView,
    AdminSanitaryOverviewView,
    AdminSanitaryRelatedCleaningLogView,
    AdminSanitaryRelatedDocumentView,
    AdminSanitaryScopeView,
    AdminSanitaryScoreResultView,
    AdminSanitaryTemplateItemView,
    AdminSanitaryTemplateView,
    AdminSanitaryVerificationCancelRequest,
    AdminSanitaryVerificationCompleteRequest,
    AdminSanitaryVerificationCreateRequest,
    AdminSanitaryVerificationDetailView,
    AdminSanitaryVerificationListItemView,
    AdminSanitaryVerificationListResponse,
    AdminSanitaryWarningView,
    SanitaryItemResult,
    SanitaryResult,
    SanitaryRiskLevel,
    SanitaryStatus,
)
from zeromerma_api.modules.quality.domain.constants import (
    AUDIT_ACTION_SANITARY_VERIFICATION_CANCELLED,
    AUDIT_ACTION_SANITARY_VERIFICATION_COMPLETED,
    AUDIT_ACTION_SANITARY_VERIFICATION_CREATED,
    AUDIT_ACTION_SANITARY_VERIFICATION_HIGH_RISK_NOTIFIED,
    AUDIT_ACTION_SANITARY_VERIFICATION_STARTED,
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
    CLEANING_RISK_CRITICAL,
    CLEANING_RISK_HIGH,
    CLEANING_RISK_LOW,
    CLEANING_RISK_MEDIUM,
    OUTBOX_EVENT_SANITARY_VERIFICATION_CANCELLED_V1,
    OUTBOX_EVENT_SANITARY_VERIFICATION_COMPLETED_V1,
    OUTBOX_EVENT_SANITARY_VERIFICATION_CREATED_V1,
    OUTBOX_EVENT_SANITARY_VERIFICATION_HIGH_RISK_ALERT_V1,
    OUTBOX_EVENT_SANITARY_VERIFICATION_STARTED_V1,
    SANITARY_ITEM_RESULT_FAILED,
    SANITARY_ITEM_RESULT_NOT_APPLICABLE,
    SANITARY_ITEM_RESULT_PASSED,
    SANITARY_ITEM_RESULT_PENDING,
    SANITARY_PROCESS_DISPLAY,
    SANITARY_PROCESS_EQUIPMENT,
    SANITARY_PROCESS_OTHER,
    SANITARY_PROCESS_PRODUCTION,
    SANITARY_PROCESS_SANITATION,
    SANITARY_PROCESS_STORAGE,
    SANITARY_RESOURCE_TYPE,
    SANITARY_RESULT_FAILED,
    SANITARY_RESULT_NOT_EVALUATED,
    SANITARY_RESULT_PARTIAL,
    SANITARY_RESULT_PASSED,
    SANITARY_STATUS_CANCELLED,
    SANITARY_STATUS_COMPLETED,
    SANITARY_STATUS_IN_PROGRESS,
    SANITARY_STATUS_PENDING,
    SANITARY_STATUS_REQUIRES_FOLLOW_UP,
    SANITARY_STATUS_SCHEDULED,
    SANITARY_WARNING_FAILED,
    SANITARY_WARNING_FOLLOW_UP,
    SANITARY_WARNING_HIGH_RISK,
    SANITARY_WARNING_OK,
    SANITARY_WARNING_OVERDUE,
    VALID_CLEANING_AREA_TYPES,
    VALID_CLEANING_RISK_LEVELS,
    VALID_SANITARY_ITEM_RESULTS,
    VALID_SANITARY_PROCESS_TYPES,
)
from zeromerma_api.modules.quality.domain.exceptions import (
    SanitaryVerificationNotFoundError,
    SanitaryVerificationValidationError,
)
from zeromerma_api.modules.quality.infrastructure.models import (
    CleaningLog,
    SanitaryVerification,
    SanitaryVerificationChecklistItem,
    SanitaryVerificationTemplate,
    SanitaryVerificationTemplateItem,
)

_SANITARY_ITEM_RESULT_ADAPTER: TypeAdapter[SanitaryItemResult] = TypeAdapter(SanitaryItemResult)
_SANITARY_RESULT_ADAPTER: TypeAdapter[SanitaryResult] = TypeAdapter(SanitaryResult)
_SANITARY_RISK_LEVEL_ADAPTER: TypeAdapter[SanitaryRiskLevel] = TypeAdapter(SanitaryRiskLevel)
_SANITARY_STATUS_ADAPTER: TypeAdapter[SanitaryStatus] = TypeAdapter(SanitaryStatus)
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

PROCESS_TYPE_LABELS = {
    SANITARY_PROCESS_STORAGE: "Almacen",
    SANITARY_PROCESS_PRODUCTION: "Produccion",
    SANITARY_PROCESS_DISPLAY: "Mostrador",
    SANITARY_PROCESS_EQUIPMENT: "Equipo",
    SANITARY_PROCESS_SANITATION: "Sanidad",
    SANITARY_PROCESS_OTHER: "Otro",
}

RESULT_LABELS = {
    SANITARY_RESULT_NOT_EVALUATED: "Sin evaluar",
    SANITARY_RESULT_PASSED: "Aprobada",
    SANITARY_RESULT_FAILED: "Fallida",
    SANITARY_RESULT_PARTIAL: "Parcial",
}

RISK_LABELS = {
    CLEANING_RISK_LOW: "Bajo",
    CLEANING_RISK_MEDIUM: "Medio",
    CLEANING_RISK_HIGH: "Alto",
    CLEANING_RISK_CRITICAL: "Critico",
}

STATUS_LABELS = {
    SANITARY_STATUS_SCHEDULED: "Programada",
    SANITARY_STATUS_PENDING: "Pendiente",
    SANITARY_STATUS_IN_PROGRESS: "En proceso",
    SANITARY_STATUS_COMPLETED: "Completada",
    SANITARY_STATUS_CANCELLED: "Cancelada",
    SANITARY_STATUS_REQUIRES_FOLLOW_UP: "Por seguimiento",
}

OPEN_STATUSES = {
    SANITARY_STATUS_SCHEDULED,
    SANITARY_STATUS_PENDING,
    SANITARY_STATUS_IN_PROGRESS,
}

FINAL_STATUSES = {
    SANITARY_STATUS_COMPLETED,
    SANITARY_STATUS_CANCELLED,
    SANITARY_STATUS_REQUIRES_FOLLOW_UP,
}


@dataclass(frozen=True)
class _SanitaryRow:
    branch: Branch
    checklist_items: list[SanitaryVerificationChecklistItem]
    created_by_user: User
    inspector_user: User
    template: SanitaryVerificationTemplate | None
    verification: SanitaryVerification


class _ComputedSanitaryResult(TypedDict):
    failed: int
    max_score: int | None
    not_applicable: int
    passed: int
    requires_follow_up: bool
    result: str
    score_percent: int | None
    status: str
    total: int


class AdminSanitaryVerificationService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_verifications(
        self,
        session: Session,
        *,
        area_name: str | None,
        area_type: str | None,
        branch_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        evidence_state: str | None,
        incident_state: str | None,
        inspector_user_id: uuid.UUID | None,
        page: int,
        page_size: int,
        process_name: str | None,
        process_type: str | None,
        result: str | None,
        risk_level: str | None,
        search: str | None,
        status_filter: str | None,
        template_id: uuid.UUID | None,
        warning_state: str | None,
    ) -> AdminSanitaryVerificationListResponse:
        rows = self._fetch_rows(session)

        if branch_id is not None:
            rows = [row for row in rows if row.verification.branch_id == branch_id]
        if inspector_user_id is not None:
            rows = [row for row in rows if row.verification.inspector_user_id == inspector_user_id]
        if template_id is not None:
            rows = [row for row in rows if row.verification.template_id == template_id]

        rows = self._filter_by_text(rows, area_name, lambda row: row.verification.area_name)
        rows = self._filter_by_text(
            rows,
            process_name,
            lambda row: row.verification.process_name or "",
        )
        rows = self._filter_by_code(rows, area_type, lambda row: row.verification.area_type)
        rows = self._filter_by_code(rows, process_type, lambda row: row.verification.process_type)
        rows = self._filter_by_code(rows, risk_level, lambda row: row.verification.risk_level)
        rows = self._filter_by_code(rows, result, lambda row: row.verification.result)
        rows = self._filter_by_code(rows, status_filter, lambda row: row.verification.status)

        if date_from is not None:
            rows = [row for row in rows if _as_utc(row.verification.scheduled_at) >= date_from]
        if date_to is not None:
            rows = [row for row in rows if _as_utc(row.verification.scheduled_at) <= date_to]

        normalized_evidence = _normalize_optional(evidence_state)
        if normalized_evidence == "with_evidence":
            rows = [row for row in rows if row.verification.has_evidence]
        elif normalized_evidence == "without_evidence":
            rows = [row for row in rows if not row.verification.has_evidence]

        normalized_incident = _normalize_optional(incident_state)
        if normalized_incident == "with_incident":
            rows = [row for row in rows if row.verification.has_incident]
        elif normalized_incident == "without_incident":
            rows = [row for row in rows if not row.verification.has_incident]

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

        return AdminSanitaryVerificationListResponse(
            filter_options=self._build_filter_options(session, rows),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def list_templates(self, session: Session) -> list[AdminSanitaryTemplateView]:
        templates = (
            session.execute(
                select(SanitaryVerificationTemplate)
                .where(SanitaryVerificationTemplate.is_active.is_(True))
                .order_by(SanitaryVerificationTemplate.name.asc()),
            )
            .scalars()
            .all()
        )
        return [self._template_view(session, template) for template in templates]

    def get_detail(
        self,
        session: Session,
        *,
        verification_id: uuid.UUID,
    ) -> AdminSanitaryVerificationDetailView:
        return self._to_detail(session, self._get_row(session, verification_id))

    def create_verification(
        self,
        session: Session,
        *,
        command: AdminSanitaryVerificationCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminSanitaryVerificationDetailView:
        branch = self._get_branch(session, command.branch_id)
        if not branch.is_active:
            raise SanitaryVerificationValidationError("Sanitary branch is inactive.")
        inspector_user = self._get_user(session, command.inspector_user_id)
        if not inspector_user.is_active:
            raise SanitaryVerificationValidationError("Inspector user is inactive.")
        created_by_user = self._get_user(session, current_user.id)
        template = self._get_template(session, command.template_id) if command.template_id else None

        self._validate_codes(
            area_type=command.area_type,
            process_type=command.process_type,
            risk_level=command.risk_level,
        )

        checklist_inputs = self._resolve_checklist_inputs(session, command, template)
        if not checklist_inputs:
            raise SanitaryVerificationValidationError(
                "Sanitary checklist must include at least one item."
            )

        should_complete = command.complete_immediately
        now = _utc_now()
        completed_at = _as_utc(command.completed_at) if command.completed_at else now
        template_name = command.template_name or (template.name if template else None)
        if not _has_text(template_name):
            raise SanitaryVerificationValidationError(
                "Sanitary checklist or template name is required."
            )

        risk_level = template.risk_level if template else command.risk_level
        pass_threshold = template.pass_threshold_percent if template else 80
        requires_evidence = self._requires_evidence(
            template=template,
            risk_level=risk_level,
            checklist_inputs=checklist_inputs,
        )

        computed = self._compute_result(
            checklist_inputs,
            complete=should_complete,
            evidence_note=command.evidence_note,
            findings_notes=command.findings_notes,
            requires_evidence=requires_evidence,
            threshold_percent=pass_threshold,
        )

        verification = SanitaryVerification(
            area_name=command.area_name,
            area_type=command.area_type,
            branch_id=branch.id,
            checklist_total_count=computed["total"],
            completed_at=completed_at if should_complete else None,
            created_by_user_id=current_user.id,
            equipment_name=command.equipment_name,
            evidence_note=command.evidence_note,
            failed_count=computed["failed"],
            findings_notes=command.findings_notes,
            folio=self._generate_folio(session),
            follow_up_required=bool(computed["requires_follow_up"]),
            has_evidence=_has_text(command.evidence_note),
            inspector_user_id=inspector_user.id,
            max_score=computed["max_score"],
            not_applicable_count=computed["not_applicable"],
            notes=command.notes,
            pass_threshold_percent=pass_threshold,
            passed_count=computed["passed"],
            process_name=command.process_name,
            process_type=template.process_type if template else command.process_type,
            result=str(computed["result"]),
            risk_level=risk_level,
            scheduled_at=_as_utc(command.scheduled_at),
            score_percent=computed["score_percent"],
            started_at=now if should_complete else None,
            status=str(computed["status"] if should_complete else SANITARY_STATUS_PENDING),
            template_id=template.id if template else None,
            template_name=str(template_name),
        )
        session.add(verification)
        session.flush()

        self._replace_checklist(session, verification.id, checklist_inputs)
        self._record_change(
            session,
            action=AUDIT_ACTION_SANITARY_VERIFICATION_CREATED,
            actor_id=current_user.id,
            branch_id=branch.id,
            verification=verification,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_SANITARY_VERIFICATION_CREATED_V1,
            verification=verification,
            branch=branch,
        )
        if should_complete:
            self._record_change(
                session,
                action=AUDIT_ACTION_SANITARY_VERIFICATION_COMPLETED,
                actor_id=current_user.id,
                branch_id=branch.id,
                verification=verification,
                request_id=request_id,
            )
            self._append_event(
                session,
                event_name=OUTBOX_EVENT_SANITARY_VERIFICATION_COMPLETED_V1,
                verification=verification,
                branch=branch,
            )
        if self._is_high_risk_verification(verification):
            self._record_high_risk_alert(
                session, current_user.id, branch.id, verification, request_id
            )

        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise SanitaryVerificationValidationError(
                "Sanitary verification could not be saved."
            ) from error

        return self._to_detail(
            session,
            _SanitaryRow(
                branch=branch,
                checklist_items=self._get_checklist(session, verification.id),
                created_by_user=created_by_user,
                inspector_user=inspector_user,
                template=template,
                verification=verification,
            ),
        )

    def start_verification(
        self,
        session: Session,
        *,
        verification_id: uuid.UUID,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminSanitaryVerificationDetailView:
        row = self._get_row(session, verification_id)
        if row.verification.status not in {
            SANITARY_STATUS_SCHEDULED,
            SANITARY_STATUS_PENDING,
        }:
            raise SanitaryVerificationValidationError(
                "Sanitary verification cannot be started from its current status."
            )

        row.verification.status = SANITARY_STATUS_IN_PROGRESS
        row.verification.started_at = row.verification.started_at or _utc_now()
        self._record_change(
            session,
            action=AUDIT_ACTION_SANITARY_VERIFICATION_STARTED,
            actor_id=current_user.id,
            branch_id=row.verification.branch_id,
            verification=row.verification,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_SANITARY_VERIFICATION_STARTED_V1,
            verification=row.verification,
            branch=row.branch,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, verification_id))

    def complete_verification(
        self,
        session: Session,
        *,
        verification_id: uuid.UUID,
        command: AdminSanitaryVerificationCompleteRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminSanitaryVerificationDetailView:
        row = self._get_row(session, verification_id)
        if row.verification.status in FINAL_STATUSES:
            raise SanitaryVerificationValidationError(
                "Sanitary verification cannot be completed from its current status."
            )

        checklist_inputs = (
            command.checklist_results
            if command.checklist_results
            else [
                AdminSanitaryChecklistItemInput(
                    evidence_required_on_failure=item.evidence_required_on_failure,
                    expected_standard=item.expected_standard,
                    id=item.id,
                    is_required=item.is_required,
                    label=item.label,
                    notes=item.notes,
                    result=_SANITARY_ITEM_RESULT_ADAPTER.validate_python(item.result),
                    risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(item.risk_level),
                )
                for item in row.checklist_items
            ]
        )
        evidence_note = (
            command.evidence_note
            if command.evidence_note is not None
            else row.verification.evidence_note
        )
        findings_notes = (
            command.findings_notes
            if command.findings_notes is not None
            else row.verification.findings_notes
        )
        computed = self._compute_result(
            checklist_inputs,
            complete=True,
            evidence_note=evidence_note,
            findings_notes=findings_notes,
            requires_evidence=self._requires_evidence(
                template=row.template,
                risk_level=row.verification.risk_level,
                checklist_inputs=checklist_inputs,
            ),
            threshold_percent=row.verification.pass_threshold_percent,
        )

        now = _utc_now()
        row.verification.started_at = row.verification.started_at or now
        row.verification.completed_at = (
            _as_utc(command.completed_at) if command.completed_at else now
        )
        row.verification.evidence_note = evidence_note
        row.verification.failed_count = computed["failed"]
        row.verification.findings_notes = findings_notes
        row.verification.follow_up_required = bool(computed["requires_follow_up"])
        row.verification.has_evidence = _has_text(evidence_note)
        row.verification.max_score = computed["max_score"]
        row.verification.not_applicable_count = computed["not_applicable"]
        row.verification.notes = (
            command.notes if command.notes is not None else row.verification.notes
        )
        row.verification.passed_count = computed["passed"]
        row.verification.result = str(computed["result"])
        row.verification.score_percent = computed["score_percent"]
        row.verification.status = str(computed["status"])
        row.verification.checklist_total_count = computed["total"]
        self._replace_checklist(session, row.verification.id, checklist_inputs)
        session.flush()

        self._record_change(
            session,
            action=AUDIT_ACTION_SANITARY_VERIFICATION_COMPLETED,
            actor_id=current_user.id,
            branch_id=row.verification.branch_id,
            verification=row.verification,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_SANITARY_VERIFICATION_COMPLETED_V1,
            verification=row.verification,
            branch=row.branch,
        )
        if self._is_high_risk_verification(row.verification):
            self._record_high_risk_alert(
                session, current_user.id, row.verification.branch_id, row.verification, request_id
            )

        session.commit()
        return self._to_detail(session, self._get_row(session, verification_id))

    def cancel_verification(
        self,
        session: Session,
        *,
        verification_id: uuid.UUID,
        command: AdminSanitaryVerificationCancelRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminSanitaryVerificationDetailView:
        row = self._get_row(session, verification_id)
        if row.verification.status in FINAL_STATUSES:
            raise SanitaryVerificationValidationError(
                "Completed or cancelled sanitary verifications cannot be cancelled."
            )

        row.verification.status = SANITARY_STATUS_CANCELLED
        row.verification.cancellation_reason = command.reason
        self._record_change(
            session,
            action=AUDIT_ACTION_SANITARY_VERIFICATION_CANCELLED,
            actor_id=current_user.id,
            branch_id=row.verification.branch_id,
            verification=row.verification,
            request_id=request_id,
        )
        self._append_event(
            session,
            event_name=OUTBOX_EVENT_SANITARY_VERIFICATION_CANCELLED_V1,
            verification=row.verification,
            branch=row.branch,
        )
        session.commit()
        return self._to_detail(session, self._get_row(session, verification_id))

    def _fetch_rows(self, session: Session) -> list[_SanitaryRow]:
        verifications = (
            session.execute(
                select(SanitaryVerification).order_by(
                    SanitaryVerification.scheduled_at.desc(),
                    SanitaryVerification.created_at.desc(),
                ),
            )
            .scalars()
            .all()
        )
        return [
            self._row_from_verification(session, verification) for verification in verifications
        ]

    def _get_row(self, session: Session, verification_id: uuid.UUID) -> _SanitaryRow:
        verification = session.get(SanitaryVerification, verification_id)
        if verification is None:
            raise SanitaryVerificationNotFoundError("Sanitary verification was not found.")
        return self._row_from_verification(session, verification)

    def _row_from_verification(
        self,
        session: Session,
        verification: SanitaryVerification,
    ) -> _SanitaryRow:
        branch = session.get(Branch, verification.branch_id)
        inspector_user = session.get(User, verification.inspector_user_id)
        created_by_user = session.get(User, verification.created_by_user_id)
        if branch is None or inspector_user is None or created_by_user is None:
            raise SanitaryVerificationValidationError(
                "Sanitary verification references unavailable branch or user."
            )
        template = (
            session.get(SanitaryVerificationTemplate, verification.template_id)
            if verification.template_id
            else None
        )
        return _SanitaryRow(
            branch=branch,
            checklist_items=self._get_checklist(session, verification.id),
            created_by_user=created_by_user,
            inspector_user=inspector_user,
            template=template,
            verification=verification,
        )

    def _to_list_item(self, row: _SanitaryRow) -> AdminSanitaryVerificationListItemView:
        return AdminSanitaryVerificationListItemView(
            area_name=row.verification.area_name,
            branch_id=row.branch.id,
            branch_name=row.branch.name,
            checklist_total_count=len(row.checklist_items),
            completed_at=row.verification.completed_at,
            equipment_name=row.verification.equipment_name,
            failed_count=row.verification.failed_count,
            folio=row.verification.folio,
            has_evidence=row.verification.has_evidence,
            has_incident=row.verification.has_incident,
            id=row.verification.id,
            inspector_user_id=row.inspector_user.id,
            inspector_user_name=row.inspector_user.full_name,
            passed_count=row.verification.passed_count,
            process_name=row.verification.process_name,
            result=_SANITARY_RESULT_ADAPTER.validate_python(row.verification.result),
            risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(row.verification.risk_level),
            scheduled_at=row.verification.scheduled_at,
            status=_SANITARY_STATUS_ADAPTER.validate_python(row.verification.status),
            template_name=row.verification.template_name,
            updated_at=row.verification.updated_at,
            warning_state=self._warning_state(row),
            warnings=self._warnings(row),
        )

    def _to_detail(
        self,
        session: Session,
        row: _SanitaryRow,
    ) -> AdminSanitaryVerificationDetailView:
        failed_required = sum(
            1
            for item in row.checklist_items
            if item.is_required and item.result == SANITARY_ITEM_RESULT_FAILED
        )
        checklist = [self._checklist_view(item) for item in row.checklist_items]
        return AdminSanitaryVerificationDetailView(
            available_actions=self._available_actions(session, row),
            checklist_results=checklist,
            checklist_template=AdminSanitaryChecklistTemplateView(
                area_type=row.verification.area_type,
                description=row.template.description if row.template else None,
                failed_items=row.verification.failed_count,
                frequency=row.template.frequency if row.template else None,
                passed_items=row.verification.passed_count,
                pass_threshold_percent=row.verification.pass_threshold_percent,
                process_type=row.verification.process_type,
                risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(
                    row.verification.risk_level
                ),
                template_id=row.template.id if row.template else None,
                template_name=row.verification.template_name,
                total_items=len(row.checklist_items),
            ),
            evidence=AdminSanitaryEvidenceView(
                evidence_note=row.verification.evidence_note,
                has_evidence=row.verification.has_evidence,
            ),
            findings_observations=AdminSanitaryFindingsView(
                cancellation_reason=row.verification.cancellation_reason,
                failed_required_count=failed_required,
                findings_notes=row.verification.findings_notes,
                follow_up_due_at=row.verification.follow_up_due_at,
                follow_up_required=row.verification.follow_up_required,
                notes=row.verification.notes,
            ),
            overview=AdminSanitaryOverviewView(
                area_name=row.verification.area_name,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                completed_at=row.verification.completed_at,
                created_at=row.verification.created_at,
                created_by_user_id=row.created_by_user.id,
                created_by_user_name=row.created_by_user.full_name,
                equipment_name=row.verification.equipment_name,
                folio=row.verification.folio,
                id=row.verification.id,
                inspector_user_id=row.inspector_user.id,
                inspector_user_name=row.inspector_user.full_name,
                process_name=row.verification.process_name,
                result=_SANITARY_RESULT_ADAPTER.validate_python(row.verification.result),
                risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(
                    row.verification.risk_level
                ),
                scheduled_at=row.verification.scheduled_at,
                started_at=row.verification.started_at,
                status=_SANITARY_STATUS_ADAPTER.validate_python(row.verification.status),
                warning_state=self._warning_state(row),
            ),
            related_cleaning_logs=self._related_cleaning_logs(session, row),
            related_documents=self._related_documents(row),
            scope=AdminSanitaryScopeView(
                area_name=row.verification.area_name,
                area_type=row.verification.area_type,
                branch_code=row.branch.code,
                branch_id=row.branch.id,
                branch_name=row.branch.name,
                equipment_name=row.verification.equipment_name,
                process_name=row.verification.process_name,
                process_type=row.verification.process_type,
            ),
            score_result=AdminSanitaryScoreResultView(
                max_score=row.verification.max_score,
                percentage=row.verification.score_percent,
                result=_SANITARY_RESULT_ADAPTER.validate_python(row.verification.result),
                score=row.verification.passed_count,
                threshold_percent=row.verification.pass_threshold_percent,
            ),
            warnings=self._warnings(row),
        )

    def _build_filter_options(
        self,
        session: Session,
        rows: list[_SanitaryRow],
    ) -> AdminSanitaryFilterOptionsView:
        branches = session.execute(select(Branch).order_by(Branch.name.asc())).scalars().all()
        users = session.scalars(
            select(User).where(operational_user_predicate(session)).order_by(User.full_name.asc())
        ).all()
        templates = (
            session.execute(
                select(SanitaryVerificationTemplate)
                .where(SanitaryVerificationTemplate.is_active.is_(True))
                .order_by(SanitaryVerificationTemplate.name.asc()),
            )
            .scalars()
            .all()
        )
        return AdminSanitaryFilterOptionsView(
            area_types=[
                AdminSanitaryFilterOptionView(id=key, label=value)
                for key, value in AREA_TYPE_LABELS.items()
            ],
            areas=_dedupe_options(
                AdminSanitaryFilterOptionView(
                    id=row.verification.area_name,
                    label=row.verification.area_name,
                )
                for row in rows
            ),
            branches=[
                AdminSanitaryFilterOptionView(
                    id=str(branch.id), label=f"{branch.name} - {branch.code}"
                )
                for branch in branches
            ],
            evidence_states=[
                AdminSanitaryFilterOptionView(id="with_evidence", label="Con evidencia"),
                AdminSanitaryFilterOptionView(id="without_evidence", label="Sin evidencia"),
            ],
            incident_states=[
                AdminSanitaryFilterOptionView(id="with_incident", label="Con incidencia"),
                AdminSanitaryFilterOptionView(id="without_incident", label="Sin incidencia"),
            ],
            inspectors=[
                AdminSanitaryFilterOptionView(id=str(user.id), label=user.full_name)
                for user in users
                if user.is_active
            ],
            process_types=[
                AdminSanitaryFilterOptionView(id=key, label=value)
                for key, value in PROCESS_TYPE_LABELS.items()
            ],
            processes=_dedupe_options(
                AdminSanitaryFilterOptionView(
                    id=row.verification.process_name,
                    label=row.verification.process_name,
                )
                for row in rows
                if row.verification.process_name
            ),
            results=[
                AdminSanitaryFilterOptionView(id=key, label=value)
                for key, value in RESULT_LABELS.items()
            ],
            risk_levels=[
                AdminSanitaryFilterOptionView(id=key, label=value)
                for key, value in RISK_LABELS.items()
            ],
            statuses=[
                AdminSanitaryFilterOptionView(id=key, label=value)
                for key, value in STATUS_LABELS.items()
            ],
            templates=[
                AdminSanitaryFilterOptionView(id=str(template.id), label=template.name)
                for template in templates
            ],
        )

    def _build_metrics(self, rows: list[_SanitaryRow]) -> AdminSanitaryMetricsView:
        return AdminSanitaryMetricsView(
            failed_count=sum(
                1 for row in rows if row.verification.result == SANITARY_RESULT_FAILED
            ),
            high_risk_count=sum(
                1 for row in rows if self._is_high_risk_verification(row.verification)
            ),
            pending_count=sum(1 for row in rows if row.verification.status in OPEN_STATUSES),
            passed_count=sum(
                1 for row in rows if row.verification.result == SANITARY_RESULT_PASSED
            ),
            requires_follow_up_count=sum(
                1
                for row in rows
                if row.verification.status == SANITARY_STATUS_REQUIRES_FOLLOW_UP
                or row.verification.follow_up_required
            ),
            total_count=len(rows),
            with_evidence_count=sum(1 for row in rows if row.verification.has_evidence),
            with_incident_count=sum(1 for row in rows if row.verification.has_incident),
        )

    def _template_view(
        self,
        session: Session,
        template: SanitaryVerificationTemplate,
    ) -> AdminSanitaryTemplateView:
        items = (
            session.execute(
                select(SanitaryVerificationTemplateItem)
                .where(SanitaryVerificationTemplateItem.template_id == template.id)
                .order_by(SanitaryVerificationTemplateItem.display_order.asc()),
            )
            .scalars()
            .all()
        )
        return AdminSanitaryTemplateView(
            area_type=template.area_type,
            description=template.description,
            frequency=template.frequency,
            id=template.id,
            is_active=template.is_active,
            items=[
                AdminSanitaryTemplateItemView(
                    description=item.description,
                    display_order=item.display_order,
                    evidence_required_on_failure=item.evidence_required_on_failure,
                    expected_standard=item.expected_standard,
                    id=item.id,
                    is_required=item.is_required,
                    label=item.label,
                    risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(item.risk_level),
                )
                for item in items
            ],
            name=template.name,
            pass_threshold_percent=template.pass_threshold_percent,
            process_type=template.process_type,
            requires_evidence_on_failure=template.requires_evidence_on_failure,
            risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(template.risk_level),
        )

    def _resolve_checklist_inputs(
        self,
        session: Session,
        command: AdminSanitaryVerificationCreateRequest,
        template: SanitaryVerificationTemplate | None,
    ) -> list[AdminSanitaryChecklistItemInput]:
        if command.checklist_results:
            return command.checklist_results
        if template is None:
            return []
        template_items = (
            session.execute(
                select(SanitaryVerificationTemplateItem)
                .where(SanitaryVerificationTemplateItem.template_id == template.id)
                .order_by(SanitaryVerificationTemplateItem.display_order.asc()),
            )
            .scalars()
            .all()
        )
        result = (
            SANITARY_ITEM_RESULT_PASSED
            if command.complete_immediately
            else SANITARY_ITEM_RESULT_PENDING
        )
        return [
            AdminSanitaryChecklistItemInput(
                evidence_required_on_failure=item.evidence_required_on_failure,
                expected_standard=item.expected_standard,
                is_required=item.is_required,
                label=item.label,
                result=_SANITARY_ITEM_RESULT_ADAPTER.validate_python(result),
                risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(item.risk_level),
            )
            for item in template_items
        ]

    def _replace_checklist(
        self,
        session: Session,
        verification_id: uuid.UUID,
        checklist_items: list[AdminSanitaryChecklistItemInput],
    ) -> None:
        existing = (
            session.execute(
                select(SanitaryVerificationChecklistItem).where(
                    SanitaryVerificationChecklistItem.verification_id == verification_id,
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
                SanitaryVerificationChecklistItem(
                    evidence_required_on_failure=item.evidence_required_on_failure,
                    expected_standard=item.expected_standard,
                    display_order=index,
                    is_required=item.is_required,
                    label=item.label,
                    notes=item.notes,
                    result=item.result,
                    risk_level=item.risk_level,
                    verification_id=verification_id,
                )
            )

    def _get_checklist(
        self,
        session: Session,
        verification_id: uuid.UUID,
    ) -> list[SanitaryVerificationChecklistItem]:
        return list(
            session.execute(
                select(SanitaryVerificationChecklistItem)
                .where(SanitaryVerificationChecklistItem.verification_id == verification_id)
                .order_by(SanitaryVerificationChecklistItem.display_order.asc()),
            )
            .scalars()
            .all()
        )

    def _checklist_view(
        self,
        item: SanitaryVerificationChecklistItem,
    ) -> AdminSanitaryChecklistItemView:
        return AdminSanitaryChecklistItemView(
            display_order=item.display_order,
            evidence_required_on_failure=item.evidence_required_on_failure,
            expected_standard=item.expected_standard,
            id=item.id,
            is_required=item.is_required,
            label=item.label,
            notes=item.notes,
            result=_SANITARY_ITEM_RESULT_ADAPTER.validate_python(item.result),
            risk_level=_SANITARY_RISK_LEVEL_ADAPTER.validate_python(item.risk_level),
        )

    def _compute_result(
        self,
        checklist_inputs: list[AdminSanitaryChecklistItemInput],
        *,
        complete: bool,
        evidence_note: str | None,
        findings_notes: str | None,
        requires_evidence: bool,
        threshold_percent: int,
    ) -> _ComputedSanitaryResult:
        self._validate_checklist_inputs(checklist_inputs)
        if not complete:
            return {
                "failed": 0,
                "max_score": None,
                "not_applicable": 0,
                "passed": 0,
                "requires_follow_up": False,
                "result": SANITARY_RESULT_NOT_EVALUATED,
                "score_percent": None,
                "status": SANITARY_STATUS_PENDING,
                "total": len(checklist_inputs),
            }

        if any(
            item.is_required and item.result == SANITARY_ITEM_RESULT_PENDING
            for item in checklist_inputs
        ):
            raise SanitaryVerificationValidationError(
                "Required sanitary checklist items must have a result."
            )
        if any(
            item.is_required
            and item.result == SANITARY_ITEM_RESULT_FAILED
            and not _has_text(item.notes)
            for item in checklist_inputs
        ):
            raise SanitaryVerificationValidationError(
                "Notes are required for failed required sanitary checks."
            )
        if requires_evidence and not _has_text(evidence_note):
            raise SanitaryVerificationValidationError(
                "Evidence note is required for this sanitary verification."
            )

        passed = sum(1 for item in checklist_inputs if item.result == SANITARY_ITEM_RESULT_PASSED)
        failed = sum(1 for item in checklist_inputs if item.result == SANITARY_ITEM_RESULT_FAILED)
        not_applicable = sum(
            1 for item in checklist_inputs if item.result == SANITARY_ITEM_RESULT_NOT_APPLICABLE
        )
        total = len(checklist_inputs)
        max_score = max(total - not_applicable, 0)
        score_percent = round((passed / max_score) * 100) if max_score else None
        failed_required = any(
            item.is_required and item.result == SANITARY_ITEM_RESULT_FAILED
            for item in checklist_inputs
        )
        high_risk_failure = any(
            item.result == SANITARY_ITEM_RESULT_FAILED
            and item.risk_level in {CLEANING_RISK_HIGH, CLEANING_RISK_CRITICAL}
            for item in checklist_inputs
        )
        requires_follow_up = bool(failed_required or high_risk_failure)
        if requires_follow_up and not _has_text(findings_notes):
            raise SanitaryVerificationValidationError(
                "Findings notes are required when sanitary checks fail."
            )

        if failed:
            result = SANITARY_RESULT_FAILED if failed_required else SANITARY_RESULT_PARTIAL
        elif score_percent is not None and score_percent < threshold_percent:
            result = SANITARY_RESULT_PARTIAL
        else:
            result = SANITARY_RESULT_PASSED

        status = (
            SANITARY_STATUS_REQUIRES_FOLLOW_UP if requires_follow_up else SANITARY_STATUS_COMPLETED
        )
        return {
            "failed": failed,
            "max_score": max_score,
            "not_applicable": not_applicable,
            "passed": passed,
            "requires_follow_up": requires_follow_up,
            "result": result,
            "score_percent": score_percent,
            "status": status,
            "total": total,
        }

    def _validate_checklist_inputs(
        self,
        checklist_inputs: list[AdminSanitaryChecklistItemInput],
    ) -> None:
        if not checklist_inputs:
            raise SanitaryVerificationValidationError(
                "Sanitary checklist must include at least one item."
            )
        for item in checklist_inputs:
            if item.result not in VALID_SANITARY_ITEM_RESULTS:
                raise SanitaryVerificationValidationError(
                    "Sanitary checklist item result is not supported."
                )
            if item.risk_level not in VALID_CLEANING_RISK_LEVELS:
                raise SanitaryVerificationValidationError(
                    "Sanitary checklist item risk level is not supported."
                )

    def _validate_codes(
        self,
        *,
        area_type: str,
        process_type: str,
        risk_level: str,
    ) -> None:
        if area_type not in VALID_CLEANING_AREA_TYPES:
            raise SanitaryVerificationValidationError("Sanitary area type is not supported.")
        if process_type not in VALID_SANITARY_PROCESS_TYPES:
            raise SanitaryVerificationValidationError("Sanitary process type is not supported.")
        if risk_level not in VALID_CLEANING_RISK_LEVELS:
            raise SanitaryVerificationValidationError("Sanitary risk level is not supported.")

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise SanitaryVerificationValidationError("Sanitary branch does not exist.")
        return branch

    def _get_user(self, session: Session, user_id: uuid.UUID) -> User:
        user = session.get(User, user_id)
        if user is None:
            raise SanitaryVerificationValidationError("Sanitary user does not exist.")
        return user

    def _get_template(
        self,
        session: Session,
        template_id: uuid.UUID | None,
    ) -> SanitaryVerificationTemplate:
        template = session.get(SanitaryVerificationTemplate, template_id)
        if template is None or not template.is_active:
            raise SanitaryVerificationValidationError(
                "Sanitary template does not exist or is inactive."
            )
        return template

    def _generate_folio(self, session: Session) -> str:
        count = session.execute(select(SanitaryVerification.id)).scalars().all()
        return f"SAN-{len(count) + 1:06d}"

    def _warning_state(self, row: _SanitaryRow) -> str:
        if row.verification.status == SANITARY_STATUS_REQUIRES_FOLLOW_UP:
            return SANITARY_WARNING_FOLLOW_UP
        if self._is_overdue(row.verification):
            return SANITARY_WARNING_OVERDUE
        if row.verification.failed_count > 0 or row.verification.result == SANITARY_RESULT_FAILED:
            return SANITARY_WARNING_FAILED
        if self._is_high_risk_verification(row.verification):
            return SANITARY_WARNING_HIGH_RISK
        return SANITARY_WARNING_OK

    def _warnings(self, row: _SanitaryRow) -> list[AdminSanitaryWarningView]:
        warnings: list[AdminSanitaryWarningView] = []
        if self._is_overdue(row.verification):
            warnings.append(
                AdminSanitaryWarningView(
                    code="overdue",
                    message="La verificacion esta vencida y requiere seguimiento.",
                    severity="critical"
                    if self._is_high_risk_verification(row.verification)
                    else "warning",
                )
            )
        if row.verification.failed_count > 0:
            warnings.append(
                AdminSanitaryWarningView(
                    code="failed_checks",
                    message="La verificacion tiene puntos sanitarios fallidos.",
                    severity="critical",
                )
            )
        if row.verification.status == SANITARY_STATUS_REQUIRES_FOLLOW_UP:
            warnings.append(
                AdminSanitaryWarningView(
                    code="requires_follow_up",
                    message="La verificacion requiere seguimiento documentado.",
                    severity="critical",
                )
            )
        if self._is_high_risk_verification(row.verification):
            warnings.append(
                AdminSanitaryWarningView(
                    code="high_risk",
                    message="La verificacion corresponde a zona, proceso o falla de alto riesgo.",
                    severity="warning",
                )
            )
        return warnings

    def _available_actions(
        self, session: Session, row: _SanitaryRow
    ) -> AdminSanitaryAvailableActionsView:
        is_open = row.verification.status in OPEN_STATUSES
        is_pending = row.verification.status in {
            SANITARY_STATUS_SCHEDULED,
            SANITARY_STATUS_PENDING,
        }
        is_final = row.verification.status in FINAL_STATUSES
        return restrict_actions(
            session,
            AdminSanitaryAvailableActionsView(
                can_add_evidence=is_open,
                can_cancel=is_open,
                can_complete=is_open,
                can_create_incident=row.verification.failed_count > 0
                or row.verification.status == SANITARY_STATUS_REQUIRES_FOLLOW_UP,
                can_edit=is_open,
                can_export=False,
                can_print=False,
                can_start=is_pending,
                note=(
                    "Incidencias, adjuntos de archivo y exportacion requieren contratos backend "
                    "dedicados."
                    if not is_final
                    else "Verificacion cerrada; el checklist es de solo lectura."
                ),
            ),
            {
                "can_add_evidence": "quality_hygiene.manage",
                "can_cancel": "quality_hygiene.manage",
                "can_complete": "quality_hygiene.manage",
                "can_create_incident": "quality_hygiene.manage",
                "can_edit": "quality_hygiene.manage",
                "can_start": "quality_hygiene.manage",
            },
            branch_ids=(row.verification.branch_id,),
            global_only=False,
        )

    def _related_documents(self, row: _SanitaryRow) -> list[AdminSanitaryRelatedDocumentView]:
        documents: list[AdminSanitaryRelatedDocumentView] = []
        if row.template is not None:
            documents.append(
                AdminSanitaryRelatedDocumentView(
                    document_id=row.template.id,
                    document_type="SANITARY_TEMPLATE",
                    folio=row.template.code,
                    status="ACTIVE" if row.template.is_active else "INACTIVE",
                )
            )
        return documents

    def _related_cleaning_logs(
        self,
        session: Session,
        row: _SanitaryRow,
    ) -> list[AdminSanitaryRelatedCleaningLogView]:
        logs = (
            session.execute(
                select(CleaningLog)
                .where(CleaningLog.branch_id == row.verification.branch_id)
                .order_by(CleaningLog.scheduled_at.desc(), CleaningLog.created_at.desc()),
            )
            .scalars()
            .all()
        )
        matched: list[CleaningLog] = []
        area = row.verification.area_name.casefold()
        equipment = (
            row.verification.equipment_name.casefold() if row.verification.equipment_name else None
        )
        for log in logs:
            log_equipment = log.equipment_name.casefold() if log.equipment_name else None
            if log.area_name.casefold() == area or (equipment and log_equipment == equipment):
                matched.append(log)
            if len(matched) >= 5:
                break

        result: list[AdminSanitaryRelatedCleaningLogView] = []
        for log in matched:
            responsible = session.get(User, log.responsible_user_id)
            result.append(
                AdminSanitaryRelatedCleaningLogView(
                    completed_at=log.completed_at,
                    folio=log.folio,
                    id=log.id,
                    responsible_user_name=responsible.full_name if responsible else "Sin usuario",
                    status=log.status,
                )
            )
        return result

    def _is_overdue(self, verification: SanitaryVerification) -> bool:
        return (
            verification.status in OPEN_STATUSES and _as_utc(verification.scheduled_at) < _utc_now()
        )

    def _is_high_risk_verification(self, verification: SanitaryVerification) -> bool:
        return (
            verification.risk_level in {CLEANING_RISK_HIGH, CLEANING_RISK_CRITICAL}
            or verification.area_type
            in {
                CLEANING_AREA_TYPE_PRODUCTION,
                CLEANING_AREA_TYPE_EQUIPMENT,
            }
            or verification.process_type
            in {
                SANITARY_PROCESS_PRODUCTION,
                SANITARY_PROCESS_EQUIPMENT,
                SANITARY_PROCESS_SANITATION,
            }
            or verification.failed_count > 0
        )

    def _requires_evidence(
        self,
        *,
        template: SanitaryVerificationTemplate | None,
        risk_level: str,
        checklist_inputs: list[AdminSanitaryChecklistItemInput],
    ) -> bool:
        failed_evidence_required = any(
            item.result == SANITARY_ITEM_RESULT_FAILED
            and (item.evidence_required_on_failure or item.risk_level == CLEANING_RISK_CRITICAL)
            for item in checklist_inputs
        )
        high_risk_failure = any(
            item.result == SANITARY_ITEM_RESULT_FAILED
            and item.risk_level in {CLEANING_RISK_HIGH, CLEANING_RISK_CRITICAL}
            for item in checklist_inputs
        )
        return bool(template and template.requires_evidence_on_failure and high_risk_failure) or (
            failed_evidence_required and risk_level in {CLEANING_RISK_HIGH, CLEANING_RISK_CRITICAL}
        )

    def _matches_search(self, row: _SanitaryRow, search: str) -> bool:
        haystack = " ".join(
            [
                row.verification.folio,
                row.branch.name,
                row.verification.area_name,
                row.verification.equipment_name or "",
                row.verification.process_name or "",
                row.verification.template_name,
                row.inspector_user.full_name,
                row.verification.notes or "",
                row.verification.findings_notes or "",
            ]
        ).casefold()
        return search.casefold() in haystack

    def _filter_by_code(
        self,
        rows: list[_SanitaryRow],
        value: str | None,
        getter: Callable[[_SanitaryRow], str | None],
    ) -> list[_SanitaryRow]:
        normalized = _normalize_optional(value)
        if not normalized or normalized == "all":
            return rows
        return [row for row in rows if getter(row) == normalized]

    def _filter_by_text(
        self,
        rows: list[_SanitaryRow],
        value: str | None,
        getter: Callable[[_SanitaryRow], str],
    ) -> list[_SanitaryRow]:
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
        verification: SanitaryVerification,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            action=action,
            actor_id=actor_id,
            branch_id=branch_id,
            metadata={
                "folio": verification.folio,
                "result": verification.result,
                "risk_level": verification.risk_level,
                "status": verification.status,
                "template_name": verification.template_name,
            },
            request_id=request_id,
            resource_id=str(verification.id),
            resource_type=SANITARY_RESOURCE_TYPE,
        )

    def _append_event(
        self,
        session: Session,
        *,
        event_name: str,
        verification: SanitaryVerification,
        branch: Branch,
    ) -> None:
        self._outbox_writer.append(
            session,
            aggregate_id=str(verification.id),
            aggregate_type=SANITARY_RESOURCE_TYPE,
            event_name=event_name,
            payload={
                "area_name": verification.area_name,
                "branch_code": branch.code,
                "branch_id": str(branch.id),
                "folio": verification.folio,
                "result": verification.result,
                "risk_level": verification.risk_level,
                "status": verification.status,
                "template_name": verification.template_name,
            },
        )

    def _record_high_risk_alert(
        self,
        session: Session,
        actor_id: uuid.UUID,
        branch_id: uuid.UUID,
        verification: SanitaryVerification,
        request_id: str | None,
    ) -> None:
        self._record_change(
            session,
            action=AUDIT_ACTION_SANITARY_VERIFICATION_HIGH_RISK_NOTIFIED,
            actor_id=actor_id,
            branch_id=branch_id,
            verification=verification,
            request_id=request_id,
        )
        self._outbox_writer.append(
            session,
            aggregate_id=str(verification.id),
            aggregate_type=SANITARY_RESOURCE_TYPE,
            event_name=OUTBOX_EVENT_SANITARY_VERIFICATION_HIGH_RISK_ALERT_V1,
            payload={
                "area_name": verification.area_name,
                "folio": verification.folio,
                "risk_level": verification.risk_level,
                "scheduled_at": verification.scheduled_at.isoformat(),
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
    options: Iterable[AdminSanitaryFilterOptionView],
) -> list[AdminSanitaryFilterOptionView]:
    result: dict[str, AdminSanitaryFilterOptionView] = {}
    for option in options:
        if option.id not in result:
            result[option.id] = option
    return sorted(result.values(), key=lambda option: option.label)
