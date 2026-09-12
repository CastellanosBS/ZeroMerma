from __future__ import annotations

import uuid
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import TypedDict
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter
from sqlalchemy import Select, String, cast, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.config import ApiSettings, get_settings
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.application.visibility import (
    AuditVisibilityQueryService,
    BackofficeNotificationConfig,
    build_audit_actor_snapshot,
)
from zeromerma_api.modules.branches.application.access import (
    WorkstationAccessService,
    WorkstationContext,
)
from zeromerma_api.modules.branches.application.schemas import BranchSummary, WorkstationSummary
from zeromerma_api.modules.branches.infrastructure.models import Branch, Brand, Workstation
from zeromerma_api.modules.cash.application.schemas import CashSessionView
from zeromerma_api.modules.cash.application.services import CashSessionQueryService
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.discounts.application.schemas import (
    AdminCommercialDiscountBackendContractView,
    AdminCommercialDiscountCreateRequest,
    AdminCommercialDiscountDuplicateRequest,
    AdminCommercialDiscountFilterOptionsView,
    AdminCommercialDiscountFilterOptionView,
    AdminCommercialDiscountMetricsView,
    AdminCommercialDiscountsListResponse,
    AdminCommercialDiscountStatus,
    AdminCommercialDiscountUpdateRequest,
    AdminCommercialDiscountView,
    AdminCommercialDiscountWarningsView,
    CreateOperationalDiscountRequest,
    DiscountControlsView,
    DiscountsBootstrapResponse,
    DiscountsListResponse,
    OperationalDiscountCategoryView,
    OperationalDiscountDetailResponse,
    OperationalDiscountFilterOptionView,
    OperationalDiscountListItemView,
    OperationalDiscountMethodView,
    OperationalDiscountScopeView,
)
from zeromerma_api.modules.discounts.domain.constants import (
    AUDIT_ACTION_COMMERCIAL_DISCOUNT_CREATED,
    AUDIT_ACTION_COMMERCIAL_DISCOUNT_UPDATED,
    AUDIT_ACTION_OPERATIONAL_DISCOUNT_COMMITTED,
    AUDIT_ACTION_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_REQUESTED,
    COMMERCIAL_DISCOUNT_RESOURCE_TYPE,
    COMMERCIAL_DISCOUNT_SCOPE_CLASS,
    COMMERCIAL_DISCOUNT_SCOPE_GLOBAL,
    COMMERCIAL_DISCOUNT_SCOPE_PRODUCT,
    COMMERCIAL_DISCOUNT_STATUS_ACTIVE,
    COMMERCIAL_DISCOUNT_STATUS_ARCHIVED,
    COMMERCIAL_DISCOUNT_STATUS_INACTIVE,
    COMMERCIAL_DISCOUNT_TYPE_FIXED_AMOUNT,
    COMMERCIAL_DISCOUNT_TYPE_PERCENTAGE,
    DISCOUNT_LIST_SCOPE_CURRENT_SHIFT,
    DISCOUNT_LIST_SCOPE_RECENT,
    DISCOUNT_LIST_SCOPE_TODAY,
    DISCOUNT_STATUS_COMMITTED,
    OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
    OUTBOX_EVENT_COMMERCIAL_DISCOUNT_CREATED_V1,
    OUTBOX_EVENT_COMMERCIAL_DISCOUNT_UPDATED_V1,
    OUTBOX_EVENT_OPERATIONAL_DISCOUNT_COMMITTED_V1,
    OUTBOX_EVENT_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_V1,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_MIXED,
    SUPPORTED_OPERATIONAL_DISCOUNT_METHOD_CODES,
    VALID_OPERATIONAL_DISCOUNT_LIST_SCOPES,
    VALID_OPERATIONAL_DISCOUNT_METHOD_CODES,
)
from zeromerma_api.modules.discounts.domain.exceptions import (
    OperationalDiscountConflictError,
    OperationalDiscountNotFoundError,
    OperationalDiscountValidationError,
)
from zeromerma_api.modules.discounts.infrastructure.models import (
    CommercialDiscount,
    OperationalDiscount,
    OperationalDiscountCategory,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.operations.domain.constants import BRANCH_BRAND_MAPPING
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.sales.domain.constants import (
    CASH_MOVEMENT_DIRECTION_IN,
    CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT,
)
from zeromerma_api.modules.sales.infrastructure.models import CashMovement

_ADMIN_COMMERCIAL_DISCOUNT_STATUS_ADAPTER: TypeAdapter[AdminCommercialDiscountStatus] = TypeAdapter(
    AdminCommercialDiscountStatus
)
MAX_DISCOUNTS_PER_LIST = 80
MONEY_QUANTIZER = Decimal("0.01")
ZERO_MONEY = Decimal("0.00")
COMMERCIAL_DISCOUNT_PAGE_SIZE_MAX = 100

_DiscountTarget = TypedDict(
    "_DiscountTarget", {"product": Product | None, "class": ProductClass | None}
)


class AdminCommercialDiscountService:
    def __init__(
        self,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
    ) -> None:
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()

    def list_discounts(
        self,
        session: Session,
        *,
        brand_id: uuid.UUID | None,
        class_id: uuid.UUID | None,
        status_filter: str | None,
        discount_type: str | None,
        target_scope: str | None,
        validity: str | None,
        warning_state: str | None,
        search: str | None,
        page: int,
        page_size: int,
    ) -> AdminCommercialDiscountsListResponse:
        discounts = self._fetch_discounts(session, search=search)
        items = [self._to_discount_view(session, discount) for discount in discounts]

        normalized_brand_id = str(brand_id) if brand_id is not None else None
        if normalized_brand_id:
            items = [item for item in items if str(item.brand_id) == normalized_brand_id]

        normalized_class_id = str(class_id) if class_id is not None else None
        if normalized_class_id:
            items = [
                item
                for item in items
                if str(item.target_class_id) == normalized_class_id
                or (
                    item.target_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS
                    and str(item.target_id) == normalized_class_id
                )
            ]

        normalized_status = _normalize_optional(status_filter)
        if normalized_status and normalized_status != "all":
            self._validate_status_filter(normalized_status)
            items = [item for item in items if item.status == normalized_status]

        normalized_type = _normalize_optional(discount_type)
        if normalized_type and normalized_type != "all":
            self._validate_type_filter(normalized_type)
            items = [item for item in items if item.discount_type == normalized_type]

        normalized_scope = _normalize_optional(target_scope)
        if normalized_scope and normalized_scope != "all":
            self._validate_scope_filter(normalized_scope)
            items = [item for item in items if item.target_scope == normalized_scope]

        normalized_validity = _normalize_optional(validity)
        if normalized_validity and normalized_validity != "all":
            if normalized_validity not in {"current", "upcoming", "expired", "not_scheduled"}:
                raise OperationalDiscountValidationError("Unsupported discount validity filter.")
            items = [item for item in items if item.validity_status == normalized_validity]

        normalized_warning_state = _normalize_optional(warning_state)
        if normalized_warning_state and normalized_warning_state != "all":
            if normalized_warning_state == "with_warnings":
                items = [item for item in items if item.warnings.codes]
            elif normalized_warning_state == "without_warnings":
                items = [item for item in items if not item.warnings.codes]
            else:
                raise OperationalDiscountValidationError("Unsupported discount warning filter.")

        total = len(items)
        safe_page = max(page, 1)
        safe_page_size = min(max(page_size, 1), COMMERCIAL_DISCOUNT_PAGE_SIZE_MAX)
        offset = (safe_page - 1) * safe_page_size

        return AdminCommercialDiscountsListResponse(
            backend_contract=AdminCommercialDiscountBackendContractView(),
            is_backend_connected=True,
            items=items[offset : offset + safe_page_size],
            total=total,
            page=safe_page,
            page_size=safe_page_size,
            metrics=self._build_metrics(items),
            filter_options=self._build_filter_options(session),
        )

    def get_discount_detail(
        self,
        session: Session,
        *,
        discount_id: uuid.UUID,
    ) -> AdminCommercialDiscountView:
        return self._to_discount_view(session, self._get_discount(session, discount_id))

    def create_discount(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: AdminCommercialDiscountCreateRequest,
        request_id: str | None,
    ) -> AdminCommercialDiscountView:
        target = self._resolve_target(
            session, target_scope=command.target_scope, target_id=command.target_id
        )
        brand_id = self._resolve_brand_id(
            explicit_brand_id=command.brand_id,
            target_scope=command.target_scope,
            target=target,
        )
        self._validate_discount_shape(
            discount_type=command.discount_type,
            value=command.value,
            currency_code=command.currency_code,
            target_scope=command.target_scope,
            target=target,
        )
        discount = CommercialDiscount(
            brand_id=brand_id,
            product_id=target["product"].id if target["product"] is not None else None,
            product_class_id=target["class"].id
            if command.target_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS
            and target["class"] is not None
            else None,
            code=_normalize_optional(command.code),
            name=command.name.strip(),
            description=_normalize_optional(command.description),
            discount_type=command.discount_type,
            target_scope=command.target_scope,
            value=command.value,
            currency_code=command.currency_code.strip().upper(),
            valid_from_utc=command.valid_from_utc,
            valid_to_utc=command.valid_to_utc,
            priority=command.priority,
            is_pos_eligible=command.is_pos_eligible,
            status=command.status,
            created_by_user_id=current_user.id,
        )

        try:
            session.add(discount)
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_COMMERCIAL_DISCOUNT_CREATED,
                event_name=OUTBOX_EVENT_COMMERCIAL_DISCOUNT_CREATED_V1,
                discount=discount,
                request_id=request_id,
                metadata={"current": self._discount_snapshot(discount)},
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationalDiscountValidationError("Discount code must be unique.") from error

        return self.get_discount_detail(session, discount_id=discount.id)

    def update_discount(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        discount_id: uuid.UUID,
        command: AdminCommercialDiscountUpdateRequest,
        request_id: str | None,
    ) -> AdminCommercialDiscountView:
        discount = self._get_discount(session, discount_id)
        previous_snapshot = self._discount_snapshot(discount)

        next_scope = (
            command.target_scope if command.target_scope is not None else discount.target_scope
        )
        next_target_id = command.target_id
        if command.target_scope is None and "target_id" not in command.model_fields_set:
            next_target_id = (
                discount.product_id
                if discount.target_scope == COMMERCIAL_DISCOUNT_SCOPE_PRODUCT
                else discount.product_class_id
            )
        target = self._resolve_target(session, target_scope=next_scope, target_id=next_target_id)
        next_type = (
            command.discount_type if command.discount_type is not None else discount.discount_type
        )
        next_value = command.value if command.value is not None else discount.value
        next_currency = (
            command.currency_code if command.currency_code is not None else discount.currency_code
        )
        self._validate_discount_shape(
            discount_type=next_type,
            value=next_value,
            currency_code=next_currency,
            target_scope=next_scope,
            target=target,
        )

        if command.name is not None:
            discount.name = command.name.strip()
        if "code" in command.model_fields_set:
            discount.code = _normalize_optional(command.code)
        if "description" in command.model_fields_set:
            discount.description = _normalize_optional(command.description)
        if command.discount_type is not None:
            discount.discount_type = command.discount_type
        if command.value is not None:
            discount.value = command.value
        if command.currency_code is not None:
            discount.currency_code = command.currency_code.strip().upper()
        if command.target_scope is not None or "target_id" in command.model_fields_set:
            discount.target_scope = next_scope
            discount.product_id = target["product"].id if target["product"] is not None else None
            discount.product_class_id = (
                target["class"].id
                if next_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS and target["class"] is not None
                else None
            )
        if "brand_id" in command.model_fields_set:
            discount.brand_id = self._resolve_brand_id(
                explicit_brand_id=command.brand_id,
                target_scope=discount.target_scope,
                target=target,
            )
        elif command.target_scope is not None or "target_id" in command.model_fields_set:
            discount.brand_id = self._resolve_brand_id(
                explicit_brand_id=discount.brand_id,
                target_scope=discount.target_scope,
                target=target,
            )
        if "valid_from_utc" in command.model_fields_set:
            discount.valid_from_utc = command.valid_from_utc
        if "valid_to_utc" in command.model_fields_set:
            discount.valid_to_utc = command.valid_to_utc
        if command.priority is not None:
            discount.priority = command.priority
        if command.is_pos_eligible is not None:
            discount.is_pos_eligible = command.is_pos_eligible
        if command.status is not None:
            discount.status = command.status

        self._validate_validity_range(discount.valid_from_utc, discount.valid_to_utc)

        try:
            session.flush()
            self._record_change(
                session,
                current_user=current_user,
                action=AUDIT_ACTION_COMMERCIAL_DISCOUNT_UPDATED,
                event_name=OUTBOX_EVENT_COMMERCIAL_DISCOUNT_UPDATED_V1,
                discount=discount,
                request_id=request_id,
                metadata={
                    "previous": previous_snapshot,
                    "current": self._discount_snapshot(discount),
                },
            )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationalDiscountValidationError(
                "Discount update violates commercial rules."
            ) from error

        return self.get_discount_detail(session, discount_id=discount.id)

    def duplicate_discount(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        discount_id: uuid.UUID,
        command: AdminCommercialDiscountDuplicateRequest,
        request_id: str | None,
    ) -> AdminCommercialDiscountView:
        source = self._get_discount(session, discount_id)
        payload = AdminCommercialDiscountCreateRequest(
            brand_id=source.brand_id,
            code=_normalize_optional(command.code),
            description=source.description,
            discount_type=source.discount_type,  # type: ignore[arg-type]
            is_pos_eligible=source.is_pos_eligible,
            name=(command.name or f"{source.name} copia").strip(),
            priority=source.priority + 1,
            status=_ADMIN_COMMERCIAL_DISCOUNT_STATUS_ADAPTER.validate_python(
                COMMERCIAL_DISCOUNT_STATUS_INACTIVE
            ),
            target_id=source.product_id or source.product_class_id,
            target_scope=source.target_scope,  # type: ignore[arg-type]
            value=source.value,
            currency_code=source.currency_code,
            valid_from_utc=source.valid_from_utc,
            valid_to_utc=source.valid_to_utc,
        )
        return self.create_discount(
            session,
            current_user=current_user,
            command=payload,
            request_id=request_id,
        )

    def _fetch_discounts(self, session: Session, *, search: str | None) -> list[CommercialDiscount]:
        statement = select(CommercialDiscount).order_by(
            CommercialDiscount.priority.asc(),
            CommercialDiscount.updated_at.desc(),
        )
        normalized_search = _normalize_optional(search)
        if normalized_search:
            pattern = f"%{normalized_search}%"
            product_ids = select(Product.id).where(
                or_(
                    Product.code.ilike(pattern),
                    Product.name.ilike(pattern),
                    Product.quick_name.ilike(pattern),
                    Product.search_aliases.ilike(pattern),
                )
            )
            class_ids = select(ProductClass.id).where(
                or_(
                    ProductClass.code.ilike(pattern),
                    ProductClass.name.ilike(pattern),
                    ProductClass.quick_name.ilike(pattern),
                    ProductClass.search_aliases.ilike(pattern),
                )
            )
            statement = statement.where(
                or_(
                    CommercialDiscount.code.ilike(pattern),
                    CommercialDiscount.name.ilike(pattern),
                    CommercialDiscount.description.ilike(pattern),
                    CommercialDiscount.product_id.in_(product_ids),
                    CommercialDiscount.product_class_id.in_(class_ids),
                )
            )

        return list(session.execute(statement).scalars())

    def _to_discount_view(
        self,
        session: Session,
        discount: CommercialDiscount,
    ) -> AdminCommercialDiscountView:
        target = self._resolve_existing_target(session, discount)
        brand = self._resolve_existing_brand(session, discount, target)
        base_price = self._resolve_base_price(discount, target)
        preview_price = self._calculate_preview_price(discount, base_price)
        validity_status = self._validity_status(discount)
        warnings = self._build_warnings(
            discount, target, base_price, preview_price, validity_status
        )
        health = self._resolve_health(warnings, validity_status)

        target_product = target["product"]
        target_class = target["class"]
        target_id = None
        target_code = None
        target_name = None
        target_status = None
        target_class_id = None
        target_class_name = None
        if target_product is not None:
            target_id = target_product.id
            target_code = target_product.code
            target_name = target_product.name
            target_status = _discount_product_status(target_product)
            target_class_id = target_class.id if target_class is not None else None
            target_class_name = target_class.name if target_class is not None else None
        elif target_class is not None:
            target_id = target_class.id
            target_code = target_class.code
            target_name = target_class.name
            target_status = _discount_class_status(target_class)
            target_class_id = target_class.id
            target_class_name = target_class.name
        elif discount.target_scope == COMMERCIAL_DISCOUNT_SCOPE_GLOBAL:
            target_name = "Alcance global"

        return AdminCommercialDiscountView(
            id=discount.id,
            code=discount.code,
            name=discount.name,
            description=discount.description,
            discount_type=discount.discount_type,  # type: ignore[arg-type]
            target_scope=discount.target_scope,  # type: ignore[arg-type]
            target_id=target_id,
            target_code=target_code,
            target_name=target_name,
            target_status=target_status,
            target_class_id=target_class_id,
            target_class_name=target_class_name,
            brand_id=brand.id if brand is not None else None,
            brand_name=brand.name if brand is not None else None,
            value=discount.value,
            currency_code=discount.currency_code,
            base_price=base_price,
            preview_price=preview_price,
            status=discount.status,  # type: ignore[arg-type]
            validity_status=validity_status,  # type: ignore[arg-type]
            valid_from_utc=discount.valid_from_utc,
            valid_to_utc=discount.valid_to_utc,
            priority=discount.priority,
            is_pos_eligible=discount.is_pos_eligible,
            health=health,  # type: ignore[arg-type]
            warnings=warnings,
            created_at=discount.created_at,
            updated_at=discount.updated_at,
        )

    def _resolve_existing_target(
        self,
        session: Session,
        discount: CommercialDiscount,
    ) -> _DiscountTarget:
        if (
            discount.target_scope == COMMERCIAL_DISCOUNT_SCOPE_PRODUCT
            and discount.product_id is not None
        ):
            product = session.execute(
                select(Product).where(Product.id == discount.product_id)
            ).scalar_one_or_none()
            product_class = (
                session.execute(
                    select(ProductClass).where(ProductClass.id == product.product_class_id)
                ).scalar_one_or_none()
                if product is not None
                else None
            )
            return {"product": product, "class": product_class}
        if (
            discount.target_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS
            and discount.product_class_id is not None
        ):
            product_class = session.execute(
                select(ProductClass).where(ProductClass.id == discount.product_class_id)
            ).scalar_one_or_none()
            return {"product": None, "class": product_class}
        return {"product": None, "class": None}

    def _resolve_target(
        self,
        session: Session,
        *,
        target_scope: str,
        target_id: uuid.UUID | None,
    ) -> _DiscountTarget:
        self._validate_scope_filter(target_scope)
        if target_scope == COMMERCIAL_DISCOUNT_SCOPE_GLOBAL:
            if target_id is not None:
                raise OperationalDiscountValidationError(
                    "Global discounts cannot reference a target entity."
                )
            return {"product": None, "class": None}
        if target_id is None:
            raise OperationalDiscountValidationError("Discount target is required for this scope.")
        if target_scope == COMMERCIAL_DISCOUNT_SCOPE_PRODUCT:
            product = session.execute(
                select(Product).where(Product.id == target_id)
            ).scalar_one_or_none()
            if product is None:
                raise OperationalDiscountNotFoundError("Discount target product was not found.")
            product_class = session.execute(
                select(ProductClass).where(ProductClass.id == product.product_class_id)
            ).scalar_one()
            return {"product": product, "class": product_class}
        target_class = session.execute(
            select(ProductClass).where(ProductClass.id == target_id)
        ).scalar_one_or_none()
        if target_class is None:
            raise OperationalDiscountNotFoundError("Discount target class was not found.")
        return {"product": None, "class": target_class}

    def _resolve_existing_brand(
        self,
        session: Session,
        discount: CommercialDiscount,
        target: _DiscountTarget,
    ) -> Brand | None:
        if discount.brand_id is not None:
            return session.execute(
                select(Brand).where(Brand.id == discount.brand_id)
            ).scalar_one_or_none()
        target_class = target["class"]
        if isinstance(target_class, ProductClass):
            return session.execute(
                select(Brand).where(Brand.id == target_class.brand_id)
            ).scalar_one_or_none()
        return None

    def _resolve_brand_id(
        self,
        *,
        explicit_brand_id: uuid.UUID | None,
        target_scope: str,
        target: _DiscountTarget,
    ) -> uuid.UUID | None:
        target_class = target["class"]
        if isinstance(target_class, ProductClass):
            if explicit_brand_id is not None and explicit_brand_id != target_class.brand_id:
                raise OperationalDiscountValidationError("Discount brand must match target brand.")
            return target_class.brand_id
        if target_scope == COMMERCIAL_DISCOUNT_SCOPE_GLOBAL:
            return explicit_brand_id
        return explicit_brand_id

    def _resolve_base_price(
        self,
        discount: CommercialDiscount,
        target: _DiscountTarget,
    ) -> Decimal | None:
        if discount.target_scope == COMMERCIAL_DISCOUNT_SCOPE_PRODUCT:
            product = target["product"]
            return product.unit_price if isinstance(product, Product) else None
        if discount.target_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS:
            product_class = target["class"]
            return (
                product_class.class_capture_unit_price
                if isinstance(product_class, ProductClass)
                else None
            )
        return None

    def _calculate_preview_price(
        self,
        discount: CommercialDiscount,
        base_price: Decimal | None,
    ) -> Decimal | None:
        if base_price is None:
            return None
        if discount.discount_type == COMMERCIAL_DISCOUNT_TYPE_PERCENTAGE:
            multiplier = (Decimal("100") - discount.value) / Decimal("100")
            return (base_price * multiplier).quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
        return max(ZERO_MONEY, base_price - discount.value).quantize(
            MONEY_QUANTIZER, rounding=ROUND_HALF_UP
        )

    def _validity_status(self, discount: CommercialDiscount) -> str:
        now = datetime.now(tz=UTC)
        if discount.valid_from_utc is None and discount.valid_to_utc is None:
            return "not_scheduled"
        if discount.valid_from_utc is not None and now < discount.valid_from_utc:
            return "upcoming"
        if discount.valid_to_utc is not None and now > discount.valid_to_utc:
            return "expired"
        return "current"

    def _build_warnings(
        self,
        discount: CommercialDiscount,
        target: _DiscountTarget,
        base_price: Decimal | None,
        preview_price: Decimal | None,
        validity_status: str,
    ) -> AdminCommercialDiscountWarningsView:
        warnings: list[tuple[str, str]] = []
        if discount.value <= ZERO_MONEY:
            warnings.append(("invalid_value", "El descuento debe ser mayor a cero."))
        if (
            discount.discount_type == COMMERCIAL_DISCOUNT_TYPE_PERCENTAGE
            and discount.value > Decimal("100")
        ):
            warnings.append(("invalid_percentage", "El porcentaje no puede ser mayor a 100."))
        if discount.status == COMMERCIAL_DISCOUNT_STATUS_ACTIVE and validity_status == "expired":
            warnings.append(("active_expired", "El descuento esta activo pero su vigencia expiro."))
        if discount.target_scope in {
            COMMERCIAL_DISCOUNT_SCOPE_PRODUCT,
            COMMERCIAL_DISCOUNT_SCOPE_CLASS,
        }:
            if target["product"] is None and target["class"] is None:
                warnings.append(("missing_target", "El descuento no tiene un objetivo valido."))
        product = target["product"]
        product_class = target["class"]
        if isinstance(product, Product) and (not product.is_active or not product.is_sellable):
            warnings.append(
                ("target_product_inactive", "El producto objetivo no esta activo o vendible.")
            )
        if isinstance(product_class, ProductClass) and (
            not product_class.is_active or not product_class.is_sellable
        ):
            warnings.append(
                ("target_class_inactive", "La clase objetivo no esta activa o vendible.")
            )
        if (
            base_price is not None
            and discount.discount_type == COMMERCIAL_DISCOUNT_TYPE_FIXED_AMOUNT
        ):
            if discount.value >= base_price:
                warnings.append(
                    ("fixed_discount_exceeds_price", "El descuento fijo deja el precio en cero.")
                )
        if preview_price is not None and preview_price <= ZERO_MONEY:
            warnings.append(("zero_preview_price", "El precio estimado queda en cero."))
        if discount.status == COMMERCIAL_DISCOUNT_STATUS_ACTIVE and not discount.is_pos_eligible:
            warnings.append(
                ("active_not_pos_eligible", "El descuento esta activo pero no elegible para POS.")
            )

        return AdminCommercialDiscountWarningsView(
            codes=[code for code, _ in warnings],
            messages=[message for _, message in warnings],
        )

    def _resolve_health(
        self, warnings: AdminCommercialDiscountWarningsView, validity_status: str
    ) -> str:
        invalid_codes = {"invalid_value", "invalid_percentage", "missing_target"}
        if any(code in invalid_codes for code in warnings.codes):
            return "invalid"
        if "active_expired" in warnings.codes or validity_status == "expired":
            return "expired"
        if warnings.codes:
            return "warning"
        return "healthy"

    def _build_metrics(
        self,
        items: list[AdminCommercialDiscountView],
    ) -> AdminCommercialDiscountMetricsView:
        return AdminCommercialDiscountMetricsView(
            total_discounts=len(items),
            active_discounts=sum(
                1 for item in items if item.status == COMMERCIAL_DISCOUNT_STATUS_ACTIVE
            ),
            upcoming_discounts=sum(1 for item in items if item.validity_status == "upcoming"),
            expired_discounts=sum(1 for item in items if item.validity_status == "expired"),
            with_warnings=sum(1 for item in items if item.warnings.codes),
            product_scoped=sum(
                1 for item in items if item.target_scope == COMMERCIAL_DISCOUNT_SCOPE_PRODUCT
            ),
            class_scoped=sum(
                1 for item in items if item.target_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS
            ),
        )

    def _build_filter_options(self, session: Session) -> AdminCommercialDiscountFilterOptionsView:
        brands = session.execute(
            select(Brand.id, Brand.name).where(Brand.is_active.is_(True)).order_by(Brand.name.asc())
        ).all()
        classes = session.execute(
            select(ProductClass.id, ProductClass.name)
            .where(ProductClass.is_active.is_(True))
            .order_by(ProductClass.display_order.asc(), ProductClass.name.asc())
        ).all()
        products = session.execute(
            select(Product.id, Product.name)
            .where(Product.is_active.is_(True), Product.is_sellable.is_(True))
            .order_by(Product.name.asc())
        ).all()
        return AdminCommercialDiscountFilterOptionsView(
            brands=[
                AdminCommercialDiscountFilterOptionView(id=brand_id, label=brand_name)
                for brand_id, brand_name in brands
            ],
            classes=[
                AdminCommercialDiscountFilterOptionView(id=class_id, label=class_name)
                for class_id, class_name in classes
            ],
            products=[
                AdminCommercialDiscountFilterOptionView(id=product_id, label=product_name)
                for product_id, product_name in products
            ],
        )

    def _get_discount(self, session: Session, discount_id: uuid.UUID) -> CommercialDiscount:
        discount = session.execute(
            select(CommercialDiscount).where(CommercialDiscount.id == discount_id)
        ).scalar_one_or_none()
        if discount is None:
            raise OperationalDiscountNotFoundError("Commercial discount was not found.")
        return discount

    def _validate_discount_shape(
        self,
        *,
        discount_type: str,
        value: Decimal,
        currency_code: str,
        target_scope: str,
        target: _DiscountTarget,
    ) -> None:
        self._validate_type_filter(discount_type)
        self._validate_scope_filter(target_scope)
        if value <= ZERO_MONEY:
            raise OperationalDiscountValidationError("Discount value must be greater than zero.")
        if discount_type == COMMERCIAL_DISCOUNT_TYPE_PERCENTAGE and value > Decimal("100"):
            raise OperationalDiscountValidationError(
                "Percentage discounts must be less than or equal to 100."
            )
        if (
            discount_type == COMMERCIAL_DISCOUNT_TYPE_FIXED_AMOUNT
            and len(currency_code.strip()) != 3
        ):
            raise OperationalDiscountValidationError(
                "Fixed discounts require a three-letter currency code."
            )
        if target_scope == COMMERCIAL_DISCOUNT_SCOPE_PRODUCT and target["product"] is None:
            raise OperationalDiscountValidationError("Product discount requires a product target.")
        if target_scope == COMMERCIAL_DISCOUNT_SCOPE_CLASS and target["class"] is None:
            raise OperationalDiscountValidationError("Class discount requires a class target.")

    def _validate_validity_range(
        self,
        valid_from: datetime | None,
        valid_to: datetime | None,
    ) -> None:
        if valid_from is not None and valid_to is not None and valid_from >= valid_to:
            raise OperationalDiscountValidationError("Validity range must end after it starts.")

    def _validate_type_filter(self, value: str) -> None:
        if value not in {
            COMMERCIAL_DISCOUNT_TYPE_PERCENTAGE,
            COMMERCIAL_DISCOUNT_TYPE_FIXED_AMOUNT,
        }:
            raise OperationalDiscountValidationError("Unsupported commercial discount type.")

    def _validate_scope_filter(self, value: str) -> None:
        if value not in {
            COMMERCIAL_DISCOUNT_SCOPE_GLOBAL,
            COMMERCIAL_DISCOUNT_SCOPE_PRODUCT,
            COMMERCIAL_DISCOUNT_SCOPE_CLASS,
        }:
            raise OperationalDiscountValidationError("Unsupported commercial discount scope.")

    def _validate_status_filter(self, value: str) -> None:
        if value not in {
            COMMERCIAL_DISCOUNT_STATUS_ACTIVE,
            COMMERCIAL_DISCOUNT_STATUS_INACTIVE,
            COMMERCIAL_DISCOUNT_STATUS_ARCHIVED,
        }:
            raise OperationalDiscountValidationError("Unsupported commercial discount status.")

    def _record_change(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        action: str,
        event_name: str,
        discount: CommercialDiscount,
        request_id: str | None,
        metadata: dict[str, object],
    ) -> None:
        self._audit_recorder.record(
            session,
            actor_id=current_user.id,
            action=action,
            resource_type=COMMERCIAL_DISCOUNT_RESOURCE_TYPE,
            resource_id=str(discount.id),
            branch_id=None,
            request_id=request_id,
            metadata=metadata,
        )
        self._outbox_writer.append(
            session,
            aggregate_type=COMMERCIAL_DISCOUNT_RESOURCE_TYPE,
            aggregate_id=str(discount.id),
            event_name=event_name,
            payload={"discount_id": str(discount.id), **metadata},
            headers={"request_id": request_id} if request_id else {},
        )

    def _discount_snapshot(self, discount: CommercialDiscount) -> dict[str, object | None]:
        return {
            "id": str(discount.id),
            "brand_id": str(discount.brand_id) if discount.brand_id else None,
            "product_id": str(discount.product_id) if discount.product_id else None,
            "product_class_id": str(discount.product_class_id)
            if discount.product_class_id
            else None,
            "code": discount.code,
            "name": discount.name,
            "discount_type": discount.discount_type,
            "target_scope": discount.target_scope,
            "value": str(discount.value),
            "currency_code": discount.currency_code,
            "valid_from_utc": discount.valid_from_utc.isoformat()
            if discount.valid_from_utc
            else None,
            "valid_to_utc": discount.valid_to_utc.isoformat() if discount.valid_to_utc else None,
            "priority": discount.priority,
            "is_pos_eligible": discount.is_pos_eligible,
            "status": discount.status,
        }


class DiscountsQueryService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        settings: ApiSettings | None = None,
        audit_visibility: AuditVisibilityQueryService | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._settings = settings or get_settings()
        self._audit_visibility = audit_visibility or AuditVisibilityQueryService()

    def get_bootstrap(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
    ) -> DiscountsBootstrapResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = self._cash_session_query.get_open_session_for_workstation_code(
            session,
            workstation_code=workstation_code,
        )
        local_timestamp = datetime.now(tz=UTC).astimezone(ZoneInfo(context.branch_timezone))
        categories = session.execute(
            select(OperationalDiscountCategory)
            .where(OperationalDiscountCategory.is_active.is_(True))
            .order_by(
                OperationalDiscountCategory.display_order.asc(),
                OperationalDiscountCategory.name.asc(),
            )
        ).scalars()

        return DiscountsBootstrapResponse(
            user=current_user,
            branch=BranchSummary(
                id=context.branch_id,
                code=context.branch_code,
                name=context.branch_name,
                timezone=context.branch_timezone,
                is_active=context.branch_is_active,
            ),
            workstation=WorkstationSummary(
                id=context.workstation_id,
                code=context.workstation_code,
                name=context.workstation_name,
                is_active=context.workstation_is_active,
            ),
            local_timestamp=local_timestamp,
            current_open_cash_session=current_open_cash_session,
            branch_brand_key=_get_branch_brand_key(context.branch_code),
            discount_registration_allowed=(
                current_open_cash_session is not None
                and current_open_cash_session.user_id == current_user.id
            ),
            default_scope=DISCOUNT_LIST_SCOPE_CURRENT_SHIFT,
            available_scopes=[
                OperationalDiscountScopeView(
                    code=DISCOUNT_LIST_SCOPE_CURRENT_SHIFT,
                    label="Turno actual",
                ),
                OperationalDiscountScopeView(code=DISCOUNT_LIST_SCOPE_TODAY, label="Hoy"),
                OperationalDiscountScopeView(code=DISCOUNT_LIST_SCOPE_RECENT, label="Recientes"),
            ],
            active_discount_methods=_get_discount_method_views(),
            active_categories=[
                OperationalDiscountCategoryView(
                    code=category.code,
                    name=category.name,
                    display_order=category.display_order,
                )
                for category in categories
            ],
            discount_controls=DiscountControlsView(
                high_value_amount_threshold=self._settings.discount_high_value_amount_threshold,
                high_value_requires_acknowledgement=True,
            ),
        )

    def list_discounts(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        scope: str | None,
        created_by_user_id: uuid.UUID | None,
        query: str | None,
        category_filter: str | None,
        payment_method_filter: str | None,
    ) -> DiscountsListResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        normalized_scope = _validate_discount_list_scope(scope)
        normalized_query = _normalize_query(query)
        normalized_category = _validate_category_filter(session, category_filter)
        normalized_payment_method = _validate_payment_method_filter(payment_method_filter)

        base_statement = (
            select(
                OperationalDiscount.id,
                OperationalDiscount.status,
                OperationalDiscount.created_by_user_id,
                OperationalDiscount.subject_name,
                OperationalDiscount.concept,
                OperationalDiscount.category_code,
                OperationalDiscountCategory.name.label("category_name"),
                OperationalDiscount.payment_method_code,
                OperationalDiscount.total_amount,
                OperationalDiscount.cash_amount,
                OperationalDiscount.non_cash_amount,
                OperationalDiscount.currency_code,
                OperationalDiscount.created_at_utc,
                User.full_name.label("operator_full_name"),
            )
            .select_from(OperationalDiscount)
            .join(User, User.id == OperationalDiscount.created_by_user_id)
            .outerjoin(
                OperationalDiscountCategory,
                OperationalDiscountCategory.code == OperationalDiscount.category_code,
            )
            .where(
                OperationalDiscount.branch_id == context.branch_id,
                OperationalDiscount.workstation_id == context.workstation_id,
            )
        )
        base_statement = _apply_discount_list_scope_filters(
            base_statement,
            normalized_scope=normalized_scope,
            context=context,
            current_cash_session_id=current_open_cash_session.id,
        )
        if normalized_category is not None:
            base_statement = base_statement.where(
                OperationalDiscount.category_code == normalized_category
            )
        if normalized_payment_method is not None:
            base_statement = base_statement.where(
                OperationalDiscount.payment_method_code == normalized_payment_method
            )
        if normalized_query is not None:
            discount_id_prefix = normalized_query.removeprefix("des-")
            pattern = f"%{normalized_query}%"
            base_statement = base_statement.where(
                or_(
                    func.lower(cast(OperationalDiscount.id, String)).like(f"{discount_id_prefix}%"),
                    func.lower(cast(OperationalDiscount.id, String)).contains(normalized_query),
                    func.lower(OperationalDiscount.subject_name).like(pattern),
                    func.lower(OperationalDiscount.concept).like(pattern),
                    func.lower(func.coalesce(OperationalDiscount.notes, "")).like(pattern),
                    func.lower(User.full_name).like(pattern),
                    func.lower(func.coalesce(OperationalDiscountCategory.name, "")).like(pattern),
                )
            )

        available_user_rows = (
            session.execute(
                base_statement.with_only_columns(
                    OperationalDiscount.created_by_user_id,
                    User.full_name.label("operator_full_name"),
                )
                .distinct()
                .order_by(User.full_name.asc())
            )
            .mappings()
            .all()
        )

        statement = base_statement
        if created_by_user_id is not None:
            statement = statement.where(
                OperationalDiscount.created_by_user_id == created_by_user_id
            )

        records = (
            session.execute(
                statement.order_by(OperationalDiscount.created_at_utc.desc()).limit(
                    MAX_DISCOUNTS_PER_LIST
                )
            )
            .mappings()
            .all()
        )
        return DiscountsListResponse(
            workstation_code=workstation_code,
            scope=normalized_scope,
            created_by_user_id=str(created_by_user_id) if created_by_user_id is not None else None,
            query=_normalize_optional_string(query),
            category=normalized_category,
            payment_method=normalized_payment_method,
            available_users=[
                OperationalDiscountFilterOptionView(
                    value=str(record["created_by_user_id"]),
                    label=record["operator_full_name"],
                )
                for record in available_user_rows
            ],
            discounts=[
                OperationalDiscountListItemView(
                    id=record["id"],
                    folio=_build_discount_folio(record["id"]),
                    status=record["status"],
                    subject_name=record["subject_name"],
                    concept=record["concept"],
                    category_code=record["category_code"],
                    category_name=record["category_name"],
                    payment_method_code=record["payment_method_code"],
                    total_amount=record["total_amount"],
                    cash_amount=record["cash_amount"],
                    non_cash_amount=record["non_cash_amount"],
                    currency_code=record["currency_code"],
                    created_at_utc=record["created_at_utc"],
                    operator_full_name=record["operator_full_name"],
                    branch_code=context.branch_code,
                    branch_name=context.branch_name,
                    workstation_code=context.workstation_code,
                    workstation_name=context.workstation_name,
                    affects_cash_drawer=Decimal(record["cash_amount"]) > ZERO_MONEY,
                )
                for record in records
            ],
        )

    def get_discount_detail(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        workstation_code: str,
        discount_id: uuid.UUID,
    ) -> OperationalDiscountDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=workstation_code,
        )
        _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=workstation_code,
            context=context,
        )
        discount = _get_discount_for_branch(
            session,
            discount_id=discount_id,
            branch_id=context.branch_id,
        )
        return _build_discount_detail(session, discount)


