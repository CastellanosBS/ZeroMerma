from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserAccountRoleRef(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool

    model_config = ConfigDict(extra="forbid")


class AdminUserAccountBranchRef(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool

    model_config = ConfigDict(extra="forbid")


class AdminUserAccountOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    branch_id: int
    role_id: int
    has_password: bool
    created_at: datetime
    updated_at: datetime
    role: AdminUserAccountRoleRef
    branch: AdminUserAccountBranchRef

    model_config = ConfigDict(extra="forbid")


class AdminUserAccountCreateIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    branch_id: int = Field(ge=1)
    role_id: int = Field(ge=1)
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True


class AdminUserAccountUpdateIn(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    branch_id: int | None = Field(default=None, ge=1)
    role_id: int | None = Field(default=None, ge=1)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
