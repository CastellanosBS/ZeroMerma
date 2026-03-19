# apps/backend/src/zeromerma_api/schemas/admin.py
# PURPOSE:
#   Pydantic schemas for administrative endpoints (/admin/*).
#
# SECURITY MODEL:
#   - These endpoints are restricted to ADMIN users only.
#   - Request models forbid unknown fields (extra="forbid") to prevent accidental
#     overposting and to detect stale clients early.

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AdminRoleOut(BaseModel):
    """
    Response model for roles.
    """

    id: int
    code: str
    name: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminBranchOut(BaseModel):
    """
    Response model for branches.
    """

    id: int
    code: str
    name: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserOut(BaseModel):
    """
    Response model for user accounts.

    NOTE:
      We never expose password_hash.
    """

    id: int
    branch_id: int
    role_id: int
    email: str
    full_name: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserCreateIn(BaseModel):
    """
    POST payload for creating a new user.

    Notes:
    - We intentionally use plain 'str' for email to avoid overly strict validators
      that reject special-use domains (e.g., .local). We still validate basic shape.
    - The password is hashed server-side using the project's existing PBKDF2 scheme.
    """

    branch_id: int = Field(..., ge=1)
    role_id: int = Field(..., ge=1)
    email: str = Field(..., min_length=3, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    is_active: bool = True

    model_config = ConfigDict(extra="forbid")


class AdminUserUpdateIn(BaseModel):
    """
    PATCH payload for updating a user.

    We intentionally allow only a small subset of fields:
      - branch_id: move the user to another branch
      - role_id: change permissions
      - full_name: update display name
      - is_active: deactivate/reactivate
    """

    branch_id: Optional[int] = Field(default=None, ge=1)
    role_id: Optional[int] = Field(default=None, ge=1)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class AdminPasswordResetIn(BaseModel):
    """
    POST payload for resetting a user's password (ADMIN-only).

    The password is hashed server-side.
    """

    new_password: str = Field(..., min_length=8, max_length=255)

    model_config = ConfigDict(extra="forbid")
