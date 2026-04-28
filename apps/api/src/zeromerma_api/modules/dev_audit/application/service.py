from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from typing import cast as typing_cast
from uuid import UUID

from sqlalchemy import String, and_, cast, func, or_, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, aliased

from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.cash_close.infrastructure.models import (
    CashSessionClose,
    CashSessionCloseClassReconciliation,
    CashSessionClosePaymentMethodCount,
    CashSessionCloseProductCount,
)
from zeromerma_api.modules.corrections.infrastructure.models import (
    CorrectionDocument,
    CorrectionDocumentLine,
)
from zeromerma_api.modules.dev_audit.application.schemas import (
    DevAuditDatabaseOverview,
    DevAuditFiltersApplied,
    DevAuditSnapshotResponse,
    DevAuditTableSnapshot,
    ScopeStatus,
)
from zeromerma_api.modules.discounts.infrastructure.models import OperationalDiscount
from zeromerma_api.modules.operations.infrastructure.models import (
    OperationDocument,
    OperationDocumentLine,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.payments.infrastructure.models import OperationalPayment
from zeromerma_api.modules.returns.infrastructure.models import SaleReturn, SaleReturnLine
from zeromerma_api.modules.sales.infrastructure.models import (
    CashMovement,
    Sale,
    SaleLine,
    SalePayment,
)

SNAPSHOT_VERSION = "dev-audit-snapshot.v1"
MAX_RECENT_LIMIT = 20
TRACKED_TABLE_COUNT = 19


@dataclass(frozen=True)
class ResolvedScope:
    requested_branch_code: str | None
    requested_workstation_code: str | None
    branch_id: UUID | None = None
    branch_code: str | None = None
    workstation_id: UUID | None = None
    workstation_code: str | None = None
    scope_inferred_from_workstation: bool = False

    @property
    def has_filters(self) -> bool:
        return self.branch_id is not None or self.workstation_id is not None

    def to_filters_applied(
        self,
        *,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditFiltersApplied:
        return DevAuditFiltersApplied(
            requested_branch_code=self.requested_branch_code,
            requested_workstation_code=self.requested_workstation_code,
            resolved_branch_id=self.branch_id,
            resolved_branch_code=self.branch_code,
            resolved_workstation_id=self.workstation_id,
            resolved_workstation_code=self.workstation_code,
            scope_inferred_from_workstation=self.scope_inferred_from_workstation,
            include_recent_rows=include_recent_rows,
            recent_limit=recent_limit,
        )

    def to_scope_summary(self) -> str:
        if self.workstation_code is not None and self.branch_code is not None:
            return f"workstation {self.workstation_code} in branch {self.branch_code}"
        if self.branch_code is not None:
            return f"branch {self.branch_code}"
        return "global snapshot"


class DevAuditSnapshotService:
    def build_snapshot(
        self,
        session: Session,
        *,
        environment: str,
        dev_audit_feature_enabled: bool,
        branch_code: str | None,
        workstation_code: str | None,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditSnapshotResponse:
        resolved_recent_limit = min(max(recent_limit, 1), MAX_RECENT_LIMIT)
        scope = self._resolve_scope(
            session,
            branch_code=branch_code,
            workstation_code=workstation_code,
        )

        table_names = set(sa_inspect(session.get_bind()).get_table_names())
        tables = self._build_table_snapshots(
            session,
            table_names=table_names,
            scope=scope,
            include_recent_rows=include_recent_rows,
            recent_limit=resolved_recent_limit,
        )

        warnings = [
            f"{table.table_name} is unavailable in the current database."
            for table in tables
            if table.scope_status == "unavailable"
        ]

        return DevAuditSnapshotResponse(
            generated_at=datetime.now(tz=UTC),
            environment=environment,
            snapshot_version=SNAPSHOT_VERSION,
            database_overview=DevAuditDatabaseOverview(
                dev_audit_feature_enabled=dev_audit_feature_enabled,
                scope_summary=scope.to_scope_summary(),
                total_tracked_tables=TRACKED_TABLE_COUNT,
                available_tables=sum(1 for table in tables if table.scope_status != "unavailable"),
                warnings=warnings,
            ),
            filters_applied=scope.to_filters_applied(
                include_recent_rows=include_recent_rows,
                recent_limit=resolved_recent_limit,
            ),
            tables=tables,
        )

    def _build_table_snapshots(
        self,
        session: Session,
        *,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> list[DevAuditTableSnapshot]:
        return [
            self._build_audit_log_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_outbox_events_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_cash_sessions_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_sales_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_sale_lines_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_sale_payments_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_cash_movements_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_operation_documents_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_operation_document_lines_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_correction_documents_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_correction_document_lines_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_sale_returns_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_sale_return_lines_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_operational_payments_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_operational_discounts_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_cash_session_closes_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_cash_session_close_payment_method_counts_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_cash_session_close_product_counts_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
            self._build_cash_session_close_class_reconciliations_snapshot(
                session, table_names, scope, include_recent_rows, recent_limit
            ),
        ]

    def _resolve_scope(
        self,
        session: Session,
        *,
        branch_code: str | None,
        workstation_code: str | None,
    ) -> ResolvedScope:
        normalized_branch_code = _normalize_optional_string(branch_code)
        normalized_workstation_code = _normalize_optional_string(workstation_code)

        branch_record: Branch | None = None
        workstation_record: Workstation | None = None

        if normalized_branch_code is not None:
            branch_record = session.execute(
                select(Branch).where(Branch.code == normalized_branch_code)
            ).scalar_one_or_none()
            if branch_record is None:
                raise ValueError("Unknown branch_code for development audit snapshot.")

        if normalized_workstation_code is not None:
            workstation_record = session.execute(
                select(Workstation).where(Workstation.code == normalized_workstation_code)
            ).scalar_one_or_none()
            if workstation_record is None:
                raise ValueError("Unknown workstation_code for development audit snapshot.")

        if workstation_record is not None and branch_record is not None:
            if workstation_record.branch_id != branch_record.id:
                raise ValueError(
                    "The provided workstation_code does not belong to the provided branch_code."
                )

        scope_inferred_from_workstation = False
        if workstation_record is not None and branch_record is None:
            branch_record = session.execute(
                select(Branch).where(Branch.id == workstation_record.branch_id)
            ).scalar_one()
            scope_inferred_from_workstation = True

        return ResolvedScope(
            requested_branch_code=normalized_branch_code,
            requested_workstation_code=normalized_workstation_code,
            branch_id=branch_record.id if branch_record is not None else None,
            branch_code=branch_record.code if branch_record is not None else None,
            workstation_id=workstation_record.id if workstation_record is not None else None,
            workstation_code=workstation_record.code if workstation_record is not None else None,
            scope_inferred_from_workstation=scope_inferred_from_workstation,
        )

    def _build_audit_log_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "audit_log"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        total_count = self._count(session, select(func.count()).select_from(AuditLog))
        scope_condition, scope_status, scope_note = self._audit_log_scope(scope)
        scoped_count = (
            self._count(
                session,
                select(func.count()).select_from(AuditLog).where(scope_condition),
            )
            if scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(AuditLog.occurred_at)).select_from(AuditLog),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    AuditLog.id.label("id"),
                    AuditLog.action.label("action"),
                    AuditLog.resource_type.label("resource_type"),
                    AuditLog.resource_id.label("resource_id"),
                    AuditLog.request_id.label("request_id"),
                    AuditLog.occurred_at.label("occurred_at"),
                    branch_alias.code.label("branch_code"),
                )
                .select_from(AuditLog)
                .outerjoin(branch_alias, branch_alias.id == AuditLog.branch_id)
                .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="occurred_at",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_outbox_events_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "outbox_events"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        total_count = self._count(session, select(func.count()).select_from(OutboxEvent))
        scope_clause, scope_status, scope_note = self._outbox_scope_clause(scope)
        scoped_count = (
            self._count(
                session,
                select(func.count()).select_from(OutboxEvent).where(scope_clause),
            )
            if scope_clause is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(OutboxEvent.occurred_at)).select_from(OutboxEvent),
            scope_clause,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    OutboxEvent.id.label("id"),
                    OutboxEvent.event_name.label("event_name"),
                    OutboxEvent.aggregate_type.label("aggregate_type"),
                    OutboxEvent.aggregate_id.label("aggregate_id"),
                    OutboxEvent.status.label("status"),
                    OutboxEvent.occurred_at.label("occurred_at"),
                    OutboxEvent.processed_at.label("processed_at"),
                    OutboxEvent.attempts.label("attempts"),
                )
                .select_from(OutboxEvent)
                .order_by(OutboxEvent.occurred_at.desc(), OutboxEvent.id.desc())
                .limit(recent_limit)
            )
            if scope_clause is not None:
                recent_statement = recent_statement.where(scope_clause)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="occurred_at",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_cash_sessions_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "cash_sessions"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=CashSession.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=CashSession.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(CashSession))
        scoped_count = self._scoped_count(session, CashSession, scope_condition, total_count, scope)
        latest_value = self._latest_value(
            session,
            select(func.max(CashSession.opened_at)).select_from(CashSession),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CashSession.id.label("id"),
                    CashSession.status.label("status"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CashSession.opening_amount.label("opening_amount"),
                    CashSession.opened_at.label("opened_at"),
                    CashSession.closed_at.label("closed_at"),
                )
                .select_from(CashSession)
                .join(branch_alias, branch_alias.id == CashSession.branch_id)
                .join(workstation_alias, workstation_alias.id == CashSession.workstation_id)
                .order_by(CashSession.opened_at.desc(), CashSession.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="opened_at",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_sales_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "sales"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=Sale.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=Sale.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(Sale))
        scoped_count = self._scoped_count(session, Sale, scope_condition, total_count, scope)
        latest_value = self._latest_value(
            session,
            select(func.max(Sale.confirmed_at)).select_from(Sale),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    Sale.id.label("id"),
                    Sale.status.label("status"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    Sale.cash_session_id.label("cash_session_id"),
                    Sale.total_amount.label("total_amount"),
                    Sale.paid_amount.label("paid_amount"),
                    Sale.change_amount.label("change_amount"),
                    Sale.confirmed_at.label("confirmed_at"),
                )
                .select_from(Sale)
                .join(branch_alias, branch_alias.id == Sale.branch_id)
                .join(workstation_alias, workstation_alias.id == Sale.workstation_id)
                .order_by(Sale.confirmed_at.desc(), Sale.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="confirmed_at",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_sale_lines_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "sale_lines"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        sale_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=Sale.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=Sale.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(SaleLine))
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(SaleLine)
                .join(Sale, Sale.id == SaleLine.sale_id)
                .where(sale_scope_condition),
            )
            if sale_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(Sale.confirmed_at))
            .select_from(SaleLine)
            .join(Sale, Sale.id == SaleLine.sale_id),
            sale_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    SaleLine.id.label("id"),
                    SaleLine.sale_id.label("sale_id"),
                    SaleLine.sequence.label("sequence"),
                    SaleLine.capture_mode.label("capture_mode"),
                    SaleLine.catalog_code_snapshot.label("catalog_code"),
                    SaleLine.catalog_name_snapshot.label("catalog_name"),
                    SaleLine.quantity.label("quantity"),
                    SaleLine.line_total_amount.label("line_total_amount"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    Sale.confirmed_at.label("confirmed_at"),
                )
                .select_from(SaleLine)
                .join(Sale, Sale.id == SaleLine.sale_id)
                .join(branch_alias, branch_alias.id == Sale.branch_id)
                .join(workstation_alias, workstation_alias.id == Sale.workstation_id)
                .order_by(Sale.confirmed_at.desc(), SaleLine.sequence.asc(), SaleLine.id.desc())
                .limit(recent_limit)
            )
            if sale_scope_condition is not None:
                recent_statement = recent_statement.where(sale_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="confirmed_at",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through sales only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_sale_payments_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "sale_payments"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        sale_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=Sale.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=Sale.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(SalePayment))
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(SalePayment)
                .join(Sale, Sale.id == SalePayment.sale_id)
                .where(sale_scope_condition),
            )
            if sale_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(SalePayment.received_at))
            .select_from(SalePayment)
            .join(Sale, Sale.id == SalePayment.sale_id),
            sale_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    SalePayment.id.label("id"),
                    SalePayment.sale_id.label("sale_id"),
                    SalePayment.sequence.label("sequence"),
                    SalePayment.payment_method_code.label("payment_method_code"),
                    SalePayment.tendered_amount.label("tendered_amount"),
                    SalePayment.applied_amount.label("applied_amount"),
                    SalePayment.change_amount.label("change_amount"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    SalePayment.received_at.label("received_at"),
                )
                .select_from(SalePayment)
                .join(Sale, Sale.id == SalePayment.sale_id)
                .join(branch_alias, branch_alias.id == Sale.branch_id)
                .join(workstation_alias, workstation_alias.id == Sale.workstation_id)
                .order_by(SalePayment.received_at.desc(), SalePayment.sequence.asc())
                .limit(recent_limit)
            )
            if sale_scope_condition is not None:
                recent_statement = recent_statement.where(sale_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="received_at",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through sales only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_cash_movements_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "cash_movements"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=CashMovement.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=CashMovement.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(CashMovement))
        scoped_count = self._scoped_count(
            session,
            CashMovement,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CashMovement.occurred_at)).select_from(CashMovement),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CashMovement.id.label("id"),
                    CashMovement.sale_id.label("sale_id"),
                    CashMovement.cash_session_id.label("cash_session_id"),
                    CashMovement.movement_type.label("movement_type"),
                    CashMovement.direction.label("direction"),
                    CashMovement.payment_method_code.label("payment_method_code"),
                    CashMovement.amount.label("amount"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CashMovement.occurred_at.label("occurred_at"),
                )
                .select_from(CashMovement)
                .join(branch_alias, branch_alias.id == CashMovement.branch_id)
                .join(workstation_alias, workstation_alias.id == CashMovement.workstation_id)
                .order_by(CashMovement.occurred_at.desc(), CashMovement.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="occurred_at",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_operation_documents_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "operation_documents"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        source_branch_alias = aliased(Branch)
        destination_branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._operation_document_scope(scope)
        total_count = self._count(session, select(func.count()).select_from(OperationDocument))
        scoped_count = self._scoped_count(
            session,
            OperationDocument,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(OperationDocument.created_at_utc)).select_from(OperationDocument),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    OperationDocument.id.label("id"),
                    OperationDocument.document_type.label("document_type"),
                    OperationDocument.status.label("status"),
                    source_branch_alias.code.label("source_branch_code"),
                    destination_branch_alias.code.label("destination_branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    OperationDocument.created_at_utc.label("created_at_utc"),
                    OperationDocument.committed_at_utc.label("committed_at_utc"),
                )
                .select_from(OperationDocument)
                .outerjoin(
                    source_branch_alias,
                    source_branch_alias.id == OperationDocument.source_branch_id,
                )
                .outerjoin(
                    destination_branch_alias,
                    destination_branch_alias.id == OperationDocument.destination_branch_id,
                )
                .outerjoin(
                    workstation_alias, workstation_alias.id == OperationDocument.workstation_id
                )
                .order_by(OperationDocument.created_at_utc.desc(), OperationDocument.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_operation_document_lines_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "operation_document_lines"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        source_branch_alias = aliased(Branch)
        destination_branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        parent_scope_condition, _, _ = self._operation_document_scope(scope)
        total_count = self._count(session, select(func.count()).select_from(OperationDocumentLine))
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(OperationDocumentLine)
                .join(
                    OperationDocument,
                    OperationDocument.id == OperationDocumentLine.operation_document_id,
                )
                .where(parent_scope_condition),
            )
            if parent_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(OperationDocument.created_at_utc))
            .select_from(OperationDocumentLine)
            .join(
                OperationDocument,
                OperationDocument.id == OperationDocumentLine.operation_document_id,
            ),
            parent_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    OperationDocumentLine.id.label("id"),
                    OperationDocumentLine.operation_document_id.label("operation_document_id"),
                    OperationDocumentLine.line_number.label("line_number"),
                    OperationDocumentLine.product_code_snapshot.label("product_code"),
                    OperationDocumentLine.product_name_snapshot.label("product_name"),
                    OperationDocumentLine.quantity.label("quantity"),
                    OperationDocumentLine.expected_quantity.label("expected_quantity"),
                    OperationDocumentLine.received_quantity.label("received_quantity"),
                    source_branch_alias.code.label("source_branch_code"),
                    destination_branch_alias.code.label("destination_branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    OperationDocument.created_at_utc.label("created_at_utc"),
                )
                .select_from(OperationDocumentLine)
                .join(
                    OperationDocument,
                    OperationDocument.id == OperationDocumentLine.operation_document_id,
                )
                .outerjoin(
                    source_branch_alias,
                    source_branch_alias.id == OperationDocument.source_branch_id,
                )
                .outerjoin(
                    destination_branch_alias,
                    destination_branch_alias.id == OperationDocument.destination_branch_id,
                )
                .outerjoin(
                    workstation_alias, workstation_alias.id == OperationDocument.workstation_id
                )
                .order_by(
                    OperationDocument.created_at_utc.desc(), OperationDocumentLine.line_number.asc()
                )
                .limit(recent_limit)
            )
            if parent_scope_condition is not None:
                recent_statement = recent_statement.where(parent_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through operation_documents only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_correction_documents_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "correction_documents"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        source_branch_alias = aliased(Branch)
        destination_branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=CorrectionDocument.source_branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CorrectionDocument.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(CorrectionDocument))
        scoped_count = self._scoped_count(
            session,
            CorrectionDocument,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CorrectionDocument.created_at_utc)).select_from(CorrectionDocument),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CorrectionDocument.id.label("id"),
                    CorrectionDocument.target_document_id.label("target_document_id"),
                    CorrectionDocument.target_document_type.label("target_document_type"),
                    CorrectionDocument.correction_type.label("correction_type"),
                    CorrectionDocument.status.label("status"),
                    source_branch_alias.code.label("source_branch_code"),
                    destination_branch_alias.code.label("corrected_destination_branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CorrectionDocument.created_at_utc.label("created_at_utc"),
                    CorrectionDocument.committed_at_utc.label("committed_at_utc"),
                )
                .select_from(CorrectionDocument)
                .outerjoin(
                    source_branch_alias,
                    source_branch_alias.id == CorrectionDocument.source_branch_id,
                )
                .outerjoin(
                    destination_branch_alias,
                    destination_branch_alias.id
                    == CorrectionDocument.corrected_destination_branch_id,
                )
                .outerjoin(
                    workstation_alias, workstation_alias.id == CorrectionDocument.workstation_id
                )
                .order_by(CorrectionDocument.created_at_utc.desc(), CorrectionDocument.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_correction_document_lines_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "correction_document_lines"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        source_branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        parent_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=CorrectionDocument.source_branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CorrectionDocument.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(CorrectionDocumentLine))
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(CorrectionDocumentLine)
                .join(
                    CorrectionDocument,
                    CorrectionDocument.id == CorrectionDocumentLine.correction_document_id,
                )
                .where(parent_scope_condition),
            )
            if parent_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CorrectionDocument.created_at_utc))
            .select_from(CorrectionDocumentLine)
            .join(
                CorrectionDocument,
                CorrectionDocument.id == CorrectionDocumentLine.correction_document_id,
            ),
            parent_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CorrectionDocumentLine.id.label("id"),
                    CorrectionDocumentLine.correction_document_id.label("correction_document_id"),
                    CorrectionDocumentLine.line_number.label("line_number"),
                    CorrectionDocumentLine.product_code_snapshot.label("product_code"),
                    CorrectionDocumentLine.product_name_snapshot.label("product_name"),
                    CorrectionDocumentLine.delta_quantity.label("delta_quantity"),
                    source_branch_alias.code.label("source_branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CorrectionDocument.created_at_utc.label("created_at_utc"),
                )
                .select_from(CorrectionDocumentLine)
                .join(
                    CorrectionDocument,
                    CorrectionDocument.id == CorrectionDocumentLine.correction_document_id,
                )
                .outerjoin(
                    source_branch_alias,
                    source_branch_alias.id == CorrectionDocument.source_branch_id,
                )
                .outerjoin(
                    workstation_alias, workstation_alias.id == CorrectionDocument.workstation_id
                )
                .order_by(
                    CorrectionDocument.created_at_utc.desc(),
                    CorrectionDocumentLine.line_number.asc(),
                )
                .limit(recent_limit)
            )
            if parent_scope_condition is not None:
                recent_statement = recent_statement.where(parent_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through correction_documents only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_sale_returns_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "sale_returns"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=SaleReturn.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=SaleReturn.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(SaleReturn))
        scoped_count = self._scoped_count(
            session,
            SaleReturn,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(SaleReturn.created_at_utc)).select_from(SaleReturn),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    SaleReturn.id.label("id"),
                    SaleReturn.original_sale_id.label("original_sale_id"),
                    SaleReturn.status.label("status"),
                    SaleReturn.refund_method_code.label("refund_method_code"),
                    SaleReturn.total_refund_amount.label("total_refund_amount"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    SaleReturn.created_at_utc.label("created_at_utc"),
                )
                .select_from(SaleReturn)
                .join(branch_alias, branch_alias.id == SaleReturn.branch_id)
                .join(workstation_alias, workstation_alias.id == SaleReturn.workstation_id)
                .order_by(SaleReturn.created_at_utc.desc(), SaleReturn.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_sale_return_lines_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "sale_return_lines"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        parent_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=SaleReturn.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=SaleReturn.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(SaleReturnLine))
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(SaleReturnLine)
                .join(SaleReturn, SaleReturn.id == SaleReturnLine.sale_return_id)
                .where(parent_scope_condition),
            )
            if parent_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(SaleReturn.created_at_utc))
            .select_from(SaleReturnLine)
            .join(SaleReturn, SaleReturn.id == SaleReturnLine.sale_return_id),
            parent_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    SaleReturnLine.id.label("id"),
                    SaleReturnLine.sale_return_id.label("sale_return_id"),
                    SaleReturnLine.line_number.label("line_number"),
                    SaleReturnLine.returned_product_code_snapshot.label("product_code"),
                    SaleReturnLine.returned_product_name_snapshot.label("product_name"),
                    SaleReturnLine.returned_quantity.label("returned_quantity"),
                    SaleReturnLine.refund_line_total_amount.label("refund_line_total_amount"),
                    SaleReturnLine.disposition_code.label("disposition_code"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    SaleReturn.created_at_utc.label("created_at_utc"),
                )
                .select_from(SaleReturnLine)
                .join(SaleReturn, SaleReturn.id == SaleReturnLine.sale_return_id)
                .join(branch_alias, branch_alias.id == SaleReturn.branch_id)
                .join(workstation_alias, workstation_alias.id == SaleReturn.workstation_id)
                .order_by(SaleReturn.created_at_utc.desc(), SaleReturnLine.line_number.asc())
                .limit(recent_limit)
            )
            if parent_scope_condition is not None:
                recent_statement = recent_statement.where(parent_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through sale_returns only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_operational_payments_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "operational_payments"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=OperationalPayment.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=OperationalPayment.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(OperationalPayment))
        scoped_count = self._scoped_count(
            session,
            OperationalPayment,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(OperationalPayment.created_at_utc)).select_from(OperationalPayment),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    OperationalPayment.id.label("id"),
                    OperationalPayment.payee_name.label("payee_name"),
                    OperationalPayment.concept.label("concept"),
                    OperationalPayment.category_code.label("category_code"),
                    OperationalPayment.payment_method_code.label("payment_method_code"),
                    OperationalPayment.total_amount.label("total_amount"),
                    OperationalPayment.status.label("status"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    OperationalPayment.created_at_utc.label("created_at_utc"),
                )
                .select_from(OperationalPayment)
                .join(branch_alias, branch_alias.id == OperationalPayment.branch_id)
                .join(workstation_alias, workstation_alias.id == OperationalPayment.workstation_id)
                .order_by(OperationalPayment.created_at_utc.desc(), OperationalPayment.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_operational_discounts_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "operational_discounts"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=OperationalDiscount.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=OperationalDiscount.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(OperationalDiscount))
        scoped_count = self._scoped_count(
            session,
            OperationalDiscount,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(OperationalDiscount.created_at_utc)).select_from(OperationalDiscount),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    OperationalDiscount.id.label("id"),
                    OperationalDiscount.subject_name.label("subject_name"),
                    OperationalDiscount.concept.label("concept"),
                    OperationalDiscount.category_code.label("category_code"),
                    OperationalDiscount.payment_method_code.label("payment_method_code"),
                    OperationalDiscount.total_amount.label("total_amount"),
                    OperationalDiscount.status.label("status"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    OperationalDiscount.created_at_utc.label("created_at_utc"),
                )
                .select_from(OperationalDiscount)
                .join(branch_alias, branch_alias.id == OperationalDiscount.branch_id)
                .join(workstation_alias, workstation_alias.id == OperationalDiscount.workstation_id)
                .order_by(OperationalDiscount.created_at_utc.desc(), OperationalDiscount.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="created_at_utc",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_cash_session_closes_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "cash_session_closes"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        scope_condition, scope_status, scope_note = self._direct_scope(
            scope,
            branch_condition=CashSessionClose.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CashSessionClose.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(session, select(func.count()).select_from(CashSessionClose))
        scoped_count = self._scoped_count(
            session,
            CashSessionClose,
            scope_condition,
            total_count,
            scope,
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CashSessionClose.started_at_utc)).select_from(CashSessionClose),
            scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CashSessionClose.id.label("id"),
                    CashSessionClose.cash_session_id.label("cash_session_id"),
                    CashSessionClose.status.label("status"),
                    CashSessionClose.reconciliation_status.label("reconciliation_status"),
                    CashSessionClose.expected_cash_amount.label("expected_cash_amount"),
                    CashSessionClose.counted_cash_amount.label("counted_cash_amount"),
                    CashSessionClose.cash_variance_amount.label("cash_variance_amount"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CashSessionClose.started_at_utc.label("started_at_utc"),
                    CashSessionClose.committed_at_utc.label("committed_at_utc"),
                )
                .select_from(CashSessionClose)
                .join(branch_alias, branch_alias.id == CashSessionClose.branch_id)
                .join(workstation_alias, workstation_alias.id == CashSessionClose.workstation_id)
                .order_by(CashSessionClose.started_at_utc.desc(), CashSessionClose.id.desc())
                .limit(recent_limit)
            )
            if scope_condition is not None:
                recent_statement = recent_statement.where(scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="started_at_utc",
            latest_timestamp_value=latest_value,
            scope_status=scope_status,
            scope_note=scope_note,
            recent_rows=recent_rows,
        )

    def _build_cash_session_close_payment_method_counts_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "cash_session_close_payment_method_counts"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        parent_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=CashSessionClose.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CashSessionClose.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(
            session, select(func.count()).select_from(CashSessionClosePaymentMethodCount)
        )
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(CashSessionClosePaymentMethodCount)
                .join(
                    CashSessionClose,
                    CashSessionClose.id == CashSessionClosePaymentMethodCount.cash_session_close_id,
                )
                .where(parent_scope_condition),
            )
            if parent_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CashSessionClose.started_at_utc))
            .select_from(CashSessionClosePaymentMethodCount)
            .join(
                CashSessionClose,
                CashSessionClose.id == CashSessionClosePaymentMethodCount.cash_session_close_id,
            ),
            parent_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CashSessionClosePaymentMethodCount.id.label("id"),
                    CashSessionClosePaymentMethodCount.cash_session_close_id.label(
                        "cash_session_close_id"
                    ),
                    CashSessionClosePaymentMethodCount.payment_method_code.label(
                        "payment_method_code"
                    ),
                    CashSessionClosePaymentMethodCount.counted_amount.label("counted_amount"),
                    CashSessionClosePaymentMethodCount.expected_amount.label("expected_amount"),
                    CashSessionClosePaymentMethodCount.variance_amount.label("variance_amount"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CashSessionClose.started_at_utc.label("started_at_utc"),
                )
                .select_from(CashSessionClosePaymentMethodCount)
                .join(
                    CashSessionClose,
                    CashSessionClose.id == CashSessionClosePaymentMethodCount.cash_session_close_id,
                )
                .join(branch_alias, branch_alias.id == CashSessionClose.branch_id)
                .join(workstation_alias, workstation_alias.id == CashSessionClose.workstation_id)
                .order_by(
                    CashSessionClose.started_at_utc.desc(),
                    CashSessionClosePaymentMethodCount.id.desc(),
                )
                .limit(recent_limit)
            )
            if parent_scope_condition is not None:
                recent_statement = recent_statement.where(parent_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="started_at_utc",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through cash_session_closes only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_cash_session_close_product_counts_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "cash_session_close_product_counts"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        parent_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=CashSessionClose.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CashSessionClose.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(
            session, select(func.count()).select_from(CashSessionCloseProductCount)
        )
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(CashSessionCloseProductCount)
                .join(
                    CashSessionClose,
                    CashSessionClose.id == CashSessionCloseProductCount.cash_session_close_id,
                )
                .where(parent_scope_condition),
            )
            if parent_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CashSessionClose.started_at_utc))
            .select_from(CashSessionCloseProductCount)
            .join(
                CashSessionClose,
                CashSessionClose.id == CashSessionCloseProductCount.cash_session_close_id,
            ),
            parent_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CashSessionCloseProductCount.id.label("id"),
                    CashSessionCloseProductCount.cash_session_close_id.label(
                        "cash_session_close_id"
                    ),
                    CashSessionCloseProductCount.product_code_snapshot.label("product_code"),
                    CashSessionCloseProductCount.product_name_snapshot.label("product_name"),
                    CashSessionCloseProductCount.product_class_code_snapshot.label(
                        "product_class_code"
                    ),
                    CashSessionCloseProductCount.quantity.label("quantity"),
                    CashSessionCloseProductCount.bucket_code.label("bucket_code"),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CashSessionClose.started_at_utc.label("started_at_utc"),
                )
                .select_from(CashSessionCloseProductCount)
                .join(
                    CashSessionClose,
                    CashSessionClose.id == CashSessionCloseProductCount.cash_session_close_id,
                )
                .join(branch_alias, branch_alias.id == CashSessionClose.branch_id)
                .join(workstation_alias, workstation_alias.id == CashSessionClose.workstation_id)
                .order_by(
                    CashSessionClose.started_at_utc.desc(), CashSessionCloseProductCount.id.desc()
                )
                .limit(recent_limit)
            )
            if parent_scope_condition is not None:
                recent_statement = recent_statement.where(parent_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="started_at_utc",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through cash_session_closes only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _build_cash_session_close_class_reconciliations_snapshot(
        self,
        session: Session,
        table_names: set[str],
        scope: ResolvedScope,
        include_recent_rows: bool,
        recent_limit: int,
    ) -> DevAuditTableSnapshot:
        table_name = "cash_session_close_class_reconciliations"
        if table_name not in table_names:
            return self._unavailable_snapshot(table_name)

        branch_alias = aliased(Branch)
        workstation_alias = aliased(Workstation)
        parent_scope_condition, _, _ = self._direct_scope(
            scope,
            branch_condition=CashSessionClose.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CashSessionClose.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        total_count = self._count(
            session, select(func.count()).select_from(CashSessionCloseClassReconciliation)
        )
        scoped_count = (
            self._count(
                session,
                select(func.count())
                .select_from(CashSessionCloseClassReconciliation)
                .join(
                    CashSessionClose,
                    CashSessionClose.id
                    == CashSessionCloseClassReconciliation.cash_session_close_id,
                )
                .where(parent_scope_condition),
            )
            if parent_scope_condition is not None
            else (total_count if scope.has_filters else None)
        )
        latest_value = self._latest_value(
            session,
            select(func.max(CashSessionClose.started_at_utc))
            .select_from(CashSessionCloseClassReconciliation)
            .join(
                CashSessionClose,
                CashSessionClose.id == CashSessionCloseClassReconciliation.cash_session_close_id,
            ),
            parent_scope_condition,
        )
        recent_rows: list[dict[str, Any]] = []
        if include_recent_rows:
            recent_statement = (
                select(
                    CashSessionCloseClassReconciliation.id.label("id"),
                    CashSessionCloseClassReconciliation.cash_session_close_id.label(
                        "cash_session_close_id"
                    ),
                    CashSessionCloseClassReconciliation.product_class_code_snapshot.label(
                        "product_class_code"
                    ),
                    CashSessionCloseClassReconciliation.product_class_name_snapshot.label(
                        "product_class_name"
                    ),
                    CashSessionCloseClassReconciliation.expected_quantity.label(
                        "expected_quantity"
                    ),
                    CashSessionCloseClassReconciliation.attributed_quantity.label(
                        "attributed_quantity"
                    ),
                    CashSessionCloseClassReconciliation.variance_quantity.label(
                        "variance_quantity"
                    ),
                    CashSessionCloseClassReconciliation.resolution_status.label(
                        "resolution_status"
                    ),
                    branch_alias.code.label("branch_code"),
                    workstation_alias.code.label("workstation_code"),
                    CashSessionClose.started_at_utc.label("started_at_utc"),
                )
                .select_from(CashSessionCloseClassReconciliation)
                .join(
                    CashSessionClose,
                    CashSessionClose.id
                    == CashSessionCloseClassReconciliation.cash_session_close_id,
                )
                .join(branch_alias, branch_alias.id == CashSessionClose.branch_id)
                .join(workstation_alias, workstation_alias.id == CashSessionClose.workstation_id)
                .order_by(
                    CashSessionClose.started_at_utc.desc(),
                    CashSessionCloseClassReconciliation.id.desc(),
                )
                .limit(recent_limit)
            )
            if parent_scope_condition is not None:
                recent_statement = recent_statement.where(parent_scope_condition)
            recent_rows = self._fetch_recent_rows(session, recent_statement)

        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=total_count,
            scoped_row_count=scoped_count,
            latest_timestamp_field_used="started_at_utc",
            latest_timestamp_value=latest_value,
            scope_status="partial" if scope.has_filters else "global",
            scope_note="scoped through cash_session_closes only" if scope.has_filters else None,
            recent_rows=recent_rows,
        )

    def _count(self, session: Session, statement: Any) -> int:
        return int(session.execute(statement).scalar_one())

    def _latest_value(
        self,
        session: Session,
        statement: Any,
        scope_condition: Any | None,
    ) -> datetime | None:
        if scope_condition is not None:
            statement = statement.where(scope_condition)
        value = session.execute(statement).scalar_one()
        return typing_cast(datetime | None, value)

    def _fetch_recent_rows(self, session: Session, statement: Any) -> list[dict[str, Any]]:
        rows = session.execute(statement).mappings().all()
        return [self._serialize_mapping_row(dict(row)) for row in rows]

    def _serialize_mapping_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {key: _serialize_value(value) for key, value in row.items()}

    def _scoped_count(
        self,
        session: Session,
        model: Any,
        scope_condition: Any | None,
        total_count: int,
        scope: ResolvedScope,
    ) -> int | None:
        if not scope.has_filters:
            return None
        if scope_condition is None:
            return total_count
        return self._count(
            session,
            select(func.count()).select_from(model).where(scope_condition),
        )

    def _audit_log_scope(
        self, scope: ResolvedScope
    ) -> tuple[Any | None, ScopeStatus, str | None]:
        if not scope.has_filters:
            return None, "global", None
        if scope.branch_id is None:
            return None, "global", "table has no reliable direct branch reference"
        if scope.workstation_id is not None:
            return (
                AuditLog.branch_id == scope.branch_id,
                "partial",
                "scoped through branch only because audit_log has no workstation reference",
            )
        return AuditLog.branch_id == scope.branch_id, "direct", None

    def _outbox_scope_clause(
        self, scope: ResolvedScope
    ) -> tuple[Any | None, ScopeStatus, str | None]:
        if not scope.has_filters:
            return None, "global", None

        sale_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=Sale.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=Sale.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        cash_session_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=CashSession.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=CashSession.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        sale_return_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=SaleReturn.branch_id == scope.branch_id if scope.branch_id else None,
            workstation_condition=SaleReturn.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        payment_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=OperationalPayment.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=OperationalPayment.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        discount_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=OperationalDiscount.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=OperationalDiscount.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        close_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=CashSessionClose.branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CashSessionClose.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        correction_scope, _, _ = self._direct_scope(
            scope,
            branch_condition=CorrectionDocument.source_branch_id == scope.branch_id
            if scope.branch_id
            else None,
            workstation_condition=CorrectionDocument.workstation_id == scope.workstation_id
            if scope.workstation_id
            else None,
            workstation_scope_supported=True,
            branch_scope_supported=True,
        )
        operation_scope, _, _ = self._operation_document_scope(scope)

        clauses: list[Any] = []
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="cash_session",
                subquery=select(cast(CashSession.id, String)).where(cash_session_scope)
                if cash_session_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="sale",
                subquery=select(cast(Sale.id, String)).where(sale_scope)
                if sale_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="sale_return",
                subquery=select(cast(SaleReturn.id, String)).where(sale_return_scope)
                if sale_return_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="operational_payment",
                subquery=select(cast(OperationalPayment.id, String)).where(payment_scope)
                if payment_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="operational_discount",
                subquery=select(cast(OperationalDiscount.id, String)).where(discount_scope)
                if discount_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="cash_session_close",
                subquery=select(cast(CashSessionClose.id, String)).where(close_scope)
                if close_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="correction",
                subquery=select(cast(CorrectionDocument.id, String)).where(correction_scope)
                if correction_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="operation_document",
                subquery=select(cast(OperationDocument.id, String)).where(operation_scope)
                if operation_scope is not None
                else None,
            )
        )
        clauses.extend(
            self._aggregate_scope_clauses(
                aggregate_type="transfer",
                subquery=select(cast(OperationDocument.id, String)).where(operation_scope)
                if operation_scope is not None
                else None,
            )
        )

        if not clauses:
            return None, "global", "table has no reliable direct branch/workstation reference"
        return or_(*clauses), "partial", "scoped through known aggregate references only"

    def _aggregate_scope_clauses(self, *, aggregate_type: str, subquery: Any | None) -> list[Any]:
        if subquery is None:
            return []
        return [
            and_(
                OutboxEvent.aggregate_type == aggregate_type,
                OutboxEvent.aggregate_id.in_(subquery),
            )
        ]

    def _operation_document_scope(
        self, scope: ResolvedScope
    ) -> tuple[Any | None, ScopeStatus, str | None]:
        if not scope.has_filters:
            return None, "global", None

        conditions: list[Any] = []
        scope_note: str | None = None

        if scope.workstation_id is not None:
            conditions.append(OperationDocument.workstation_id == scope.workstation_id)
        if scope.branch_id is not None:
            conditions.append(
                or_(
                    OperationDocument.source_branch_id == scope.branch_id,
                    OperationDocument.destination_branch_id == scope.branch_id,
                )
            )
        if not conditions:
            return None, "global", "table has no reliable direct branch/workstation reference"
        if scope.workstation_id is not None and scope.branch_id is not None:
            scope_note = "scoped by workstation and branch involvement"
        return and_(*conditions), "direct", scope_note

    def _direct_scope(
        self,
        scope: ResolvedScope,
        *,
        branch_condition: Any | None,
        workstation_condition: Any | None,
        workstation_scope_supported: bool,
        branch_scope_supported: bool,
    ) -> tuple[Any | None, ScopeStatus, str | None]:
        if not scope.has_filters:
            return None, "global", None

        conditions: list[Any] = []
        scope_status: ScopeStatus = "direct"
        scope_note: str | None = None

        if scope.branch_id is not None and branch_condition is not None:
            conditions.append(branch_condition)
        elif scope.branch_id is not None and not branch_scope_supported:
            scope_status = "global"
            scope_note = "table has no reliable direct branch reference"

        if scope.workstation_id is not None:
            if workstation_condition is not None and workstation_scope_supported:
                conditions.append(workstation_condition)
            elif branch_condition is not None and scope.branch_id is not None:
                scope_status = "partial"
                scope_note = (
                    "scoped through branch only because the table has no workstation reference"
                )
            else:
                scope_status = "global"
                scope_note = "table has no reliable direct workstation reference"

        if not conditions:
            return None, scope_status, scope_note
        return and_(*conditions), scope_status, scope_note

    def _unavailable_snapshot(self, table_name: str) -> DevAuditTableSnapshot:
        return DevAuditTableSnapshot(
            table_name=table_name,
            row_count=0,
            scoped_row_count=0,
            latest_timestamp_field_used=None,
            latest_timestamp_value=None,
            scope_status="unavailable",
            scope_note="table is unavailable in the current database",
            recent_rows=[],
        )


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _serialize_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value
