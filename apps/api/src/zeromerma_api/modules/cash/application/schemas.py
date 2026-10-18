from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OpenCashSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workstation_code: str = Field(min_length=1, max_length=64)
    opening_amount: Decimal = Field(ge=Decimal("0.00"), max_digits=12, decimal_places=2)


class CashSessionOpenResultView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    status: Literal["OPEN"]
    opening_amount: Decimal
    opened_at: datetime
    branch_id: UUID
    workstation_id: UUID


class CashSessionView(BaseModel):
    id: UUID
    status: str
    opening_amount: Decimal
    opened_at: datetime
    branch_id: UUID
    branch_code: str
    branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    user_id: UUID
    user_email: str = Field(min_length=3, max_length=320)
    user_full_name: str