class DiscountsCommandService:
    def __init__(
        self,
        workstation_access: WorkstationAccessService | None = None,
        cash_session_query: CashSessionQueryService | None = None,
        audit_recorder: AuditRecorder | None = None,
        outbox_writer: OutboxWriter | None = None,
        query_service: DiscountsQueryService | None = None,
        settings: ApiSettings | None = None,
    ) -> None:
        self._workstation_access = workstation_access or WorkstationAccessService()
        self._cash_session_query = cash_session_query or CashSessionQueryService()
        self._audit_recorder = audit_recorder or AuditRecorder()
        self._outbox_writer = outbox_writer or OutboxWriter()
        self._settings = settings or get_settings()
        self._query_service = query_service or DiscountsQueryService(
            workstation_access=self._workstation_access,
            cash_session_query=self._cash_session_query,
            settings=self._settings,
        )

    def create_discount(
        self,
        session: Session,
        *,
        current_user: AuthenticatedUser,
        command: CreateOperationalDiscountRequest,
        request_id: str | None,
    ) -> OperationalDiscountDetailResponse:
        context = self._workstation_access.resolve_context(
            session,
            user_id=current_user.id,
            workstation_code=command.workstation_code,
        )
        current_open_cash_session = _require_open_cash_session(
            session,
            cash_session_query=self._cash_session_query,
            current_user=current_user,
            workstation_code=command.workstation_code,
            context=context,
        )
        subject_name = _require_non_empty(command.subject_name, field_label="persona o entidad")
        concept = _require_non_empty(command.concept, field_label="motivo o referencia")
        category_code = _validate_category_filter(session, command.category_code)
        payment_method_code = _validate_supported_payment_method_code(command.payment_method_code)
        total_amount = _quantize_money(command.total_amount)
        notes = _normalize_optional_string(command.notes)
        is_high_value = total_amount >= self._settings.discount_high_value_amount_threshold
        if is_high_value and not command.high_value_acknowledged:
            raise OperationalDiscountValidationError(
                "Confirma el descuento de alto valor antes de registrar."
            )
        created_at = datetime.now(tz=UTC)
        resolved_request_id = request_id or str(uuid.uuid4())
        cash_amount = total_amount if payment_method_code == PAYMENT_METHOD_CASH else ZERO_MONEY
        non_cash_amount = total_amount if payment_method_code == PAYMENT_METHOD_CARD else ZERO_MONEY

        discount = OperationalDiscount(
            branch_id=context.branch_id,
            workstation_id=context.workstation_id,
            created_by_user_id=current_user.id,
            active_cash_session_id=current_open_cash_session.id,
            subject_name=subject_name,
            concept=concept,
            category_code=category_code,
            notes=notes,
            payment_method_code=payment_method_code,
            currency_code="MXN",
            total_amount=total_amount,
            cash_amount=cash_amount,
            non_cash_amount=non_cash_amount,
            status=DISCOUNT_STATUS_COMMITTED,
            created_at_utc=created_at,
            committed_at_utc=created_at,
        )

        try:
            session.add(discount)
            session.flush()

            if cash_amount > ZERO_MONEY:
                session.add(
                    CashMovement(
                        sale_id=None,
                        cash_session_id=current_open_cash_session.id,
                        branch_id=context.branch_id,
                        workstation_id=context.workstation_id,
                        operator_id=current_user.id,
                        movement_type=CASH_MOVEMENT_TYPE_OPERATIONAL_DISCOUNT,
                        direction=CASH_MOVEMENT_DIRECTION_IN,
                        payment_method_code=PAYMENT_METHOD_CASH,
                        amount=cash_amount,
                        currency_code="MXN",
                        occurred_at=created_at,
                    )
                )

            discount_folio = _build_discount_folio(discount.id)
            self._audit_recorder.record(
                session,
                actor_id=current_user.id,
                action=AUDIT_ACTION_OPERATIONAL_DISCOUNT_COMMITTED,
                resource_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                resource_id=str(discount.id),
                branch_id=context.branch_id,
                request_id=resolved_request_id,
                metadata={
                    "folio": discount_folio,
                    "branch_code": context.branch_code,
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "subject_name": subject_name,
                    "concept": concept,
                    "category_code": category_code,
                    "payment_method_code": payment_method_code,
                    "currency_code": "MXN",
                    "total_amount": str(total_amount),
                    "cash_amount": str(cash_amount),
                    "non_cash_amount": str(non_cash_amount),
                    "notes": notes,
                    "high_value": is_high_value,
                    "high_value_acknowledged": command.high_value_acknowledged,
                    "high_value_threshold_amount": str(
                        self._settings.discount_high_value_amount_threshold
                    ),
                },
            )
            self._outbox_writer.append(
                session,
                aggregate_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                aggregate_id=str(discount.id),
                event_name=OUTBOX_EVENT_OPERATIONAL_DISCOUNT_COMMITTED_V1,
                payload={
                    "discount_id": str(discount.id),
                    "folio": discount_folio,
                    "branch_id": str(context.branch_id),
                    "branch_code": context.branch_code,
                    "workstation_id": str(context.workstation_id),
                    "workstation_code": context.workstation_code,
                    "cash_session_id": str(current_open_cash_session.id),
                    "created_by_user_id": str(current_user.id),
                    "subject_name": subject_name,
                    "concept": concept,
                    "category_code": category_code,
                    "payment_method_code": payment_method_code,
                    "currency_code": "MXN",
                    "total_amount": str(total_amount),
                    "cash_amount": str(cash_amount),
                    "non_cash_amount": str(non_cash_amount),
                    "notes": notes,
                    "high_value": is_high_value,
                    "high_value_acknowledged": command.high_value_acknowledged,
                    "high_value_threshold_amount": str(
                        self._settings.discount_high_value_amount_threshold
                    ),
                    "committed_at_utc": created_at.isoformat(),
                },
                headers={"request_id": resolved_request_id},
            )
            if is_high_value:
                self._audit_recorder.record(
                    session,
                    actor_id=current_user.id,
                    action=AUDIT_ACTION_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_REQUESTED,
                    resource_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                    resource_id=str(discount.id),
                    branch_id=context.branch_id,
                    request_id=resolved_request_id,
                    metadata={
                        "folio": discount_folio,
                        "notification_target": "backoffice",
                        "threshold_amount": str(
                            self._settings.discount_high_value_amount_threshold
                        ),
                        "total_amount": str(total_amount),
                        "category_code": category_code,
                    },
                )
                self._outbox_writer.append(
                    session,
                    aggregate_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                    aggregate_id=str(discount.id),
                    event_name=OUTBOX_EVENT_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_V1,
                    payload={
                        "discount_id": str(discount.id),
                        "folio": discount_folio,
                        "notification_target": "backoffice",
                        "branch_id": str(context.branch_id),
                        "branch_code": context.branch_code,
                        "workstation_id": str(context.workstation_id),
                        "workstation_code": context.workstation_code,
                        "created_by_user_id": str(current_user.id),
                        "subject_name": subject_name,
                        "category_code": category_code,
                        "total_amount": str(total_amount),
                        "threshold_amount": str(
                            self._settings.discount_high_value_amount_threshold
                        ),
                        "committed_at_utc": created_at.isoformat(),
                    },
                    headers={"request_id": resolved_request_id},
                )
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise OperationalDiscountValidationError(
                "Las reglas de integridad del descuento fallaron durante el guardado."
            ) from error

        return self._query_service.get_discount_detail(
            session,
            current_user=current_user,
            workstation_code=command.workstation_code,
            discount_id=discount.id,
        )


