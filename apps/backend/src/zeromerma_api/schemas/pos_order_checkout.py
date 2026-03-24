from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from zeromerma_api.core.payment_method import PaymentMethod

from .common import NonNegativeMoney, ORMReadSchema, StrictInputSchema
from .pos_receipt import PosReceiptOut

OrderCheckoutSaleStatus = Literal["PAID"]
OrderCheckoutPaymentStatus = Literal["AUTHORIZED"]
OrderDeliveryStatus = Literal["DELIVERED"]


class PosOrderCheckoutPreviewLineOut(ORMReadSchema):
    """
    One frozen line shown when a READY order is transformed into a POS checkout
    preview.

    Important:
    - qty and prices come from order snapshots
    - they do NOT recalculate from current catalog price
    """

    product_id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    qty: Decimal
    unit_price_snapshot: Decimal
    line_total_snapshot: Decimal


class PosOrderCheckoutPreviewOut(ORMReadSchema):
    """
    Preview returned before delivering a READY order through POS checkout.
    """

    order_id: int
    branch_id: int
    status: str

    customer_name: str | None = None
    customer_phone: str | None = None
    note: str | None = None
    requested_for_at: datetime | None = None

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    items: list[PosOrderCheckoutPreviewLineOut] = Field(default_factory=list)


class PosOrderDeliverCheckoutPaymentIn(StrictInputSchema):
    """
    Payment input for atomic order delivery checkout.

    Supported methods in POS v1:
    - CASH
    - CARD
    - TRANSFER
    - OTHER

    Rules:
    - CASH requires amount_tendered
    - non-cash methods must not send amount_tendered
    """

    method: PaymentMethod
    amount_tendered: NonNegativeMoney | None = None
    reference: str | None = Field(default=None, max_length=64)
    external_auth_code: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_method_specific_fields(
        self,
    ) -> "PosOrderDeliverCheckoutPaymentIn":
        if self.method == PaymentMethod.CASH:
            if self.amount_tendered is None:
                raise ValueError("amount_tendered is required when payment method is CASH.")
        else:
            if self.amount_tendered is not None:
                raise ValueError("amount_tendered is only allowed when payment method is CASH.")
        return self


class PosOrderDeliverCheckoutIn(StrictInputSchema):
    """
    Atomic delivery + checkout request for a READY customer order.
    """

    cash_session_id: int = Field(ge=1)
    payment: PosOrderDeliverCheckoutPaymentIn
    print_ticket: bool = True


class PosOrderDeliverCheckoutOut(ORMReadSchema):
    """
    Final response for delivering one READY customer order through the POS checkout flow.
    """

    order_id: int
    sale_id: int
    payment_id: int

    order_status: OrderDeliveryStatus | str
    sale_status: OrderCheckoutSaleStatus | str
    payment_status: OrderCheckoutPaymentStatus | str

    subtotal: Decimal
    tax: Decimal
    total: Decimal

    paid_amount: Decimal
    change_due: Decimal
    balance_due: Decimal

    print_ticket: bool
    receipt: PosReceiptOut
