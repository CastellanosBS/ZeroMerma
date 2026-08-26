from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch, Brand
from zeromerma_api.modules.catalog.application.admin_schemas import (
    AdminProductClassCreateRequest,
    AdminProductClassesListResponse,
    AdminProductClassFilterOptionsView,
    AdminProductClassMetricsView,
    AdminProductClassProductSummaryView,
    AdminProductClassStatus,
    AdminProductClassUpdateRequest,
    AdminProductClassView,
    AdminProductClassWarningsView,
    AdminRecipeCostDetailView,
    AdminRecipeCostFilterOptionsView,
    AdminRecipeCostMetricsView,
    AdminRecipeCostProductSummaryView,
    AdminRecipeCostsListResponse,
    AdminRecipeCostWarningsView,
    AdminRecipeCreateRequest,
    AdminRecipeDuplicateRequest,
    AdminRecipeInputView,
    AdminRecipeState,
    AdminRecipeView,
    AdminProductAvailabilitySummaryView,
    AdminProductCreateRequest,
    AdminProductFilterOptionView,
    AdminProductFilterOptionsView,
    AdminProductMetricsView,
    AdminProductReadinessView,
    AdminProductRelatedReadinessView,
    AdminProductsListResponse,
    AdminProductStatus,
    AdminProductUpdateRequest,
    AdminProductView,
    AdminPriceDetailView,
    AdminPriceFilterOptionsView,
    AdminPriceMetricsView,
    AdminPriceRowView,
    AdminPricesListResponse,
    AdminPriceUpdateRequest,
    AdminPriceWarningsView,
)
from zeromerma_api.modules.catalog.domain.constants import (
    CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
    CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
    CATALOG_PRODUCT_KIND_FINISHED_GOOD,
    CATALOG_PRODUCT_KIND_RAW_MATERIAL,
)
from zeromerma_api.modules.catalog.domain.exceptions import (
    CatalogError,
    ProductClassNotFoundError,
    ProductNotFoundError,
    RecipeNotFoundError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass, Recipe, RecipeInput
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.outbox.application.service import OutboxWriter

AUDIT_ACTION_ADMIN_PRODUCT_CREATED = "admin.product.created"
AUDIT_ACTION_ADMIN_PRODUCT_UPDATED = "admin.product.updated"
OUTBOX_EVENT_ADMIN_PRODUCT_CREATED_V1 = "admin.product.created.v1"
OUTBOX_EVENT_ADMIN_PRODUCT_UPDATED_V1 = "admin.product.updated.v1"
AUDIT_ACTION_ADMIN_PRODUCT_CLASS_CREATED = "admin.product_class.created"
AUDIT_ACTION_ADMIN_PRODUCT_CLASS_UPDATED = "admin.product_class.updated"
OUTBOX_EVENT_ADMIN_PRODUCT_CLASS_CREATED_V1 = "admin.product_class.created.v1"
OUTBOX_EVENT_ADMIN_PRODUCT_CLASS_UPDATED_V1 = "admin.product_class.updated.v1"
AUDIT_ACTION_ADMIN_RECIPE_CREATED = "admin.recipe.created"
AUDIT_ACTION_ADMIN_RECIPE_ACTIVATED = "admin.recipe.activated"
AUDIT_ACTION_ADMIN_RECIPE_DUPLICATED = "admin.recipe.duplicated"
AUDIT_ACTION_ADMIN_PRODUCT_STANDARD_COST_UPDATED = "admin.product.standard_cost_updated"
OUTBOX_EVENT_ADMIN_RECIPE_CREATED_V1 = "admin.recipe.created.v1"
OUTBOX_EVENT_ADMIN_RECIPE_ACTIVATED_V1 = "admin.recipe.activated.v1"
OUTBOX_EVENT_ADMIN_RECIPE_DUPLICATED_V1 = "admin.recipe.duplicated.v1"
OUTBOX_EVENT_ADMIN_PRODUCT_STANDARD_COST_UPDATED_V1 = "admin.product.standard_cost_updated.v1"
PRODUCT_RESOURCE_TYPE = "product"
PRODUCT_CLASS_RESOURCE_TYPE = "product_class"
RECIPE_RESOURCE_TYPE = "recipe"
COST_VARIANCE_WARNING_THRESHOLD = Decimal("20")
LOW_MARGIN_WARNING_THRESHOLD = Decimal("20")


class AdminProductValidationError(CatalogError):
    """Raised when an administrative product change violates catalog rules."""


@dataclass(frozen=True)
class _ProductRow:
    product: Product
    product_class: ProductClass
    brand: Brand


@dataclass(frozen=True)
class _ProductClassRow:
    product_class: ProductClass
    brand: Brand
    product_count: int
    active_product_count: int
    inactive_product_count: int


@dataclass(frozen=True)
class _RecipeCostRow:
    product: Product
    product_class: ProductClass
    brand: Brand
    active_recipe: Recipe | None
    recipe_count: int


@dataclass(frozen=True)
class _PriceProductRow:
    product: Product
    product_class: ProductClass
    brand: Brand


@dataclass(frozen=True)
class _PriceClassRow:
    product_class: ProductClass
    brand: Brand
    product_count: int


class AdminProductCatalogService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_products(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        branch_id: uuid.UUID | None,
        status_filter: str | None,
        class_id: uuid.UUID | None,
        capture_mode: str | None,
        readiness: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminProductsListResponse:
        effective_brand_id = brand_id
        if branch_id is not None:
            branch = self._get_branch(session, branch_id)
            if effective_brand_id is not None and branch.brand_id != effective_brand_id:
                rows: list[_ProductRow] = []
            else:
                effective_brand_id = branch.brand_id
                rows = self._fetch_product_rows(
                    session,
                    brand_id=effective_brand_id,
                    status_filter=status_filter,
                    class_id=class_id,
                    capture_mode=capture_mode,
                    search=search,
                )
        else:
            if effective_brand_id is not None:
                self._get_brand(session, effective_brand_id)
            rows = self._fetch_product_rows(
                session,
                brand_id=effective_brand_id,
                status_filter=status_filter,
                class_id=class_id,
                capture_mode=capture_mode,
                search=search,
            )
        items = [self._to_product_view(row.product, row.product_class, row.brand) for row in rows]
        normalized_readiness = _normalize_optional(readiness)
        if normalized_readiness and normalized_readiness != "all":
            items = [item for item in items if item.readiness.status == normalized_readiness]

        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size
        page_items = items[offset : offset + safe_page_size]

        return AdminProductsListResponse(
            items=page_items,
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            metrics=self._build_metrics(items),
            filter_options=self._build_filter_options(session, brand_id=effective_brand_id),
        )

    def get_product_detail(self, session: Session, *, product_id: uuid.UUID) -> AdminProductView:
        row = self._get_product_row(session, product_id)
        return self._to_product_view(row.product, row.product_class, row.brand)

    def create_product(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminProductCreateRequest,
        request_id: str | None,
    ) -> AdminProductView:
        product_class = self._get_product_class(session, command.product_class_id)
        self._validate_capture_mode(product_class, command.capture_mode)
        self._ensure_unique_code(session, command.code)

        product = Product(
            product_class_id=product_class.id,
            code=command.code.strip(),
            name=command.name.strip(),
            quick_name=_normalize_optional(command.quick_name),
            search_aliases=_normalize_optional(command.search_aliases),
            display_order=self._next_display_order(session, product_class.id),
            unit_price=command.unit_price,
            currency_code=product_class.currency_code,
            is_active=command.status == "active",
            is_sellable=command.status == "active",
        )

        try:
            session.add(product)
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_ADMIN_PRODUCT_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_PRODUCT_CREATED_V1,
                product=product,
                request_id=request_id,
                metadata={
                    "code": product.code,
                    "name": product.name,
                    "product_class_id": str(product.product_class_id),
                    "brand_id": str(product_class.brand_id),
                    "capture_mode": product_class.capture_mode_default,
                    "status": _product_status(product),
                    "unit_price": str(product.unit_price),
                    "currency_code": product.currency_code,
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminProductValidationError("Product code must be unique.") from error

        return self.get_product_detail(session, product_id=product.id)

    def update_product(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        product_id: uuid.UUID,
        command: AdminProductUpdateRequest,
        request_id: str | None,
    ) -> AdminProductView:
        row = self._get_product_row(session, product_id)
        product = row.product
        previous_snapshot = self._product_snapshot(product, row.product_class)

        if command.product_class_id is not None:
            product_class = self._get_product_class(session, command.product_class_id)
            self._validate_capture_mode(product_class, command.capture_mode)
            product.product_class_id = product_class.id
            product.currency_code = product_class.currency_code
        else:
            product_class = row.product_class
            self._validate_capture_mode(product_class, command.capture_mode)

        if command.code is not None and command.code.strip() != product.code:
            self._ensure_unique_code(session, command.code.strip(), product_id=product.id)
            product.code = command.code.strip()
        if command.name is not None:
            product.name = command.name.strip()
        if "quick_name" in command.model_fields_set:
            product.quick_name = _normalize_optional(command.quick_name)
        if "search_aliases" in command.model_fields_set:
            product.search_aliases = _normalize_optional(command.search_aliases)
        if command.unit_price is not None:
            product.unit_price = command.unit_price
        if command.status is not None:
            product.is_active = command.status == "active"
            product.is_sellable = command.status == "active"

        try:
            session.flush()
            updated_class = self._get_product_class(session, product.product_class_id)
            self._record_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_ADMIN_PRODUCT_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_PRODUCT_UPDATED_V1,
                product=product,
                request_id=request_id,
                metadata={
                    "previous": previous_snapshot,
                    "current": self._product_snapshot(product, updated_class),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminProductValidationError("Product update violates catalog integrity.") from error

        return self.get_product_detail(session, product_id=product.id)

    def _fetch_product_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        status_filter: str | None,
        class_id: uuid.UUID | None,
        capture_mode: str | None,
        search: str | None,
    ) -> list[_ProductRow]:
        statement = (
            select(Product, ProductClass, Brand)
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .order_by(ProductClass.display_order.asc(), Product.display_order.asc(), Product.name.asc())
        )
        normalized_status = _normalize_optional(status_filter)
        if normalized_status == "active":
            statement = statement.where(Product.is_active.is_(True), Product.is_sellable.is_(True))
        elif normalized_status == "inactive":
            statement = statement.where(
                or_(Product.is_active.is_(False), Product.is_sellable.is_(False))
            )
        elif normalized_status not in (None, "all"):
            raise AdminProductValidationError("Unsupported product status filter.")

        if class_id is not None:
            statement = statement.where(Product.product_class_id == class_id)
        if brand_id is not None:
            statement = statement.where(ProductClass.brand_id == brand_id)

        normalized_capture_mode = _normalize_optional(capture_mode)
        if normalized_capture_mode and normalized_capture_mode != "all":
            if normalized_capture_mode not in (
                CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
                CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
            ):
                raise AdminProductValidationError("Unsupported capture mode filter.")
            statement = statement.where(ProductClass.capture_mode_default == normalized_capture_mode)

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                )
            )

        return [
            _ProductRow(product=product, product_class=product_class, brand=brand)
            for product, product_class, brand in session.execute(statement).all()
        ]

    def _to_product_view(
        self,
        product: Product,
        product_class: ProductClass,
        brand: Brand,
    ) -> AdminProductView:
        return AdminProductView(
            id=product.id,
            code=product.code,
            sku=product.code,
            name=product.name,
            quick_name=product.quick_name,
            description=product.search_aliases,
            class_id=product_class.id,
            class_name=product_class.name,
            capture_mode=product_class.capture_mode_default,  # type: ignore[arg-type]
            status=_product_status(product),
            product_kind=product.product_kind,  # type: ignore[arg-type]
            unit_price=product.unit_price,
            standard_cost=product.standard_cost,
            currency_code=product.currency_code,
            unit_of_measure=product.unit_of_measure,
            brand_id=brand.id,
            brand_name=brand.name,
            visible_in_pos=product.is_active and product.is_sellable,
            availability=AdminProductAvailabilitySummaryView(
                configured_branches_count=None,
                total_branches_count=None,
                state="unknown",
            ),
            branch_availability=[],
            readiness=_build_readiness(product, product_class),
            updated_at=product.updated_at,
        )

    def _build_filter_options(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
    ) -> AdminProductFilterOptionsView:
        branch_statement = (
            select(Branch.id, Branch.name, Brand.name)
            .join(Brand, Brand.id == Branch.brand_id)
            .where(Branch.is_active.is_(True))
            .order_by(Brand.name.asc(), Branch.name.asc())
        )
        if brand_id is not None:
            branch_statement = branch_statement.where(Branch.brand_id == brand_id)
        branches = session.execute(branch_statement).all()
        brands = session.execute(
            select(Brand.id, Brand.name).where(Brand.is_active.is_(True)).order_by(Brand.name.asc())
        ).all()
        class_statement = (
            select(ProductClass.id, ProductClass.name)
            .where(ProductClass.is_active.is_(True))
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )
        if brand_id is not None:
            class_statement = class_statement.where(ProductClass.brand_id == brand_id)
        classes = session.execute(
            class_statement
        ).all()
        return AdminProductFilterOptionsView(
            branches=[
                AdminProductFilterOptionView(id=branch_id, label=f"{branch_name} - {brand_name}")
                for branch_id, branch_name, brand_name in branches
            ],
            brands=[
                AdminProductFilterOptionView(id=brand_option_id, label=brand_name)
                for brand_option_id, brand_name in brands
            ],
            classes=[
                AdminProductFilterOptionView(id=class_id, label=class_name)
                for class_id, class_name in classes
            ],
        )

    def _build_metrics(self, items: list[AdminProductView]) -> AdminProductMetricsView:
        return AdminProductMetricsView(
            active_products=sum(1 for item in items if item.status == "active"),
            product_direct=sum(
                1 for item in items if item.capture_mode == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT
            ),
            class_capture=sum(
                1 for item in items if item.capture_mode == CATALOG_CAPTURE_MODE_CLASS_CAPTURE
            ),
            require_attention=sum(
                1 for item in items if item.readiness.status in {"requires_attention", "incomplete"}
            ),
            without_branch_availability=None,
        )

    def _get_product_row(self, session: Session, product_id: uuid.UUID) -> _ProductRow:
        row = session.execute(
            select(Product, ProductClass, Brand)
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .where(Product.id == product_id)
        ).one_or_none()
        if row is None:
            raise ProductNotFoundError("Product was not found.")
        product, product_class, brand = row
        return _ProductRow(product=product, product_class=product_class, brand=brand)

    def _get_product_class(self, session: Session, class_id: uuid.UUID) -> ProductClass:
        product_class = session.execute(
            select(ProductClass).where(ProductClass.id == class_id)
        ).scalar_one_or_none()
        if product_class is None:
            raise ProductClassNotFoundError("Product class was not found.")
        return product_class

    def _get_branch(self, session: Session, branch_id: uuid.UUID) -> Branch:
        branch = session.execute(select(Branch).where(Branch.id == branch_id)).scalar_one_or_none()
        if branch is None:
            raise AdminProductValidationError("Branch was not found.")
        return branch

    def _get_brand(self, session: Session, brand_id: uuid.UUID) -> Brand:
        brand = session.execute(select(Brand).where(Brand.id == brand_id)).scalar_one_or_none()
        if brand is None:
            raise AdminProductValidationError("Brand was not found.")
        return brand

    def _ensure_unique_code(
        self,
        session: Session,
        code: str,
        product_id: uuid.UUID | None = None,
    ) -> None:
        statement = select(Product.id).where(Product.code == code.strip())
        if product_id is not None:
            statement = statement.where(Product.id != product_id)
        existing_id = session.execute(statement).scalar_one_or_none()
        if existing_id is not None:
            raise AdminProductValidationError("Product code must be unique.")

    def _next_display_order(self, session: Session, product_class_id: uuid.UUID) -> int:
        max_order = session.execute(
            select(func.max(Product.display_order)).where(Product.product_class_id == product_class_id)
        ).scalar_one()
        return int(max_order or 0) + 10

    def _validate_capture_mode(
        self,
        product_class: ProductClass,
        capture_mode: str | None,
    ) -> None:
        if capture_mode is None:
            return
        if capture_mode != product_class.capture_mode_default:
            raise AdminProductValidationError(
                "Product capture mode is derived from its class and cannot conflict with it."
            )

    def _record_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        action: str,
        event_name: str,
        product: Product,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=PRODUCT_RESOURCE_TYPE,
            resource_id=str(product.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=PRODUCT_RESOURCE_TYPE,
            aggregate_id=str(product.id),
            event_name=event_name,
            payload={"product_id": str(product.id), **metadata},
            headers={"request_id": request_id} if request_id else {},
        )

    def _product_snapshot(self, product: Product, product_class: ProductClass) -> dict[str, object]:
        return {
            "id": str(product.id),
            "code": product.code,
            "name": product.name,
            "product_class_id": str(product.product_class_id),
            "brand_id": str(product_class.brand_id),
            "capture_mode": product_class.capture_mode_default,
            "status": _product_status(product),
            "unit_price": str(product.unit_price),
            "currency_code": product.currency_code,
            "quick_name": product.quick_name,
            "search_aliases": product.search_aliases,
        }


class AdminProductClassCatalogService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_classes(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        status_filter: str | None,
        capture_mode: str | None,
        product_presence: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminProductClassesListResponse:
        if brand_id is not None:
            self._get_brand(session, brand_id)

        rows = self._fetch_class_rows(
            session,
            brand_id=brand_id,
            status_filter=status_filter,
            capture_mode=capture_mode,
            search=search,
        )

        normalized_product_presence = _normalize_optional(product_presence) or "all"
        if normalized_product_presence not in {"all", "with_products", "without_products"}:
            raise AdminProductValidationError("Unsupported product presence filter.")
        if normalized_product_presence == "with_products":
            rows = [row for row in rows if row.product_count > 0]
        elif normalized_product_presence == "without_products":
            rows = [row for row in rows if row.product_count == 0]

        items = [self._to_class_view(session, row) for row in rows]
        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminProductClassesListResponse(
            items=items[offset : offset + safe_page_size],
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            metrics=self._build_class_metrics(items),
            filter_options=self._build_class_filter_options(session),
        )

    def get_class_detail(self, session: Session, *, class_id: uuid.UUID) -> AdminProductClassView:
        row = self._get_class_row(session, class_id)
        return self._to_class_view(session, row, include_products=True)

    def create_class(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminProductClassCreateRequest,
        request_id: str | None,
    ) -> AdminProductClassView:
        brand = self._get_brand(session, command.brand_id)
        self._ensure_unique_class_code(session, command.code)
        self._validate_class_price_shape(
            capture_mode=command.capture_mode_default,
            class_capture_unit_price=command.class_capture_unit_price,
        )

        product_class = ProductClass(
            brand_id=brand.id,
            code=command.code.strip(),
            name=command.name.strip(),
            quick_name=_normalize_optional(command.quick_name),
            search_aliases=_normalize_optional(command.search_aliases),
            display_order=command.display_order,
            capture_mode_default=command.capture_mode_default,
            class_capture_unit_price=(
                command.class_capture_unit_price
                if command.capture_mode_default == CATALOG_CAPTURE_MODE_CLASS_CAPTURE
                else None
            ),
            currency_code=command.currency_code.strip().upper(),
            is_active=command.status == "active",
            is_sellable=command.is_sellable,
        )

        try:
            session.add(product_class)
            session.flush()
            snapshot = self._class_snapshot(product_class)
            self._record_class_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_ADMIN_PRODUCT_CLASS_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_PRODUCT_CLASS_CREATED_V1,
                product_class=product_class,
                request_id=request_id,
                metadata=snapshot,
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminProductValidationError("Product class code must be unique.") from error

        return self.get_class_detail(session, class_id=product_class.id)

    def update_class(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        class_id: uuid.UUID,
        command: AdminProductClassUpdateRequest,
        request_id: str | None,
    ) -> AdminProductClassView:
        row = self._get_class_row(session, class_id)
        product_class = row.product_class
        previous_snapshot = self._class_snapshot(product_class)

        if command.brand_id is not None:
            brand = self._get_brand(session, command.brand_id)
            product_class.brand_id = brand.id
        if command.code is not None and command.code.strip() != product_class.code:
            self._ensure_unique_class_code(session, command.code.strip(), class_id=product_class.id)
            product_class.code = command.code.strip()
        if command.name is not None:
            product_class.name = command.name.strip()
        if "quick_name" in command.model_fields_set:
            product_class.quick_name = _normalize_optional(command.quick_name)
        if "search_aliases" in command.model_fields_set:
            product_class.search_aliases = _normalize_optional(command.search_aliases)
        if command.capture_mode_default is not None:
            product_class.capture_mode_default = command.capture_mode_default
        if "class_capture_unit_price" in command.model_fields_set:
            product_class.class_capture_unit_price = command.class_capture_unit_price
        if command.currency_code is not None:
            product_class.currency_code = command.currency_code.strip().upper()
        if command.display_order is not None:
            product_class.display_order = command.display_order
        if command.status is not None:
            product_class.is_active = command.status == "active"
        if command.is_sellable is not None:
            product_class.is_sellable = command.is_sellable

        if product_class.capture_mode_default == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT:
            product_class.class_capture_unit_price = None
        self._validate_class_price_shape(
            capture_mode=product_class.capture_mode_default,
            class_capture_unit_price=product_class.class_capture_unit_price,
        )

        try:
            session.flush()
            self._record_class_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_ADMIN_PRODUCT_CLASS_UPDATED,
                event_name=OUTBOX_EVENT_ADMIN_PRODUCT_CLASS_UPDATED_V1,
                product_class=product_class,
                request_id=request_id,
                metadata={
                    "previous": previous_snapshot,
                    "current": self._class_snapshot(product_class),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminProductValidationError("Product class update violates catalog integrity.") from error

        return self.get_class_detail(session, class_id=product_class.id)

    def _fetch_class_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        status_filter: str | None,
        capture_mode: str | None,
        search: str | None,
    ) -> list[_ProductClassRow]:
        product_count = (
            select(func.count(Product.id))
            .where(Product.product_class_id == ProductClass.id)
            .correlate(ProductClass)
            .scalar_subquery()
        )
        active_product_count = (
            select(func.count(Product.id))
            .where(
                Product.product_class_id == ProductClass.id,
                Product.is_active.is_(True),
                Product.is_sellable.is_(True),
            )
            .correlate(ProductClass)
            .scalar_subquery()
        )
        inactive_product_count = (
            select(func.count(Product.id))
            .where(
                Product.product_class_id == ProductClass.id,
                or_(Product.is_active.is_(False), Product.is_sellable.is_(False)),
            )
            .correlate(ProductClass)
            .scalar_subquery()
        )
        statement = (
            select(ProductClass, Brand, product_count, active_product_count, inactive_product_count)
            .select_from(ProductClass)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )

        if brand_id is not None:
            statement = statement.where(ProductClass.brand_id == brand_id)

        normalized_status = _normalize_optional(status_filter)
        if normalized_status == "active":
            statement = statement.where(ProductClass.is_active.is_(True))
        elif normalized_status == "inactive":
            statement = statement.where(ProductClass.is_active.is_(False))
        elif normalized_status not in (None, "all"):
            raise AdminProductValidationError("Unsupported class status filter.")

        normalized_capture_mode = _normalize_optional(capture_mode)
        if normalized_capture_mode and normalized_capture_mode != "all":
            if normalized_capture_mode not in (
                CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
                CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
            ):
                raise AdminProductValidationError("Unsupported capture mode filter.")
            statement = statement.where(ProductClass.capture_mode_default == normalized_capture_mode)

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search}%"
            statement = statement.where(
                or_(
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                )
            )

        return [
            _ProductClassRow(
                product_class=product_class,
                brand=brand,
                product_count=int(product_count_value or 0),
                active_product_count=int(active_product_count_value or 0),
                inactive_product_count=int(inactive_product_count_value or 0),
            )
            for (
                product_class,
                brand,
                product_count_value,
                active_product_count_value,
                inactive_product_count_value,
            ) in session.execute(statement).all()
        ]

    def _to_class_view(
        self,
        session: Session,
        row: _ProductClassRow,
        *,
        include_products: bool = False,
    ) -> AdminProductClassView:
        product_class = row.product_class
        warnings = _build_class_warnings(row)
        linked_products = self._list_class_products(session, product_class.id, limit=12 if include_products else 5)
        readiness: AdminProductReadinessStatus = "ready"
        if "class_capture_missing_price" in warnings.codes:
            readiness = "incomplete"
        elif warnings.codes:
            readiness = "requires_attention"

        return AdminProductClassView(
            id=product_class.id,
            brand_id=product_class.brand_id,
            brand_name=row.brand.name,
            code=product_class.code,
            name=product_class.name,
            quick_name=product_class.quick_name,
            search_aliases=product_class.search_aliases,
            capture_mode_default=product_class.capture_mode_default,  # type: ignore[arg-type]
            class_capture_unit_price=product_class.class_capture_unit_price,
            currency_code=product_class.currency_code,
            display_order=product_class.display_order,
            status=_class_status(product_class),
            is_sellable=product_class.is_sellable,
            product_count=row.product_count,
            active_product_count=row.active_product_count,
            inactive_product_count=row.inactive_product_count,
            linked_products=linked_products,
            warnings=warnings,
            readiness=readiness,
            updated_at=product_class.updated_at,
        )

    def _list_class_products(
        self,
        session: Session,
        class_id: uuid.UUID,
        *,
        limit: int,
    ) -> list[AdminProductClassProductSummaryView]:
        rows = session.execute(
            select(Product)
            .where(Product.product_class_id == class_id)
            .order_by(Product.display_order.asc(), Product.name.asc())
            .limit(limit)
        ).scalars()
        return [
            AdminProductClassProductSummaryView(
                id=product.id,
                code=product.code,
                name=product.name,
                status=_product_status(product),
                unit_price=product.unit_price,
                updated_at=product.updated_at,
            )
            for product in rows
        ]

    def _build_class_metrics(self, items: list[AdminProductClassView]) -> AdminProductClassMetricsView:
        return AdminProductClassMetricsView(
            total_classes=len(items),
            active_classes=sum(1 for item in items if item.status == "active"),
            class_capture=sum(
                1 for item in items if item.capture_mode_default == CATALOG_CAPTURE_MODE_CLASS_CAPTURE
            ),
            product_direct=sum(
                1 for item in items if item.capture_mode_default == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT
            ),
            without_products=sum(1 for item in items if item.product_count == 0),
            with_warnings=sum(1 for item in items if item.warnings.codes),
        )

    def _build_class_filter_options(self, session: Session) -> AdminProductClassFilterOptionsView:
        brands = session.execute(
            select(Brand.id, Brand.name).where(Brand.is_active.is_(True)).order_by(Brand.name.asc())
        ).all()
        return AdminProductClassFilterOptionsView(
            brands=[
                AdminProductFilterOptionView(id=brand_id, label=brand_name)
                for brand_id, brand_name in brands
            ],
        )

    def _get_class_row(self, session: Session, class_id: uuid.UUID) -> _ProductClassRow:
        rows = self._fetch_class_rows(
            session,
            brand_id=None,
            status_filter=None,
            capture_mode=None,
            search=None,
        )
        row = next((item for item in rows if item.product_class.id == class_id), None)
        if row is None:
            raise ProductClassNotFoundError("Product class was not found.")
        return row

    def _get_brand(self, session: Session, brand_id: uuid.UUID) -> Brand:
        brand = session.execute(select(Brand).where(Brand.id == brand_id)).scalar_one_or_none()
        if brand is None:
            raise AdminProductValidationError("Brand was not found.")
        return brand

    def _ensure_unique_class_code(
        self,
        session: Session,
        code: str,
        class_id: uuid.UUID | None = None,
    ) -> None:
        statement = select(ProductClass.id).where(ProductClass.code == code.strip())
        if class_id is not None:
            statement = statement.where(ProductClass.id != class_id)
        existing_id = session.execute(statement).scalar_one_or_none()
        if existing_id is not None:
            raise AdminProductValidationError("Product class code must be unique.")

    def _validate_class_price_shape(
        self,
        *,
        capture_mode: str,
        class_capture_unit_price: Decimal | None,
    ) -> None:
        if capture_mode == CATALOG_CAPTURE_MODE_CLASS_CAPTURE and class_capture_unit_price is None:
            raise AdminProductValidationError(
                "CLASS_CAPTURE product classes require a class capture unit price."
            )
        if capture_mode == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT and class_capture_unit_price is not None:
            raise AdminProductValidationError(
                "PRODUCT_DIRECT product classes cannot define a class capture unit price."
            )

    def _record_class_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        action: str,
        event_name: str,
        product_class: ProductClass,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=PRODUCT_CLASS_RESOURCE_TYPE,
            resource_id=str(product_class.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=PRODUCT_CLASS_RESOURCE_TYPE,
            aggregate_id=str(product_class.id),
            event_name=event_name,
            payload={"product_class_id": str(product_class.id), **metadata},
            headers={"request_id": request_id} if request_id else {},
        )

    def _class_snapshot(self, product_class: ProductClass) -> dict[str, object]:
        return {
            "id": str(product_class.id),
            "brand_id": str(product_class.brand_id),
            "code": product_class.code,
            "name": product_class.name,
            "quick_name": product_class.quick_name,
            "search_aliases": product_class.search_aliases,
            "capture_mode_default": product_class.capture_mode_default,
            "class_capture_unit_price": (
                str(product_class.class_capture_unit_price)
                if product_class.class_capture_unit_price is not None
                else None
            ),
            "currency_code": product_class.currency_code,
            "display_order": product_class.display_order,
            "status": _class_status(product_class),
            "is_sellable": product_class.is_sellable,
        }


class AdminPriceCatalogService:
    def list_prices(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        entity_type: str | None,
        capture_mode: str | None,
        status_filter: str | None,
        price_health: str | None,
        updated_from: datetime | None,
        updated_to: datetime | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminPricesListResponse:
        rows = self._fetch_price_rows(
            session,
            brand_id=brand_id,
            class_id=class_id,
            entity_type=entity_type,
            capture_mode=capture_mode,
            search=search,
            updated_from=updated_from,
            updated_to=updated_to,
        )
        items = [self._to_price_row_view(row) for row in rows]

        normalized_status = _normalize_optional(status_filter) or "all"
        if normalized_status not in {"all", "active", "inactive"}:
            raise AdminProductValidationError("Unsupported price status filter.")
        if normalized_status != "all":
            items = [item for item in items if item.status == normalized_status]

        normalized_health = _normalize_optional(price_health) or "all"
        if normalized_health not in {
            "all",
            "healthy",
            "missing_price",
            "warning",
            "low_margin",
            "negative_margin",
        }:
            raise AdminProductValidationError("Unsupported price health filter.")
        if normalized_health != "all":
            items = [item for item in items if item.health == normalized_health]

        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminPricesListResponse(
            items=items[offset : offset + safe_page_size],
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            metrics=self._build_price_metrics(items),
            filter_options=self._build_price_filter_options(session, brand_id=brand_id),
        )

    def get_price_detail(
        self,
        session: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> AdminPriceDetailView:
        item = self._get_price_row_view(session, entity_type=entity_type, entity_id=entity_id)
        return AdminPriceDetailView(
            price=item,
            history_note=(
                "El historial completo de precios se consultara desde auditoria cuando el "
                "endpoint administrativo de eventos este disponible."
            ),
        )

    def update_price(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        entity_type: str,
        entity_id: uuid.UUID,
        command: AdminPriceUpdateRequest,
        request_id: str | None,
    ) -> AdminPriceDetailView:
        normalized_entity_type = _normalize_optional(entity_type)
        if normalized_entity_type == "product":
            product_row = self._get_price_product_row(session, entity_id)
            if product_row.product_class.capture_mode_default != CATALOG_CAPTURE_MODE_PRODUCT_DIRECT:
                raise AdminProductValidationError(
                    "Only PRODUCT_DIRECT products can own product-level prices."
                )
            AdminProductCatalogService().update_product(
                session,
                current_user=current_user,
                product_id=product_row.product.id,
                command=AdminProductUpdateRequest(unit_price=command.price),
                request_id=request_id,
            )
            return self.get_price_detail(session, entity_type="product", entity_id=entity_id)

        if normalized_entity_type == "class":
            class_row = self._get_price_class_row(session, entity_id)
            if class_row.product_class.capture_mode_default != CATALOG_CAPTURE_MODE_CLASS_CAPTURE:
                raise AdminProductValidationError(
                    "Only CLASS_CAPTURE classes can own class-level prices."
                )
            AdminProductClassCatalogService().update_class(
                session,
                current_user=current_user,
                class_id=class_row.product_class.id,
                command=AdminProductClassUpdateRequest(class_capture_unit_price=command.price),
                request_id=request_id,
            )
            return self.get_price_detail(session, entity_type="class", entity_id=entity_id)

        raise AdminProductValidationError("Unsupported price entity type.")

    def _fetch_price_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        entity_type: str | None,
        capture_mode: str | None,
        search: str | None,
        updated_from: datetime | None,
        updated_to: datetime | None,
    ) -> list[_PriceProductRow | _PriceClassRow]:
        normalized_entity_type = _normalize_optional(entity_type) or "all"
        if normalized_entity_type not in {"all", "product", "class"}:
            raise AdminProductValidationError("Unsupported price entity type filter.")

        normalized_capture_mode = _normalize_optional(capture_mode) or "all"
        if normalized_capture_mode not in {
            "all",
            CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
            CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
        }:
            raise AdminProductValidationError("Unsupported capture mode filter.")

        rows: list[_PriceProductRow | _PriceClassRow] = []
        if normalized_entity_type in {"all", "product"} and normalized_capture_mode in {
            "all",
            CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
        }:
            rows.extend(
                self._fetch_price_product_rows(
                    session,
                    brand_id=brand_id,
                    class_id=class_id,
                    search=search,
                    updated_from=updated_from,
                    updated_to=updated_to,
                )
            )
        if normalized_entity_type in {"all", "class"} and normalized_capture_mode in {
            "all",
            CATALOG_CAPTURE_MODE_CLASS_CAPTURE,
        }:
            rows.extend(
                self._fetch_price_class_rows(
                    session,
                    brand_id=brand_id,
                    class_id=class_id,
                    search=search,
                    updated_from=updated_from,
                    updated_to=updated_to,
                )
            )

        return sorted(
            rows,
            key=lambda row: (
                row.product_class.display_order,
                row.product.name if isinstance(row, _PriceProductRow) else row.product_class.name,
            ),
        )

    def _fetch_price_product_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        search: str | None,
        updated_from: datetime | None,
        updated_to: datetime | None,
    ) -> list[_PriceProductRow]:
        statement = (
            select(Product, ProductClass, Brand)
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .where(
                Product.product_kind == CATALOG_PRODUCT_KIND_FINISHED_GOOD,
                ProductClass.capture_mode_default == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,
            )
        )
        if brand_id is not None:
            statement = statement.where(ProductClass.brand_id == brand_id)
        if class_id is not None:
            statement = statement.where(Product.product_class_id == class_id)
        if updated_from is not None:
            statement = statement.where(Product.updated_at >= updated_from)
        if updated_to is not None:
            statement = statement.where(Product.updated_at <= updated_to)

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                )
            )

        return [
            _PriceProductRow(product=product, product_class=product_class, brand=brand)
            for product, product_class, brand in session.execute(statement).all()
        ]

    def _fetch_price_class_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        search: str | None,
        updated_from: datetime | None,
        updated_to: datetime | None,
    ) -> list[_PriceClassRow]:
        product_count = (
            select(func.count(Product.id))
            .where(Product.product_class_id == ProductClass.id)
            .correlate(ProductClass)
            .scalar_subquery()
        )
        statement = (
            select(ProductClass, Brand, product_count)
            .select_from(ProductClass)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .where(ProductClass.capture_mode_default == CATALOG_CAPTURE_MODE_CLASS_CAPTURE)
        )
        if brand_id is not None:
            statement = statement.where(ProductClass.brand_id == brand_id)
        if class_id is not None:
            statement = statement.where(ProductClass.id == class_id)
        if updated_from is not None:
            statement = statement.where(ProductClass.updated_at >= updated_from)
        if updated_to is not None:
            statement = statement.where(ProductClass.updated_at <= updated_to)

        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search}%"
            statement = statement.where(
                or_(
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                )
            )

        return [
            _PriceClassRow(
                product_class=product_class,
                brand=brand,
                product_count=int(product_count_value or 0),
            )
            for product_class, brand, product_count_value in session.execute(statement).all()
        ]

    def _to_price_row_view(self, row: _PriceProductRow | _PriceClassRow) -> AdminPriceRowView:
        if isinstance(row, _PriceProductRow):
            return self._to_product_price_row_view(row)
        return self._to_class_price_row_view(row)

    def _to_product_price_row_view(self, row: _PriceProductRow) -> AdminPriceRowView:
        product = row.product
        price = product.unit_price
        delta = None
        margin_percent = None
        if product.standard_cost is not None:
            delta = price - product.standard_cost
            if price != Decimal("0"):
                margin_percent = (delta / price) * Decimal("100")
        warnings = self._build_product_price_warnings(row, delta=delta, margin_percent=margin_percent)
        health = self._resolve_price_health(price=price, warnings=warnings)
        return AdminPriceRowView(
            entity_id=product.id,
            entity_type="product",
            entity_name=product.name,
            entity_code=product.code,
            class_id=row.product_class.id,
            class_name=row.product_class.name,
            brand_id=row.brand.id,
            brand_name=row.brand.name,
            capture_mode=CATALOG_CAPTURE_MODE_PRODUCT_DIRECT,  # type: ignore[arg-type]
            current_price=price,
            currency_code=product.currency_code,
            price_owner="product_unit_price",
            standard_cost=product.standard_cost,
            price_cost_delta=delta,
            margin_percent=margin_percent,
            status=self._product_price_status(row),  # type: ignore[arg-type]
            health=health,  # type: ignore[arg-type]
            warnings=warnings,
            related_product_id=product.id,
            related_class_id=row.product_class.id,
            updated_at=product.updated_at,
        )

    def _to_class_price_row_view(self, row: _PriceClassRow) -> AdminPriceRowView:
        product_class = row.product_class
        price = product_class.class_capture_unit_price
        warnings = self._build_class_price_warnings(row)
        health = self._resolve_price_health(price=price, warnings=warnings)
        return AdminPriceRowView(
            entity_id=product_class.id,
            entity_type="class",
            entity_name=product_class.name,
            entity_code=product_class.code,
            class_id=product_class.id,
            class_name=product_class.name,
            brand_id=row.brand.id,
            brand_name=row.brand.name,
            capture_mode=CATALOG_CAPTURE_MODE_CLASS_CAPTURE,  # type: ignore[arg-type]
            current_price=price,
            currency_code=product_class.currency_code,
            price_owner="class_capture_unit_price",
            standard_cost=None,
            price_cost_delta=None,
            margin_percent=None,
            status=self._class_price_status(product_class),  # type: ignore[arg-type]
            health=health,  # type: ignore[arg-type]
            warnings=warnings,
            related_product_id=None,
            related_class_id=product_class.id,
            updated_at=product_class.updated_at,
        )

    def _build_product_price_warnings(
        self,
        row: _PriceProductRow,
        *,
        delta: Decimal | None,
        margin_percent: Decimal | None,
    ) -> AdminPriceWarningsView:
        warnings: list[tuple[str, str]] = []
        if row.product.unit_price <= Decimal("0"):
            warnings.append(("missing_or_zero_price", "El producto directo no tiene precio comercial valido."))
        if row.product.standard_cost is None:
            warnings.append(("missing_standard_cost", "No hay costo estandar para comparar margen."))
        if delta is not None and delta < Decimal("0"):
            warnings.append(("price_below_standard_cost", "El precio esta por debajo del costo estandar."))
        elif margin_percent is not None and margin_percent < LOW_MARGIN_WARNING_THRESHOLD:
            warnings.append(("low_margin", "El margen estimado esta por debajo del umbral operativo."))
        if self._product_price_status(row) == "inactive" and row.product.unit_price > Decimal("0"):
            warnings.append(("inactive_entity_has_price", "La entidad no esta activa/vendible y conserva precio."))
        if not row.product_class.is_active or not row.product_class.is_sellable:
            warnings.append(("source_class_not_sellable", "La clase fuente no esta lista para venta."))

        return AdminPriceWarningsView(
            codes=[code for code, _ in warnings],
            messages=[message for _, message in warnings],
        )

    def _build_class_price_warnings(self, row: _PriceClassRow) -> AdminPriceWarningsView:
        warnings: list[tuple[str, str]] = []
        if row.product_class.class_capture_unit_price is None or row.product_class.class_capture_unit_price <= Decimal("0"):
            warnings.append(("missing_or_zero_price", "La clase CLASS_CAPTURE no tiene precio comercial valido."))
        if self._class_price_status(row.product_class) == "inactive" and (
            row.product_class.class_capture_unit_price is not None
            and row.product_class.class_capture_unit_price > Decimal("0")
        ):
            warnings.append(("inactive_entity_has_price", "La clase no esta activa/vendible y conserva precio."))
        if row.product_count == 0:
            warnings.append(("class_without_products", "La clase no tiene productos asociados."))

        return AdminPriceWarningsView(
            codes=[code for code, _ in warnings],
            messages=[message for _, message in warnings],
        )

    def _resolve_price_health(
        self,
        *,
        price: Decimal | None,
        warnings: AdminPriceWarningsView,
    ) -> str:
        if price is None or price <= Decimal("0") or "missing_or_zero_price" in warnings.codes:
            return "missing_price"
        if "price_below_standard_cost" in warnings.codes:
            return "negative_margin"
        if "low_margin" in warnings.codes:
            return "low_margin"
        if warnings.codes:
            return "warning"
        return "healthy"

    def _product_price_status(self, row: _PriceProductRow) -> str:
        if (
            row.product.is_active
            and row.product.is_sellable
            and row.product_class.is_active
            and row.product_class.is_sellable
        ):
            return "active"
        return "inactive"

    def _class_price_status(self, product_class: ProductClass) -> str:
        if product_class.is_active and product_class.is_sellable:
            return "active"
        return "inactive"

    def _build_price_metrics(self, items: list[AdminPriceRowView]) -> AdminPriceMetricsView:
        recent_threshold = datetime.now(tz=UTC) - timedelta(days=7)
        return AdminPriceMetricsView(
            total_entities=len(items),
            product_direct=sum(1 for item in items if item.entity_type == "product"),
            class_capture=sum(1 for item in items if item.entity_type == "class"),
            missing_or_invalid=sum(1 for item in items if item.health == "missing_price"),
            high_variance=sum(
                1 for item in items if item.health in {"low_margin", "negative_margin"}
            ),
            recently_changed=sum(
                1
                for item in items
                if item.updated_at is not None and item.updated_at >= recent_threshold
            ),
        )

    def _build_price_filter_options(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
    ) -> AdminPriceFilterOptionsView:
        brands = session.execute(
            select(Brand.id, Brand.name).where(Brand.is_active.is_(True)).order_by(Brand.name.asc())
        ).all()
        class_statement = (
            select(ProductClass.id, ProductClass.name)
            .where(ProductClass.is_active.is_(True))
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )
        if brand_id is not None:
            class_statement = class_statement.where(ProductClass.brand_id == brand_id)
        return AdminPriceFilterOptionsView(
            brands=[
                AdminProductFilterOptionView(id=brand_option_id, label=brand_name)
                for brand_option_id, brand_name in brands
            ],
            classes=[
                AdminProductFilterOptionView(id=class_option_id, label=class_name)
                for class_option_id, class_name in session.execute(class_statement).all()
            ],
        )

    def _get_price_row_view(
        self,
        session: Session,
        *,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> AdminPriceRowView:
        normalized_entity_type = _normalize_optional(entity_type)
        if normalized_entity_type == "product":
            return self._to_product_price_row_view(self._get_price_product_row(session, entity_id))
        if normalized_entity_type == "class":
            return self._to_class_price_row_view(self._get_price_class_row(session, entity_id))
        raise AdminProductValidationError("Unsupported price entity type.")

    def _get_price_product_row(self, session: Session, product_id: uuid.UUID) -> _PriceProductRow:
        row = session.execute(
            select(Product, ProductClass, Brand)
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .where(Product.id == product_id)
        ).one_or_none()
        if row is None:
            raise ProductNotFoundError("Product price entity was not found.")
        product, product_class, brand = row
        if product.product_kind != CATALOG_PRODUCT_KIND_FINISHED_GOOD:
            raise AdminProductValidationError("Only finished goods can be commercial price entities.")
        return _PriceProductRow(product=product, product_class=product_class, brand=brand)

    def _get_price_class_row(self, session: Session, class_id: uuid.UUID) -> _PriceClassRow:
        product_count = (
            select(func.count(Product.id))
            .where(Product.product_class_id == ProductClass.id)
            .correlate(ProductClass)
            .scalar_subquery()
        )
        row = session.execute(
            select(ProductClass, Brand, product_count)
            .select_from(ProductClass)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .where(ProductClass.id == class_id)
        ).one_or_none()
        if row is None:
            raise ProductClassNotFoundError("Class price entity was not found.")
        product_class, brand, product_count_value = row
        return _PriceClassRow(
            product_class=product_class,
            brand=brand,
            product_count=int(product_count_value or 0),
        )


class AdminRecipeCostCatalogService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_recipe_costs(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        recipe_state: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminRecipeCostsListResponse:
        if brand_id is not None:
            self._get_brand(session, brand_id)

        rows = self._fetch_recipe_cost_rows(
            session,
            brand_id=brand_id,
            class_id=class_id,
            search=search,
        )
        items = [self._to_recipe_cost_summary(session, row) for row in rows]

        normalized_recipe_state = _normalize_optional(recipe_state) or "all"
        if normalized_recipe_state not in {"all", "no_recipe", "active_recipe", "warning"}:
            raise AdminProductValidationError("Unsupported recipe state filter.")
        if normalized_recipe_state == "no_recipe":
            items = [item for item in items if item.active_recipe_id is None]
        elif normalized_recipe_state == "active_recipe":
            items = [item for item in items if item.active_recipe_id is not None]
        elif normalized_recipe_state == "warning":
            items = [item for item in items if item.health_status != "healthy"]

        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), 100)
        offset = (safe_page - 1) * safe_page_size

        return AdminRecipeCostsListResponse(
            items=items[offset : offset + safe_page_size],
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            metrics=self._build_recipe_cost_metrics(items),
            filter_options=self._build_recipe_cost_filter_options(session, brand_id=brand_id),
        )

    def get_product_recipe_detail(
        self,
        session: Session,
        *,
        product_id: uuid.UUID,
    ) -> AdminRecipeCostDetailView:
        row = self._get_recipe_cost_row(session, product_id)
        product = self._to_recipe_cost_summary(session, row)
        versions = self._list_recipe_versions(session, product_id)
        active_recipe = next((recipe for recipe in versions if recipe.is_active), None)
        return AdminRecipeCostDetailView(
            product=product,
            active_recipe=active_recipe,
            recipe_versions=versions,
        )

    def create_recipe(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminRecipeCreateRequest,
        request_id: str | None,
    ) -> AdminRecipeCostDetailView:
        product = self._get_product(session, command.product_id)
        if product.product_kind != CATALOG_PRODUCT_KIND_FINISHED_GOOD:
            raise AdminProductValidationError("Recipes can only target finished goods.")
        self._validate_recipe_inputs(session, command.inputs)

        recipe = Recipe(
            product_id=product.id,
            version_name=_normalize_optional(command.version_name),
            yield_qty=command.yield_qty,
            yield_uom=command.yield_uom.strip(),
            is_active=command.activate,
            created_by_user_id=current_user.id,
        )

        try:
            if command.activate:
                self._deactivate_other_recipes(session, product.id)
            session.add(recipe)
            session.flush()
            for index, input_command in enumerate(command.inputs):
                session.add(
                    RecipeInput(
                        recipe_id=recipe.id,
                        input_product_id=input_command.input_product_id,
                        quantity=input_command.quantity,
                        display_order=(index + 1) * 10,
                    )
                )
            session.flush()
            self._record_recipe_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_ADMIN_RECIPE_CREATED,
                event_name=OUTBOX_EVENT_ADMIN_RECIPE_CREATED_V1,
                recipe=recipe,
                request_id=request_id,
                metadata=self._recipe_snapshot(session, recipe),
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminProductValidationError("Recipe violates catalog integrity.") from error

        return self.get_product_recipe_detail(session, product_id=product.id)

    def activate_recipe(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        recipe_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminRecipeCostDetailView:
        recipe = self._get_recipe(session, recipe_id)
        self._deactivate_other_recipes(session, recipe.product_id)
        recipe.is_active = True
        self._record_recipe_change(
            session,
            current_user=current_user,
            action=AUDIT_ACTION_ADMIN_RECIPE_ACTIVATED,
            event_name=OUTBOX_EVENT_ADMIN_RECIPE_ACTIVATED_V1,
            recipe=recipe,
            request_id=request_id,
            metadata=self._recipe_snapshot(session, recipe),
        )
        session.commit()
        return self.get_product_recipe_detail(session, product_id=recipe.product_id)

    def duplicate_recipe(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        recipe_id: uuid.UUID,
        command: AdminRecipeDuplicateRequest,
        request_id: str | None,
    ) -> AdminRecipeCostDetailView:
        source_recipe = self._get_recipe(session, recipe_id)
        source_inputs = self._list_recipe_input_rows(session, source_recipe.id)
        if not source_inputs:
            raise AdminProductValidationError("Cannot duplicate a recipe without inputs.")

        new_recipe = Recipe(
            product_id=source_recipe.product_id,
            version_name=_normalize_optional(command.version_name)
            or f"Copia de {source_recipe.version_name or 'receta'}",
            yield_qty=source_recipe.yield_qty,
            yield_uom=source_recipe.yield_uom,
            is_active=command.activate,
            created_by_user_id=current_user.id,
        )

        try:
            if command.activate:
                self._deactivate_other_recipes(session, source_recipe.product_id)
            session.add(new_recipe)
            session.flush()
            for recipe_input, _ in source_inputs:
                session.add(
                    RecipeInput(
                        recipe_id=new_recipe.id,
                        input_product_id=recipe_input.input_product_id,
                        quantity=recipe_input.quantity,
                        display_order=recipe_input.display_order,
                    )
                )
            session.flush()
            self._record_recipe_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_ADMIN_RECIPE_DUPLICATED,
                event_name=OUTBOX_EVENT_ADMIN_RECIPE_DUPLICATED_V1,
                recipe=new_recipe,
                request_id=request_id,
                metadata={
                    "source_recipe_id": str(source_recipe.id),
                    **self._recipe_snapshot(session, new_recipe),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise AdminProductValidationError("Recipe duplicate violates catalog integrity.") from error

        return self.get_product_recipe_detail(session, product_id=new_recipe.product_id)

    def apply_recipe_cost_to_product(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        recipe_id: uuid.UUID,
        request_id: str | None,
    ) -> AdminRecipeCostDetailView:
        recipe = self._get_recipe(session, recipe_id)
        product = self._get_product(session, recipe.product_id)
        recipe_view = self._to_recipe_view(session, recipe)
        if recipe_view.calculated_unit_cost is None:
            raise AdminProductValidationError("Recipe cost cannot be calculated while inputs miss standard cost.")

        previous_cost = product.standard_cost
        product.standard_cost = recipe_view.calculated_unit_cost
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=AUDIT_ACTION_ADMIN_PRODUCT_STANDARD_COST_UPDATED,
            resource_type=PRODUCT_RESOURCE_TYPE,
            resource_id=str(product.id),
            branch_id=None,
            request_id=request_id,
            metadata={
                "recipe_id": str(recipe.id),
                "previous_standard_cost": str(previous_cost) if previous_cost is not None else None,
                "new_standard_cost": str(product.standard_cost),
            },
        )
        self._outbox_writer.append(
            session,
            aggregate_type=PRODUCT_RESOURCE_TYPE,
            aggregate_id=str(product.id),
            event_name=OUTBOX_EVENT_ADMIN_PRODUCT_STANDARD_COST_UPDATED_V1,
            payload={
                "product_id": str(product.id),
                "recipe_id": str(recipe.id),
                "previous_standard_cost": str(previous_cost) if previous_cost is not None else None,
                "new_standard_cost": str(product.standard_cost),
            },
            headers={"request_id": request_id} if request_id else {},
        )
        session.commit()
        return self.get_product_recipe_detail(session, product_id=product.id)

    def _fetch_recipe_cost_rows(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        search: str | None,
    ) -> list[_RecipeCostRow]:
        recipe_count = (
            select(func.count(Recipe.id))
            .where(Recipe.product_id == Product.id)
            .correlate(Product)
            .scalar_subquery()
        )
        statement = (
            select(Product, ProductClass, Brand, Recipe, recipe_count)
            .select_from(Product)
            .join(ProductClass, ProductClass.id == Product.product_class_id)
            .join(Brand, Brand.id == ProductClass.brand_id)
            .outerjoin(Recipe, and_(Recipe.product_id == Product.id, Recipe.is_active.is_(True)))
            .where(Product.product_kind == CATALOG_PRODUCT_KIND_FINISHED_GOOD)
            .order_by(ProductClass.display_order.asc(), Product.display_order.asc(), Product.name.asc())
        )
        if brand_id is not None:
            statement = statement.where(ProductClass.brand_id == brand_id)
        if class_id is not None:
            statement = statement.where(Product.product_class_id == class_id)
        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search}%"
            statement = statement.where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                )
            )

        return [
            _RecipeCostRow(
                product=product,
                product_class=product_class,
                brand=brand,
                active_recipe=recipe,
                recipe_count=int(recipe_count_value or 0),
            )
            for product, product_class, brand, recipe, recipe_count_value in session.execute(statement).all()
        ]

    def _to_recipe_cost_summary(
        self,
        session: Session,
        row: _RecipeCostRow,
    ) -> AdminRecipeCostProductSummaryView:
        recipe_view = self._to_recipe_view(session, row.active_recipe) if row.active_recipe else None
        warnings = self._build_recipe_warnings(row, recipe_view)
        calculated_unit_cost = recipe_view.calculated_unit_cost if recipe_view else None
        cost_variance = None
        cost_variance_percent = None
        if calculated_unit_cost is not None and row.product.standard_cost is not None:
            cost_variance = calculated_unit_cost - row.product.standard_cost
            if row.product.standard_cost != Decimal("0"):
                cost_variance_percent = (cost_variance / row.product.standard_cost) * Decimal("100")

        health_status = "healthy"
        if row.active_recipe is None:
            health_status = "no_recipe"
        elif "recipe_cost_incomplete" in warnings.codes:
            health_status = "incomplete"
        elif warnings.codes:
            health_status = "warning"

        return AdminRecipeCostProductSummaryView(
            product_id=row.product.id,
            product_code=row.product.code,
            product_name=row.product.name,
            class_id=row.product_class.id,
            class_name=row.product_class.name,
            brand_id=row.brand.id,
            brand_name=row.brand.name,
            unit_of_measure=row.product.unit_of_measure,
            product_status=_product_status(row.product),
            product_standard_cost=row.product.standard_cost,
            product_unit_price=row.product.unit_price,
            currency_code=row.product.currency_code,
            active_recipe_id=row.active_recipe.id if row.active_recipe else None,
            active_recipe_version_name=row.active_recipe.version_name if row.active_recipe else None,
            active_recipe_updated_at=row.active_recipe.updated_at if row.active_recipe else None,
            recipe_input_count=recipe_view.input_count if recipe_view else 0,
            yield_qty=recipe_view.yield_qty if recipe_view else None,
            yield_uom=recipe_view.yield_uom if recipe_view else None,
            total_batch_cost=recipe_view.total_batch_cost if recipe_view else None,
            calculated_unit_cost=calculated_unit_cost,
            cost_variance=cost_variance,
            cost_variance_percent=cost_variance_percent,
            health_status=health_status,  # type: ignore[arg-type]
            warnings=warnings,
            updated_at=row.active_recipe.updated_at if row.active_recipe else row.product.updated_at,
        )

    def _build_recipe_warnings(
        self,
        row: _RecipeCostRow,
        recipe_view: AdminRecipeView | None,
    ) -> AdminRecipeCostWarningsView:
        warnings: list[tuple[str, str]] = []
        if row.active_recipe is None:
            warnings.append(("no_active_recipe", "El producto no tiene receta activa."))
        if row.product.standard_cost is None:
            warnings.append(("missing_product_standard_cost", "El producto no tiene costo estandar."))
        if row.product.is_active and not row.product.is_sellable:
            warnings.append(("product_not_sellable", "El producto esta activo pero no vendible."))
        if recipe_view is not None:
            if recipe_view.input_count == 0:
                warnings.append(("recipe_without_inputs", "La receta no tiene insumos."))
            if recipe_view.calculated_unit_cost is None:
                warnings.append(("recipe_cost_incomplete", "Hay insumos sin costo estandar."))
            if (
                recipe_view.calculated_unit_cost is not None
                and row.product.standard_cost is not None
                and row.product.standard_cost != Decimal("0")
            ):
                variance_percent = (
                    abs(recipe_view.calculated_unit_cost - row.product.standard_cost)
                    / row.product.standard_cost
                ) * Decimal("100")
                if variance_percent > COST_VARIANCE_WARNING_THRESHOLD:
                    warnings.append(("high_cost_variance", "El costo calculado difiere del costo estandar."))
            for recipe_input in recipe_view.inputs:
                if recipe_input.status != "active":
                    warnings.append(("inactive_raw_material", "La receta usa insumos inactivos."))
                    break

        return AdminRecipeCostWarningsView(
            codes=[code for code, _ in warnings],
            messages=[message for _, message in warnings],
        )

    def _to_recipe_view(self, session: Session, recipe: Recipe | None) -> AdminRecipeView:
        if recipe is None:
            raise RecipeNotFoundError("Recipe was not found.")
        input_rows = self._list_recipe_input_rows(session, recipe.id)
        inputs = [
            self._to_recipe_input_view(recipe_input, input_product)
            for recipe_input, input_product in input_rows
        ]
        total_batch_cost: Decimal | None = Decimal("0")
        for recipe_input in inputs:
            if recipe_input.extended_cost is None:
                total_batch_cost = None
                break
            total_batch_cost += recipe_input.extended_cost
        calculated_unit_cost = None
        if total_batch_cost is not None:
            calculated_unit_cost = total_batch_cost / recipe.yield_qty

        return AdminRecipeView(
            id=recipe.id,
            product_id=recipe.product_id,
            version_name=recipe.version_name,
            yield_qty=recipe.yield_qty,
            yield_uom=recipe.yield_uom,
            is_active=recipe.is_active,
            input_count=len(inputs),
            total_batch_cost=total_batch_cost,
            calculated_unit_cost=calculated_unit_cost,
            created_at=recipe.created_at,
            updated_at=recipe.updated_at,
            inputs=inputs,
        )

    def _to_recipe_input_view(
        self,
        recipe_input: RecipeInput,
        input_product: Product,
    ) -> AdminRecipeInputView:
        extended_cost = None
        if input_product.standard_cost is not None:
            extended_cost = input_product.standard_cost * recipe_input.quantity
        return AdminRecipeInputView(
            id=recipe_input.id,
            input_product_id=input_product.id,
            input_product_code=input_product.code,
            input_product_name=input_product.name,
            unit_of_measure=input_product.unit_of_measure,
            quantity=recipe_input.quantity,
            standard_cost=input_product.standard_cost,
            extended_cost=extended_cost,
            status=_product_status(input_product),
        )

    def _list_recipe_versions(self, session: Session, product_id: uuid.UUID) -> list[AdminRecipeView]:
        recipes = session.execute(
            select(Recipe)
            .where(Recipe.product_id == product_id)
            .order_by(Recipe.is_active.desc(), Recipe.updated_at.desc())
        ).scalars()
        return [self._to_recipe_view(session, recipe) for recipe in recipes]

    def _list_recipe_input_rows(
        self,
        session: Session,
        recipe_id: uuid.UUID,
    ) -> list[tuple[RecipeInput, Product]]:
        return list(
            session.execute(
                select(RecipeInput, Product)
                .join(Product, Product.id == RecipeInput.input_product_id)
                .where(RecipeInput.recipe_id == recipe_id)
                .order_by(RecipeInput.display_order.asc(), Product.name.asc())
            ).all()
        )

    def _build_recipe_cost_metrics(
        self,
        items: list[AdminRecipeCostProductSummaryView],
    ) -> AdminRecipeCostMetricsView:
        return AdminRecipeCostMetricsView(
            with_active_recipe=sum(1 for item in items if item.active_recipe_id is not None),
            without_recipe=sum(1 for item in items if item.active_recipe_id is None),
            with_warnings=sum(1 for item in items if item.warnings.codes),
            high_variance=sum(1 for item in items if "high_cost_variance" in item.warnings.codes),
            recently_updated=sum(1 for item in items if item.active_recipe_updated_at is not None),
        )

    def _build_recipe_cost_filter_options(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
    ) -> AdminRecipeCostFilterOptionsView:
        brands = session.execute(
            select(Brand.id, Brand.name).where(Brand.is_active.is_(True)).order_by(Brand.name.asc())
        ).all()
        class_statement = (
            select(ProductClass.id, ProductClass.name)
            .where(ProductClass.is_active.is_(True))
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        )
        if brand_id is not None:
            class_statement = class_statement.where(ProductClass.brand_id == brand_id)
        raw_materials = session.execute(
            select(Product.id, Product.name)
            .where(Product.product_kind == CATALOG_PRODUCT_KIND_RAW_MATERIAL, Product.is_active.is_(True))
            .order_by(Product.name.asc())
        ).all()
        return AdminRecipeCostFilterOptionsView(
            brands=[
                AdminProductFilterOptionView(id=brand_option_id, label=brand_name)
                for brand_option_id, brand_name in brands
            ],
            classes=[
                AdminProductFilterOptionView(id=class_id, label=class_name)
                for class_id, class_name in session.execute(class_statement).all()
            ],
            raw_materials=[
                AdminProductFilterOptionView(id=product_id, label=product_name)
                for product_id, product_name in raw_materials
            ],
        )

    def _get_recipe_cost_row(self, session: Session, product_id: uuid.UUID) -> _RecipeCostRow:
        rows = self._fetch_recipe_cost_rows(session, brand_id=None, class_id=None, search=None)
        row = next((item for item in rows if item.product.id == product_id), None)
        if row is None:
            raise ProductNotFoundError("Finished product was not found.")
        return row

    def _get_product(self, session: Session, product_id: uuid.UUID) -> Product:
        product = session.execute(select(Product).where(Product.id == product_id)).scalar_one_or_none()
        if product is None:
            raise ProductNotFoundError("Product was not found.")
        return product

    def _get_recipe(self, session: Session, recipe_id: uuid.UUID) -> Recipe:
        recipe = session.execute(select(Recipe).where(Recipe.id == recipe_id)).scalar_one_or_none()
        if recipe is None:
            raise RecipeNotFoundError("Recipe was not found.")
        return recipe

    def _get_brand(self, session: Session, brand_id: uuid.UUID) -> Brand:
        brand = session.execute(select(Brand).where(Brand.id == brand_id)).scalar_one_or_none()
        if brand is None:
            raise AdminProductValidationError("Brand was not found.")
        return brand

    def _validate_recipe_inputs(
        self,
        session: Session,
        inputs: list[object],
    ) -> None:
        if not inputs:
            raise AdminProductValidationError("Recipe requires at least one input.")
        input_ids = [input_command.input_product_id for input_command in inputs]  # type: ignore[attr-defined]
        if len(input_ids) != len(set(input_ids)):
            raise AdminProductValidationError("Recipe cannot contain duplicate input products.")
        products = session.execute(select(Product).where(Product.id.in_(input_ids))).scalars().all()
        products_by_id = {product.id: product for product in products}
        for input_id in input_ids:
            product = products_by_id.get(input_id)
            if product is None:
                raise ProductNotFoundError("Recipe input product was not found.")
            if product.product_kind != CATALOG_PRODUCT_KIND_RAW_MATERIAL:
                raise AdminProductValidationError("Recipe inputs must be RAW_MATERIAL products.")

    def _deactivate_other_recipes(self, session: Session, product_id: uuid.UUID) -> None:
        existing_recipes = session.execute(
            select(Recipe).where(Recipe.product_id == product_id, Recipe.is_active.is_(True))
        ).scalars()
        for recipe in existing_recipes:
            recipe.is_active = False

    def _record_recipe_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        action: str,
        event_name: str,
        recipe: Recipe,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=RECIPE_RESOURCE_TYPE,
            resource_id=str(recipe.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=RECIPE_RESOURCE_TYPE,
            aggregate_id=str(recipe.id),
            event_name=event_name,
            payload={"recipe_id": str(recipe.id), **metadata},
            headers={"request_id": request_id} if request_id else {},
        )

    def _recipe_snapshot(self, session: Session, recipe: Recipe) -> dict[str, object]:
        recipe_view = self._to_recipe_view(session, recipe)
        return {
            "id": str(recipe.id),
            "product_id": str(recipe.product_id),
            "version_name": recipe.version_name,
            "yield_qty": str(recipe.yield_qty),
            "yield_uom": recipe.yield_uom,
            "is_active": recipe.is_active,
            "input_count": recipe_view.input_count,
            "total_batch_cost": (
                str(recipe_view.total_batch_cost) if recipe_view.total_batch_cost is not None else None
            ),
            "calculated_unit_cost": (
                str(recipe_view.calculated_unit_cost)
                if recipe_view.calculated_unit_cost is not None
                else None
            ),
        }