def _build_discount_detail(
    session: Session,
    discount: OperationalDiscount,
) -> OperationalDiscountDetailResponse:
    branch = session.execute(select(Branch).where(Branch.id == discount.branch_id)).scalar_one()
    workstation = session.execute(
        select(Workstation).where(Workstation.id == discount.workstation_id)
    ).scalar_one()
    created_by = session.execute(
        select(User).where(User.id == discount.created_by_user_id)
    ).scalar_one()
    category_name = (
        session.execute(
            select(OperationalDiscountCategory.name).where(
                OperationalDiscountCategory.code == discount.category_code
            )
        ).scalar_one_or_none()
        if discount.category_code is not None
        else None
    )

    return OperationalDiscountDetailResponse(
        id=discount.id,
        folio=_build_discount_folio(discount.id),
        status=discount.status,
        branch=BranchSummary(
            id=branch.id,
            code=branch.code,
            name=branch.name,
            timezone=branch.timezone,
            is_active=branch.is_active,
        ),
        workstation=WorkstationSummary(
            id=workstation.id,
            code=workstation.code,
            name=workstation.name,
            is_active=workstation.is_active,
        ),
        created_by=AuthenticatedUser(
            id=created_by.id,
            email=created_by.email,
            full_name=created_by.full_name,
            is_active=created_by.is_active,
        ),
        active_cash_session_id=discount.active_cash_session_id,
        subject_name=discount.subject_name,
        concept=discount.concept,
        category_code=discount.category_code,
        category_name=category_name,
        notes=discount.notes,
        payment_method_code=discount.payment_method_code,
        currency_code=discount.currency_code,
        total_amount=discount.total_amount,
        cash_amount=discount.cash_amount,
        non_cash_amount=discount.non_cash_amount,
        created_at_utc=discount.created_at_utc,
        committed_at_utc=discount.committed_at_utc,
        affects_cash_drawer=discount.cash_amount > ZERO_MONEY,
        audit_summary=AuditVisibilityQueryService().build_summary(
            session,
            created_actor=build_audit_actor_snapshot(
                user_id=created_by.id,
                full_name=created_by.full_name,
                email=created_by.email,
            ),
            created_at_utc=discount.created_at_utc,
            confirmed_at_utc=discount.committed_at_utc,
            acknowledgement_label="Validacion de alto valor",
            notes=discount.notes,
            notification_config=BackofficeNotificationConfig(
                aggregate_id=str(discount.id),
                aggregate_type=OPERATIONAL_DISCOUNT_RESOURCE_TYPE,
                event_names=(OUTBOX_EVENT_OPERATIONAL_DISCOUNT_HIGH_VALUE_ALERT_V1,),
                label="Alerta a backoffice",
            ),
        ),
    )


