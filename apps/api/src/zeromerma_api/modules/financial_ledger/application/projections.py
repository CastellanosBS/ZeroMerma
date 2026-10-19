"""Internal, authorized projections of canonical facts; no legacy fallback or write API."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import require_session_capabilities
from zeromerma_api.modules.financial_ledger.domain.constants import (
    Direction,
    EntryState,
    EvidenceKind,
    ExecutionMode,
    ObligationKind,
    OperationKind,
    PaymentMethod,
)
from zeromerma_api.modules.financial_ledger.domain.models import (
    CashProjection,
    FinancialEntrySnapshot,
    FinancialOperationSnapshot,
)
from zeromerma_api.modules.financial_ledger.domain.rules import (
    project_cash_session,
    validate_ledger,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)


@dataclass(frozen=True)
class FinancialLedgerSnapshot:
    operations: tuple[FinancialOperationSnapshot, ...]
    entries: tuple[FinancialEntrySnapshot, ...]


def _operation_snapshot(row: FinancialOperation) -> FinancialOperationSnapshot:
    return FinancialOperationSnapshot(
        id=row.id,
        kind=OperationKind(row.kind),
        source_type=row.source_type,
        source_id=row.source_id,
        effect_code=row.effect_code,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        amount_due=row.amount_due,
        branch_id=row.branch_id,
        currency_code=row.currency_code,
        cash_session_id=row.cash_session_id,
        opening_obligation_kind=(
            ObligationKind(row.opening_obligation_kind) if row.opening_obligation_kind else None
        ),
        related_operation_id=row.related_operation_id,
        relation_kind=row.relation_kind,
        opening_reason_code=row.opening_reason_code,
        source_evidence_reference=row.source_evidence_reference,
        cutover_at=row.cutover_at,
    )


def _entry_snapshot(row: FinancialEntry) -> FinancialEntrySnapshot:
    return FinancialEntrySnapshot(
        id=row.id,
        financial_operation_id=row.financial_operation_id,
        leg_key=row.leg_key,
        payment_method_code=PaymentMethod(row.payment_method_code),
        direction=Direction(row.direction),
        amount=row.amount,
        state=EntryState(row.state),
        branch_id=row.branch_id,
        currency_code=row.currency_code,
        cash_session_id=row.cash_session_id,
        tendered_amount=row.tendered_amount,
        change_amount=row.change_amount,
        execution_mode=ExecutionMode(row.execution_mode),
        confirmed_at=row.confirmed_at,
        resolution_kind=EvidenceKind(row.resolution_kind) if row.resolution_kind else None,
        resolution_reference=row.resolution_reference,
        reverses_entry_id=row.reverses_entry_id,
    )


class FinancialLedgerQueryService:
    def read_branch(self, session: Session, *, branch_id: UUID) -> FinancialLedgerSnapshot:
        scope = require_session_capabilities(session, ("cash_finance.view",))
        current_user = resolve_authorization(session, scope.user, surface=scope.surface)
        require_branches(current_user, "cash_finance.view", (branch_id,))
        # One SELECT gives the whole graph one PostgreSQL statement snapshot, even under
        # READ COMMITTED. Split operation/entry reads could observe different commits.
        statement = (
            select(FinancialOperation, FinancialEntry)
            .outerjoin(
                FinancialEntry, FinancialEntry.financial_operation_id == FinancialOperation.id
            )
            .where(FinancialOperation.branch_id == branch_id)
            .order_by(FinancialOperation.id, FinancialEntry.id)
            .execution_options(populate_existing=True)
        )
        operations: dict[UUID, FinancialOperationSnapshot] = {}
        entries: list[FinancialEntrySnapshot] = []
        with session.no_autoflush:
            for operation, entry in session.execute(statement):
                operations[operation.id] = _operation_snapshot(operation)
                if entry is not None:
                    entries.append(_entry_snapshot(entry))
        snapshot = FinancialLedgerSnapshot(tuple(operations.values()), tuple(entries))
        validate_ledger(snapshot.operations, snapshot.entries)
        return snapshot

    def get_cash_projection(
        self, session: Session, *, branch_id: UUID, cash_session_id: UUID
    ) -> CashProjection:
        snapshot = self.read_branch(session, branch_id=branch_id)
        return project_cash_session(
            branch_id, cash_session_id, snapshot.operations, snapshot.entries
        )
