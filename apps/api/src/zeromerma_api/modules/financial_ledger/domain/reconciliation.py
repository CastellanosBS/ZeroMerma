"""Evidence manifests describe authorized transformations, never synthetic history."""

from __future__ import annotations

from decimal import Decimal
from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import Direction, ObligationKind, OperationKind, PaymentMethod
from .money import ZERO, FinancialModelError, financial_calculation, require_money

KNOWN_DEMO_SOURCES = frozenset({"PG-ZM-CURRENT", "PG-ZM-LEGACY"})


class EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ImportLeg(EvidenceModel):
    leg_key: str = Field(min_length=1, max_length=40)
    payment_method: PaymentMethod
    direction: Direction
    amount: Decimal
    tendered_amount: Decimal | None = None
    change_amount: Decimal = ZERO
    external_recording_reference: UUID | None = None

    @field_validator("amount", "tendered_amount", "change_amount", mode="before")
    @classmethod
    def exact_money(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Money must be an exact decimal string.")
        return require_money(Decimal(value))


class ImportRow(EvidenceModel):
    row_key: str = Field(min_length=1, max_length=80)
    idempotency_key: UUID
    treatment: Literal[
        "OPENING_ADJUSTMENT", "BACKFILL", "MANUAL_RECONCILIATION", "ARCHIVE_READ_ONLY"
    ]
    kind: OperationKind
    source_type: str = Field(min_length=1, max_length=40)
    source_id: UUID
    subject_type: str = Field(min_length=1, max_length=32)
    subject_id: UUID
    amount_due: Decimal
    currency_code: Literal["MXN"] = "MXN"
    occurred_at: AwareDatetime
    workstation_id: UUID | None = None
    cash_session_id: UUID | None = None
    evidence_reference: UUID
    evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reason_code: str = Field(min_length=1, max_length=64)
    opening_obligation_kind: ObligationKind | None = None
    legs: tuple[ImportLeg, ...] = ()

    @field_validator("amount_due", mode="before")
    @classmethod
    def exact_amount(cls, value: object) -> Decimal:
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Money must be an exact decimal string.")
        return require_money(Decimal(value))

    @field_validator("idempotency_key")
    @classmethod
    def command_key(cls, value: UUID) -> UUID:
        if value.version != 7:
            raise ValueError("Import commands require stable UUIDv7 keys.")
        return value

    @model_validator(mode="after")
    @financial_calculation
    def coherent_evidence(self) -> ImportRow:
        if len({leg.leg_key for leg in self.legs}) != len(self.legs):
            raise ValueError("A row cannot repeat a financial leg.")
        if any(leg.amount <= ZERO for leg in self.legs):
            raise ValueError("Zero financial entries are prohibited.")
        if self.treatment == "OPENING_ADJUSTMENT":
            if self.source_type != "OPENING_STATE" or self.source_id != self.evidence_reference:
                raise ValueError("Opening state requires its own immutable evidence identity.")
            if self.kind not in {OperationKind.CASH_OPENING, OperationKind.OPENING_OBLIGATION}:
                raise ValueError("Opening state cannot fabricate historical transactions.")
            if self.kind == OperationKind.OPENING_OBLIGATION:
                if self.legs or self.cash_session_id or self.workstation_id:
                    raise ValueError("Opening obligations do not affect drawer cash.")
                if self.opening_obligation_kind is None or self.amount_due == ZERO:
                    raise ValueError(
                        "An opening obligation requires a positive classified balance."
                    )
        elif self.treatment == "BACKFILL":
            if self.source_type == "OPENING_STATE" or self.opening_obligation_kind:
                raise ValueError("Backfill requires an existing actual business cause.")
        if self.kind != OperationKind.OPENING_OBLIGATION and self.treatment in {
            "BACKFILL",
            "OPENING_ADJUSTMENT",
        }:
            if sum((leg.amount for leg in self.legs), ZERO) != self.amount_due:
                raise ValueError("Actual financial legs must reconcile to the source amount.")
        return self


class FinancialImportManifest(EvidenceModel):
    manifest_id: UUID
    branch_id: UUID
    source_id: str = Field(min_length=1, max_length=120)
    source_classification: Literal["REAL_OPERATIONAL", "DEVELOPMENT_DEMO_TEST", "UNKNOWN"]
    source_authority: Literal["closed_and_reconcilable_economic_evidence"]
    source_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    approval_reference: str = Field(min_length=1, max_length=160)
    approval_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    controlled_window_reference: str = Field(min_length=1, max_length=160)
    cutover_at: AwareDatetime
    expected_row_count: int = Field(ge=1, le=1000)
    expected_amount_due: Decimal
    rows: tuple[ImportRow, ...] = Field(min_length=1, max_length=1000)

    @field_validator("expected_amount_due", mode="before")
    @classmethod
    def exact_total(cls, value: object) -> Decimal:
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Manifest totals must be exact decimal strings.")
        return require_money(Decimal(value))

    @model_validator(mode="after")
    @financial_calculation
    def reconciled_manifest(self) -> FinancialImportManifest:
        if self.expected_row_count != len(self.rows):
            raise ValueError("Manifest row count does not reconcile.")
        if self.expected_amount_due != sum((row.amount_due for row in self.rows), ZERO):
            raise ValueError("Manifest total does not reconcile.")
        for field in ("row_key", "idempotency_key"):
            if len({getattr(row, field) for row in self.rows}) != len(self.rows):
                raise ValueError("Manifest row identity is duplicated.")
        if len({(row.source_type, row.source_id, row.kind) for row in self.rows}) != len(self.rows):
            raise ValueError("Manifest repeats an economic cause.")
        openings = [row for row in self.rows if row.kind == OperationKind.OPENING_OBLIGATION]
        if len(
            {(row.subject_type, row.subject_id, row.opening_obligation_kind) for row in openings}
        ) != len(openings):
            raise ValueError("Manifest repeats an opening obligation for the same subject.")
        for row in self.rows:
            if row.occurred_at > self.cutover_at:
                raise ValueError("Source evidence cannot postdate cutover.")
        return self

    def require_productive_source(self) -> None:
        if (
            self.source_classification != "REAL_OPERATIONAL"
            or self.source_id.upper() in KNOWN_DEMO_SOURCES
        ):
            raise FinancialModelError(
                "Demo/test or unclassified sources cannot become productive history."
            )

    def digest(self) -> str:
        return sha256(self.model_dump_json().encode("utf-8")).hexdigest()


def row_digest(row: ImportRow) -> str:
    return sha256(row.model_dump_json().encode("utf-8")).hexdigest()
