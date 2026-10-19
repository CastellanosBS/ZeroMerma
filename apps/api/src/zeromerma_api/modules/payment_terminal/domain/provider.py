"""Provider evidence is trusted only after the concrete adapter authenticates it.

No BBVA protocol or production adapter is assumed. Test doubles are injected by tests.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from zeromerma_api.modules.financial_ledger.domain.money import require_money
from zeromerma_api.modules.idempotency.domain.exceptions import IdempotencyError


class TerminalError(IdempotencyError):
    def __init__(self, code: str, message: str, status: int = 409) -> None:
        super().__init__(code, status, message)


class ProviderState(StrEnum):
    PROCESSING = "PROCESSING"
    AUTHORIZED = "AUTHORIZED"
    UNKNOWN = "UNKNOWN"
    CAPTURED = "CAPTURED"
    REFUNDED = "REFUNDED"
    DECLINED = "DECLINED"
    FAILED = "FAILED"


TERMINAL_STATES = frozenset({"CAPTURED", "REFUNDED", "DECLINED", "FAILED"})


def opaque_reference(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,119}", value):
        raise TerminalError("EXTERNAL_PAYMENT_EVIDENCE_INVALID", "Invalid opaque reference.")
    return value


@dataclass(frozen=True, kw_only=True)
class ProviderReadiness:
    provider_code: str
    environment: str
    contract_evidence_id: UUID
    hardware_evidence_id: UUID
    certification_evidence_id: UUID

    def validate(self) -> None:
        opaque_reference(self.provider_code)
        if self.environment not in {"SANDBOX", "PRODUCTION"} or not all(
            value.int
            for value in (
                self.contract_evidence_id,
                self.hardware_evidence_id,
                self.certification_evidence_id,
            )
        ):
            raise TerminalError("EXTERNAL_PAYMENT_GATE_CLOSED", "Provider evidence is incomplete.")


@dataclass(frozen=True, kw_only=True)
class ProviderRequest:
    operation_id: UUID
    provider_idempotency_key: UUID
    operation_type: str
    account_reference: str
    terminal_reference: str
    amount: Decimal
    currency_code: str
    original_provider_operation_id: str | None = None


@dataclass(frozen=True, kw_only=True)
class ProviderEvidence:
    event_id: str
    provider_idempotency_key: UUID
    account_reference: str
    terminal_reference: str
    amount: Decimal
    currency_code: str
    state: ProviderState
    occurred_at: datetime
    provider_operation_id: str | None = None

    def validate_for(self, request: ProviderRequest) -> None:
        opaque_reference(self.event_id)
        if self.provider_operation_id is not None:
            opaque_reference(self.provider_operation_id)
        if (
            self.provider_idempotency_key != request.provider_idempotency_key
            or self.account_reference != request.account_reference
            or self.terminal_reference != request.terminal_reference
            or require_money(self.amount, positive=True) != request.amount
            or self.currency_code != request.currency_code
            or self.occurred_at.tzinfo is None
            or self.occurred_at.utcoffset() is None
        ):
            raise TerminalError(
                "EXTERNAL_PAYMENT_EVIDENCE_MISMATCH",
                "Provider evidence does not match the operation.",
            )
        success = "REFUNDED" if request.operation_type == "REFUND" else "CAPTURED"
        if self.state in {ProviderState.CAPTURED, ProviderState.REFUNDED} and (
            self.state != success or self.provider_operation_id is None
        ):
            raise TerminalError(
                "EXTERNAL_PAYMENT_EVIDENCE_MISMATCH", "Provider success evidence is incomplete."
            )


class ExternalPaymentProvider(Protocol):
    readiness: ProviderReadiness

    def execute(self, request: ProviderRequest) -> ProviderEvidence: ...

    def query(self, request: ProviderRequest) -> ProviderEvidence: ...

    def authenticate_callback(self, body: bytes, signature: str) -> ProviderEvidence: ...


def next_state(current: str, evidence: ProviderState) -> str:
    if current in TERMINAL_STATES:
        if current != evidence:
            raise TerminalError(
                "EXTERNAL_RECONCILIATION_DISCREPANCY",
                "Conflicting terminal evidence requires reconciliation.",
            )
        return current
    # Delayed processing cannot downgrade an already uncertain/authorized operation.
    if evidence == ProviderState.PROCESSING and current in {"UNKNOWN", "AUTHORIZED"}:
        return current
    return evidence.value
