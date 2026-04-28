from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
)


class ConfirmSaleLineRequest(BaseModel):
    capture_mode: str = Field(min_length=1, max_length=32)
    product_class_id: UUID | None = None
    product_id: UUID | None = None
    quantity: Decimal = Field(gt=Decimal("0"), max_digits=12, decimal_places=3)

    @model_validator(mode="after")
    def validate_reference_shape(self) -> ConfirmSaleLineRequest:
        if self.capture_mode not in {
            CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
            CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
        }:
            raise ValueError("capture_mode must be CLASS_CAPTURE or PRODUCT_DIRECT.")

        if self.capture_mode == CATALOG_CAPTURE_MODE_CLASS_CAPTURE:
            if self.product_class_id is None or self.product_id is not None:
                raise ValueError(
                    "CLASS_CAPTURE lines require product_class_id and must not include product_id."
                )
        else:
            if self.product_id is None or self.product_class_id is not None:
                raise ValueError(
                    "PRODUCT_DIRECT lines require product_id and must not include product_class_id."
                )

        return self


class ConfirmSalePaymentRequest(BaseModel):
    payment_method_code: str = Field(min_length=1, max_length=40)
    tendered_amount: Decimal = Field(ge=Decimal("0.00"), max_digits=12, decimal_places=2)


class ConfirmSaleRequest(BaseModel):
    workstation_code: str = Field(min_length=1, max_length=64)
    lines: list[ConfirmSaleLineRequest] = Field(min_length=1)
    payments: list[ConfirmSalePaymentRequest] = Field(min_length=1)


class SaleLineView(BaseModel):
    id: UUID
    sequence: int
    capture_mode: str
    product_class_id: UUID | None = None
    product_class_code: str | None = None
    product_class_name: str | None = None
    product_id: UUID | None = None
    product_code: str | None = None
    product_name: str | None = None
    catalog_code_snapshot: str
    catalog_name_snapshot: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal
    physical_attribution_status: str


class SalePaymentView(BaseModel):
    id: UUID
    sequence: int
    payment_method_code: str
    tendered_amount: Decimal
    applied_amount: Decimal
    change_amount: Decimal
    currency_code: str
    received_at: datetime


class CashMovementView(BaseModel):
    id: UUID
    movement_type: str
    direction: str
    payment_method_code: str
    amount: Decimal
    currency_code: str
    occurred_at: datetime


class SaleDetailView(BaseModel):
    id: UUID
    status: str
    branch_id: UUID
    branch_code: str
    branch_name: str
    workstation_id: UUID
    workstation_code: str
    workstation_name: str
    cash_session_id: UUID
    operator_id: UUID
    operator_email: str
    operator_full_name: str
    currency_code: str
    subtotal_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    change_amount: Decimal
    confirmed_at: datetime
    lines: list[SaleLineView]
    payments: list[SalePaymentView]
    cash_movements: list[CashMovementView]

