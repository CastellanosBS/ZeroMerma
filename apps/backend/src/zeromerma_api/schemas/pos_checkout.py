from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from zeromerma_api.core.payment_method import PaymentMethod

from .common import NonNegativeMoney, ORMReadSchema, PositiveQuantity, StrictInputSchema
from .pos_receipt import PosReceiptOut

CheckoutSaleStatus = Literal["PAID"]
CheckoutPaymentStatus = Literal["AUTHORIZED"]


class PosCheckoutItemIn(StrictInputSchema):
    """
    One cart line sent by the POS frontend.

    Pricing is NOT authoritative from the client side in checkout v1.
    Backend resolves the effective unit price server-side.
    """

    product_id: int = Field(ge=1)
    qty: PositiveQuantity


class PosCheckoutPaymentIn(StrictInputSchema):
    """
    Payment block for atomic checkout.

    Supported methods in POS v1:
    - CASH
    - CARD
    - TRANSFER
    - OTHER

    Rules:
    - CASH requires amount_tendered and it must be >= total (validated later in service)
    - non-cash methods must not send amount_tendered
    - reference/external_auth_code are optional metadata fields
    """

    method: PaymentMethod
    amount_tendered: NonNegativeMoney | None = None
    reference: str | None = Field(default=None, max_length=64)
    external_auth_code: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_method_specific_fields(self) -> "PosCheckoutPaymentIn":
        if self.method == PaymentMethod.CASH:
            if self.amount_tendered is None:
                raise ValueError("amount_tendered is required when payment method is CASH.")
        else:
            if self.amount_tendered is not None:
                raise ValueError("amount_tendered is only allowed when payment method is CASH.")
        return self


class PosCheckoutIn(StrictInputSchema):
    """
    Atomic POS checkout request.

    This endpoint creates:
    - sale
    - payment
    - inventory effects

    in one operational flow.
    """

    branch_id: int = Field(ge=1)
    cash_session_id: int = Field(ge=1)
    items: list[PosCheckoutItemIn] = Field(min_length=1)
    payment: PosCheckoutPaymentIn
    print_ticket: bool = True


class PosCheckoutOut(ORMReadSchema):
    """
    Final checkout response for POS v1.
    """

    sale_id: int
    payment_id: int

    sale_status: CheckoutSaleStatus | str
    payment_status: CheckoutPaymentStatus | str

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    paid_amount: Decimal
    change_due: Decimal
    balance_due: Decimal

    print_ticket: bool
    receipt: PosReceiptOut
