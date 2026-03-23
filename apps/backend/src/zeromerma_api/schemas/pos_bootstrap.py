from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from .common import ORMReadSchema


class PosBootstrapCashSessionOut(ORMReadSchema):
    """
    Minimal cash session payload required by the POS bootstrap.

    This is intentionally smaller than the full cash-session response used in
    other endpoints. The bootstrap only needs current operational context.
    """

    id: int
    status: str
    opened_at: datetime
    opening_amount: Decimal


class PosPaymentMethodOut(ORMReadSchema):
    """
    Payment method exposed to the POS client.
    """

    code: str
    label: str


class PosBootstrapCapabilitiesOut(ORMReadSchema):
    """
    Feature/capability flags exposed to the POS client.

    These flags allow frontend behavior to evolve without forcing the frontend
    to hardcode assumptions about available operational flows.
    """

    can_take_orders: bool
    can_deliver_orders: bool
    keyboard_first: bool


class PosBootstrapProductOut(ORMReadSchema):
    """
    One sellable POS product projection.

    Important:
    - This is not the full product master.
    - It contains only what the POS needs to render sellable items quickly.
    """

    id: int
    sku: str | None = None
    name: str
    quick_name: str | None = None
    default_pos_order: int
    uom: str
    effective_price: Decimal | None = None


class PosBootstrapCategoryOut(ORMReadSchema):
    """
    One POS-visible category with its sellable products.
    """

    id: int
    code: str
    name: str
    quick_name: str | None = None
    default_pos_order: int
    products: list[PosBootstrapProductOut] = Field(default_factory=list)


class PosBootstrapOut(ORMReadSchema):
    """
    Full POS bootstrap payload.

    The backend provides:
    - current branch context
    - open cash session (if any)
    - available payment methods
    - POS capability flags
    - visible categories/products
    - effective price per product

    The frontend remains responsible for:
    - final layout
    - keyboard mapping
    - touch arrangement
    - temporary/local UX state
    """

    branch_id: int
    cash_session: PosBootstrapCashSessionOut | None = None
    payment_methods: list[PosPaymentMethodOut] = Field(default_factory=list)
    capabilities: PosBootstrapCapabilitiesOut
    categories: list[PosBootstrapCategoryOut] = Field(default_factory=list)