def _get_discount_for_branch(
    session: Session,
    *,
    discount_id: uuid.UUID,
    branch_id: uuid.UUID,
) -> OperationalDiscount:
    discount = session.execute(
        select(OperationalDiscount).where(
            OperationalDiscount.id == discount_id,
            OperationalDiscount.branch_id == branch_id,
        )
    ).scalar_one_or_none()
    if discount is None:
        raise OperationalDiscountNotFoundError(
            "El descuento solicitado no existe en la sucursal actual."
        )
    return discount


def _get_branch_brand_key(branch_code: str) -> str:
    return BRANCH_BRAND_MAPPING.get(branch_code, "EL_MEJOR_PAN")


def _get_discount_method_views() -> list[OperationalDiscountMethodView]:
    return [
        OperationalDiscountMethodView(
            code=PAYMENT_METHOD_CASH,
            label="Efectivo",
            affects_cash_drawer=True,
            is_enabled=True,
            helper_text="Registra un cobro interno y aumenta el efectivo esperado del turno.",
        ),
        OperationalDiscountMethodView(
            code=PAYMENT_METHOD_CARD,
            label="Tarjeta",
            affects_cash_drawer=False,
            is_enabled=True,
            helper_text="Queda auditado, pero no cambia el efectivo esperado de la caja.",
        ),
        OperationalDiscountMethodView(
            code=PAYMENT_METHOD_MIXED,
            label="Mixto",
            affects_cash_drawer=False,
            is_enabled=False,
            helper_text="No esta disponible todavia en esta fase.",
        ),
    ]


