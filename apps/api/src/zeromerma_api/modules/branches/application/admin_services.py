from __future__ import annotations

import uuid
from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.application.admin_schemas import (
    AdminBranchAvailableActionsView,
    AdminBranchCreateRequest,
    AdminBranchDetailView,
    AdminBranchFilterOptionView,
    AdminBranchFilterOptionsView,
    AdminBranchListItemView,
    AdminBranchLocationContactView,
    AdminBranchMetricsView,
    AdminBranchOperationalConfigView,
    AdminBranchOverviewView,
    AdminBranchReadinessStatus,
    AdminBranchRelatedOperationsSummaryView,
    AdminBranchesListResponse,
    AdminBranchUpdateRequest,
    AdminBranchUserAssignmentView,
    AdminBranchUsersSummaryView,
    AdminBranchWarningView,
    AdminBranchWorkstationView,
    AdminBranchWorkstationsSummaryView,
    AdminWorkstationAccessContextView,
    AdminWorkstationAccessUserView,
    AdminWorkstationAvailableActionsView,
    AdminWorkstationBranchRelationshipView,
    AdminWorkstationCashSessionContextView,
    AdminWorkstationCashSessionState,
    AdminWorkstationCashSessionSummaryView,
    AdminWorkstationCreateRequest,
    AdminWorkstationDetailView,
    AdminWorkstationFilterOptionsView,
    AdminWorkstationListItemView,
    AdminWorkstationMetricsView,
    AdminWorkstationOperationalConfigView,
    AdminWorkstationOverviewView,
    AdminWorkstationReadinessStatus,
    AdminWorkstationsListResponse,
    AdminWorkstationUpdateRequest,
)
from zeromerma_api.modules.branches.domain.exceptions import (
    BranchConflictError,
    BranchNotFoundError,
    BranchValidationError,
    BrandNotFoundError,
    WorkstationAdminNotFoundError,
    WorkstationConflictError,
    WorkstationValidationError,
)
from zeromerma_api.modules.branches.infrastructure.models import Branch, Brand, Workstation
from zeromerma_api.modules.cash.domain.constants import CASH_SESSION_STATUS_CLOSED, CASH_SESSION_STATUS_OPEN
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment
from zeromerma_api.modules.outbox.application.service import OutboxWriter

AUDIT_ACTION_ADMIN_BRANCH_CREATED = "admin.branch.created"
AUDIT_ACTION_ADMIN_BRANCH_UPDATED = "admin.branch.updated"
OUTBOX_EVENT_ADMIN_BRANCH_CREATED_V1 = "admin.branch.created.v1"
OUTBOX_EVENT_ADMIN_BRANCH_UPDATED_V1 = "admin.branch.updated.v1"
AUDIT_ACTION_ADMIN_WORKSTATION_CREATED = "admin.workstation.created"
AUDIT_ACTION_ADMIN_WORKSTATION_UPDATED = "admin.workstation.updated"
OUTBOX_EVENT_ADMIN_WORKSTATION_CREATED_V1 = "admin.workstation.created.v1"
OUTBOX_EVENT_ADMIN_WORKSTATION_UPDATED_V1 = "admin.workstation.updated.v1"
BRANCH_RESOURCE_TYPE = "branch"
WORKSTATION_RESOURCE_TYPE = "workstation"


@dataclass(frozen=True)
class _BranchAdminRow:
    branch: Branch
    brand: Brand
    workstation_count: int
    active_workstation_count: int
    assigned_user_count: int
    open_cash_sessions: int


@dataclass(frozen=True)
class _WorkstationAdminRow:
    workstation: Workstation
    branch: Branch
    active_session: CashSession | None
    last_closed_session: CashSession | None
    assigned_user_count: int
    active_assigned_user_count: int