def _class_status(product_class: ProductClass) -> AdminProductClassStatus:
    if product_class.is_active:
        return "active"
    return "inactive"


def _build_class_warnings(row: _ProductClassRow) -> AdminProductClassWarningsView:
    product_class = row.product_class
    warnings: list[tuple[str, str]] = []
    if (
        product_class.capture_mode_default == CATALOG_CAPTURE_MODE_CLASS_CAPTURE
        and product_class.class_capture_unit_price is None
    ):
        warnings.append(("class_capture_missing_price", "CLASS_CAPTURE requiere precio de clase."))
    if product_class.capture_mode_default == CATALOG_CAPTURE_MODE_PRODUCT_DIRECT and row.product_count == 0:
        warnings.append(("product_direct_without_products", "PRODUCT_DIRECT no tiene productos asociados."))
    if product_class.is_active and not product_class.is_sellable:
        warnings.append(("active_not_sellable", "La clase esta activa pero no vendible."))
    if not product_class.is_active and row.active_product_count > 0:
        warnings.append(("inactive_with_active_products", "La clase inactiva conserva productos activos."))
    if not _normalize_optional(product_class.quick_name) and not _normalize_optional(product_class.search_aliases):
        warnings.append(("weak_search_metadata", "Faltan nombre corto o alias de busqueda."))

    return AdminProductClassWarningsView(
        codes=[code for code, _ in warnings],
        messages=[message for _, message in warnings],
    )


