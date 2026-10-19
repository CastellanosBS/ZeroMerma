"""Canonical monetary facts preserve amount, causal identity and cash conservation."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from typing import cast
from uuid import UUID, uuid4

import pytest

from zeromerma_api.modules.financial_ledger.domain.constants import (
    Direction,
    EntryState,
    EvidenceKind,
    ExecutionMode,
    ObligationKind,
    OperationKind,
    OperationState,
    PaymentMethod,
)
from zeromerma_api.modules.financial_ledger.domain.models import (
    FinancialEntrySnapshot,
    FinancialOperationSnapshot,
)
from zeromerma_api.modules.financial_ledger.domain.money import (
    MAX_AMOUNT,
    ZERO,
    FinancialModelError,
    quantize_money,
    require_currency,
    require_money,
)
from zeromerma_api.modules.financial_ledger.domain.rules import (
    allocate_refund,
    derive_payment_method,
    project_cash_session,
    summarize_operation,
    validate_ledger,
)

BRANCH = uuid4()
SHIFT = uuid4()
NOW = datetime(2026, 10, 19, 12, tzinfo=UTC)


def _operation(
    kind: OperationKind = OperationKind.SALE_COLLECTION,
    amount: str = "100.00",
    *,
    source_id: UUID | None = None,
    subject_id: UUID | None = None,
    cash_session_id: UUID = SHIFT,
) -> FinancialOperationSnapshot:
    source, subject = {
        OperationKind.CASH_OPENING: ("CASH_SESSION", "CASH_SESSION"),
        OperationKind.SALE_COLLECTION: ("SALE", "SALE"),
        OperationKind.ORDER_ADVANCE: ("ORDER_PAYMENT", "ORDER"),
        OperationKind.ORDER_SETTLEMENT: ("ORDER_PAYMENT", "ORDER"),
        OperationKind.SALE_REFUND: ("SALE_RETURN", "SALE"),
        OperationKind.OPERATIONAL_PAYMENT: ("OPERATIONAL_PAYMENT", "OPERATIONAL_PAYMENT"),
        OperationKind.OPERATIONAL_CHARGE: ("OPERATIONAL_DISCOUNT", "OPERATIONAL_DISCOUNT"),
    }[kind]
    if kind == OperationKind.CASH_OPENING:
        source_id = subject_id = cash_session_id
    source_id = source_id or uuid4()
    return FinancialOperationSnapshot(
        id=uuid4(),
        kind=kind,
        source_type=source,
        source_id=source_id,
        effect_code=kind.value,
        subject_type=subject,
        subject_id=subject_id or (source_id if source == subject else uuid4()),
        amount_due=Decimal(amount),
        branch_id=BRANCH,
        cash_session_id=cash_session_id,
    )


def _entry(
    operation: FinancialOperationSnapshot,
    amount: str,
    *,
    method: PaymentMethod = PaymentMethod.CASH,
    direction: Direction = Direction.IN,
    state: EntryState = EntryState.CONFIRMED,
    leg_key: str | None = None,
) -> FinancialEntrySnapshot:
    confirmed = state == EntryState.CONFIRMED
    cash = method == PaymentMethod.CASH
    return FinancialEntrySnapshot(
        id=uuid4(),
        financial_operation_id=operation.id,
        leg_key=leg_key or str(uuid4()),
        payment_method_code=method,
        direction=direction,
        amount=Decimal(amount),
        state=state,
        branch_id=operation.branch_id,
        currency_code=operation.currency_code,
        cash_session_id=operation.cash_session_id,
        tendered_amount=Decimal(amount) if cash and direction == Direction.IN else None,
        execution_mode=ExecutionMode.LOCAL if cash else ExecutionMode.ACCOUNTING_ONLY,
        confirmed_at=NOW if confirmed else None,
        resolution_kind=(EvidenceKind.LOCAL_CASH if cash else EvidenceKind.EXTERNAL_RECORDING)
        if confirmed
        else None,
        resolution_reference=uuid4() if confirmed and not cash else None,
    )


def _opening(
    amount: str = "100.00",
) -> tuple[FinancialOperationSnapshot, list[FinancialEntrySnapshot]]:
    operation = _operation(OperationKind.CASH_OPENING, amount)
    return operation, [_entry(operation, amount)] if Decimal(amount) else []


def _reversal(
    operation: FinancialOperationSnapshot, original: FinancialEntrySnapshot
) -> tuple[FinancialOperationSnapshot, FinancialEntrySnapshot]:
    reversal = replace(
        operation,
        id=uuid4(),
        kind=OperationKind.TECHNICAL_REVERSAL,
        source_type="FINANCIAL_ENTRY",
        source_id=original.id,
        effect_code=OperationKind.TECHNICAL_REVERSAL.value,
        amount_due=original.amount,
        related_operation_id=operation.id,
        relation_kind="REVERSAL_OF",
    )
    entry = replace(
        _entry(
            reversal,
            str(original.amount),
            method=original.payment_method_code,
            direction=Direction.OUT if original.direction == Direction.IN else Direction.IN,
        ),
        reverses_entry_id=original.id,
    )
    return reversal, entry


@pytest.mark.parametrize("value", [0.1, 1, "1.00", None, True])
def test_money_rejects_non_decimal_input(value: object) -> None:
    with pytest.raises(FinancialModelError):
        require_money(cast(Decimal, value))


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity"])
def test_money_rejects_non_finite_values(value: str) -> None:
    with pytest.raises(FinancialModelError):
        require_money(Decimal(value))


def test_persisted_money_requires_cents_without_silent_rounding() -> None:
    assert require_money(Decimal("1.2300")) == Decimal("1.23")
    assert require_money(ZERO) == ZERO
    with pytest.raises(FinancialModelError):
        require_money(Decimal("1.001"))
    with pytest.raises(FinancialModelError):
        require_money(ZERO, positive=True)
    with pytest.raises(FinancialModelError):
        require_money(Decimal("-0.01"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1.005", "1.01"), ("1.004", "1.00"), ("-1.005", "-1.01")],
)
def test_calculation_rounds_explicitly_half_up(value: str, expected: str) -> None:
    assert quantize_money(Decimal(value)) == Decimal(expected)


def test_money_precision_and_range_are_independent_of_the_ambient_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 2
        assert require_money(MAX_AMOUNT) == MAX_AMOUNT
        assert quantize_money(Decimal("123456.785")) == Decimal("123456.79")
    with pytest.raises(FinancialModelError):
        require_money(Decimal("10000000000.00"))


@pytest.mark.parametrize("currency", ["USD", "mxn", "MXN ", ""])
def test_currency_has_no_implicit_fx_or_normalization(currency: str) -> None:
    require_currency("MXN")
    with pytest.raises(FinancialModelError):
        require_currency(currency)


def test_zero_opening_is_explicit_without_a_fabricated_zero_leg() -> None:
    opening, entries = _opening("0.00")
    projection = project_cash_session(BRANCH, SHIFT, [opening], entries)
    assert projection.opening_amount == projection.expected_cash == ZERO
    assert projection.confirmed_entry_ids == ()
    assert summarize_operation(opening, []).state == OperationState.COMPLETED
    with pytest.raises(FinancialModelError):
        project_cash_session(BRANCH, SHIFT, [], [])
    with pytest.raises(FinancialModelError):
        validate_ledger([opening], [_entry(opening, "0.00")])


def test_mixed_sale_counts_cash_applied_once_and_preserves_tendered_and_change() -> None:
    opening, opening_entries = _opening()
    sale = _operation()
    cash = replace(
        _entry(sale, "40.00"), tendered_amount=Decimal("50.00"), change_amount=Decimal("10.00")
    )
    card = _entry(sale, "60.00", method=PaymentMethod.CARD)
    summary = summarize_operation(sale, [cash, card])
    projection = project_cash_session(
        BRANCH, SHIFT, [opening, sale], [*opening_entries, cash, card]
    )
    assert summary.state == OperationState.COMPLETED
    assert summary.payment_method == "MIXED"
    assert summary.confirmed_amount == Decimal("100.00")
    assert summary.pending_amount == summary.unassigned_amount == ZERO
    assert projection.cash_in == Decimal("40.00")
    assert projection.cash_out == ZERO
    assert projection.expected_cash == Decimal("140.00")
    assert projection.variance(Decimal("138.00")) == Decimal("-2.00")
    assert set(projection.confirmed_entry_ids) == {opening_entries[0].id, cash.id}
    assert cash.tendered_amount == Decimal("50.00") and cash.change_amount == Decimal("10.00")


def test_same_method_legs_do_not_make_a_mixed_payment_and_unconfirmed_card_is_excluded() -> None:
    operation = _operation()
    cash = [_entry(operation, "30.00"), _entry(operation, "40.00")]
    pending = _entry(operation, "30.00", method=PaymentMethod.CARD, state=EntryState.PENDING)
    validate_ledger([operation], [*cash, pending])
    assert derive_payment_method(cash) == "CASH"
    assert derive_payment_method([*cash, pending]) == "CASH"
    assert derive_payment_method([pending]) is None
    assert derive_payment_method([]) is None


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (EntryState.PENDING, OperationState.PENDING),
        (EntryState.PROCESSING, OperationState.PROCESSING),
        (EntryState.UNKNOWN, OperationState.UNKNOWN),
    ],
)
def test_unresolved_card_never_increases_cash_or_claims_settlement(
    state: EntryState, expected: OperationState
) -> None:
    opening, opening_entries = _opening()
    sale = _operation()
    card = _entry(sale, "100.00", method=PaymentMethod.CARD, state=state)
    summary = summarize_operation(sale, [card])
    projection = project_cash_session(BRANCH, SHIFT, [opening, sale], [*opening_entries, card])
    assert summary.state == expected
    assert summary.confirmed_amount == ZERO and summary.pending_amount == Decimal("100.00")
    assert summary.unassigned_amount == ZERO
    assert projection.expected_cash == Decimal("100.00")
    assert projection.unresolved_operation_ids == (sale.id,)


@pytest.mark.parametrize("state", [EntryState.REJECTED, EntryState.CANCELLED])
def test_rejected_or_cancelled_leg_leaves_room_for_a_new_attempt_without_extra_money(
    state: EntryState,
) -> None:
    sale = _operation()
    failed = _entry(sale, "100.00", method=PaymentMethod.CARD, state=state)
    cash = _entry(sale, "100.00")
    validate_ledger([sale], [failed, cash])
    summary = summarize_operation(sale, [failed, cash])
    assert summary.confirmed_amount == Decimal("100.00")
    assert summary.state == OperationState.COMPLETED
    assert summary.payment_method == "CASH"


@pytest.mark.parametrize(
    ("due", "cash", "eligible_card", "expected"),
    [
        ("500.00", "300.00", "200.00", ("300.00", "200.00", "0.00")),
        ("100.00", "40.00", "0.00", ("40.00", "0.00", "60.00")),
        ("80.00", "100.00", "60.00", ("80.00", "0.00", "0.00")),
        ("100.00", "-10.00", "30.00", ("0.00", "30.00", "70.00")),
        ("0.00", "0.00", "0.00", ("0.00", "0.00", "0.00")),
    ],
)
def test_refund_allocation_is_cash_first_bounded_and_preserves_unfunded_remainder(
    due: str, cash: str, eligible_card: str, expected: tuple[str, str, str]
) -> None:
    allocation = allocate_refund(Decimal(due), Decimal(cash), Decimal(eligible_card))
    assert (allocation.cash_amount, allocation.card_amount, allocation.pending_amount) == tuple(
        map(Decimal, expected)
    )
    assert allocation.cash_amount + allocation.card_amount + allocation.pending_amount == Decimal(
        due
    )


def test_partially_settled_refund_retains_its_unassigned_claim_and_actual_method() -> None:
    opening, opening_entries = _opening("40.00")
    sale = _operation()
    original_card = _entry(sale, "100.00", method=PaymentMethod.CARD)
    refund = replace(
        _operation(OperationKind.SALE_REFUND),
        subject_id=sale.subject_id,
        related_operation_id=sale.id,
        relation_kind="REFUND_OF",
    )
    cash = _entry(refund, "40.00", direction=Direction.OUT)
    summary = summarize_operation(refund, [cash])
    projection = project_cash_session(
        BRANCH, SHIFT, [opening, sale, refund], [*opening_entries, original_card, cash]
    )
    assert summary.state == OperationState.PARTIALLY_SETTLED
    assert summary.confirmed_amount == Decimal("40.00")
    assert summary.pending_amount == summary.unassigned_amount == Decimal("60.00")
    assert summary.payment_method == "CASH"
    assert projection.expected_cash == ZERO
    assert projection.unresolved_operation_ids == (refund.id,)


@pytest.mark.parametrize(
    ("entry_state", "summary_state"),
    [
        (EntryState.PROCESSING, OperationState.PROCESSING),
        (EntryState.UNKNOWN, OperationState.UNKNOWN),
    ],
)
def test_refund_external_remainder_keeps_its_identity_without_claiming_full_settlement(
    entry_state: EntryState, summary_state: OperationState
) -> None:
    opening, opening_entries = _opening("300.00")
    collection = _operation(amount="500.00")
    original = _entry(collection, "500.00", method=PaymentMethod.CARD)
    refund = replace(
        _operation(OperationKind.SALE_REFUND, "500.00"),
        subject_id=collection.subject_id,
        related_operation_id=collection.id,
        relation_kind="REFUND_OF",
    )
    paid = _entry(refund, "300.00", direction=Direction.OUT)
    pending = replace(
        _entry(
            refund,
            "200.00",
            method=PaymentMethod.CARD,
            direction=Direction.OUT,
            state=entry_state,
        ),
        execution_mode=ExecutionMode.PROVIDER_INTEGRATED,
    )
    operations = [opening, collection, refund]
    entries = [*opening_entries, original, paid, pending]
    summary = summarize_operation(refund, [paid, pending])
    projection = project_cash_session(BRANCH, SHIFT, operations, entries)
    assert summary.state == summary_state
    assert summary.confirmed_amount == Decimal("300.00")
    assert summary.pending_amount == Decimal("200.00")
    assert summary.unassigned_amount == ZERO
    assert summary.payment_method == "CASH"
    assert projection.expected_cash == ZERO
    assert pending.id not in projection.confirmed_entry_ids
    assert projection.unresolved_operation_ids == (refund.id,)
    with pytest.raises(FinancialModelError):
        validate_ledger(operations, [*entries, _entry(refund, "200.00", direction=Direction.OUT)])


@pytest.mark.parametrize("kind", list(ObligationKind))
def test_opening_obligations_preserve_evidence_without_adding_cash(kind: ObligationKind) -> None:
    opening, entries = _opening()
    obligation = FinancialOperationSnapshot(
        id=uuid4(),
        kind=OperationKind.OPENING_OBLIGATION,
        source_type="OPENING_STATE",
        source_id=uuid4(),
        effect_code=OperationKind.OPENING_OBLIGATION.value,
        subject_type="ORDER" if kind == ObligationKind.CUSTOMER_ADVANCE else "OPENING_BALANCE",
        subject_id=uuid4(),
        amount_due=Decimal("500.00"),
        branch_id=BRANCH,
        opening_obligation_kind=kind,
        opening_reason_code="VERIFIED_CUTOVER",
        source_evidence_reference=uuid4(),
        cutover_at=NOW,
    )
    summary = summarize_operation(obligation, [])
    projection = project_cash_session(BRANCH, SHIFT, [opening, obligation], entries)
    assert summary.state == OperationState.OPENING_RECORDED
    assert summary.confirmed_amount == summary.pending_amount == summary.unassigned_amount == ZERO
    assert projection.expected_cash == Decimal("100.00")
    with pytest.raises(FinancialModelError):
        validate_ledger(
            [obligation], [replace(_entry(obligation, "500.00"), cash_session_id=SHIFT)]
        )
    with pytest.raises(FinancialModelError):
        validate_ledger([replace(obligation, source_evidence_reference=None)], [])


def test_reversal_compensates_original_without_mutating_or_hiding_it() -> None:
    opening, opening_entries = _opening()
    sale = _operation()
    original = _entry(sale, "100.00")
    reversal, compensation = _reversal(sale, original)
    entries = [*opening_entries, original, compensation]
    projection = project_cash_session(BRANCH, SHIFT, [opening, sale, reversal], entries)
    summary = summarize_operation(sale, [original], entries)
    assert summary.confirmed_amount == summary.reversed_amount == Decimal("100.00")
    assert summary.net_amount == ZERO and summary.state == OperationState.REVERSED
    assert projection.cash_in == projection.cash_out == Decimal("100.00")
    assert projection.expected_cash == Decimal("100.00")
    assert original.state == EntryState.CONFIRMED and original.amount == Decimal("100.00")
    with pytest.raises(FrozenInstanceError):
        original.amount = ZERO  # type: ignore[misc]
    with pytest.raises(FinancialModelError):
        validate_ledger(
            [sale, reversal], [original, replace(compensation, amount=Decimal("99.00"))]
        )
    with pytest.raises(FinancialModelError):
        validate_ledger(
            [sale, reversal],
            [
                original,
                compensation,
                replace(compensation, id=uuid4(), leg_key="duplicate-reversal"),
            ],
        )


def test_multiple_order_payments_share_subject_but_have_distinct_causal_effects_and_sessions() -> (
    None
):
    later_shift, order_id = uuid4(), uuid4()
    opening, entries = _opening()
    advance = _operation(OperationKind.ORDER_ADVANCE, "50.00", subject_id=order_id)
    settlement = _operation(
        OperationKind.ORDER_SETTLEMENT, "50.00", subject_id=order_id, cash_session_id=later_shift
    )
    first = _entry(advance, "50.00")
    second = _entry(settlement, "50.00")
    projection = project_cash_session(
        BRANCH, SHIFT, [opening, advance, settlement], [*entries, first, second]
    )
    assert projection.expected_cash == Decimal("150.00")
    assert second.id not in projection.confirmed_entry_ids
    assert summarize_operation(settlement, [second]).confirmed_amount == Decimal("50.00")
    with pytest.raises(FinancialModelError):
        validate_ledger([advance, replace(advance, id=uuid4())], [])


def test_operational_charge_and_payment_have_opposite_cash_effects() -> None:
    opening, entries = _opening()
    charge = _operation(OperationKind.OPERATIONAL_CHARGE, "12.00")
    payment = _operation(OperationKind.OPERATIONAL_PAYMENT, "7.00")
    projection = project_cash_session(
        BRANCH,
        SHIFT,
        [opening, charge, payment],
        [*entries, _entry(charge, "12.00"), _entry(payment, "7.00", direction=Direction.OUT)],
    )
    assert projection.cash_in == Decimal("12.00") and projection.cash_out == Decimal("7.00")
    assert projection.expected_cash == Decimal("105.00")


@pytest.mark.parametrize(
    "problem",
    [
        "mixed",
        "card-change",
        "cash-change",
        "foreign-branch",
        "foreign-currency",
        "over-allocation",
        "unproved-confirmation",
    ],
)
def test_invalid_method_scope_or_conservation_cannot_enter_the_ledger(problem: str) -> None:
    sale = _operation()
    entry = _entry(sale, "100.00")
    if problem == "mixed":
        entry = replace(entry, payment_method_code=cast(PaymentMethod, "MIXED"))
    elif problem == "card-change":
        entry = replace(
            _entry(sale, "100.00", method=PaymentMethod.CARD), change_amount=Decimal("1.00")
        )
    elif problem == "cash-change":
        entry = replace(entry, tendered_amount=Decimal("105.00"))
    elif problem == "foreign-branch":
        entry = replace(entry, branch_id=uuid4())
    elif problem == "foreign-currency":
        entry = replace(entry, currency_code="USD")
    elif problem == "over-allocation":
        entry = replace(entry, amount=Decimal("101.00"), tendered_amount=Decimal("101.00"))
    else:
        entry = replace(entry, resolution_kind=None)
    with pytest.raises(FinancialModelError):
        validate_ledger([sale], [entry])


def test_cash_projection_rejects_missing_incomplete_duplicate_or_foreign_opening() -> None:
    opening, entries = _opening()
    with pytest.raises(FinancialModelError):
        project_cash_session(BRANCH, SHIFT, [opening], [])
    with pytest.raises(FinancialModelError):
        project_cash_session(BRANCH, SHIFT, [opening, replace(opening, id=uuid4())], entries)
    with pytest.raises(FinancialModelError):
        project_cash_session(uuid4(), SHIFT, [opening], entries)


def test_refund_and_projection_calculations_preserve_cents_under_small_decimal_precision() -> None:
    opening, entries = _opening("123456.78")
    sale = _operation(amount="12.34")
    with localcontext() as context:
        context.prec = 2
        projection = project_cash_session(
            BRANCH, SHIFT, [opening, sale], [*entries, _entry(sale, "12.34")]
        )
        assert projection.expected_cash == Decimal("123469.12")
        assert projection.variance(Decimal("123469.10")) == Decimal("-0.02")
        allocation = allocate_refund(Decimal("1234.56"), Decimal("300.01"), Decimal("100.02"))
        assert allocation.pending_amount == Decimal("834.53")


@pytest.mark.parametrize("problem", ["missing_source", "wrong_parent", "unconfirmed", "amount"])
def test_reversal_admission_validates_its_original_before_a_compensating_leg_exists(
    problem: str,
) -> None:
    sale = _operation()
    original = _entry(sale, "100.00")
    reversal, _ = _reversal(sale, original)
    operations = [sale, reversal]
    entries = [original]
    if problem == "missing_source":
        operations[1] = replace(reversal, source_id=uuid4())
    elif problem == "wrong_parent":
        other_sale = _operation()
        other_entry = _entry(other_sale, "100.00")
        operations.append(other_sale)
        entries.append(other_entry)
        operations[1] = replace(reversal, source_id=other_entry.id)
    elif problem == "unconfirmed":
        entries[0] = replace(
            original,
            state=EntryState.PENDING,
            confirmed_at=None,
            resolution_kind=None,
        )
    else:
        operations[1] = replace(reversal, amount_due=Decimal("50.00"))

    with pytest.raises(FinancialModelError):
        validate_ledger(operations, entries)


@pytest.mark.parametrize("problem", ["direction", "amount", "method", "duplicate"])
def test_summary_never_counts_an_invalid_compensation_pair(problem: str) -> None:
    sale = _operation()
    original = _entry(sale, "40.00")
    second_leg = _entry(sale, "60.00")
    reversal, compensation = _reversal(sale, original)
    validate_ledger([sale, reversal], [original, second_leg, compensation])
    valid = summarize_operation(sale, [original, second_leg], [compensation])
    assert valid.reversed_amount == Decimal("40.00")
    assert valid.net_amount == Decimal("60.00")
    assert valid.state == OperationState.PARTIALLY_REVERSED

    compensations = [compensation]
    if problem == "direction":
        compensations[0] = replace(
            compensation, direction=Direction.IN, tendered_amount=compensation.amount
        )
    elif problem == "amount":
        compensations[0] = replace(compensation, amount=Decimal("20.00"))
    elif problem == "method":
        compensations[0] = replace(
            compensation,
            payment_method_code=PaymentMethod.CARD,
            execution_mode=ExecutionMode.ACCOUNTING_ONLY,
            resolution_kind=EvidenceKind.EXTERNAL_RECORDING,
            resolution_reference=uuid4(),
        )
    else:
        compensations.append(replace(compensation, id=uuid4(), leg_key="duplicate-compensation"))

    with pytest.raises(FinancialModelError):
        summarize_operation(sale, [original, second_leg], compensations)


def test_compensation_does_not_hide_an_unresolved_leg_in_the_same_operation() -> None:
    sale = _operation()
    cash = _entry(sale, "40.00")
    unknown_card = _entry(sale, "60.00", method=PaymentMethod.CARD, state=EntryState.UNKNOWN)
    reversal, compensation = _reversal(sale, cash)
    validate_ledger([sale, reversal], [cash, unknown_card, compensation])

    summary = summarize_operation(sale, [cash, unknown_card], [compensation])

    assert summary.state == OperationState.UNKNOWN
    assert summary.pending_amount == Decimal("60.00")
    assert summary.reversed_amount == Decimal("40.00")
    assert summary.net_amount == ZERO
    assert summary.unassigned_amount == ZERO
