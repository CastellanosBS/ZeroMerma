from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast as type_cast

from sqlalchemy import String, and_, cast, exists, func, or_, select
from sqlalchemy.engine import RowMapping
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.application.reconciliation_schemas import (
    AdminPendingDiscrepanciesResponse,
    AdminPendingDiscrepancyItemView,
    AdminReconciliationAvailableActionsView,
    AdminReconciliationBackendContractView,
    AdminReconciliationCreateRequest,
    AdminReconciliationDetailView,
    AdminReconciliationDifferenceBreakdownView,
    AdminReconciliationEvidenceView,
    AdminReconciliationExplanationView,
    AdminReconciliationFilterOptionsView,
    AdminReconciliationFilterOptionView,
    AdminReconciliationListItemView,
    AdminReconciliationListResponse,
    AdminReconciliationMetricsView,
    AdminReconciliationOverviewView,
    AdminReconciliationRelatedDocumentView,
    AdminReconciliationResolutionView,
    AdminReconciliationResolveRequest,
    AdminReconciliationSourceContextView,
)
from zeromerma_api.modules.cash_close.domain.constants import (
    CASH_CLOSE_PAYMENT_METHOD_CASH,
    CASH_CLOSE_STATUS_COMMITTED,
    FINANCIAL_RECONCILIATION_REASON_OTHER,
    FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT,
    FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
    FINANCIAL_RECONCILIATION_STATUS_PENDING,
    FINANCIAL_RECONCILIATION_STATUS_RECONCILED,
    FINANCIAL_RECONCILIATION_STATUS_VOIDED,
    OUTBOX_EVENT_FINANCIAL_RECONCILIATION_CREATED_V1,
    OUTBOX_EVENT_FINANCIAL_RECONCILIATION_RESOLVED_V1,
    VALID_FINANCIAL_RECONCILIATION_REASONS,
    VALID_FINANCIAL_RECONCILIATION_SOURCES,
    VALID_FINANCIAL_RECONCILIATION_STATUSES,
)
from zeromerma_api.modules.cash_close.domain.exceptions import (
    CashCloseNotFoundError,
    CashCloseValidationError,
)
from zeromerma_api.modules.cash_close.infrastructure.models import (
    CashSessionClose,
    FinancialReconciliation,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.payments.infrastructure.models import (
    OperationalPayment,
    OperationalPaymentCategory,
)
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn
from zeromerma_api.modules.sales.domain.constants import (
    SALE_PAYMENT_METHOD_CARD,
    SALE_PAYMENT_METHOD_CASH,
    SALE_PAYMENT_METHOD_MIXED,
)
from zeromerma_api.modules.sales.infrastructure.models import Sale
from zeromerma_api.modules.tickets.application.admin_services import build_ticket_folio

ADMIN_RECONCILIATION_PAGE_SIZE_MAX = 100
ADMIN_RECONCILIATION_RESOURCE_TYPE = "financial_reconciliation"
AUDIT_ACTION_FINANCIAL_RECONCILIATION_CREATED = "admin.financial_reconciliation.created"
AUDIT_ACTION_FINANCIAL_RECONCILIATION_RESOLVED = "admin.financial_reconciliation.resolved"
DISCREPANCY_DIRECTION_EXACT = "EXACT"
DISCREPANCY_DIRECTION_OVERAGE = "OVERAGE"
DISCREPANCY_DIRECTION_SHORTAGE = "SHORTAGE"
EVIDENCE_STATE_WITH = "WITH_EVIDENCE"
EVIDENCE_STATE_WITHOUT = "WITHOUT_EVIDENCE"
ZERO_MONEY = Decimal("0.00")
MONEY_QUANTIZER = Decimal("0.01")
HIGH_IMPACT_DIFFERENCE_THRESHOLD = Decimal("100.00")


class AdminReconciliationService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_reconciliations(
        self,
        session: Session,
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        discrepancy_type: str | None,
        evidence_state: str | None,
        page: int,
        page_size: int,
        payment_method: str | None,
        search: str | None,
        source_type: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> AdminReconciliationListResponse:
        resolved_page = max(page, 1)
        resolved_page_size = min(max(page_size, 1), ADMIN_RECONCILIATION_PAGE_SIZE_MAX)
        conditions = self._build_record_conditions(
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            discrepancy_type=discrepancy_type,
            evidence_state=evidence_state,
            payment_method=payment_method,
            search=search,
            source_type=source_type,
            status_filter=status_filter,
            workstation_id=workstation_id,
        )
        base_statement = self._base_record_statement(conditions)
        total = int(
            session.execute(
                select(func.count()).select_from(base_statement.order_by(None).subquery())
            ).scalar_one()
        )
        rows = (
            session.execute(
                base_statement.order_by(
                    FinancialReconciliation.source_occurred_at.desc(),
                    FinancialReconciliation.created_at.desc(),
                )
                .limit(resolved_page_size)
                .offset((resolved_page - 1) * resolved_page_size)
            )
            .mappings()
            .all()
        )
        pending_discrepancies = self._list_pending_discrepancies(
            session,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            discrepancy_type=discrepancy_type,
            payment_method=payment_method,
            search=search,
            source_type=source_type,
            status_filter=status_filter,
            workstation_id=workstation_id,
            limit=25,
        )

        return AdminReconciliationListResponse(
            backend_contract=_backend_contract(),
            filter_options=self._build_filter_options(session),
            is_backend_connected=True,
            items=[_map_record_list_item(row) for row in rows],
            metrics=self._build_metrics(
                session,
                record_conditions=conditions,
                pending_items=pending_discrepancies,
            ),
            page=resolved_page,
            page_size=resolved_page_size,
            pending_discrepancies=pending_discrepancies,
            total=total,
        )

    def list_pending_discrepancies(
        self,
        session: Session,
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        discrepancy_type: str | None,
        payment_method: str | None,
        search: str | None,
        source_type: str | None,
        workstation_id: uuid.UUID | None,
    ) -> AdminPendingDiscrepanciesResponse:
        items = self._list_pending_discrepancies(
            session,
            amount_max=amount_max,
            amount_min=amount_min,
            branch_id=branch_id,
            cashier_id=cashier_id,
            date_from=date_from,
            date_to=date_to,
            discrepancy_type=discrepancy_type,
            limit=100,
            payment_method=payment_method,
            search=search,
            source_type=source_type,
            status_filter=None,
            workstation_id=workstation_id,
        )
        return AdminPendingDiscrepanciesResponse(
            backend_contract=_backend_contract(),
            items=items,
            total=len(items),
        )

    def get_reconciliation_detail(
        self,
        session: Session,
        *,
        reconciliation_id: uuid.UUID,
    ) -> AdminReconciliationDetailView:
        row = (
            session.execute(
                self._base_record_statement([]).where(
                    FinancialReconciliation.id == reconciliation_id
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CashCloseNotFoundError("Reconciliation record was not found.")
        return self._to_detail(session, row=row)

    def create_reconciliation(
        self,
        session: Session,
        *,
        command: AdminReconciliationCreateRequest,
        current_user: AuthenticatedUser,
        request_id: str | None,
    ) -> AdminReconciliationDetailView:
        source_type = _normalize_required(command.source_type)
        if source_type not in VALID_FINANCIAL_RECONCILIATION_SOURCES:
            raise CashCloseValidationError("Unsupported reconciliation source type.")
        if source_type != FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT:
            raise CashCloseValidationError("Only cash cut reconciliation is currently supported.")

        reason_code = _normalize_reason(command.reason_code)
        notes = _normalize_text(command.notes)
        if reason_code == FINANCIAL_RECONCILIATION_REASON_OTHER and not notes:
            raise CashCloseValidationError("Notes are required for OTHER reason.")

        final_status = _normalize_required(command.final_status)
        if final_status not in {
            FINANCIAL_RECONCILIATION_STATUS_PENDING,
            FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
            FINANCIAL_RECONCILIATION_STATUS_RECONCILED,
        }:
            raise CashCloseValidationError("Unsupported reconciliation final status.")

        source = self._get_cash_cut_source(session, close_id=command.source_document_id)
        self._ensure_no_existing_reconciliation(
            session,
            source_type=source_type,
            source_document_id=command.source_document_id,
            payment_method=source["payment_method"],
        )

        now = datetime.now(tz=UTC)
        reconciliation_id = uuid.uuid4()
        evidence_note = _normalize_text(command.evidence_note)
        record = FinancialReconciliation(
            id=reconciliation_id,
            folio=_build_reconciliation_folio(reconciliation_id),
            source_type=source_type,
            source_document_id=command.source_document_id,
            source_reference=type_cast(str, source["source_reference"]),
            source_occurred_at=type_cast(datetime, source["source_occurred_at"]),
            branch_id=type_cast(uuid.UUID, source["branch_id"]),
            workstation_id=type_cast(uuid.UUID, source["workstation_id"]),
            operator_user_id=type_cast(uuid.UUID, source["operator_user_id"]),
            payment_method_code=type_cast(str, source["payment_method"]),
            expected_amount=type_cast(Decimal, source["expected_amount"]),
            actual_amount=type_cast(Decimal, source["actual_amount"]),
            difference_amount=type_cast(Decimal, source["difference_amount"]),
            status=final_status,
            reason_code=reason_code,
            notes=notes,
            evidence_note=evidence_note,
            has_evidence=bool(evidence_note),
            created_by_user_id=current_user.id,
            resolved_by_user_id=(
                current_user.id
                if final_status == FINANCIAL_RECONCILIATION_STATUS_RECONCILED
                else None
            ),
            resolved_at=(
                now if final_status == FINANCIAL_RECONCILIATION_STATUS_RECONCILED else None
            ),
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        metadata = _record_metadata(record)
        try:
            session.flush()
            self._record_audit_and_outbox(
                session,
                action=AUDIT_ACTION_FINANCIAL_RECONCILIATION_CREATED,
                event_name=OUTBOX_EVENT_FINANCIAL_RECONCILIATION_CREATED_V1,
                current_user=current_user,
                metadata=metadata,
                record=record,
                request_id=request_id,
            )
            if final_status == FINANCIAL_RECONCILIATION_STATUS_RECONCILED:
                self._record_audit_and_outbox(
                    session,
                    action=AUDIT_ACTION_FINANCIAL_RECONCILIATION_RESOLVED,
                    event_name=OUTBOX_EVENT_FINANCIAL_RECONCILIATION_RESOLVED_V1,
                    current_user=current_user,
                    metadata=metadata,
                    record=record,
                    request_id=request_id,
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise CashCloseValidationError(
                "A reconciliation already exists for this source document."
            ) from error

        return self.get_reconciliation_detail(session, reconciliation_id=record.id)

    def resolve_reconciliation(
        self,
        session: Session,
        *,
        command: AdminReconciliationResolveRequest,
        current_user: AuthenticatedUser,
        reconciliation_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminReconciliationDetailView:
        record = session.get(FinancialReconciliation, reconciliation_id)
        if record is None:
            raise CashCloseNotFoundError("Reconciliation record was not found.")
        if record.status == FINANCIAL_RECONCILIATION_STATUS_RECONCILED:
            raise CashCloseValidationError("This reconciliation is already resolved.")
        if record.status == FINANCIAL_RECONCILIATION_STATUS_VOIDED:
            raise CashCloseValidationError("Voided reconciliations cannot be resolved.")

        reason_code = _normalize_reason(command.reason_code)
        notes = _normalize_text(command.notes)
        if reason_code == FINANCIAL_RECONCILIATION_REASON_OTHER and not notes:
            raise CashCloseValidationError("Notes are required for OTHER reason.")

        evidence_note = _normalize_text(command.evidence_note)
        now = datetime.now(tz=UTC)
        record.status = FINANCIAL_RECONCILIATION_STATUS_RECONCILED
        record.reason_code = reason_code
        record.notes = notes
        record.evidence_note = evidence_note
        record.has_evidence = bool(evidence_note)
        record.resolved_by_user_id = current_user.id
        record.resolved_at = now
        record.updated_at = now
        metadata = _record_metadata(record)

        self._record_audit_and_outbox(
            session,
            action=AUDIT_ACTION_FINANCIAL_RECONCILIATION_RESOLVED,
            event_name=OUTBOX_EVENT_FINANCIAL_RECONCILIATION_RESOLVED_V1,
            current_user=current_user,
            metadata=metadata,
            record=record,
            request_id=request_id,
        )
        session.commit()
        return self.get_reconciliation_detail(session, reconciliation_id=record.id)

    def _base_record_statement(self, conditions: list[object]):
        operator_alias = aliased(User)
        created_alias = aliased(User)
        resolved_alias = aliased(User)
        statement = (
            select(
                FinancialReconciliation.id,
                FinancialReconciliation.folio,
                FinancialReconciliation.source_type,
                FinancialReconciliation.source_document_id,
                FinancialReconciliation.source_reference,
                FinancialReconciliation.source_occurred_at,
                FinancialReconciliation.branch_id,
                Branch.name.label("branch_name"),
                FinancialReconciliation.workstation_id,
                Workstation.name.label("workstation_name"),
                Workstation.code.label("workstation_code"),
                FinancialReconciliation.operator_user_id,
                operator_alias.full_name.label("operator_name"),
                FinancialReconciliation.payment_method_code,
                FinancialReconciliation.expected_amount,
                FinancialReconciliation.actual_amount,
                FinancialReconciliation.difference_amount,
                FinancialReconciliation.status,
                FinancialReconciliation.reason_code,
                FinancialReconciliation.notes,
                FinancialReconciliation.evidence_note,
                FinancialReconciliation.has_evidence,
                FinancialReconciliation.created_by_user_id,
                created_alias.full_name.label("created_by_name"),
                FinancialReconciliation.resolved_by_user_id,
                resolved_alias.full_name.label("resolved_by_name"),
                FinancialReconciliation.resolved_at,
                FinancialReconciliation.created_at,
                FinancialReconciliation.updated_at,
            )
            .select_from(FinancialReconciliation)
            .join(Branch, Branch.id == FinancialReconciliation.branch_id)
            .join(Workstation, Workstation.id == FinancialReconciliation.workstation_id)
            .outerjoin(
                operator_alias, operator_alias.id == FinancialReconciliation.operator_user_id
            )
            .join(created_alias, created_alias.id == FinancialReconciliation.created_by_user_id)
            .outerjoin(
                resolved_alias,
                resolved_alias.id == FinancialReconciliation.resolved_by_user_id,
            )
        )
        if conditions:
            statement = statement.where(and_(*conditions))
        return statement

    def _build_record_conditions(
        self,
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        discrepancy_type: str | None,
        evidence_state: str | None,
        payment_method: str | None,
        search: str | None,
        source_type: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> list[object]:
        conditions: list[object] = []
        if branch_id is not None:
            conditions.append(FinancialReconciliation.branch_id == branch_id)
        if workstation_id is not None:
            conditions.append(FinancialReconciliation.workstation_id == workstation_id)
        if cashier_id is not None:
            conditions.append(FinancialReconciliation.operator_user_id == cashier_id)
        if date_from is not None:
            conditions.append(FinancialReconciliation.source_occurred_at >= _ensure_utc(date_from))
        if date_to is not None:
            conditions.append(FinancialReconciliation.source_occurred_at <= _ensure_utc(date_to))
        if amount_min is not None:
            conditions.append(func.abs(FinancialReconciliation.difference_amount) >= amount_min)
        if amount_max is not None:
            conditions.append(func.abs(FinancialReconciliation.difference_amount) <= amount_max)

        normalized_status = _normalize_optional(status_filter)
        if normalized_status:
            if normalized_status not in VALID_FINANCIAL_RECONCILIATION_STATUSES:
                raise CashCloseValidationError("Unsupported reconciliation status filter.")
            conditions.append(FinancialReconciliation.status == normalized_status)

        normalized_source = _normalize_optional(source_type)
        if normalized_source:
            if normalized_source not in VALID_FINANCIAL_RECONCILIATION_SOURCES:
                raise CashCloseValidationError("Unsupported reconciliation source filter.")
            conditions.append(FinancialReconciliation.source_type == normalized_source)

        normalized_method = _normalize_optional(payment_method)
        if normalized_method:
            conditions.append(FinancialReconciliation.payment_method_code == normalized_method)

        normalized_discrepancy = _normalize_optional(discrepancy_type)
        if normalized_discrepancy:
            conditions.extend(
                _difference_conditions(
                    FinancialReconciliation.difference_amount, normalized_discrepancy
                )
            )

        normalized_evidence = _normalize_optional(evidence_state)
        if normalized_evidence:
            if normalized_evidence == EVIDENCE_STATE_WITH:
                conditions.append(FinancialReconciliation.has_evidence.is_(True))
            elif normalized_evidence == EVIDENCE_STATE_WITHOUT:
                conditions.append(FinancialReconciliation.has_evidence.is_(False))
            else:
                raise CashCloseValidationError("Unsupported evidence state filter.")

        normalized_search = _normalize_search(search)
        if normalized_search:
            id_search = normalized_search.removeprefix("con-").removeprefix("cc-")
            conditions.append(
                or_(
                    func.lower(FinancialReconciliation.folio).contains(normalized_search),
                    func.lower(FinancialReconciliation.source_reference).contains(
                        normalized_search
                    ),
                    func.lower(FinancialReconciliation.source_type).contains(normalized_search),
                    func.lower(FinancialReconciliation.payment_method_code).contains(
                        normalized_search
                    ),
                    func.lower(FinancialReconciliation.reason_code).contains(normalized_search),
                    func.lower(FinancialReconciliation.notes).contains(normalized_search),
                    func.lower(Branch.name).contains(normalized_search),
                    func.lower(Workstation.name).contains(normalized_search),
                    func.lower(Workstation.code).contains(normalized_search),
                    func.lower(cast(FinancialReconciliation.id, String)).contains(id_search),
                    func.lower(cast(FinancialReconciliation.source_document_id, String)).contains(
                        id_search
                    ),
                )
            )
        return conditions

    def _list_pending_discrepancies(
        self,
        session: Session,
        *,
        amount_max: Decimal | None,
        amount_min: Decimal | None,
        branch_id: uuid.UUID | None,
        cashier_id: uuid.UUID | None,
        date_from: datetime | None,
        date_to: datetime | None,
        discrepancy_type: str | None,
        limit: int,
        payment_method: str | None,
        search: str | None,
        source_type: str | None,
        status_filter: str | None,
        workstation_id: uuid.UUID | None,
    ) -> list[AdminPendingDiscrepancyItemView]:
        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != FINANCIAL_RECONCILIATION_STATUS_PENDING:
            return []
        normalized_source = _normalize_optional(source_type)
        if normalized_source and normalized_source != FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT:
            return []
        normalized_method = _normalize_optional(payment_method)
        if normalized_method and normalized_method != CASH_CLOSE_PAYMENT_METHOD_CASH:
            return []

        conditions: list[object] = [
            CashSessionClose.status == CASH_CLOSE_STATUS_COMMITTED,
            CashSessionClose.cash_variance_amount.is_not(None),
            CashSessionClose.cash_variance_amount != ZERO_MONEY,
            ~exists(
                select(FinancialReconciliation.id).where(
                    FinancialReconciliation.source_type == FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT,
                    FinancialReconciliation.source_document_id == CashSessionClose.id,
                    FinancialReconciliation.payment_method_code == CASH_CLOSE_PAYMENT_METHOD_CASH,
                    FinancialReconciliation.status != FINANCIAL_RECONCILIATION_STATUS_VOIDED,
                )
            ),
        ]
        if branch_id is not None:
            conditions.append(CashSessionClose.branch_id == branch_id)
        if workstation_id is not None:
            conditions.append(CashSessionClose.workstation_id == workstation_id)
        if cashier_id is not None:
            conditions.append(CashSession.user_id == cashier_id)
        if date_from is not None:
            conditions.append(CashSessionClose.committed_at_utc >= _ensure_utc(date_from))
        if date_to is not None:
            conditions.append(CashSessionClose.committed_at_utc <= _ensure_utc(date_to))
        if amount_min is not None:
            conditions.append(func.abs(CashSessionClose.cash_variance_amount) >= amount_min)
        if amount_max is not None:
            conditions.append(func.abs(CashSessionClose.cash_variance_amount) <= amount_max)
        normalized_discrepancy = _normalize_optional(discrepancy_type)
        if normalized_discrepancy:
            conditions.extend(
                _difference_conditions(
                    CashSessionClose.cash_variance_amount,
                    normalized_discrepancy,
                )
            )
        normalized_search = _normalize_search(search)
        if normalized_search:
            id_search = normalized_search.removeprefix("cc-").removeprefix("con-")
            conditions.append(
                or_(
                    func.lower(Branch.name).contains(normalized_search),
                    func.lower(Branch.code).contains(normalized_search),
                    func.lower(Workstation.name).contains(normalized_search),
                    func.lower(Workstation.code).contains(normalized_search),
                    func.lower(User.full_name).contains(normalized_search),
                    func.lower(cast(CashSessionClose.id, String)).contains(id_search),
                    func.lower(cast(CashSession.id, String)).contains(id_search),
                )
            )

        rows = (
            session.execute(
                select(
                    CashSessionClose.id.label("source_document_id"),
                    CashSessionClose.expected_cash_amount.label("expected_amount"),
                    CashSessionClose.counted_cash_amount.label("actual_amount"),
                    CashSessionClose.cash_variance_amount.label("difference_amount"),
                    CashSessionClose.committed_at_utc.label("occurred_at"),
                    CashSessionClose.branch_id,
                    Branch.name.label("branch_name"),
                    CashSessionClose.workstation_id,
                    Workstation.name.label("workstation_name"),
                    CashSession.user_id.label("operator_id"),
                    User.full_name.label("operator_name"),
                )
                .select_from(CashSessionClose)
                .join(CashSession, CashSession.id == CashSessionClose.cash_session_id)
                .join(Branch, Branch.id == CashSessionClose.branch_id)
                .join(Workstation, Workstation.id == CashSessionClose.workstation_id)
                .join(User, User.id == CashSession.user_id)
                .where(and_(*conditions))
                .order_by(CashSessionClose.committed_at_utc.desc(), CashSessionClose.id.desc())
                .limit(limit)
            )
            .mappings()
            .all()
        )
        return [_map_pending_row(row) for row in rows]

    def _build_filter_options(self, session: Session) -> AdminReconciliationFilterOptionsView:
        branches = (
            session.execute(select(Branch.id, Branch.name).order_by(Branch.name.asc()))
            .mappings()
            .all()
        )
        workstations = (
            session.execute(
                select(Workstation.id, Workstation.name, Workstation.code).order_by(
                    Workstation.name.asc()
                )
            )
            .mappings()
            .all()
        )
        cashiers = (
            session.execute(
                select(User.id, User.full_name)
                .where(exists(select(CashSession.id).where(CashSession.user_id == User.id)))
                .order_by(User.full_name.asc())
            )
            .mappings()
            .all()
        )
        return AdminReconciliationFilterOptionsView(
            branches=[
                AdminReconciliationFilterOptionView(
                    id=str(row["id"]),
                    label=type_cast(str, row["name"]),
                )
                for row in branches
            ],
            cashiers=[
                AdminReconciliationFilterOptionView(
                    id=str(row["id"]),
                    label=type_cast(str, row["full_name"]),
                )
                for row in cashiers
            ],
            discrepancy_types=[
                AdminReconciliationFilterOptionView(
                    id=DISCREPANCY_DIRECTION_SHORTAGE, label="Faltantes"
                ),
                AdminReconciliationFilterOptionView(
                    id=DISCREPANCY_DIRECTION_OVERAGE, label="Sobrantes"
                ),
            ],
            evidence_states=[
                AdminReconciliationFilterOptionView(id=EVIDENCE_STATE_WITH, label="Con evidencia"),
                AdminReconciliationFilterOptionView(
                    id=EVIDENCE_STATE_WITHOUT, label="Sin evidencia"
                ),
            ],
            payment_methods=[
                AdminReconciliationFilterOptionView(id=SALE_PAYMENT_METHOD_CASH, label="Efectivo"),
                AdminReconciliationFilterOptionView(id=SALE_PAYMENT_METHOD_CARD, label="Tarjeta"),
                AdminReconciliationFilterOptionView(id=SALE_PAYMENT_METHOD_MIXED, label="Mixto"),
            ],
            reason_codes=[
                AdminReconciliationFilterOptionView(id=code, label=_reason_label(code))
                for code in sorted(VALID_FINANCIAL_RECONCILIATION_REASONS)
            ],
            source_types=[
                AdminReconciliationFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT, label="Corte de caja"
                ),
                AdminReconciliationFilterOptionView(id="PAYMENT_SETTLEMENT", label="Pago terminal"),
                AdminReconciliationFilterOptionView(id="DEPOSIT", label="Deposito"),
                AdminReconciliationFilterOptionView(id="RETURN_REFUND", label="Devolucion"),
                AdminReconciliationFilterOptionView(
                    id="OPERATIONAL_PAYMENT", label="Pago operativo"
                ),
                AdminReconciliationFilterOptionView(id="CORRECTION", label="Correccion"),
            ],
            statuses=[
                AdminReconciliationFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_STATUS_PENDING, label="Pendiente"
                ),
                AdminReconciliationFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW, label="En revision"
                ),
                AdminReconciliationFilterOptionView(
                    id=FINANCIAL_RECONCILIATION_STATUS_RECONCILED, label="Conciliada"
                ),
            ],
            workstations=[
                AdminReconciliationFilterOptionView(
                    id=str(row["id"]),
                    label=f"{row['name']} ({row['code']})",
                )
                for row in workstations
            ],
        )

    def _build_metrics(
        self,
        session: Session,
        *,
        pending_items: list[AdminPendingDiscrepancyItemView],
        record_conditions: list[object],
    ) -> AdminReconciliationMetricsView:
        record_statement = select(
            func.count()
            .filter(
                FinancialReconciliation.status.in_(
                    [
                        FINANCIAL_RECONCILIATION_STATUS_PENDING,
                        FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
                    ]
                )
            )
            .label("pending_count"),
            func.count()
            .filter(FinancialReconciliation.status == FINANCIAL_RECONCILIATION_STATUS_RECONCILED)
            .label("reconciled_count"),
            func.coalesce(func.sum(FinancialReconciliation.difference_amount), ZERO_MONEY).label(
                "net_difference_amount"
            ),
            func.coalesce(
                func.sum(FinancialReconciliation.difference_amount).filter(
                    FinancialReconciliation.difference_amount < ZERO_MONEY
                ),
                ZERO_MONEY,
            ).label("shortage_amount"),
            func.coalesce(
                func.sum(FinancialReconciliation.difference_amount).filter(
                    FinancialReconciliation.difference_amount > ZERO_MONEY
                ),
                ZERO_MONEY,
            ).label("overage_amount"),
            func.count()
            .filter(
                FinancialReconciliation.status != FINANCIAL_RECONCILIATION_STATUS_RECONCILED,
                FinancialReconciliation.payment_method_code == SALE_PAYMENT_METHOD_CARD,
            )
            .label("card_terminal_pending_count"),
            func.count()
            .filter(FinancialReconciliation.has_evidence.is_(True))
            .label("with_evidence_count"),
        ).select_from(FinancialReconciliation)
        if record_conditions:
            record_statement = record_statement.where(and_(*record_conditions))
        row = session.execute(record_statement).mappings().one()

        pending_count = int(type_cast(int, row["pending_count"])) + len(pending_items)
        pending_cash_count = len(
            [
                item
                for item in pending_items
                if item.payment_method == CASH_CLOSE_PAYMENT_METHOD_CASH
            ]
        )
        pending_net = sum((item.difference_amount for item in pending_items), ZERO_MONEY)
        pending_short = sum(
            (
                item.difference_amount
                for item in pending_items
                if item.difference_amount < ZERO_MONEY
            ),
            ZERO_MONEY,
        )
        pending_over = sum(
            (
                item.difference_amount
                for item in pending_items
                if item.difference_amount > ZERO_MONEY
            ),
            ZERO_MONEY,
        )
        return AdminReconciliationMetricsView(
            card_terminal_pending_count=int(type_cast(int, row["card_terminal_pending_count"])),
            cash_pending_count=pending_cash_count,
            net_difference_amount=_money(
                type_cast(Decimal, row["net_difference_amount"]) + pending_net
            ),
            overage_amount=_money(type_cast(Decimal, row["overage_amount"]) + pending_over),
            pending_count=pending_count,
            reconciled_count=int(type_cast(int, row["reconciled_count"])),
            shortage_amount=_money(abs(type_cast(Decimal, row["shortage_amount"]) + pending_short)),
            with_evidence_count=int(type_cast(int, row["with_evidence_count"])),
        )

    def _get_cash_cut_source(self, session: Session, *, close_id: uuid.UUID) -> RowMapping:
        row = (
            session.execute(
                select(
                    CashSessionClose.id.label("source_document_id"),
                    CashSessionClose.cash_session_id,
                    CashSessionClose.branch_id,
                    CashSessionClose.workstation_id,
                    CashSession.user_id.label("operator_user_id"),
                    CashSessionClose.expected_cash_amount.label("expected_amount"),
                    CashSessionClose.counted_cash_amount.label("actual_amount"),
                    CashSessionClose.cash_variance_amount.label("difference_amount"),
                    CashSessionClose.committed_at_utc.label("source_occurred_at"),
                )
                .select_from(CashSessionClose)
                .join(CashSession, CashSession.id == CashSessionClose.cash_session_id)
                .where(CashSessionClose.id == close_id)
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CashCloseNotFoundError("Cash cut source was not found.")
        if row["actual_amount"] is None or row["difference_amount"] is None:
            raise CashCloseValidationError("Cash cut does not have a counted amount.")
        if _money(type_cast(Decimal, row["difference_amount"])) == ZERO_MONEY:
            raise CashCloseValidationError("Cash cut does not have a financial difference.")
        return {
            **row,
            "payment_method": CASH_CLOSE_PAYMENT_METHOD_CASH,
            "source_reference": _build_cash_cut_folio(close_id),
        }

    def _ensure_no_existing_reconciliation(
        self,
        session: Session,
        *,
        payment_method: str,
        source_document_id: uuid.UUID,
        source_type: str,
    ) -> None:
        existing_id = session.execute(
            select(FinancialReconciliation.id).where(
                FinancialReconciliation.source_type == source_type,
                FinancialReconciliation.source_document_id == source_document_id,
                FinancialReconciliation.payment_method_code == payment_method,
                FinancialReconciliation.status != FINANCIAL_RECONCILIATION_STATUS_VOIDED,
            )
        ).scalar_one_or_none()
        if existing_id is not None:
            raise CashCloseValidationError("This source document already has a reconciliation.")

    def _record_audit_and_outbox(
        self,
        session: Session,
        *,
        action: str,
        current_user: AuthenticatedUser,
        event_name: str,
        metadata: dict[str, object],
        record: FinancialReconciliation,
        request_id: str | None,
    ) -> None:
        self._audit_recorder.record(
            session,
            action=action,
            actor_id=current_user.id,
            branch_id=record.branch_id,
            metadata=metadata,
            request_id=request_id,
            resource_id=str(record.id),
            resource_type=ADMIN_RECONCILIATION_RESOURCE_TYPE,
        )
        self._outbox_writer.append(
            session,
            aggregate_id=str(record.id),
            aggregate_type=ADMIN_RECONCILIATION_RESOURCE_TYPE,
            event_name=event_name,
            headers={"request_id": request_id} if request_id else {},
            payload=metadata,
        )

    def _to_detail(self, session: Session, *, row: RowMapping) -> AdminReconciliationDetailView:
        difference_amount = _money(type_cast(Decimal, row["difference_amount"]))
        direction = _difference_direction(difference_amount)
        source_context = self._build_source_context(session, row=row)
        related_documents = self._build_related_documents(session, row=row)
        can_resolve = row["status"] in {
            FINANCIAL_RECONCILIATION_STATUS_PENDING,
            FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
        }
        return AdminReconciliationDetailView(
            available_actions=AdminReconciliationAvailableActionsView(
                can_attach_evidence=False,
                can_export_report=False,
                can_open_source=True,
                can_resolve=can_resolve,
                can_save_notes=can_resolve,
                can_void=False,
                note=(
                    "La evidencia se registra como nota; los adjuntos de archivo "
                    "aun no tienen contrato."
                ),
            ),
            backend_contract=_backend_contract(),
            difference_breakdown=AdminReconciliationDifferenceBreakdownView(
                actual_amount=_money(type_cast(Decimal, row["actual_amount"])),
                difference_amount=difference_amount,
                direction=direction,
                expected_amount=_money(type_cast(Decimal, row["expected_amount"])),
                payment_method=type_cast(str, row["payment_method_code"]),
                tolerance_note="No hay tolerancia financiera configurable para este modulo.",
                tolerance_status="NOT_CONFIGURED",
            ),
            evidence=AdminReconciliationEvidenceView(
                empty_state="Esta conciliacion no tiene evidencia adjunta.",
                evidence_note=type_cast(str | None, row["evidence_note"]),
                files=[],
                has_evidence=bool(row["has_evidence"]),
                is_supported=True,
            ),
            explanation_reason=AdminReconciliationExplanationView(
                notes=type_cast(str | None, row["notes"]),
                reason_code=type_cast(str | None, row["reason_code"]),
                reason_label=_reason_label(type_cast(str | None, row["reason_code"])),
                responsible_user_id=type_cast(uuid.UUID | None, row["resolved_by_user_id"])
                or type_cast(uuid.UUID | None, row["created_by_user_id"]),
                responsible_user_name=type_cast(str | None, row["resolved_by_name"])
                or type_cast(str | None, row["created_by_name"]),
                timestamp=type_cast(datetime | None, row["resolved_at"])
                or type_cast(datetime, row["created_at"]),
            ),
            overview=AdminReconciliationOverviewView(
                actual_amount=_money(type_cast(Decimal, row["actual_amount"])),
                branch_id=type_cast(uuid.UUID, row["branch_id"]),
                branch_name=type_cast(str, row["branch_name"]),
                created_at=type_cast(datetime, row["created_at"]),
                difference_amount=difference_amount,
                difference_direction=direction,
                expected_amount=_money(type_cast(Decimal, row["expected_amount"])),
                folio=type_cast(str, row["folio"]),
                id=type_cast(uuid.UUID, row["id"]),
                operator_id=type_cast(uuid.UUID | None, row["operator_user_id"]),
                operator_name=_coalesce_name(row["operator_name"]),
                payment_method=type_cast(str, row["payment_method_code"]),
                resolved_at=type_cast(datetime | None, row["resolved_at"]),
                source_document_id=type_cast(uuid.UUID, row["source_document_id"]),
                source_reference=type_cast(str, row["source_reference"]),
                source_type=type_cast(str, row["source_type"]),
                status=type_cast(str, row["status"]),
                updated_at=type_cast(datetime, row["updated_at"]),
                warning_state=_warning_state(
                    difference_amount=difference_amount,
                    status=type_cast(str, row["status"]),
                    has_evidence=bool(row["has_evidence"]),
                ),
                workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
                workstation_name=type_cast(str, row["workstation_name"]),
            ),
            related_documents=related_documents,
            resolution=AdminReconciliationResolutionView(
                can_resolve=can_resolve,
                evidence_summary=type_cast(str | None, row["evidence_note"]),
                final_notes=type_cast(str | None, row["notes"]),
                required_fields=["reason_code", "notes when reason is OTHER"],
                resolution_reason=_reason_label(type_cast(str | None, row["reason_code"])),
                resolved_at=type_cast(datetime | None, row["resolved_at"]),
                resolved_by_user_id=type_cast(uuid.UUID | None, row["resolved_by_user_id"]),
                resolved_by_user_name=type_cast(str | None, row["resolved_by_name"]),
                status=type_cast(str, row["status"]),
            ),
            source_document_context=source_context,
        )

    def _build_source_context(
        self,
        session: Session,
        *,
        row: RowMapping,
    ) -> AdminReconciliationSourceContextView:
        source_type = type_cast(str, row["source_type"])
        if source_type != FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT:
            return AdminReconciliationSourceContextView(
                note="El detalle de este tipo de origen aun no tiene contrato de lectura.",
                payment_method=type_cast(str, row["payment_method_code"]),
                source_reference=type_cast(str, row["source_reference"]),
                source_route_hint=None,
                source_type=source_type,
            )

        close_row = (
            session.execute(
                select(
                    CashSession.opened_at,
                    CashSessionClose.committed_at_utc,
                    CashSessionClose.expected_cash_amount,
                    CashSessionClose.counted_cash_amount,
                    CashSessionClose.cash_variance_amount,
                )
                .select_from(CashSessionClose)
                .join(CashSession, CashSession.id == CashSessionClose.cash_session_id)
                .where(CashSessionClose.id == row["source_document_id"])
            )
            .mappings()
            .one_or_none()
        )
        return AdminReconciliationSourceContextView(
            closed_at=type_cast(datetime | None, close_row["committed_at_utc"])
            if close_row
            else None,
            counted_cash_amount=_money(type_cast(Decimal, close_row["counted_cash_amount"]))
            if close_row and close_row["counted_cash_amount"] is not None
            else None,
            difference_amount=_money(type_cast(Decimal, close_row["cash_variance_amount"]))
            if close_row and close_row["cash_variance_amount"] is not None
            else None,
            expected_cash_amount=_money(type_cast(Decimal, close_row["expected_cash_amount"]))
            if close_row
            else None,
            note="El corte se mantiene inmutable; esta conciliacion documenta la resolucion.",
            opened_at=type_cast(datetime | None, close_row["opened_at"]) if close_row else None,
            payment_method=type_cast(str, row["payment_method_code"]),
            source_reference=type_cast(str, row["source_reference"]),
            source_route_hint=f"/admin/cortes-caja?cashSession={row['source_document_id']}",
            source_type=source_type,
        )

    def _build_related_documents(
        self,
        session: Session,
        *,
        row: RowMapping,
    ) -> list[AdminReconciliationRelatedDocumentView]:
        documents = [
            AdminReconciliationRelatedDocumentView(
                amount=_money(type_cast(Decimal, row["actual_amount"])),
                document_type=type_cast(str, row["source_type"]),
                folio=type_cast(str, row["source_reference"]),
                id=str(row["source_document_id"]),
                occurred_at=type_cast(datetime, row["source_occurred_at"]),
                route_hint=f"/admin/cortes-caja?cashSession={row['source_document_id']}",
                status="SOURCE",
            )
        ]
        if row["source_type"] != FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT:
            return documents

        close_cash_session_id = session.execute(
            select(CashSessionClose.cash_session_id).where(
                CashSessionClose.id == row["source_document_id"]
            )
        ).scalar_one_or_none()
        if close_cash_session_id is None:
            return documents

        ticket_rows = (
            session.execute(
                select(Sale.id, Sale.total_amount, Sale.confirmed_at, Sale.status)
                .where(Sale.cash_session_id == close_cash_session_id)
                .order_by(Sale.confirmed_at.desc())
                .limit(5)
            )
            .mappings()
            .all()
        )
        documents.extend(
            AdminReconciliationRelatedDocumentView(
                amount=_money(type_cast(Decimal, ticket["total_amount"])),
                document_type="TICKET",
                folio=build_ticket_folio(type_cast(uuid.UUID, ticket["id"])),
                id=str(ticket["id"]),
                occurred_at=type_cast(datetime, ticket["confirmed_at"]),
                route_hint=f"/admin/ventas-tickets?ticket={ticket['id']}",
                status=type_cast(str, ticket["status"]),
            )
            for ticket in ticket_rows
        )

        return_rows = (
            session.execute(
                select(
                    SaleReturn.id,
                    SaleReturn.total_refund_amount,
                    SaleReturn.created_at_utc,
                    SaleReturn.status,
                )
                .where(SaleReturn.cash_session_id == close_cash_session_id)
                .order_by(SaleReturn.created_at_utc.desc())
                .limit(5)
            )
            .mappings()
            .all()
        )
        documents.extend(
            AdminReconciliationRelatedDocumentView(
                amount=_money(type_cast(Decimal, return_row["total_refund_amount"])),
                document_type="RETURN_REFUND",
                folio=_build_return_folio(type_cast(uuid.UUID, return_row["id"])),
                id=str(return_row["id"]),
                occurred_at=type_cast(datetime, return_row["created_at_utc"]),
                route_hint=f"/admin/devoluciones-correcciones?return={return_row['id']}",
                status=type_cast(str, return_row["status"]),
            )
            for return_row in return_rows
        )

        payment_rows = (
            session.execute(
                select(
                    OperationalPayment.id,
                    OperationalPayment.total_amount,
                    OperationalPayment.committed_at_utc,
                    OperationalPayment.status,
                    OperationalPaymentCategory.name.label("category_name"),
                )
                .select_from(OperationalPayment)
                .outerjoin(
                    OperationalPaymentCategory,
                    OperationalPaymentCategory.code == OperationalPayment.category_code,
                )
                .where(OperationalPayment.active_cash_session_id == close_cash_session_id)
                .order_by(OperationalPayment.committed_at_utc.desc())
                .limit(5)
            )
            .mappings()
            .all()
        )
        documents.extend(
            AdminReconciliationRelatedDocumentView(
                amount=_money(type_cast(Decimal, payment["total_amount"])),
                document_type="OPERATIONAL_PAYMENT",
                folio=_build_operational_payment_folio(type_cast(uuid.UUID, payment["id"])),
                id=str(payment["id"]),
                occurred_at=type_cast(datetime, payment["committed_at_utc"]),
                route_hint=f"/admin/pagos-operativos?payment={payment['id']}",
                status=type_cast(str, payment["status"]),
            )
            for payment in payment_rows
        )
        return documents


def _backend_contract() -> AdminReconciliationBackendContractView:
    return AdminReconciliationBackendContractView(
        create_endpoint="POST /v1/admin/reconciliation",
        detail_endpoint="GET /v1/admin/reconciliation/{reconciliation_id}",
        evidence_endpoint=None,
        export_endpoint=None,
        list_endpoint="GET /v1/admin/reconciliation",
        pending_endpoint="GET /v1/admin/reconciliation/pending",
        resolve_endpoint="POST /v1/admin/reconciliation/{reconciliation_id}/resolve",
    )


def _map_record_list_item(row: RowMapping) -> AdminReconciliationListItemView:
    difference_amount = _money(type_cast(Decimal, row["difference_amount"]))
    return AdminReconciliationListItemView(
        actual_amount=_money(type_cast(Decimal, row["actual_amount"])),
        branch_id=type_cast(uuid.UUID, row["branch_id"]),
        branch_name=type_cast(str, row["branch_name"]),
        difference_amount=difference_amount,
        difference_direction=_difference_direction(difference_amount),
        expected_amount=_money(type_cast(Decimal, row["expected_amount"])),
        folio=type_cast(str, row["folio"]),
        has_evidence=bool(row["has_evidence"]),
        id=type_cast(uuid.UUID, row["id"]),
        occurred_at=type_cast(datetime, row["source_occurred_at"]),
        operator_id=type_cast(uuid.UUID | None, row["operator_user_id"]),
        operator_name=_coalesce_name(row["operator_name"]),
        payment_method=type_cast(str, row["payment_method_code"]),
        reason_code=type_cast(str | None, row["reason_code"]),
        source_document_id=type_cast(uuid.UUID, row["source_document_id"]),
        source_reference=type_cast(str, row["source_reference"]),
        source_type=type_cast(str, row["source_type"]),
        status=type_cast(str, row["status"]),
        updated_at=type_cast(datetime, row["updated_at"]),
        warning_state=_warning_state(
            difference_amount=difference_amount,
            has_evidence=bool(row["has_evidence"]),
            status=type_cast(str, row["status"]),
        ),
        workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
        workstation_name=type_cast(str, row["workstation_name"]),
    )


def _map_pending_row(row: RowMapping) -> AdminPendingDiscrepancyItemView:
    difference_amount = _money(type_cast(Decimal, row["difference_amount"]))
    return AdminPendingDiscrepancyItemView(
        actual_amount=_money(type_cast(Decimal, row["actual_amount"])),
        branch_id=type_cast(uuid.UUID, row["branch_id"]),
        branch_name=type_cast(str, row["branch_name"]),
        difference_amount=difference_amount,
        difference_direction=_difference_direction(difference_amount),
        expected_amount=_money(type_cast(Decimal, row["expected_amount"])),
        occurred_at=type_cast(datetime, row["occurred_at"]),
        operator_id=type_cast(uuid.UUID | None, row["operator_id"]),
        operator_name=_coalesce_name(row["operator_name"]),
        payment_method=CASH_CLOSE_PAYMENT_METHOD_CASH,
        source_document_id=type_cast(uuid.UUID, row["source_document_id"]),
        source_reference=_build_cash_cut_folio(type_cast(uuid.UUID, row["source_document_id"])),
        source_type=FINANCIAL_RECONCILIATION_SOURCE_CASH_CUT,
        suggested_warning_state=_warning_state(
            difference_amount=difference_amount,
            has_evidence=False,
            status=FINANCIAL_RECONCILIATION_STATUS_PENDING,
        ),
        workstation_id=type_cast(uuid.UUID, row["workstation_id"]),
        workstation_name=type_cast(str, row["workstation_name"]),
    )


def _difference_conditions(difference_column, discrepancy_type: str) -> list[object]:
    if discrepancy_type == DISCREPANCY_DIRECTION_SHORTAGE:
        return [difference_column < ZERO_MONEY]
    if discrepancy_type == DISCREPANCY_DIRECTION_OVERAGE:
        return [difference_column > ZERO_MONEY]
    if discrepancy_type == DISCREPANCY_DIRECTION_EXACT:
        return [difference_column == ZERO_MONEY]
    raise CashCloseValidationError("Unsupported discrepancy type filter.")


def _record_metadata(record: FinancialReconciliation) -> dict[str, object]:
    return {
        "actual_amount": str(_money(record.actual_amount)),
        "branch_id": str(record.branch_id),
        "difference_amount": str(_money(record.difference_amount)),
        "expected_amount": str(_money(record.expected_amount)),
        "folio": record.folio,
        "has_evidence": record.has_evidence,
        "payment_method": record.payment_method_code,
        "reason_code": record.reason_code,
        "reconciliation_id": str(record.id),
        "source_document_id": str(record.source_document_id),
        "source_reference": record.source_reference,
        "source_type": record.source_type,
        "status": record.status,
    }


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.lower() == "all":
        return None
    return stripped.upper()


def _normalize_required(value: str) -> str:
    normalized = _normalize_optional(value)
    if not normalized:
        raise CashCloseValidationError("Required reconciliation value is missing.")
    return normalized


def _normalize_reason(value: str) -> str:
    reason = _normalize_required(value)
    if reason not in VALID_FINANCIAL_RECONCILIATION_REASONS:
        raise CashCloseValidationError("Unsupported reconciliation reason.")
    return reason


def _normalize_search(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    return stripped or None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTIZER)


def _difference_direction(value: Decimal) -> str:
    if value > ZERO_MONEY:
        return DISCREPANCY_DIRECTION_OVERAGE
    if value < ZERO_MONEY:
        return DISCREPANCY_DIRECTION_SHORTAGE
    return DISCREPANCY_DIRECTION_EXACT


def _warning_state(*, difference_amount: Decimal, has_evidence: bool, status: str) -> str:
    if (
        status
        in {
            FINANCIAL_RECONCILIATION_STATUS_PENDING,
            FINANCIAL_RECONCILIATION_STATUS_IN_REVIEW,
        }
        and abs(difference_amount) >= HIGH_IMPACT_DIFFERENCE_THRESHOLD
    ):
        return "critical"
    if status != FINANCIAL_RECONCILIATION_STATUS_RECONCILED:
        return "warning"
    if not has_evidence and abs(difference_amount) >= HIGH_IMPACT_DIFFERENCE_THRESHOLD:
        return "warning"
    return "ready"


def _build_reconciliation_folio(reconciliation_id: uuid.UUID) -> str:
    return f"CON-{str(reconciliation_id).split('-')[0].upper()}"


def _build_cash_cut_folio(close_id: uuid.UUID) -> str:
    return f"CC-{str(close_id).split('-')[0].upper()}"


def _build_return_folio(return_id: uuid.UUID) -> str:
    return f"DEV-{str(return_id).split('-')[0].upper()}"


def _build_operational_payment_folio(payment_id: uuid.UUID) -> str:
    return f"POP-{str(payment_id).split('-')[0].upper()}"


def _coalesce_name(value: object) -> str:
    if isinstance(value, str) and value.strip():
        return value
    return "Sin operador"


def _reason_label(code: str | None) -> str | None:
    if code is None:
        return None
    labels = {
        "CARD_SETTLEMENT_DIFFERENCE": "Diferencia en terminal",
        "CASH_MISSING": "Faltante de efectivo",
        "CASH_OVER": "Sobrante de efectivo",
        "CORRECTION_APPLIED": "Correccion aplicada",
        "COUNTING_ERROR": "Error de conteo",
        "DEPOSIT_DIFFERENCE": "Diferencia de deposito",
        "DUPLICATE_TICKET": "Ticket duplicado",
        "OPERATIONAL_PAYMENT_MISSING": "Pago operativo no registrado",
        "OTHER": "Otro",
        "REFUND_RECORDED": "Devolucion registrada",
    }
    return labels.get(code, code)
