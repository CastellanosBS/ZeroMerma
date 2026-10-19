"""Explicit evidence for a clean physical opening or a deterministic projection rebuild."""

import json
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from zeromerma_api.modules.inventory.domain.constants import VALID_INVENTORY_LOCATION_CODES
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.quantities import exact_decimal, inventory_calculation


def evidence_digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class OpeningLot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    lot_code: str = Field(min_length=1, max_length=120)
    expires_at: AwareDatetime | None = None
    quantity: Decimal = Field(gt=0)

    @field_validator("quantity", mode="before")
    @classmethod
    def decimal_input(cls, value: object) -> object:
        if not isinstance(value, (str, Decimal)):
            raise ValueError("Inventory evidence requires exact decimal strings.")
        return value

    @model_validator(mode="after")
    def exact(self) -> Self:
        exact_decimal(self.quantity)
        return self


class InventoryReconciliationItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    row_key: str = Field(min_length=1, max_length=80)
    idempotency_key: UUID
    action: Literal["OPENING", "REBUILD"]
    product_id: UUID
    location_code: str
    unit_of_measure: str = Field(min_length=1, max_length=32)
    quantity: Decimal | None = None
    inventory_value: Decimal | None = None
    lots: tuple[OpeningLot, ...] = ()
    expected_ledger_sha256: str | None = Field(default=None, pattern="^[a-f0-9]{64}$")
    evidence_reference: str = Field(min_length=1, max_length=200)
    evidence_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    reason: str = Field(min_length=1, max_length=160)

    @field_validator("quantity", "inventory_value", mode="before")
    @classmethod
    def decimal_input(cls, value: object) -> object:
        if value is not None and not isinstance(value, (str, Decimal)):
            raise ValueError("Inventory evidence requires exact decimal strings.")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def command_key(cls, value: UUID) -> UUID:
        if value.version != 7:
            raise ValueError("Reconciliation commands require stable UUIDv7 keys.")
        return value

    @model_validator(mode="after")
    @inventory_calculation
    def coherent(self) -> Self:
        if self.location_code not in VALID_INVENTORY_LOCATION_CODES:
            raise ValueError("Unknown inventory location.")
        if self.action == "OPENING":
            if self.quantity is None or self.quantity < 0:
                raise ValueError("Opening requires a nonnegative validated physical count.")
            exact_decimal(self.quantity)
            if self.inventory_value is not None:
                exact_decimal(self.inventory_value, scale=8, precision=24)
                if self.inventory_value < 0 or (self.quantity == 0 and self.inventory_value != 0):
                    raise ValueError("Opening valuation does not reconcile with its quantity.")
            if self.expected_ledger_sha256 is not None:
                raise ValueError("An opening is a new explicit fact, not historical backfill.")
            if self.lots and sum((lot.quantity for lot in self.lots), Decimal(0)) != self.quantity:
                raise ValueError("Opening lot quantities must equal the physical count.")
            if len({lot.lot_code for lot in self.lots}) != len(self.lots):
                raise ValueError("Opening lot codes cannot repeat.")
        elif (
            self.expected_ledger_sha256 is None
            or self.quantity is not None
            or self.inventory_value is not None
            or self.lots
        ):
            raise ValueError("Rebuild requires its reviewed ledger hash and cannot invent stock.")
        return self

    def digest(self) -> str:
        return evidence_digest(self.model_dump(mode="json"))


class InventoryReconciliationManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    manifest_id: UUID
    branch_id: UUID
    source_id: str = Field(min_length=1, max_length=160)
    source_classification: Literal["REAL_OPERATIONAL", "DEVELOPMENT_DEMO_TEST", "UNKNOWN"]
    source_evidence_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    approval_reference: str = Field(min_length=1, max_length=200)
    approval_evidence_sha256: str = Field(pattern="^[a-f0-9]{64}$")
    controlled_window_reference: str = Field(min_length=1, max_length=200)
    cutover_at: AwareDatetime
    expected_row_count: int = Field(ge=1, le=1000)
    rows: tuple[InventoryReconciliationItem, ...] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_rows(self) -> Self:
        if len(self.rows) != self.expected_row_count:
            raise ValueError("The declared row count must match the manifest.")
        for values in (
            [row.row_key for row in self.rows],
            [row.idempotency_key for row in self.rows],
            [(row.product_id, row.location_code) for row in self.rows],
        ):
            if len(set(values)) != len(values):
                raise ValueError("Each row, idempotency key and inventory key must be unique.")
        return self

    def digest(self) -> str:
        return evidence_digest(self.model_dump(mode="json"))

    def require_productive_source(self) -> None:
        if self.source_classification != "REAL_OPERATIONAL" or self.source_id.strip().upper() in {
            "PG-ZM-CURRENT",
            "PG-ZM-LEGACY",
        }:
            raise InventoryValidationError(
                "Demo/test or unclassified stock is never opening authority."
            )

    def require_cutover(self, now: datetime) -> None:
        if self.cutover_at > now:
            raise InventoryValidationError("The approved physical cutover has not occurred yet.")