def _require_open_cash_session(
    session: Session,
    *,
    cash_session_query: CashSessionQueryService,
    current_user: AuthenticatedUser,
    workstation_code: str,
    context: WorkstationContext,
) -> CashSessionView:
    current_open_cash_session = cash_session_query.get_open_session_for_workstation_code(
        session,
        workstation_code=workstation_code,
    )
    if current_open_cash_session is None:
        raise OperationalDiscountConflictError(
            "Necesitas una caja abierta en esta estacion para registrar descuentos."
        )
    if current_open_cash_session.user_id != current_user.id:
        raise OperationalDiscountConflictError(
            "La caja abierta de esta estacion pertenece a otro cajero."
        )
    if (
        current_open_cash_session.branch_id != context.branch_id
        or current_open_cash_session.workstation_id != context.workstation_id
    ):
        raise OperationalDiscountConflictError(
            "La caja abierta no coincide con el contexto actual de la estacion."
        )
    return current_open_cash_session


def _apply_discount_list_scope_filters(
    statement: Select[tuple[object, ...]],
    *,
    normalized_scope: str,
    context: WorkstationContext,
    current_cash_session_id: uuid.UUID,
) -> Select[tuple[object, ...]]:
    if normalized_scope == DISCOUNT_LIST_SCOPE_CURRENT_SHIFT:
        return statement.where(
            OperationalDiscount.active_cash_session_id == current_cash_session_id
        )

    if normalized_scope == DISCOUNT_LIST_SCOPE_TODAY:
        branch_timezone = ZoneInfo(context.branch_timezone)
        local_now = datetime.now(tz=UTC).astimezone(branch_timezone)
        local_start = datetime.combine(local_now.date(), time.min, tzinfo=branch_timezone)
        local_end = local_start + timedelta(days=1)
        return statement.where(
            OperationalDiscount.created_at_utc >= local_start.astimezone(UTC),
            OperationalDiscount.created_at_utc < local_end.astimezone(UTC),
        )

    return statement


