"""Financial participants: the admitted idempotent command owns every transaction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from zeromerma_api.db.operation_context import get_operation_context
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
    FinancialEntrySnapshot,
    FinancialOperationSnapshot,
)
from zeromerma_api.modules.financial_ledger.domain.money import ZERO, FinancialModelError
from zeromerma_api.modules.financial_ledger.domain.rules import validate_entry, validate_operation
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyBoundaryError


@dataclass(frozen=True)
class FinancialCommandScope:
    branch_id: UUID
    workstation_id: UUID | None
    cash_session_id: UUID | None
    actor_id: UUID


def _lineage(
    session: Session,
    *,
    scope: FinancialCommandScope,
    currency_code: str,
    occurred_at: datetime,
    opening: bool,
) -> dict[str, Any]:
    owner = execution(session)
    if owner is None or owner.record is None or not owner.action_running:
        raise IdempotencyBoundaryError("Financial facts require the admitted command action.")
    if (
        owner.record.actor_user_id != scope.actor_id
        or owner.record.branch_id != scope.branch_id
        or owner.record.workstation_id != scope.workstation_id
        or (
            owner.record.cash_session_id != scope.cash_session_id
            and not (
                opening
                and owner.record.cash_session_id is None
                and owner.record.operation_code == "cash_session.open"
            )
        )
    ):
        raise IdempotencyBoundaryError("Financial facts require the admitted actual session.")
    context = get_operation_context(session)
    if context.operation_id != owner.record.id:
        raise IdempotencyBoundaryError("Financial facts require the owning command identity.")
    return dict(
        branch_id=scope.branch_id,
        workstation_id=scope.workstation_id,
        cash_session_id=scope.cash_session_id,
        actor_id=scope.actor_id,
        currency_code=currency_code,
        context_version=1,
        source_app=context.source_app.value,
        actor_type=context.actor_type,
        operation_id=context.operation_id,
        operation_code=context.operation_code,
        correlation_id=context.correlation_id,
        causation_id=context.causation_id,
        request_id=context.request_id,
        idempotency_key=context.idempotency_key,
        related_branch_ids=sorted(
            {str(scope.branch_id), *(str(item) for item in context.related_branch_ids)}
        ),
        occurred_at=occurred_at,
    )


def _snapshot(operation: FinancialOperation) -> FinancialOperationSnapshot:
    return FinancialOperationSnapshot(
        id=operation.id,
        kind=OperationKind(operation.kind),
        source_type=operation.source_type,
        source_id=operation.source_id,
        effect_code=operation.effect_code,
        subject_type=operation.subject_type,
        subject_id=operation.subject_id,
        amount_due=operation.amount_due,
        branch_id=operation.branch_id,
        currency_code=operation.currency_code,
        cash_session_id=operation.cash_session_id,
        related_operation_id=operation.related_operation_id,
        relation_kind=operation.relation_kind,
        opening_obligation_kind=(
            ObligationKind(operation.opening_obligation_kind)
            if operation.opening_obligation_kind
            else None
        ),
        opening_reason_code=operation.opening_reason_code,
        source_evidence_reference=operation.source_evidence_reference,
        cutover_at=operation.cutover_at,
    )


def create_financial_operation(
    session: Session,
    *,
    kind: OperationKind,
    source_type: str,
    source_id: UUID,
    subject_type: str,
    subject_id: UUID,
    amount_due: Decimal,
    currency_code: str,
    scope: FinancialCommandScope,
    occurred_at: datetime,
    related_operation_id: UUID | None = None,
    relation_kind: str | None = None,
    opening_obligation_kind: ObligationKind | None = None,
    opening_reason_code: str | None = None,
    source_evidence_reference: UUID | None = None,
    cutover_at: datetime | None = None,
) -> FinancialOperation:
    operation = FinancialOperation(
        id=uuid4(),
        kind=kind.value,
        source_type=source_type,
        source_id=source_id,
        effect_code=kind.value,
        subject_type=subject_type,
        subject_id=subject_id,
        amount_due=amount_due,
        related_operation_id=related_operation_id,
        relation_kind=relation_kind,
        opening_obligation_kind=opening_obligation_kind.value if opening_obligation_kind else None,
        opening_reason_code=opening_reason_code,
        source_evidence_reference=source_evidence_reference,
        cutover_at=cutover_at,
        **_lineage(
            session,
            scope=scope,
            currency_code=currency_code,
            occurred_at=occurred_at,
            opening=kind == OperationKind.CASH_OPENING,
        ),
    )
    validate_operation(_snapshot(operation))
    if (
        kind
        in {
            OperationKind.SALE_COLLECTION,
            OperationKind.OPERATIONAL_PAYMENT,
            OperationKind.OPERATIONAL_CHARGE,
        }
        and amount_due == ZERO
    ):
        raise FinancialModelError("A completed collection or payment must have a positive amount.")
    session.add(operation)
    session.flush()
    return operation


def record_confirmed_entry(
    session: Session,
    *,
    operation: FinancialOperation,
    leg_key: str,
    payment_method: PaymentMethod,
    direction: Direction,
    amount: Decimal,
    scope: FinancialCommandScope,
    occurred_at: datetime,
    tendered_amount: Decimal | None = None,
    change_amount: Decimal = ZERO,
    external_recording_reference: UUID | None = None,
) -> FinancialEntry:
    """Record actual local cash or an explicit external accounting declaration."""
    mode = (
        ExecutionMode.LOCAL
        if payment_method == PaymentMethod.CASH
        else ExecutionMode.ACCOUNTING_ONLY
    )
    evidence = (
        EvidenceKind.LOCAL_CASH
        if payment_method == PaymentMethod.CASH
        else EvidenceKind.EXTERNAL_RECORDING
    )
    entry = FinancialEntry(
        id=uuid4(),
        financial_operation_id=operation.id,
        leg_key=leg_key,
        payment_method_code=payment_method.value,
        direction=direction.value,
        amount=amount,
        tendered_amount=tendered_amount,
        change_amount=change_amount,
        execution_mode=mode.value,
        state=EntryState.CONFIRMED.value,
        confirmed_at=occurred_at,
        resolution_kind=evidence.value,
        resolution_reference=external_recording_reference,
        **_lineage(
            session,
            scope=scope,
            currency_code=operation.currency_code,
            occurred_at=occurred_at,
            opening=operation.kind == OperationKind.CASH_OPENING.value,
        ),
    )
    if len(leg_key) > 40:
        raise FinancialModelError("A financial leg key cannot exceed 40 characters.")
    validate_entry(
        _snapshot(operation),
        FinancialEntrySnapshot(
            id=entry.id,
            financial_operation_id=operation.id,
            leg_key=leg_key,
            payment_method_code=payment_method,
            direction=direction,
            amount=amount,
            state=EntryState.CONFIRMED,
            branch_id=scope.branch_id,
            currency_code=operation.currency_code,
            cash_session_id=scope.cash_session_id,
            tendered_amount=tendered_amount,
            change_amount=change_amount,
            execution_mode=mode,
            confirmed_at=occurred_at,
            resolution_kind=evidence,
            resolution_reference=external_recording_reference,
        ),
    )
    session.add(entry)
    session.flush()
    return entry
