from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

PrivilegedOperation = Literal[
    "USER_UPDATE",
    "USER_STATUS",
    "USER_LOCK",
    "USER_UNLOCK",
    "USER_BRANCH_ASSIGNMENT",
    "USER_BRANCH_REMOVAL",
    "USER_BRANCH_DEFAULT",
    "ROLE_ASSIGNMENT",
    "ROLE_REMOVAL",
    "ROLE_UPDATE",
    "ROLE_STATUS",
]


class PrivilegedBranchTargetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    branch_id: UUID


class PrivilegedChangeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: PrivilegedOperation
    target_user_id: UUID | None = None
    target_role_id: UUID | None = None
    payload: dict[str, Any]
    reason: str = Field(min_length=8, max_length=1000)
    expires_in_minutes: int = Field(default=15, ge=1, le=60)

    @model_validator(mode="after")
    def validate_targets(self) -> PrivilegedChangeCreateRequest:
        needs_user = self.operation.startswith("USER_") or self.operation in {
            "ROLE_ASSIGNMENT",
            "ROLE_REMOVAL",
        }
        needs_role = self.operation.startswith("ROLE_")
        if needs_user != (self.target_user_id is not None):
            raise ValueError("The operation must specify exactly its required user target.")
        if needs_role != (self.target_role_id is not None):
            raise ValueError("The operation must specify exactly its required role target.")
        return self


class PrivilegedChangeConfirmationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payload_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class PrivilegedChangeView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operation: PrivilegedOperation
    target_user_id: UUID | None
    target_role_id: UUID | None
    payload: dict[str, Any]
    payload_sha256: str
    reason: str
    initiator_user_id: UUID
    approver_user_id: UUID | None
    created_at: datetime
    expires_at: datetime
    approved_at: datetime | None
    consumed_at: datetime | None