def _validate_discount_list_scope(value: str | None) -> str:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return DISCOUNT_LIST_SCOPE_CURRENT_SHIFT

    scope_code = normalized.upper()
    if scope_code not in VALID_OPERATIONAL_DISCOUNT_LIST_SCOPES:
        raise OperationalDiscountValidationError(
            "El alcance solicitado no es valido para descuentos operativos."
        )
    return scope_code


def _validate_supported_payment_method_code(value: str) -> str:
    payment_method_code = _validate_payment_method_code(value)
    if payment_method_code not in SUPPORTED_OPERATIONAL_DISCOUNT_METHOD_CODES:
        raise OperationalDiscountValidationError(
            "Por ahora solo puedes registrar descuentos en efectivo o tarjeta."
        )
    return payment_method_code


def _validate_payment_method_filter(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    return _validate_payment_method_code(normalized)


def _validate_payment_method_code(value: str) -> str:
    payment_method_code = value.strip().upper()
    if payment_method_code not in VALID_OPERATIONAL_DISCOUNT_METHOD_CODES:
        raise OperationalDiscountValidationError("Selecciona un metodo valido para este registro.")
    return payment_method_code


def _validate_category_filter(session: Session, value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    category_code = normalized.upper()
    category = session.execute(
        select(OperationalDiscountCategory.code).where(
            OperationalDiscountCategory.code == category_code,
            OperationalDiscountCategory.is_active.is_(True),
        )
    ).scalar_one_or_none()
    if category is None:
        raise OperationalDiscountValidationError("Selecciona una categoria valida.")
    return category_code


def _require_non_empty(value: str, *, field_label: str) -> str:
    normalized = value.strip()
    if len(normalized) == 0:
        raise OperationalDiscountValidationError(f"Captura un valor valido para {field_label}.")
    return normalized


def _build_discount_folio(discount_id: uuid.UUID) -> str:
    return f"DES-{str(discount_id).split('-', maxsplit=1)[0].upper()}"


def _normalize_query(value: str | None) -> str | None:
    normalized = _normalize_optional_string(value)
    return normalized.casefold() if normalized else None


def _normalize_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_optional(value: str | None) -> str | None:
    return _normalize_optional_string(value)


def _discount_product_status(product: Product) -> str:
    if product.is_active and product.is_sellable:
        return "active"
    return "inactive"


def _discount_class_status(product_class: ProductClass) -> str:
    if product_class.is_active and product_class.is_sellable:
        return "active"
    return "inactive"


def _quantize_money(value: Decimal | int | None) -> Decimal:
    raw_value = ZERO_MONEY if value is None else Decimal(value)
    return raw_value.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)
