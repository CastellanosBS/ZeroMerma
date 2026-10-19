"""Backend-owned, bounded local device messages. They contain no financial authority."""

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zeromerma_api.modules.tickets.application.receipt_schemas import OperationalReceiptView


class DeviceCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    protocol_version: Literal[1] = 1
    id: UUID
    kind: Literal["PRINT", "OPEN_DRAWER"]
    branch_id: UUID
    workstation_id: UUID
    device_id: UUID
    binding_version: int = Field(ge=1)
    environment: Literal["SANDBOX", "PRODUCTION"]
    origin: str = Field(min_length=1, max_length=200)
    receipt: OperationalReceiptView | None = None
    cash_entry_id: UUID | None = None

    @model_validator(mode="after")
    def structured_action(self) -> "DeviceCommand":
        if (self.kind == "PRINT") != (self.receipt is not None):
            raise ValueError("Print commands require exactly one immutable receipt.")
        if (self.kind == "OPEN_DRAWER") != (self.cash_entry_id is not None):
            raise ValueError("Drawer commands require exactly one confirmed cash cause.")
        return self


class SignedDeviceCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    command: DeviceCommand
    issued_at: datetime
    expires_at: datetime
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")


class DeviceCommandResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    command_id: UUID
    state: Literal[
        "QUEUED", "PROCESSING", "ACKNOWLEDGED", "PRINTED", "OPENED", "UNAVAILABLE", "UNKNOWN"
    ]
    evidence_reference: str | None = None


def canonical_bytes(value: BaseModel) -> bytes:
    return json.dumps(value.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode()


def command_digest(command: DeviceCommand) -> str:
    return hashlib.sha256(canonical_bytes(command)).hexdigest()


def _signature(key: bytes, command: DeviceCommand, issued: datetime, expires: datetime) -> str:
    if len(key) < 32:
        raise ValueError("Pairing keys require at least 256 bits.")
    message = (
        canonical_bytes(command)
        + b"\n"
        + issued.isoformat().encode()
        + b"\n"
        + expires.isoformat().encode()
    )
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def sign_device_command(command: DeviceCommand, key: bytes) -> SignedDeviceCommand:
    now = datetime.now(UTC)
    expires = now + timedelta(seconds=60)
    return SignedDeviceCommand(
        command=command,
        issued_at=now,
        expires_at=expires,
        signature=_signature(key, command, now, expires),
    )


def verify_device_command(grant: SignedDeviceCommand, key: bytes) -> None:
    now = datetime.now(UTC)
    if (
        grant.issued_at.tzinfo is None
        or grant.expires_at.tzinfo is None
        or grant.issued_at > now + timedelta(seconds=5)
        or grant.expires_at < now
        or not timedelta(0) < grant.expires_at - grant.issued_at <= timedelta(seconds=60)
        or not hmac.compare_digest(
            grant.signature,
            _signature(
                key,
                grant.command,
                grant.issued_at,
                grant.expires_at,
            ),
        )
    ):
        raise ValueError("The local device authorization is invalid or expired.")
