"""Pure rules over a complete canonical graph, never over legacy cash movements."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from .constants import (
    COLLECTION_KINDS,
    INFLOW_KINDS,
    OUTFLOW_KINDS,
    PENDING_STATES,
    REFUND_KINDS,
    SOURCE_TYPES,
    Direction,
    EntryState,
    EvidenceKind,
    ExecutionMode,
    ObligationKind,
    OperationKind,
    OperationState,
    PaymentMethod,
)
from .models import (
    CashProjection,
    FinancialEntrySnapshot,
    FinancialOperationSnapshot,
    OperationSummary,
    RefundAllocation,
)
from .money import (
    ZERO,
    FinancialModelError,
    financial_calculation,
    quantize_money,
    require_currency,
    require_money,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise FinancialModelError(message)


def validate_operation(operation: FinancialOperationSnapshot) -> None:
    require_money(operation.amount_due)
    require_currency(operation.currency_code)
    _require(operation.kind in SOURCE_TYPES, "Unknown financial operation kind.")
    _require(
        operation.source_type in SOURCE_TYPES[operation.kind]
        and operation.effect_code == operation.kind.value,
        "The causal source does not match its financial effect.",
    )
    allowed_subjects = {
        OperationKind.SALE_COLLECTION: {"SALE"},
        OperationKind.SALE_REFUND: {"SALE"},
        OperationKind.ORDER_ADVANCE: {"ORDER"},
        OperationKind.ORDER_SETTLEMENT: {"ORDER"},
        OperationKind.ORDER_REFUND: {"ORDER"},
        OperationKind.OPERATIONAL_PAYMENT: {"OPERATIONAL_PAYMENT"},
        OperationKind.OPERATIONAL_CHARGE: {"OPERATIONAL_DISCOUNT"},
        OperationKind.CASH_OPENING: {"CASH_SESSION"},
        OperationKind.CASH_DEPOSIT: {"CASH_SESSION"},
        OperationKind.CASH_WITHDRAWAL: {"CASH_SESSION"},
        OperationKind.OPENING_OBLIGATION: {"ORDER", "OPENING_BALANCE"},
        OperationKind.TECHNICAL_REVERSAL: {
            "SALE",
            "ORDER",
            "OPERATIONAL_PAYMENT",
            "OPERATIONAL_DISCOUNT",
            "CASH_SESSION",
            "OPENING_BALANCE",
        },
    }
    _require(operation.subject_type in allowed_subjects[operation.kind], "Invalid subject type.")
    if operation.kind in {
        OperationKind.SALE_COLLECTION,
        OperationKind.OPERATIONAL_PAYMENT,
        OperationKind.OPERATIONAL_CHARGE,
    }:
        _require(operation.source_id == operation.subject_id, "Source and subject must agree.")
    if operation.kind in {
        OperationKind.CASH_OPENING,
        OperationKind.CASH_DEPOSIT,
        OperationKind.CASH_WITHDRAWAL,
    }:
        _require(
            operation.cash_session_id is not None
            and operation.subject_id == operation.cash_session_id,
            "Cash operations require their cash session as the economic subject.",
        )
    if operation.source_type == "CASH_SESSION":
        _require(operation.source_id == operation.cash_session_id, "Invalid opening source.")
    opening_fields = (
        operation.opening_reason_code,
        operation.source_evidence_reference,
        operation.cutover_at,
    )
    if operation.source_type == "OPENING_STATE":
        _require(
            all(value is not None for value in opening_fields)
            and bool(operation.opening_reason_code and operation.opening_reason_code.strip()),
            "Opening state requires a reason, evidence reference and cutover date.",
        )
        assert operation.cutover_at is not None
        _require(operation.cutover_at.utcoffset() is not None, "Cutover must be timezone aware.")
    else:
        _require(all(value is None for value in opening_fields), "Unexpected opening metadata.")
    if operation.kind == OperationKind.OPENING_OBLIGATION:
        _require(
            operation.opening_obligation_kind in set(ObligationKind), "Unknown opening balance."
        )
        _require(operation.cash_session_id is None, "An opening obligation is not drawer cash.")
        if operation.opening_obligation_kind == ObligationKind.CUSTOMER_ADVANCE:
            _require(operation.subject_type == "ORDER", "Opening advances require a known order.")
    else:
        _require(operation.opening_obligation_kind is None, "Unexpected opening obligation.")
    allowed_relation = (
        "REFUND_OF"
        if operation.kind in REFUND_KINDS
        else "REVERSAL_OF"
        if operation.kind == OperationKind.TECHNICAL_REVERSAL
        else "SETTLEMENT_OF"
        if operation.kind == OperationKind.ORDER_SETTLEMENT
        else None
    )
    if operation.related_operation_id is None:
        _require(operation.relation_kind is None, "A relation requires its referenced operation.")
        _require(
            operation.kind != OperationKind.TECHNICAL_REVERSAL, "A reversal requires its cause."
        )
    else:
        _require(
            operation.id != operation.related_operation_id
            and allowed_relation is not None
            and operation.relation_kind == allowed_relation,
            "Invalid financial operation relation.",
        )


@financial_calculation
def validate_entry(operation: FinancialOperationSnapshot, entry: FinancialEntrySnapshot) -> None:
    require_money(entry.amount, positive=True)
    require_money(entry.change_amount)
    require_currency(entry.currency_code)
    _require(
        entry.financial_operation_id == operation.id
        and entry.branch_id == operation.branch_id
        and entry.currency_code == operation.currency_code,
        "Entry and operation scope must agree.",
    )
    _require(bool(entry.leg_key.strip()), "A method leg requires a stable key.")
    _require(
        entry.payment_method_code in set(PaymentMethod), "MIXED is derived, never a method leg."
    )
    _require(entry.direction in set(Direction), "Unknown financial direction.")
    _require(entry.state in set(EntryState), "Unknown financial entry state.")
    _require(
        operation.kind != OperationKind.OPENING_OBLIGATION, "Opening balances have no cash legs."
    )
    if operation.kind in INFLOW_KINDS:
        _require(entry.direction == Direction.IN, "An inflow must use IN.")
    if operation.kind in OUTFLOW_KINDS:
        _require(entry.direction == Direction.OUT, "An outflow must use OUT.")
    if entry.tendered_amount is not None:
        require_money(entry.tendered_amount, positive=True)
    if entry.payment_method_code == PaymentMethod.CASH:
        _require(
            entry.cash_session_id is not None and entry.execution_mode == ExecutionMode.LOCAL,
            "Cash requires an actual session and local execution.",
        )
        if entry.direction == Direction.IN:
            _require(
                entry.tendered_amount == entry.amount + entry.change_amount,
                "Cash tendered must equal applied cash plus change.",
            )
        else:
            _require(
                entry.change_amount == ZERO and entry.tendered_amount in {None, entry.amount},
                "An outflow cannot produce change.",
            )
    else:
        _require(
            entry.execution_mode
            in {
                ExecutionMode.ACCOUNTING_ONLY,
                ExecutionMode.PROVIDER_INTEGRATED,
                ExecutionMode.MANUAL_FALLBACK,
            }
            and entry.change_amount == ZERO
            and entry.tendered_amount in {None, entry.amount},
            "Card entries cannot use local cash execution or produce change.",
        )
    if operation.kind in {
        OperationKind.CASH_OPENING,
        OperationKind.CASH_DEPOSIT,
        OperationKind.CASH_WITHDRAWAL,
    }:
        _require(
            entry.payment_method_code == PaymentMethod.CASH
            and entry.cash_session_id == operation.cash_session_id,
            "Opening, deposit and withdrawal cash belong to their declared drawer.",
        )
    _require(
        (entry.state == EntryState.CONFIRMED) == (entry.confirmed_at is not None),
        "Only confirmed facts carry a confirmation timestamp.",
    )
    if entry.confirmed_at is not None:
        _require(entry.confirmed_at.utcoffset() is not None, "Confirmation must be timezone aware.")
    if entry.state in PENDING_STATES:
        _require(
            entry.resolution_kind is None and entry.resolution_reference is None,
            "An unresolved entry cannot claim resolution evidence.",
        )
    elif entry.state == EntryState.CONFIRMED:
        expected_evidence = {
            ExecutionMode.LOCAL: {EvidenceKind.LOCAL_CASH, EvidenceKind.MANUAL_RECONCILIATION},
            ExecutionMode.ACCOUNTING_ONLY: {
                EvidenceKind.EXTERNAL_RECORDING,
                EvidenceKind.MANUAL_RECONCILIATION,
            },
            ExecutionMode.MANUAL_FALLBACK: {EvidenceKind.MANUAL_RECONCILIATION},
            ExecutionMode.PROVIDER_INTEGRATED: {
                EvidenceKind.PROVIDER_CAPTURE
                if entry.direction == Direction.IN
                else EvidenceKind.PROVIDER_REFUND,
                EvidenceKind.MANUAL_RECONCILIATION,
            },
        }
        _require(
            entry.resolution_kind in expected_evidence[entry.execution_mode],
            "Confirmation evidence does not match execution and direction.",
        )
        _require(
            (entry.resolution_reference is None)
            == (entry.resolution_kind == EvidenceKind.LOCAL_CASH),
            "External confirmation requires an evidence reference.",
        )
    elif entry.resolution_kind is None:
        _require(entry.resolution_reference is None, "Evidence reference requires its kind.")
    else:
        _require(
            entry.resolution_reference is not None
            and (
                entry.resolution_kind == EvidenceKind.MANUAL_RECONCILIATION
                or (
                    entry.execution_mode == ExecutionMode.PROVIDER_INTEGRATED
                    and (
                        (
                            entry.state == EntryState.REJECTED
                            and entry.resolution_kind == EvidenceKind.PROVIDER_REJECTION
                        )
                        or (
                            entry.state == EntryState.CANCELLED
                            and entry.resolution_kind == EvidenceKind.PROVIDER_VOID
                        )
                    )
                )
            ),
            "Rejection or cancellation requires compatible resolution evidence.",
        )
    if operation.kind == OperationKind.TECHNICAL_REVERSAL:
        _require(
            entry.reverses_entry_id is not None and entry.state == EntryState.CONFIRMED,
            "A technical reversal is an atomic confirmed compensation.",
        )
    else:
        _require(
            entry.reverses_entry_id is None, "Only technical reversals reverse ledger entries."
        )


@financial_calculation
def validate_ledger(
    operations: Sequence[FinancialOperationSnapshot], entries: Sequence[FinancialEntrySnapshot]
) -> None:
    """Validate a complete branch graph; command admission still owns business authorization."""
    operation_map = {operation.id: operation for operation in operations}
    entry_map = {entry.id: entry for entry in entries}
    _require(len(operation_map) == len(operations), "Duplicate operation identity.")
    _require(len(entry_map) == len(entries), "Duplicate entry identity.")
    causes: set[tuple[str, UUID, str]] = set()
    openings: set[UUID] = set()
    for operation in operations:
        validate_operation(operation)
        cause = (operation.source_type, operation.source_id, operation.effect_code)
        _require(cause not in causes, "Duplicate causal financial effect.")
        causes.add(cause)
        if operation.kind == OperationKind.CASH_OPENING:
            assert operation.cash_session_id is not None
            _require(operation.cash_session_id not in openings, "A drawer has one opening.")
            openings.add(operation.cash_session_id)
        if operation.related_operation_id is not None:
            related = operation_map.get(operation.related_operation_id)
            _require(related is not None, "A related operation is missing from the graph.")
            assert related is not None
            _require(
                related.branch_id == operation.branch_id
                and related.currency_code == operation.currency_code
                and (related.subject_type, related.subject_id)
                == (operation.subject_type, operation.subject_id),
                "Financial relations must keep their economic subject and scope.",
            )
            if operation.relation_kind == "REFUND_OF":
                _require(
                    related.kind in COLLECTION_KINDS
                    or (
                        related.kind == OperationKind.OPENING_OBLIGATION
                        and related.opening_obligation_kind == ObligationKind.CUSTOMER_ADVANCE
                    ),
                    "Refund anchor must be a collection or an explicit opening advance.",
                )
            if operation.relation_kind == "SETTLEMENT_OF":
                _require(
                    related.kind == OperationKind.OPENING_OBLIGATION
                    and related.opening_obligation_kind == ObligationKind.RECEIVABLE,
                    "An opening settlement must refer to an explicit opening balance.",
                )
            if operation.relation_kind == "REVERSAL_OF":
                _require(
                    related.kind
                    not in {OperationKind.TECHNICAL_REVERSAL, OperationKind.OPENING_OBLIGATION},
                    "A reversal cannot reverse another reversal or a noncash opening balance.",
                )
        if operation.kind == OperationKind.TECHNICAL_REVERSAL:
            reversal_source = entry_map.get(operation.source_id)
            _require(
                reversal_source is not None
                and reversal_source.state == EntryState.CONFIRMED
                and reversal_source.reverses_entry_id is None
                and reversal_source.financial_operation_id == operation.related_operation_id
                and reversal_source.amount == operation.amount_due,
                "A reversal operation requires its exact confirmed source entry.",
            )
    allocated: dict[UUID, Decimal] = defaultdict(lambda: ZERO)
    legs: set[tuple[UUID, str]] = set()
    reversals: set[UUID] = set()
    for entry in entries:
        entry_operation = operation_map.get(entry.financial_operation_id)
        _require(entry_operation is not None, "An entry's operation is missing from the graph.")
        assert entry_operation is not None
        operation = entry_operation
        validate_entry(operation, entry)
        leg = (operation.id, entry.leg_key)
        _require(leg not in legs, "Duplicate method leg key.")
        legs.add(leg)
        if entry.state not in {EntryState.REJECTED, EntryState.CANCELLED}:
            allocated[operation.id] += entry.amount
        if entry.reverses_entry_id is not None:
            original = entry_map.get(entry.reverses_entry_id)
            _require(original is not None, "The compensated entry is missing.")
            assert original is not None
            _require(
                entry.reverses_entry_id not in reversals, "An entry can be reversed only once."
            )
            reversals.add(entry.reverses_entry_id)
            _require(
                original.state == EntryState.CONFIRMED
                and original.reverses_entry_id is None
                and original.id == operation.source_id
                and original.financial_operation_id == operation.related_operation_id
                and original.branch_id == entry.branch_id
                and original.currency_code == entry.currency_code
                and original.payment_method_code == entry.payment_method_code
                and original.direction != entry.direction
                and original.amount == entry.amount == operation.amount_due,
                "A technical reversal must exactly compensate its confirmed original.",
            )
    for operation in operations:
        _require(
            allocated[operation.id] <= operation.amount_due,
            "Active method legs exceed the admitted amount.",
        )


def derive_payment_method(entries: Sequence[FinancialEntrySnapshot]) -> str | None:
    methods = {
        entry.payment_method_code.value
        for entry in entries
        if entry.state == EntryState.CONFIRMED and entry.amount > ZERO
    }
    _require(methods <= {"CASH", "CARD"}, "Unknown payment method.")
    return "MIXED" if len(methods) > 1 else next(iter(methods), None)


@financial_calculation
def summarize_operation(
    operation: FinancialOperationSnapshot,
    entries: Sequence[FinancialEntrySnapshot],
    all_entries: Sequence[FinancialEntrySnapshot] = (),
) -> OperationSummary:
    """Summarize validated facts; validate_ledger checks the complete causal graph first."""
    validate_operation(operation)
    for entry in entries:
        validate_entry(operation, entry)
    _require(len({entry.id for entry in entries}) == len(entries), "Duplicate entry identity.")
    _require(len({entry.leg_key for entry in entries}) == len(entries), "Duplicate method leg key.")
    confirmed = sum(
        (entry.amount for entry in entries if entry.state == EntryState.CONFIRMED), ZERO
    )
    allocated = sum(
        (
            entry.amount
            for entry in entries
            if entry.state not in {EntryState.REJECTED, EntryState.CANCELLED}
        ),
        ZERO,
    )
    _require(allocated <= operation.amount_due, "Active method legs exceed the admitted amount.")
    confirmed_entries = {
        entry.id: entry for entry in entries if entry.state == EntryState.CONFIRMED
    }
    compensations = [
        entry
        for entry in all_entries
        if entry.state == EntryState.CONFIRMED and entry.reverses_entry_id in confirmed_entries
    ]
    _require(
        len({entry.id for entry in compensations}) == len(compensations)
        and len({entry.reverses_entry_id for entry in compensations}) == len(compensations),
        "A summary cannot count duplicate compensations.",
    )
    for compensation in compensations:
        assert compensation.reverses_entry_id is not None
        original = confirmed_entries[compensation.reverses_entry_id]
        _require(
            compensation.id != original.id
            and compensation.financial_operation_id != original.financial_operation_id
            and original.reverses_entry_id is None
            and compensation.branch_id == original.branch_id
            and compensation.currency_code == original.currency_code
            and compensation.payment_method_code == original.payment_method_code
            and compensation.amount == original.amount
            and compensation.direction
            == (Direction.OUT if original.direction == Direction.IN else Direction.IN),
            "A summary requires exact compensation pairs from a validated causal graph.",
        )
    reversed_amount = sum((entry.amount for entry in compensations), ZERO)
    _require(reversed_amount <= confirmed, "Compensations exceed confirmed facts.")
    states = {entry.state for entry in entries}
    pending = operation.amount_due - confirmed
    if operation.kind == OperationKind.OPENING_OBLIGATION:
        state = OperationState.OPENING_RECORDED
        pending = ZERO
    elif EntryState.UNKNOWN in states:
        state = OperationState.UNKNOWN
    elif EntryState.PROCESSING in states:
        state = OperationState.PROCESSING
    elif reversed_amount > ZERO:
        state = (
            OperationState.REVERSED
            if reversed_amount == confirmed and confirmed == operation.amount_due
            else OperationState.PARTIALLY_REVERSED
        )
    elif confirmed == operation.amount_due:
        state = OperationState.COMPLETED
    elif confirmed > ZERO:
        state = OperationState.PARTIALLY_SETTLED
    elif states == {EntryState.REJECTED}:
        state = OperationState.REJECTED
    elif states == {EntryState.CANCELLED}:
        state = OperationState.CANCELLED
    else:
        state = OperationState.PENDING
    return OperationSummary(
        operation_id=operation.id,
        amount_due=operation.amount_due,
        confirmed_amount=confirmed,
        reversed_amount=reversed_amount,
        net_amount=confirmed - reversed_amount,
        pending_amount=pending,
        unassigned_amount=(
            ZERO
            if operation.kind == OperationKind.OPENING_OBLIGATION
            else operation.amount_due - allocated
        ),
        state=state,
        payment_method=derive_payment_method(entries),
    )


@financial_calculation
def project_cash_session(
    branch_id: UUID,
    cash_session_id: UUID,
    operations: Sequence[FinancialOperationSnapshot],
    entries: Sequence[FinancialEntrySnapshot],
) -> CashProjection:
    validate_ledger(operations, entries)
    _require(
        all(operation.branch_id == branch_id for operation in operations),
        "A cash projection requires one authorized branch graph.",
    )
    opening_operations = [
        operation
        for operation in operations
        if operation.kind == OperationKind.CASH_OPENING
        and operation.cash_session_id == cash_session_id
    ]
    _require(len(opening_operations) == 1, "Cash projection requires an explicit opening.")
    opening = opening_operations[0]
    by_operation: dict[UUID, list[FinancialEntrySnapshot]] = defaultdict(list)
    for entry in entries:
        by_operation[entry.financial_operation_id].append(entry)
    opening_summary = summarize_operation(opening, by_operation[opening.id])
    _require(opening_summary.pending_amount == ZERO, "Opening cash is not fully confirmed.")
    confirmed = [
        entry
        for entry in entries
        if entry.cash_session_id == cash_session_id
        and entry.payment_method_code == PaymentMethod.CASH
        and entry.state == EntryState.CONFIRMED
    ]
    cash_in = sum(
        (
            entry.amount
            for entry in confirmed
            if entry.direction == Direction.IN and entry.financial_operation_id != opening.id
        ),
        ZERO,
    )
    cash_out = sum((entry.amount for entry in confirmed if entry.direction == Direction.OUT), ZERO)
    unresolved = {
        entry.financial_operation_id
        for entry in entries
        if entry.cash_session_id == cash_session_id and entry.state in PENDING_STATES
    }
    unresolved.update(
        operation.id
        for operation in operations
        if operation.cash_session_id == cash_session_id
        and summarize_operation(operation, by_operation[operation.id]).pending_amount > ZERO
    )
    return CashProjection(
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        currency_code=opening.currency_code,
        opening_amount=opening_summary.confirmed_amount,
        cash_in=cash_in,
        cash_out=cash_out,
        expected_cash=opening_summary.confirmed_amount + cash_in - cash_out,
        confirmed_entry_ids=tuple(sorted((entry.id for entry in confirmed), key=str)),
        unresolved_operation_ids=tuple(sorted(unresolved, key=str)),
    )


@financial_calculation
def allocate_refund(
    amount_due: Decimal, expected_cash: Decimal, eligible_card_amount: Decimal
) -> RefundAllocation:
    """Plan CASH_FIRST; caller supplies verified remaining original card eligibility.

    This is an allocation, not proof of payment or provider authorization. The unallocated
    remainder stays pending, and commands must reserve eligibility under their subject lock.
    """
    amount_due = require_money(amount_due)
    _require(quantize_money(expected_cash) == expected_cash, "Expected cash must use cents.")
    eligible_card_amount = require_money(eligible_card_amount)
    cash = min(amount_due, max(expected_cash, ZERO))
    card = min(amount_due - cash, eligible_card_amount)
    return RefundAllocation(
        amount_due=amount_due,
        cash_amount=cash,
        card_amount=card,
        pending_amount=amount_due - cash - card,
    )