class AdminBranchService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_branches(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        status_filter: str | None,
        has_active_workstations: str | None,
        warning_state: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminBranchesListResponse:
        if brand_id is not None:
            self._get_brand(session, brand_id)

        rows = self._fetch_rows(
            session,
            brand_id=brand_id,
            status_filter=status_filter,
            search=search,
        )

        normalized_workstation_filter = _normalize_optional(has_active_workstations)
        if normalized_workstation_filter == "yes":
            rows = [row for row in rows if row.active_workstation_count > 0]
        elif normalized_workstation_filter == "no":
            rows = [row for row in rows if row.active_workstation_count == 0]

        normalized_warning_state = _normalize_optional(warning_state)
        if normalized_warning_state == "with_warnings":
            rows = [row for row in rows if self._build_warnings(row)]
        elif normalized_warning_state == "without_warnings":
            rows = [row for row in rows if not self._build_warnings(row)]

        items = [self._to_list_item(row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminBranchesListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_branch_detail(self, session: Session, *, branch_id: uuid.UUID) -> AdminBranchDetailView:
        row = self._get_row(session, branch_id)
        return self._to_detail(session, row)

    def create_branch(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminBranchCreateRequest,
        request_id: str | None,
    ) -> AdminBranchDetailView:
        brand = self._get_brand(session, command.brand_id)
        code = self._normalize_code(command.code)
        self._validate_timezone(command.timezone)
        self._ensure_unique_code(session, code)

        branch = Branch(
            brand_id=brand.id,
            code=code,
            name=command.name.strip(),
            timezone=command.timezone.strip(),
            is_active=command.is_active,
            address_line=command.address_line,
            city=command.city,
            state=command.state,
            country=command.country,
            postal_code=command.postal_code,
            phone=command.phone,
            contact_email=command.contact_email,
            notes=command.notes,
        )

        try:
            session.add(branch)
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                branch=branch,
                action=AUDIT_ACTION_ADMIN_BRANCH_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_BRANCH_CREATED_V1,
                request_id=request_id,
                metadata=self._branch_metadata(branch, brand),
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise BranchValidationError("Branch code must be unique.") from error

        return self.get_branch_detail(session, branch_id=branch.id)

    def update_branch(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        branch_id: uuid.UUID,
        command: AdminBranchUpdateRequest,
        request_id: str | None,
    ) -> AdminBranchDetailView:
        row = self._get_row(session, branch_id)
        branch = row.branch
        brand = row.brand
        previous_status = branch.is_active

        if command.brand_id is not None and command.brand_id != branch.brand_id:
            brand = self._get_brand(session, command.brand_id)
            branch.brand_id = brand.id

        if command.code is not None:
            code = self._normalize_code(command.code)
            self._ensure_unique_code(session, code, exclude_branch_id=branch.id)
            branch.code = code

        if command.name is not None:
            branch.name = command.name.strip()

        if command.timezone is not None:
            self._validate_timezone(command.timezone)
            branch.timezone = command.timezone.strip()

        if command.is_active is not None:
            if previous_status and not command.is_active and row.open_cash_sessions > 0:
                raise BranchConflictError(
                    "Branch cannot be deactivated while it has open cash sessions.",
                )
            branch.is_active = command.is_active

        for field_name in (
            "address_line",
            "city",
            "state",
            "country",
            "postal_code",
            "phone",
            "contact_email",
            "notes",
        ):
            value = getattr(command, field_name)
            if field_name in command.model_fields_set:
                setattr(branch, field_name, value)

        try:
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                branch=branch,
                action=AUDIT_ACTION_ADMIN_BRANCH_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_BRANCH_UPDATED_V1,
                request_id=request_id,
                metadata={
                    **self._branch_metadata(branch, brand),
                    "previous_status": "active" if previous_status else "inactive",
                    "new_status": _branch_status(branch),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise BranchValidationError("Branch code must be unique.") from error

        return self.get_branch_detail(session, branch_id=branch.id)

    def _fetch_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        status_filter: str | None,
        search: str | None,
    ) -> list[_BranchAdminRow]:
        query = select(Branch, Brand).join(Brand, Branch.brand_id == Brand.id)

        if brand_id is not None:
            query = query.where(Branch.brand_id == brand_id)

        normalized_status = _normalize_optional(status_filter)
        if normalized_status == "active":
            query = query.where(Branch.is_active.is_(True))
        elif normalized_status == "inactive":
            query = query.where(Branch.is_active.is_(False))

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Branch.code).like(pattern),
                    func.lower(Branch.name).like(pattern),
                    func.lower(Brand.name).like(pattern),
                    func.lower(Branch.city).like(pattern),
                    func.lower(Branch.state).like(pattern),
                ),
            )

        branch_rows = session.execute(query.order_by(Branch.name.asc(), Branch.code.asc())).all()
        branch_ids = [branch.id for branch, _brand in branch_rows]
        workstation_counts, active_workstation_counts = self._workstation_counts(session, branch_ids)
        assignment_counts = self._assignment_counts(session, branch_ids)
        open_cash_session_counts = self._open_cash_session_counts(session, branch_ids)

        return [
            _BranchAdminRow(
                branch=branch,
                brand=brand,
                workstation_count=workstation_counts.get(branch.id, 0),
                active_workstation_count=active_workstation_counts.get(branch.id, 0),
                assigned_user_count=assignment_counts.get(branch.id, 0),
                open_cash_sessions=open_cash_session_counts.get(branch.id, 0),
            )
            for branch, brand in branch_rows
        ]

    def _get_row(self, session: Session, branch_id: uuid.UUID) -> _BranchAdminRow:
        result = session.execute(
            select(Branch, Brand)
            .join(Brand, Branch.brand_id == Brand.id)
            .where(Branch.id == branch_id),
        ).one_or_none()
        if result is None:
            raise BranchNotFoundError("Branch was not found.")

        branch, brand = result
        counts, active_counts = self._workstation_counts(session, [branch.id])
        assignment_counts = self._assignment_counts(session, [branch.id])
        open_cash_session_counts = self._open_cash_session_counts(session, [branch.id])
        return _BranchAdminRow(
            branch=branch,
            brand=brand,
            workstation_count=counts.get(branch.id, 0),
            active_workstation_count=active_counts.get(branch.id, 0),
            assigned_user_count=assignment_counts.get(branch.id, 0),
            open_cash_sessions=open_cash_session_counts.get(branch.id, 0),
        )

    def _to_list_item(self, row: _BranchAdminRow) -> AdminBranchListItemView:
        warnings = self._build_warnings(row)
        return AdminBranchListItemView(
            active_workstation_count=row.active_workstation_count,
            assigned_user_count=row.assigned_user_count,
            brand_id=row.brand.id,
            brand_name=row.brand.name,
            code=row.branch.code,
            id=row.branch.id,
            name=row.branch.name,
            readiness=self._readiness(row, warnings),
            status=_branch_status(row.branch),
            timezone=row.branch.timezone,
            updated_at=row.branch.updated_at,
            warnings=warnings,
            workstation_count=row.workstation_count,
        )

    def _to_detail(self, session: Session, row: _BranchAdminRow) -> AdminBranchDetailView:
        warnings = self._build_warnings(row)
        workstations = self._fetch_workstations(session, row.branch.id)
        assignments = self._fetch_assignments(session, row.branch.id)
        readiness = self._readiness(row, warnings)

        return AdminBranchDetailView(
            available_actions=AdminBranchAvailableActionsView(
                can_activate=not row.branch.is_active,
                can_deactivate=row.branch.is_active,
            ),
            location_contact=AdminBranchLocationContactView(
                address_line=row.branch.address_line,
                city=row.branch.city,
                state=row.branch.state,
                country=row.branch.country,
                postal_code=row.branch.postal_code,
                phone=row.branch.phone,
                contact_email=row.branch.contact_email,
                notes=row.branch.notes,
            ),
            operational_config=AdminBranchOperationalConfigView(
                is_active=row.branch.is_active,
                pos_ready=row.branch.is_active and row.active_workstation_count > 0,
                timezone=row.branch.timezone,
            ),
            overview=AdminBranchOverviewView(
                brand_id=row.brand.id,
                brand_name=row.brand.name,
                code=row.branch.code,
                created_at=row.branch.created_at,
                id=row.branch.id,
                name=row.branch.name,
                readiness=readiness,
                status=_branch_status(row.branch),
                timezone=row.branch.timezone,
                updated_at=row.branch.updated_at,
            ),
            related_operations_summary=AdminBranchRelatedOperationsSummaryView(
                open_cash_sessions=row.open_cash_sessions,
            ),
            user_assignments_summary=AdminBranchUsersSummaryView(
                active=sum(1 for item in assignments if item.is_active),
                inactive=sum(1 for item in assignments if not item.is_active),
                items=assignments,
                total=len(assignments),
            ),
            warnings=warnings,
            workstations_summary=AdminBranchWorkstationsSummaryView(
                active=sum(1 for item in workstations if item.is_active),
                inactive=sum(1 for item in workstations if not item.is_active),
                items=workstations,
                total=len(workstations),
            ),
        )

    def _build_metrics(self, rows: list[_BranchAdminRow]) -> AdminBranchMetricsView:
        return AdminBranchMetricsView(
            active_branches=sum(1 for row in rows if row.branch.is_active),
            inactive_branches=sum(1 for row in rows if not row.branch.is_active),
            total_branches=len(rows),
            with_warnings=sum(1 for row in rows if self._build_warnings(row)),
            with_workstations=sum(1 for row in rows if row.workstation_count > 0),
            without_active_workstation=sum(1 for row in rows if row.active_workstation_count == 0),
        )

    def _build_filter_options(self, session: Session) -> AdminBranchFilterOptionsView:
        brands = session.execute(select(Brand).order_by(Brand.name.asc())).scalars().all()
        return AdminBranchFilterOptionsView(
            brands=[AdminBranchFilterOptionView(id=brand.id, label=brand.name) for brand in brands],
        )

    def _build_warnings(self, row: _BranchAdminRow) -> list[AdminBranchWarningView]:
        warnings: list[AdminBranchWarningView] = []
        if not row.branch.is_active:
            warnings.append(
                AdminBranchWarningView(
                    code="inactive_branch",
                    message="La sucursal esta inactiva y no puede operar POS.",
                    severity="info",
                ),
            )
        if not row.branch.timezone.strip():
            warnings.append(
                AdminBranchWarningView(
                    code="missing_timezone",
                    message="La sucursal no tiene zona horaria configurada.",
                    severity="critical",
                ),
            )
        if row.active_workstation_count == 0:
            warnings.append(
                AdminBranchWarningView(
                    code="no_active_workstation",
                    message="No hay cajas o estaciones activas para operar POS.",
                    severity="warning",
                ),
            )
        if row.assigned_user_count == 0:
            warnings.append(
                AdminBranchWarningView(
                    code="no_assigned_users",
                    message="No hay usuarios activos asignados a esta sucursal.",
                    severity="warning",
                ),
            )
        if row.open_cash_sessions > 0:
            warnings.append(
                AdminBranchWarningView(
                    code="open_cash_sessions",
                    message="Hay sesiones de caja abiertas asociadas a esta sucursal.",
                    severity="critical",
                ),
            )
        return warnings

    def _readiness(
        self,
        row: _BranchAdminRow,
        warnings: list[AdminBranchWarningView],
    ) -> AdminBranchReadinessStatus:
        if not row.branch.is_active:
            return "inactive"
        if warnings:
            return "warning"
        return "ready"

    def _fetch_workstations(
        self,
        session: Session,
        branch_id: uuid.UUID,
    ) -> list[AdminBranchWorkstationView]:
        workstations = session.execute(
            select(Workstation)
            .where(Workstation.branch_id == branch_id)
            .order_by(Workstation.name.asc(), Workstation.code.asc()),
        ).scalars()
        return [
            AdminBranchWorkstationView(
                code=workstation.code,
                id=workstation.id,
                is_active=workstation.is_active,
                name=workstation.name,
                updated_at=workstation.updated_at,
            )
            for workstation in workstations
        ]

    def _fetch_assignments(
        self,
        session: Session,
        branch_id: uuid.UUID,
    ) -> list[AdminBranchUserAssignmentView]:
        assignments = session.execute(
            select(UserBranchAssignment, User)
            .join(User, UserBranchAssignment.user_id == User.id)
            .where(UserBranchAssignment.branch_id == branch_id)
            .order_by(User.full_name.asc(), User.email.asc()),
        ).all()
        return [
            AdminBranchUserAssignmentView(
                assignment_id=assignment.id,
                is_active=assignment.is_active and user.is_active,
                updated_at=assignment.updated_at,
                user_email=user.email,
                user_id=user.id,
                user_name=user.full_name,
            )
            for assignment, user in assignments
        ]

    def _workstation_counts(
        self,
        session: Session,
        branch_ids: list[uuid.UUID],
    ) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
        if not branch_ids:
            return {}, {}
        count_rows = session.execute(
            select(Workstation.branch_id, func.count(Workstation.id))
            .where(Workstation.branch_id.in_(branch_ids))
            .group_by(Workstation.branch_id),
        ).all()
        active_rows = session.execute(
            select(Workstation.branch_id, func.count(Workstation.id))
            .where(Workstation.branch_id.in_(branch_ids), Workstation.is_active.is_(True))
            .group_by(Workstation.branch_id),
        ).all()
        return (
            {branch_id: int(count) for branch_id, count in count_rows},
            {branch_id: int(count) for branch_id, count in active_rows},
        )

    def _assignment_counts(
        self,
        session: Session,
        branch_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        if not branch_ids:
            return {}
        rows = session.execute(
            select(UserBranchAssignment.branch_id, func.count(UserBranchAssignment.id))
            .join(User, UserBranchAssignment.user_id == User.id)
            .where(
                UserBranchAssignment.branch_id.in_(branch_ids),
                UserBranchAssignment.is_active.is_(True),
                User.is_active.is_(True),
            )
            .group_by(UserBranchAssignment.branch_id),
        ).all()
        return {branch_id: int(count) for branch_id, count in rows}

    def _open_cash_session_counts(
        self,
        session: Session,
        branch_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, int]:
        if not branch_ids:
            return {}
        rows = session.execute(
            select(CashSession.branch_id, func.count(CashSession.id))
            .where(
                CashSession.branch_id.in_(branch_ids),
                CashSession.status == CASH_SESSION_STATUS_OPEN,
            )
            .group_by(CashSession.branch_id),
        ).all()
        return {branch_id: int(count) for branch_id, count in rows}

    def _get_brand(self, session: Session, brand_id: uuid.UUID) -> Brand:
        brand = session.get(Brand, brand_id)
        if brand is None:
            raise BrandNotFoundError("Brand was not found.")
        return brand

    def _ensure_unique_code(
        self,
        session: Session,
        code: str,
        *,
        exclude_branch_id: uuid.UUID | None = None,
    ) -> None:
        query = select(Branch.id).where(Branch.code == code)
        if exclude_branch_id is not None:
            query = query.where(Branch.id != exclude_branch_id)
        existing_id = session.execute(query).scalar_one_or_none()
        if existing_id is not None:
            raise BranchValidationError("Branch code must be unique.")

    def _validate_timezone(self, timezone: str) -> None:
        try:
            ZoneInfo(timezone.strip())
        except ZoneInfoNotFoundError as error:
            raise BranchValidationError("Branch timezone is not valid.") from error

    def _normalize_code(self, value: str) -> str:
        normalized = value.strip().upper().replace(" ", "_")
        if not normalized:
            raise BranchValidationError("Branch code is required.")
        return normalized

    def _record_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        branch: Branch,
        action: str,
        event_name: str,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=BRANCH_RESOURCE_TYPE,
            resource_id=str(branch.id),
            branch_id=branch.id,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=BRANCH_RESOURCE_TYPE,
            aggregate_id=str(branch.id),
            event_name=event_name,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )

    def _branch_metadata(self, branch: Branch, brand: Brand) -> dict[str, object]:
        return {
            "brand_id": str(brand.id),
            "brand_name": brand.name,
            "code": branch.code,
            "name": branch.name,
            "status": _branch_status(branch),
            "timezone": branch.timezone,
        }