def _product_status(product: Product) -> AdminProductStatus:
    if product.is_active and product.is_sellable:
        return "active"
    return "inactive"


def _build_readiness(product: Product, product_class: ProductClass) -> AdminProductReadinessView:
    missing_requirements: list[str] = []
    if not product.code.strip():
        missing_requirements.append("code")
    if not product.name.strip():
        missing_requirements.append("name")
    if not product.product_class_id:
        missing_requirements.append("class")
    if product_class.capture_mode_default == CATALOG_CAPTURE_MODE_CLASS_CAPTURE:
        if product_class.class_capture_unit_price is None:
            missing_requirements.append("class_capture_price")
        price_readiness = "ready" if product_class.class_capture_unit_price is not None else "incomplete"
    else:
        price_readiness = "ready" if product.unit_price >= Decimal("0") else "incomplete"

    pos_visibility_readiness = (
        "ready"
        if product.is_active
        and product.is_sellable
        and product_class.is_active
        and product_class.is_sellable
        else "requires_attention"
    )
    status = "ready"
    if missing_requirements:
        status = "incomplete"
    elif pos_visibility_readiness != "ready":
        status = "requires_attention"

    return AdminProductReadinessView(
        status=status,  # type: ignore[arg-type]
        missing_requirements=missing_requirements,
        related=AdminProductRelatedReadinessView(
            price=price_readiness,  # type: ignore[arg-type]
            pos_visibility=pos_visibility_readiness,  # type: ignore[arg-type]
            branch_availability="pending_integration",
            inventory="pending_integration",
            recipe="pending_integration",
            audit_trail="ready",
        ),
    )


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None
