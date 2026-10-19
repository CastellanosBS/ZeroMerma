from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from zeromerma_api.modules.payment_terminal.domain.provider import (
    ProviderEvidence,
    ProviderReadiness,
    ProviderRequest,
    ProviderState,
    TerminalError,
    next_state,
)


def request():
    return ProviderRequest(
        operation_id=uuid4(),
        provider_idempotency_key=uuid4(),
        operation_type="CAPTURE",
        account_reference="merchant-1",
        terminal_reference="terminal-1",
        amount=Decimal("12.34"),
        currency_code="MXN",
    )


def evidence(value):
    return ProviderEvidence(
        event_id="event-1",
        provider_idempotency_key=value.provider_idempotency_key,
        account_reference=value.account_reference,
        terminal_reference=value.terminal_reference,
        amount=value.amount,
        currency_code=value.currency_code,
        state=ProviderState.CAPTURED,
        occurred_at=datetime.now(UTC),
        provider_operation_id="capture-1",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": Decimal("12.35")},
        {"currency_code": "USD"},
        {"provider_idempotency_key": uuid4()},
        {"account_reference": "other"},
        {"terminal_reference": "other"},
        {"provider_operation_id": None},
        {"state": ProviderState.REFUNDED},
        {"occurred_at": datetime(2026, 1, 1)},
        {"event_id": "unsafe\nreference"},
    ],
)
def test_provider_evidence_must_match_exact_cause_and_verified_success(changes):
    value = request()
    with pytest.raises(TerminalError):
        replace(evidence(value), **changes).validate_for(value)


def test_capture_and_refund_evidence_are_distinct():
    value = request()
    evidence(value).validate_for(value)
    refund = replace(value, operation_type="REFUND", original_provider_operation_id="capture-1")
    replace(evidence(refund), state=ProviderState.REFUNDED).validate_for(refund)


@pytest.mark.parametrize(
    "current,state,expected",
    [
        ("PROCESSING", ProviderState.UNKNOWN, "UNKNOWN"),
        ("UNKNOWN", ProviderState.PROCESSING, "UNKNOWN"),
        ("AUTHORIZED", ProviderState.PROCESSING, "AUTHORIZED"),
        ("UNKNOWN", ProviderState.CAPTURED, "CAPTURED"),
        ("PROCESSING", ProviderState.AUTHORIZED, "AUTHORIZED"),
        ("CAPTURED", ProviderState.CAPTURED, "CAPTURED"),
    ],
)
def test_evidence_transitions_preserve_uncertainty_and_do_not_treat_authorization_as_capture(
    current, state, expected
):
    assert next_state(current, state) == expected


@pytest.mark.parametrize(
    "state", [ProviderState.DECLINED, ProviderState.UNKNOWN, ProviderState.REFUNDED]
)
def test_late_conflicting_evidence_cannot_rewrite_a_terminal_result(state):
    with pytest.raises(TerminalError, match="Conflicting terminal"):
        next_state("CAPTURED", state)


def test_provider_registration_requires_environment_and_all_approval_evidence():
    valid = ProviderReadiness(
        provider_code="BBVA",
        environment="SANDBOX",
        contract_evidence_id=uuid4(),
        hardware_evidence_id=uuid4(),
        certification_evidence_id=uuid4(),
    )
    valid.validate()
    for field in ("contract_evidence_id", "hardware_evidence_id", "certification_evidence_id"):
        with pytest.raises(TerminalError):
            replace(valid, **{field: UUID(int=0)}).validate()
    with pytest.raises(TerminalError):
        replace(valid, environment="production").validate()
