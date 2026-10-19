from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class PosCatalogClassView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None = None
    display_order: int
    capture_mode_default: str
    class_capture_unit_price: Decimal | None = None
    currency_code: str
    product_count: int


class PosCatalogResponse(BaseModel):
    workstation_code: str
    query: str | None = None
    classes: list[PosCatalogClassView]


class PosCatalogAvailableLotView(BaseModel):
    lot_id: UUID
    lot_code: str
    expires_at: datetime | None
    available_quantity: Decimal


class PosCatalogProductView(BaseModel):
    id: UUID
    code: str
    name: str
    quick_name: str | None = None
    display_order: int
    unit_price: Decimal
    currency_code: str
    is_inventory_tracked: bool
    lot_tracking_enabled: bool
    available_quantity: Decimal | None
    reserved_quantity: Decimal
    available_lots: list[PosCatalogAvailableLotView]


class PosClassProductsResponse(BaseModel):
    class_id: UUID
    class_code: str
    class_name: str
    capture_mode_default: str
    currency_code: str
    query: str | None = None
    products: list[PosCatalogProductView]
