from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from .constants import (
    Direction,
    EntryState,
    EvidenceKind,
    ExecutionMode,
    ObligationKind,
    OperationKind,
    OperationState,
    PaymentMethod,
)
from .money import ZERO, financial_calculation, require_money


@dataclass(frozen=True, kw_only=True)
class FinancialOperationSnapshot:
    id: UUID
    kind: OperationKind
    source_type: str
    source_id: UUID
    effect_code: str
    subject_type: str
    subject_id: UUID
    amount_due: Decimal
    branch_id: UUID
    currency_code: str = "MXN"
    cash_session_id: UUID | None = None
    opening_obligation_kind: ObligationKind | None = None
    related_operation_id: UUID | None = None
    relation_kind: str | None = None
    opening_reason_code: str | None = None
    source_evidence_reference: UUID | None = None
    cutover_at: datetime | None = None


@dataclass(frozen=True, kw_only=True)
class FinancialEntrySnapshot:
    id: UUID
    financial_operation_id: UUID
    leg_key: str
    payment_method_code: PaymentMethod
    direction: Direction
    amount: Decimal
    state: EntryState
    branch_id: UUID
    currency_code: str = "MXN"
    cash_session_id: UUID | None = None
    tendered_amount: Decimal | None = None
    change_amount: Decimal = ZERO
    execution_mode: ExecutionMode = ExecutionMode.LOCAL
    confirmed_at: datetime | None = None
    resolution_kind: EvidenceKind | None = None
    resolution_reference: UUID | None = None
    reverses_entry_id: UUID | None = None


@dataclass(frozen=True, kw_only=True)
class OperationSummary:
    operation_id: UUID
    amount_due: Decimal
    confirmed_amount: Decimal
    reversed_amount: Decimal
    net_amount: Decimal
    pending_amount: Decimal
    unassigned_amount: Decimal
    state: OperationState
    payment_method: str | None


@dataclass(frozen=True, kw_only=True)
class CashProjection:
    branch_id: UUID
    cash_session_id: UUID
    currency_code: str
    opening_amount: Decimal
    cash_in: Decimal
    cash_out: Decimal
    expected_cash: Decimal
    confirmed_entry_ids: tuple[UUID, ...]
    unresolved_operation_ids: tuple[UUID, ...]

    @financial_calculation
    def variance(self, counted_cash: Decimal) -> Decimal:
        return require_money(counted_cash) - self.expected_cash


@dataclass(frozen=True, kw_only=True)
class RefundAllocation:
    amount_due: Decimal
    cash_amount: Decimal
    card_amount: Decimal
    pending_amount: Decimal
