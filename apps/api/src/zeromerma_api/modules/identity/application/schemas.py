from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from zeromerma_api.modules.identity.domain.constants import (
    IDENTITY_ALLOWED_SURFACES,
    IDENTITY_SURFACE_POS,
)

IdentitySurface = Literal["POS", "BACKOFFICE"]


def _default_surfaces() -> list[IdentitySurface]:
    return [IDENTITY_SURFACE_POS]


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str = Field(min_length=3, max_length=320)
    full_name: str
    allowed_surfaces: list[IdentitySurface] = Field(default_factory=_default_surfaces)
    default_surface: IdentitySurface = Field(default=IDENTITY_SURFACE_POS)
    is_active: bool

    @field_validator("allowed_surfaces", mode="before")
    @classmethod
    def normalize_allowed_surfaces(cls, value: object) -> list[str]:
        if value is None:
            return [IDENTITY_SURFACE_POS]
        if isinstance(value, str):
            values = [part.strip().upper() for part in value.split(",") if part.strip()]
        elif isinstance(value, list):
            values = [str(part).strip().upper() for part in value if str(part).strip()]
        else:
            return [IDENTITY_SURFACE_POS]

        normalized = [surface for surface in values if surface in IDENTITY_ALLOWED_SURFACES]
        return normalized or [IDENTITY_SURFACE_POS]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthenticatedUser
