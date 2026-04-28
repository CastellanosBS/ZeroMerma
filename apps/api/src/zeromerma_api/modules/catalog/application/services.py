from __future__ import annotations

import uuid

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from zeromerma_api.modules.branches.application.access import WorkstationAccessService
from zeromerma_api.modules.catalog.application.schemas import (
    PosCatalogClassView,
    PosCatalogProductView,
    PosCatalogResponse,
    PosClassProductsResponse,
)
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
)
from zeromerma_api.modules.catalog.domain.exceptions import (
    ProductClassNotFoundError,
    ProductSelectionNotAllowedError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser


class PosCatalogQueryService:
    def __init__(self, workstation_access: WorkstationAccessService | None = None) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()

    def get_catalog(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        query: str | None,
    ) -> PosCatalogResponse:
        self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_query = _normalize_query(query)
        product_count_subquery = (
            select(func.count(Product.id))
            .where(
                Product.product_class_id == ProductClass.id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .correlate(ProductClass)
            .scalar_subquery()
        )

        statement = (
            select(
                ProductClass.id,
                ProductClass.code,
                ProductClass.name,
                ProductClass.quick_name,
                ProductClass.display_order,
                ProductClass.capture_mode_default,
                ProductClass.class_capture_unit_price,
                ProductClass.currency_code,
                product_count_subquery.label("product_count"),
            )
            .where(
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
                or_(
                    ProductClass.capture_mode_default != CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
                    product_count_subquery > 0,
                ),
            )
            .order_by(
                case(
                    (ProductClass.capture_mode_default == CATALOG_CAPTURE_MODE_CLASS_CAPTURE, 0),
                    else_=1,
                ).asc(),
                ProductClass.display_order.asc(),
                ProductClass.name.asc(),
            )
        )

        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            matching_products = (
                select(Product.id)
                .where(
                    Product.product_class_id == ProductClass.id,
                    Product.is_active.is_(True),
                    Product.is_sellable.is_(True),
                    or_(
                        Product.code.ilike(pattern),
                        Product.name.ilike(pattern),
                        Product.quick_name.ilike(pattern),
                        Product.search_aliases.ilike(pattern),
                    ),
                )
                .exists()
            )
            statement = statement.where(
                or_(
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                    matching_products,
                )
            )

        records = session.execute(statement).mappings().all()

        return PosCatalogResponse(
            workstation_code=workstation_code,
            query=normalized_query,
            classes=[
                PosCatalogClassView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    display_order=record["display_order"],
                    capture_mode_default=record["capture_mode_default"],
                    class_capture_unit_price=record["class_capture_unit_price"],
                    currency_code=record["currency_code"],
                    product_count=int(record["product_count"]),
                )
                for record in records
            ],
        )

    def get_class_products(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        class_id: uuid.UUID,
        query: str | None,
    ) -> PosClassProductsResponse:
        self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        normalized_query = _normalize_query(query)
        product_class = session.execute(
            select(ProductClass).where(
                ProductClass.id == class_id,
                ProductClass.is_active.is_(True),
                ProductClass.is_sellable.is_(True),
            )
        ).scalar_one_or_none()
        if product_class is None:
            raise ProductClassNotFoundError("Product class was not found.")

        if product_class.capture_mode_default != CATALOG_CAPTURE_MODE_PRODUCT_DIRECT:
            raise ProductSelectionNotAllowedError(
                f"Product class {product_class.code} does not support direct product selection."
            )

        statement = (
            select(
                Product.id,
                Product.code,
                Product.name,
                Product.quick_name,
                Product.display_order,
                Product.unit_price,
                Product.currency_code,
            )
            .where(
                Product.product_class_id == class_id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .order_by(Product.display_order.asc(), Product.name.asc())
        )
        if normalized_query is not None:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                )
            )

        product_records = session.execute(statement).mappings().all()
        return PosClassProductsResponse(
            class_id=product_class.id,
            class_code=product_class.code,
            class_name=product_class.name,
            capture_mode_default=product_class.capture_mode_default,
            currency_code=product_class.currency_code,
            query=normalized_query,
            products=[
                PosCatalogProductView(
                    id=record["id"],
                    code=record["code"],
                    name=record["name"],
                    quick_name=record["quick_name"],
                    display_order=record["display_order"],
                    unit_price=record["unit_price"],
                    currency_code=record["currency_code"],
                )
                for record in product_records
            ],
        )


def _normalize_query(query: str | None) -> str | None:
    if query is None:
        return None

    stripped_query = query.strip()
    if stripped_query == "":
        return None

    return stripped_query
