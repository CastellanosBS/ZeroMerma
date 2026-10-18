from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser, IdentitySurface

SessionStatus = Literal["ACTIVE", "LOCKED", "REVOKED", "EXPIRED"]


class AuthSessionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audience: IdentitySurface
    status: SessionStatus
    created_at: datetime
    last_activity_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    workstation_id: UUID | None
    cash_session_id: UUID | None
    revoked_at: datetime | None
    revocation_reason: str | None


class LoginResponse(BaseModel):
    session: AuthSessionView
    user: AuthenticatedUser
    csrf_token: str = Field(repr=False)


class AuthSessionsResponse(BaseModel):
    items: list[AuthSessionView]
    total: int
    page: int
    page_size: int


class ReauthenticationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=128, repr=False)


class PasswordChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=128, repr=False)
    new_password: str = Field(min_length=12, max_length=128, repr=False)


class PasswordResetIssueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=8, max_length=1000)
    approval_id: UUID | None = None
    payload_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class PasswordResetCredentialView(BaseModel):
    reset_token: str = Field(repr=False)
    expires_at: datetime


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reset_token: str = Field(min_length=40, max_length=128, repr=False)
    new_password: str = Field(min_length=12, max_length=128, repr=False)
