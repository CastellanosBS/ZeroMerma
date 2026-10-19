"""Backend-owned immutable operational receipt contract; never a fiscal invoice."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReceiptSellerView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    legal_name: str | None = None
    tax_identifier: str | None = None
    fiscal_regime: str | None = None
    address: str | None = None
    configuration_status: Literal["UNCONFIGURED", "CONFIGURED"] = "UNCONFIGURED"


class ReceiptContextView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    branch_id: UUID
    branch_code: str
    branch_name: str
    timezone: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    actor_id: UUID
    actor_name: str
    cash_session_id: UUID


class ReceiptLineView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    sequence: int = Field(ge=1)
    name: str
    quantity: Decimal = Field(gt=0, decimal_places=3)
    unit_price: Decimal = Field(ge=0, decimal_places=2)
    total_amount: Decimal = Field(ge=0, decimal_places=2)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)


class ReceiptPaymentView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    method: Literal["CASH", "CARD", "TRANSFER"]
    execution_mode: Literal["LOCAL", "ACCOUNTING_ONLY", "PROVIDER_INTEGRATED", "MANUAL_FALLBACK"]
    amount: Decimal = Field(ge=0, decimal_places=2)
    tendered_amount: Decimal = Field(ge=0, decimal_places=2)
    change_amount: Decimal = Field(ge=0, decimal_places=2)


class OperationalReceiptView(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    source_kind: Literal["SALE", "ORDER_PAYMENT", "RETURN"]
    source_id: UUID
    folio: str
    occurred_at: datetime
    context: ReceiptContextView
    seller: ReceiptSellerView = Field(default_factory=ReceiptSellerView)
    currency_code: str = Field(default="MXN", pattern=r"^[A-Z]{3}$")
    subtotal_amount: Decimal = Field(ge=0, decimal_places=2)
    discount_amount: Decimal = Field(ge=0, decimal_places=2)
    total_amount: Decimal = Field(ge=0, decimal_places=2)
    change_amount: Decimal = Field(ge=0, decimal_places=2)
    lines: list[ReceiptLineView]
    payments: list[ReceiptPaymentView]
    related_document_folio: str | None = None
    settled_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    pending_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    fiscal_document: Literal[False] = False
    provider_receipt: Literal[False] = False