def _branch_status(branch: Branch) -> str:
    return "active" if branch.is_active else "inactive"


class AdminWorkstationService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_workstations(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        status_filter: str | None,
        cash_session_state: str | None,
        readiness: str | None,
        warning_state: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminWorkstationsListResponse:
        if branch_id is not None:
            self._get_branch(session, branch_id)

        rows = self._fetch_rows(
            session,
            branch_id=branch_id,
            status_filter=status_filter,
            search=search,
        )

        normalized_cash_state = _normalize_optional(cash_session_state)
        if normalized_cash_state and normalized_cash_state != "all":
            rows = [row for row in rows if self._cash_session_state(row) == normalized_cash_state]

        normalized_readiness = _normalize_optional(readiness)
        if normalized_readiness and normalized_readiness != "all":
            rows = [
                row
                for row in rows
                if self._readiness(row, self._build_warnings(row)) == normalized_readiness
            ]

        normalized_warning_state = _normalize_optional(warning_state)
        if normalized_warning_state == "with_warnings":
            rows = [row for row in rows if self._build_warnings(row)]
        elif normalized_warning_state == "without_warnings":
            rows = [row for row in rows if not self._build_warnings(row)]

        items = [self._to_list_item(row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminWorkstationsListResponse(
            filter_options=self._build_filter_options(session),
            items=items[offset : offset + safe_page_size],
            metrics=self._build_metrics(rows),
            page=safe_page,
            page_size=safe_page_size,
            total=total,
        )

    def get_workstation_detail(
        self,
        session: Session,
        *,
        workstation_id: uuid.UUID,
    ) -> AdminWorkstationDetailView:
        row = self._get_row(session, workstation_id)
        return self._to_detail(session, row)

    def create_workstation(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminWorkstationCreateRequest,
        request_id: str | None,
    ) -> AdminWorkstationDetailView:
        branch = self._get_branch(session, command.branch_id)
        code = self._normalize_code(command.code)
        self._ensure_unique_code(session, code)

        workstation = Workstation(
            branch_id=branch.id,
            code=code,
            name=command.name.strip(),
            is_active=command.is_active,
        )
        try:
            session.add(workstation)
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                workstation=workstation,
                action=AUDIT_ACTION_ADMIN_WORKSTATION_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_WORKSTATION_CREATED_V1,
                request_id=request_id,
                metadata=self._workstation_metadata(workstation, branch),
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise WorkstationValidationError("Workstation code must be unique.") from error

        return self.get_workstation_detail(session, workstation_id=workstation.id)

    def update_workstation(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_id: uuid.UUID,
        command: AdminWorkstationUpdateRequest,
        request_id: str | None,
    ) -> AdminWorkstationDetailView:
        row = self._get_row(session, workstation_id)
        workstation = row.workstation
        branch = row.branch
        previous_status = workstation.is_active

        if command.branch_id is not None and command.branch_id != workstation.branch_id:
            if row.active_session is not None:
                raise WorkstationConflictError(
                    "Workstation cannot be moved while it has an open cash session.",
                )
            branch = self._get_branch(session, command.branch_id)
            workstation.branch_id = branch.id

        if command.code is not None:
            code = self._normalize_code(command.code)
            self._ensure_unique_code(session, code, exclude_workstation_id=workstation.id)
            workstation.code = code

        if command.name is not None:
            workstation.name = command.name.strip()

        if command.is_active is not None:
            if previous_status and not command.is_active and row.active_session is not None:
                raise WorkstationConflictError(
                    "Workstation cannot be deactivated while it has an open cash session.",
                )
            workstation.is_active = command.is_active

        try:
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                workstation=workstation,
                action=AUDIT_ACTION_ADMIN_WORKSTATION_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_WORKSTATION_UPDATED_V1,
                request_id=request_id,
                metadata={
                    **self._workstation_metadata(workstation, branch),
                    "previous_status": "active" if previous_status else "inactive",
                    "new_status": _workstation_status(workstation),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise WorkstationValidationError("Workstation code must be unique.") from error

        return self.get_workstation_detail(session, workstation_id=workstation.id)

    def _fetch_rows(
        self,
        session: Session,
        *,
        branch_id: uuid.UUID | None,
        status_filter: str | None,
        search: str | None,
    ) -> list[_WorkstationAdminRow]:
        query = select(Workstation, Branch).join(Branch, Workstation.branch_id == Branch.id)

        if branch_id is not None:
            query = query.where(Workstation.branch_id == branch_id)

        normalized_status = _normalize_optional(status_filter)
        if normalized_status == "active":
            query = query.where(Workstation.is_active.is_(True))
        elif normalized_status == "inactive":
            query = query.where(Workstation.is_active.is_(False))

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Workstation.code).like(pattern),
                    func.lower(Workstation.name).like(pattern),
                    func.lower(Branch.code).like(pattern),
                    func.lower(Branch.name).like(pattern),
                ),
            )

        raw_rows = session.execute(
            query.order_by(Branch.name.asc(), Workstation.name.asc(), Workstation.code.asc()),
        ).all()
        workstation_ids = [workstation.id for workstation, _branch in raw_rows]
        branch_ids = [branch.id for _workstation, branch in raw_rows]
        active_sessions, last_closed_sessions = self._cash_session_maps(session, workstation_ids)
        assigned_user_counts, active_assigned_user_counts = self._assignment_counts(session, branch_ids)

        return [
            _WorkstationAdminRow(
                active_assigned_user_count=active_assigned_user_counts.get(branch.id, 0),
                active_session=active_sessions.get(workstation.id),
                assigned_user_count=assigned_user_counts.get(branch.id, 0),
                branch=branch,
                last_closed_session=last_closed_sessions.get(workstation.id),
                workstation=workstation,
            )
            for workstation, branch in raw_rows
        ]

    def _get_row(self, session: Session, workstation_id: uuid.UUID) -> _WorkstationAdminRow:
        result = session.execute(
            select(Workstation, Branch)
            .join(Branch, Workstation.branch_id == Branch.id)
            .where(Workstation.id == workstation_id),
        ).one_or_none()
        if result is None:
            raise WorkstationAdminNotFoundError("Workstation was not found.")

        workstation, branch = result
        active_sessions, last_closed_sessions = self._cash_session_maps(session, [workstation.id])
        assigned_user_counts, active_assigned_user_counts = self._assignment_counts(session, [branch.id])
        return _WorkstationAdminRow(
            active_assigned_user_count=active_assigned_user_counts.get(branch.id, 0),
            active_session=active_sessions.get(workstation.id),
            assigned_user_count=assigned_user_counts.get(branch.id, 0),
            branch=branch,
            last_closed_session=last_closed_sessions.get(workstation.id),
            workstation=workstation,
        )

    def _to_list_item(self, row: _WorkstationAdminRow) -> AdminWorkstationListItemView:
        warnings = self._build_warnings(row)
        return AdminWorkstationListItemView(
            active_cash_session_id=row.active_session.id if row.active_session else None,
            branch_code=row.branch.code,
            branch_id=row.branch.id,
            branch_is_active=row.branch.is_active,
            branch_name=row.branch.name,
            code=row.workstation.code,
            has_active_cash_session=row.active_session is not None,
            id=row.workstation.id,
            last_closed_at=row.last_closed_session.closed_at if row.last_closed_session else None,
            last_opened_at=(
                row.active_session.opened_at
                if row.active_session
                else row.last_closed_session.opened_at
                if row.last_closed_session
                else None
            ),
            name=row.workstation.name,
            readiness=self._readiness(row, warnings),
            status=_workstation_status(row.workstation),
            updated_at=row.workstation.updated_at,
            warnings=warnings,
        )

    def _to_detail(self, session: Session, row: _WorkstationAdminRow) -> AdminWorkstationDetailView:
        warnings = self._build_warnings(row)
        readiness = self._readiness(row, warnings)
        access_users = self._fetch_access_users(session, row.branch.id)

        return AdminWorkstationDetailView(
            access_context=AdminWorkstationAccessContextView(
                active_assigned_user_count=sum(1 for user in access_users if user.is_active),
                assigned_user_count=len(access_users),
                users=access_users,
            ),
            available_actions=AdminWorkstationAvailableActionsView(
                can_activate=not row.workstation.is_active,
                can_deactivate=row.workstation.is_active and row.active_session is None,
                can_open_cash_session=row.active_session is not None,
            ),
            branch_relationship=AdminWorkstationBranchRelationshipView(
                branch_code=row.branch.code,
                branch_id=row.branch.id,
                branch_is_active=row.branch.is_active,
                branch_name=row.branch.name,
                branch_timezone=row.branch.timezone,
            ),
            cash_session_context=AdminWorkstationCashSessionContextView(
                active_session=self._to_cash_session_summary(session, row.active_session),
                last_closed_session=self._to_cash_session_summary(session, row.last_closed_session),
            ),
            operational_config=AdminWorkstationOperationalConfigView(
                is_active=row.workstation.is_active,
                pos_enabled=row.workstation.is_active and row.branch.is_active,
            ),
            overview=AdminWorkstationOverviewView(
                code=row.workstation.code,
                created_at=row.workstation.created_at,
                id=row.workstation.id,
                name=row.workstation.name,
                readiness=readiness,
                status=_workstation_status(row.workstation),
                updated_at=row.workstation.updated_at,
            ),
            warnings=warnings,
        )

    def _build_metrics(self, rows: list[_WorkstationAdminRow]) -> AdminWorkstationMetricsView:
        return AdminWorkstationMetricsView(
            active_workstations=sum(1 for row in rows if row.workstation.is_active),
            inactive_workstations=sum(1 for row in rows if not row.workstation.is_active),
            total_workstations=len(rows),
            with_open_cash_session=sum(1 for row in rows if row.active_session is not None),
            with_warnings=sum(1 for row in rows if self._build_warnings(row)),
            without_active_branch=sum(1 for row in rows if not row.branch.is_active),
        )

    def _build_filter_options(self, session: Session) -> AdminWorkstationFilterOptionsView:
        branches = session.execute(select(Branch).order_by(Branch.name.asc(), Branch.code.asc())).scalars().all()
        return AdminWorkstationFilterOptionsView(
            branches=[
                AdminBranchFilterOptionView(id=branch.id, label=f"{branch.name} - {branch.code}")
                for branch in branches
            ],
        )

    def _build_warnings(self, row: _WorkstationAdminRow) -> list[AdminBranchWarningView]:
        warnings: list[AdminBranchWarningView] = []
        if not row.workstation.is_active:
            warnings.append(
                AdminBranchWarningView(
                    code="inactive_workstation",
                    message="La estacion esta inactiva y no puede operar POS.",
                    severity="critical",
                ),
            )
        if not row.branch.is_active:
            warnings.append(
                AdminBranchWarningView(
                    code="inactive_branch",
                    message="La sucursal vinculada esta inactiva.",
                    severity="critical",
                ),
            )
        if row.active_assigned_user_count == 0:
            warnings.append(
                AdminBranchWarningView(
                    code="no_branch_users",
                    message="La sucursal no tiene usuarios activos asignados para operar esta estacion.",
                    severity="warning",
                ),
            )
        if row.active_session is not None:
            warnings.append(
                AdminBranchWarningView(
                    code="open_cash_session",
                    message="Esta estacion tiene una caja abierta actualmente.",
                    severity="info",
                ),
            )
        if row.active_session is None and row.last_closed_session is None:
            warnings.append(
                AdminBranchWarningView(
                    code="no_recent_cash_activity",
                    message="No hay actividad de caja reciente registrada para esta estacion.",
                    severity="info",
                ),
            )
        return warnings

    def _readiness(
        self,
        row: _WorkstationAdminRow,
        warnings: list[AdminBranchWarningView],
    ) -> AdminWorkstationReadinessStatus:
        if not row.workstation.is_active or not row.branch.is_active:
            return "blocked"
        if any(warning.severity in ("critical", "warning") for warning in warnings):
            return "warning"
        return "ready"

    def _cash_session_state(self, row: _WorkstationAdminRow) -> AdminWorkstationCashSessionState:
        if row.active_session is not None:
            return "open"
        if row.last_closed_session is not None:
            return "closed"
        return "no_recent_session"

    def _cash_session_maps(
        self,
        session: Session,
        workstation_ids: list[uuid.UUID],
    ) -> tuple[dict[uuid.UUID, CashSession], dict[uuid.UUID, CashSession]]:
        if not workstation_ids:
            return {}, {}
        sessions = session.execute(
            select(CashSession)
            .where(CashSession.workstation_id.in_(workstation_ids))
            .order_by(CashSession.opened_at.desc()),
        ).scalars()
        active_sessions: dict[uuid.UUID, CashSession] = {}
        last_closed_sessions: dict[uuid.UUID, CashSession] = {}
        for cash_session in sessions:
            if (
                cash_session.status == CASH_SESSION_STATUS_OPEN
                and cash_session.workstation_id not in active_sessions
            ):
                active_sessions[cash_session.workstation_id] = cash_session
            if (
                (
                    cash_session.status == CASH_SESSION_STATUS_CLOSED
                    or cash_session.closed_at is not None
                )
                and cash_session.workstation_id not in last_closed_sessions
            ):
                last_closed_sessions[cash_session.workstation_id] = cash_session
        return active_sessions, last_closed_sessions

    def _assignment_counts(
        self,
        session: Session,
        branch_ids: list[uuid.UUID],
    ) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
        if not branch_ids:
            return {}, {}
        all_rows = session.execute(
            select(UserBranchAssignment.branch_id, func.count(UserBranchAssignment.id))
            .join(User, UserBranchAssignment.user_id == User.id)
            .where(UserBranchAssignment.branch_id.in_(branch_ids))
            .group_by(UserBranchAssignment.branch_id),
        ).all()
        active_rows = session.execute(
            select(UserBranchAssignment.branch_id, func.count(UserBranchAssignment.id))
            .join(User, UserBranchAssignment.user_id == User.id)
            .where(
                UserBranchAssignment.branch_id.in_(branch_ids),
                UserBranchAssignment.is_active.is_(True),
                User.is_active.is_(True),
            )
            .group_by(UserBranchAssignment.branch_id),
        ).all()
        return (
            {branch_id: int(count) for branch_id, count in all_rows},
            {branch_id: int(count) for branch_id, count in active_rows},
        )

    def _fetch_access_users(
        self,
        session: Session,
        branch_id: uuid.UUID,
    ) -> list[AdminWorkstationAccessUserView]:
        rows = session.execute(
            select(UserBranchAssignment, User)
            .join(User, UserBranchAssignment.user_id == User.id)
            .where(UserBranchAssignment.branch_id == branch_id)
            .order_by(User.full_name.asc(), User.email.asc()),
        ).all()
        return [
            AdminWorkstationAccessUserView(
                is_active=assignment.is_active and user.is_active,
                user_email=user.email,
                user_id=user.id,
                user_name=user.full_name,
            )
            for assignment, user in rows
        ]

    def _to_cash_session_summary(
        self,
        session: Session,
        cash_session: CashSession | None,
    ) -> AdminWorkstationCashSessionSummaryView | None:
        if cash_session is None:
            return None
        user = session.get(User, cash_session.user_id)
        return AdminWorkstationCashSessionSummaryView(
            closed_at=cash_session.closed_at,
            id=cash_session.id,
            opened_at=cash_session.opened_at,
            opened_by_user_id=user.id if user else None,
            opened_by_user_name=user.full_name if user else None,
            opening_amount=str(cash_session.opening_amount),
            status=cash_session.status,
        )

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.get(Branch, branch_id)
        if branch is None:
            raise BranchNotFoundError("Branch was not found.")
        return branch

    def _ensure_unique_code(
        self,
        session: Session,
        code: str,
        *,
        exclude_workstation_id: uuid.UUID | None = None,
    ) -> None:
        query = select(Workstation.id).where(Workstation.code == code)
        if exclude_workstation_id is not None:
            query = query.where(Workstation.id != exclude_workstation_id)
        existing_id = session.execute(query).scalar_one_or_none()
        if existing_id is not None:
            raise WorkstationValidationError("Workstation code must be unique.")

    def _normalize_code(self, value: str) -> str:
        normalized = value.strip().upper().replace(" ", "_")
        if not normalized:
            raise WorkstationValidationError("Workstation code is required.")
        return normalized

    def _record_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation: Workstation,
        action: str,
        event_name: str,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=WORKSTATION_RESOURCE_TYPE,
            resource_id=str(workstation.id),
            branch_id=workstation.branch_id,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=WORKSTATION_RESOURCE_TYPE,
            aggregate_id=str(workstation.id),
            event_name=event_name,
            payload=metadata,
            headers={"request_id": request_id} if request_id else {},
        )

    def _workstation_metadata(self, workstation: Workstation, branch: Branch) -> dict[str, object]:
        return {
            "branch_code": branch.code,
            "branch_id": str(branch.id),
            "branch_name": branch.name,
            "code": workstation.code,
            "name": workstation.name,
            "status": _workstation_status(workstation),
        }


def _workstation_status(workstation: Workstation) -> str:
    return "active" if workstation.is_active else "inactive"


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None
