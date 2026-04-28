from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
)
from zeromerma_api.modules.catalog.domain.exceptions import (
    ProductClassNotFoundError,
    ProductNotFoundError,
    ProductSelectionNotAllowedError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.sales.domain.constants import (
    SALE_LINE_PHYSICAL_ATTRIBUTION_DIRECT_ASSIGNED,
    SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
)
from zeromerma_api.modules.sales.domain.exceptions import SaleValidationError

MONEY_QUANTIZER = Decimal("0.01")


@dataclass(frozen=True)
class PricedSaleLine:
    capture_mode: str
    product_class_id: uuid.UUID | None
    product_id: uuid.UUID | None
    catalog_code_snapshot: str
    catalog_name_snapshot: str
    quantity: Decimal
    unit_price: Decimal
    line_total_amount: Decimal
    physical_attribution_status: str
    currency_code: str


class SalePricingService:
    def price_class_capture_line(
        self,
        session: Session,
        *,
        product_class_id: uuid.UUID,
        quantity: Decimal,
    ) -> PricedSaleLine:
        product_class = session.execute(
            select(ProductClass).where(
                ProductClass.id == product_class_id,
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
            )
        ).scalar_one_or_none()
        if product_class is None:
            raise ProductClassNotFoundError("Product class was not found.")

        if product_class.capture_mode_default != CATALOG_CAPTURE_MODE_CLASS_CAPTURE:
            raise ProductSelectionNotAllowedError(
                f"Product class {product_class.code} requires direct product selection."
            )

        unit_price = product_class.class_capture_unit_price
        if unit_price is None:
            raise SaleValidationError(
                f"Product class {product_class.code} does not have a class capture price."
            )

        return PricedSaleLine(
            capture_mode=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
            product_class_id=product_class.id,
            product_id=None,
            catalog_code_snapshot=product_class.code,
            catalog_name_snapshot=product_class.name,
            quantity=quantity,
            unit_price=unit_price,
            line_total_amount=_calculate_line_total(quantity=quantity, unit_price=unit_price),
            physical_attribution_status=SALE_LINE_PHYSICAL_ATTRIBUTION_PENDING_RECONCILIATION,
            currency_code=product_class.currency_code,
        )

    def price_product_direct_line(
        self,
        session: Session,
        *,
        product_id: uuid.UUID,
        quantity: Decimal,
    ) -> PricedSaleLine:
        row = session.execute(
            select(Product, ProductClass)
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .where(
                Product.id == product_id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
            )
        ).one_or_none()
        if row is None:
            raise ProductNotFoundError("Product was not found.")

        product, product_class = row
        if product_class.capture_mode_default != CATALOG_CAPTURE_MODE_PRODUCT_DIRECT:
            raise ProductSelectionNotAllowedError(
                f"Product {product.code} belongs to a class that does not support direct sales."
            )

        return PricedSaleLine(
            capture_mode=CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
            product_class_id=None,
            product_id=product.id,
            catalog_code_snapshot=product.code,
            catalog_name_snapshot=product.name,
            quantity=quantity,
            unit_price=product.unit_price,
            line_total_amount=_calculate_line_total(
                quantity=quantity,
                unit_price=product.unit_price,
            ),
            physical_attribution_status=SALE_LINE_PHYSICAL_ATTRIBUTION_DIRECT_ASSIGNED,
            currency_code=product.currency_code,
        )


def _calculate_line_total(*, quantity: Decimal, unit_price: Decimal) -> Decimal:
    return (quantity * unit_price).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
