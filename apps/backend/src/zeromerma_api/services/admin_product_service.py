from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, joinedload

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.product import Product
from zeromerma_api.models.product_category import ProductCategory

ALLOWED_UOMS = {"PCS", "KG", "G", "L", "ML"}


def _normalize_sku(raw: str | None) -> str | None:
    if raw is None:
        return None

    value = str(raw).strip().upper()
    return value or None


def _normalize_name(raw: str) -> str:
    value = str(raw).strip()
    if not value:
        raise DomainValidationError(message="Product name cannot be empty.")
    return value


def _normalize_quick_name(raw: str | None) -> str | None:
    if raw is None:
        return None

    value = str(raw).strip()
    return value or None


def _normalize_uom(raw: str) -> str:
    value = str(raw).strip().upper()
    if value not in ALLOWED_UOMS:
        raise DomainValidationError(
            message="Invalid unit of measure.",
            details={"allowed_uoms": sorted(ALLOWED_UOMS)},
        )
    return value


def _normalize_decimal(value: Decimal | None, *, field_name: str) -> Decimal | None:
    if value is None:
        return None

    if value < 0:
        raise DomainValidationError(
            message=f"{field_name} cannot be negative.",
            details={"field": field_name},
        )

    return value


def _get_category_or_404(db: Session, *, category_id: int) -> ProductCategory:
    category = db.get(ProductCategory, int(category_id))
    if category is None:
        raise DomainNotFoundError(
            message="Product category not found.",
            details={"category_id": int(category_id)},
        )
    return category


def _get_assignable_category_or_404(db: Session, *, category_id: int) -> ProductCategory:
    category = _get_category_or_404(db, category_id=category_id)

    if not bool(category.is_active):
        raise DomainValidationError(
            message="Assigned category is inactive.",
            details={"category_id": int(category.id)},
        )

    return category


def _ensure_unique_sku(
    db: Session,
    *,
    sku: str | None,
    exclude_product_id: int | None = None,
) -> None:
    if sku is None:
        return

    stmt = select(Product).where(Product.sku == sku)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is None:
        return

    if exclude_product_id is not None and int(existing.id) == int(exclude_product_id):
        return

    raise DomainConflictError(
        message="Product SKU already exists.",
        details={"sku": sku},
    )


def _resolve_pos_flags(
    *,
    is_input: bool,
    show_in_pos: bool,
    is_sellable_in_pos: bool,
) -> tuple[bool, bool]:
    # Backend authority:
    # input/raw-material products must not be sellable in POS.
    if is_input:
        return False, False

    return bool(show_in_pos), bool(is_sellable_in_pos)


def _validate_sellability_rules(
    *,
    is_input: bool,
    is_sellable_in_pos: bool,
    sale_price: Decimal | None,
) -> None:
    if is_input and is_sellable_in_pos:
        raise DomainValidationError(
            message="Input/raw-material products cannot be sellable in POS."
        )

    if not is_input and is_sellable_in_pos and sale_price is None:
        raise DomainValidationError(message="Sellable POS products must define sale_price.")


def list_product_categories(
    db: Session,
    *,
    include_inactive: bool = False,
) -> list[ProductCategory]:
    stmt: Select = select(ProductCategory).order_by(
        ProductCategory.default_pos_order.asc(),
        ProductCategory.name.asc(),
    )

    if not include_inactive:
        stmt = stmt.where(ProductCategory.is_active.is_(True))

    return list(db.execute(stmt).scalars().all())


def list_products(
    db: Session,
    *,
    include_inactive: bool = True,
    q: str | None = None,
    category_id: int | None = None,
    is_input: bool | None = None,
) -> list[Product]:
    stmt: Select = (
        select(Product)
        .options(joinedload(Product.category))
        .order_by(Product.is_active.desc(), Product.default_pos_order.asc(), Product.name.asc())
    )

    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))

    if q is not None and str(q).strip():
        pattern = f"%{str(q).strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(pattern),
                Product.quick_name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    if category_id is not None:
        stmt = stmt.where(Product.category_id == int(category_id))

    if is_input is not None:
        stmt = stmt.where(Product.is_input.is_(bool(is_input)))

    return list(db.execute(stmt).scalars().all())


def get_product_or_404(
    db: Session,
    *,
    product_id: int,
) -> Product:
    stmt = (
        select(Product).options(joinedload(Product.category)).where(Product.id == int(product_id))
    )

    product = db.execute(stmt).scalar_one_or_none()

    if product is None:
        raise DomainNotFoundError(
            message="Product not found.",
            details={"product_id": int(product_id)},
        )

    return product


def create_product(
    db: Session,
    *,
    sku: str | None,
    name: str,
    quick_name: str | None,
    category_id: int,
    uom: str,
    is_input: bool,
    show_in_pos: bool,
    is_sellable_in_pos: bool,
    default_pos_order: int,
    sale_price: Decimal | None,
    standard_cost: Decimal | None,
    is_active: bool,
) -> Product:
    category = _get_assignable_category_or_404(db, category_id=category_id)

    normalized_sku = _normalize_sku(sku)
    normalized_name = _normalize_name(name)
    normalized_quick_name = _normalize_quick_name(quick_name)
    normalized_uom = _normalize_uom(uom)
    normalized_sale_price = _normalize_decimal(sale_price, field_name="sale_price")
    normalized_standard_cost = _normalize_decimal(standard_cost, field_name="standard_cost")

    _ensure_unique_sku(db, sku=normalized_sku)

    final_show_in_pos, final_is_sellable_in_pos = _resolve_pos_flags(
        is_input=bool(is_input),
        show_in_pos=bool(show_in_pos),
        is_sellable_in_pos=bool(is_sellable_in_pos),
    )

    _validate_sellability_rules(
        is_input=bool(is_input),
        is_sellable_in_pos=final_is_sellable_in_pos,
        sale_price=normalized_sale_price,
    )

    product = Product(
        sku=normalized_sku,
        name=normalized_name,
        quick_name=normalized_quick_name,
        category_id=int(category.id),
        uom=normalized_uom,
        is_input=bool(is_input),
        show_in_pos=final_show_in_pos,
        is_sellable_in_pos=final_is_sellable_in_pos,
        default_pos_order=int(default_pos_order),
        sale_price=normalized_sale_price,
        standard_cost=normalized_standard_cost,
        is_active=bool(is_active),
    )

    db.add(product)
    db.commit()

    return get_product_or_404(db, product_id=int(product.id))


def update_product(
    db: Session,
    *,
    product_id: int,
    sku: str | None = None,
    name: str | None = None,
    quick_name: str | None = None,
    category_id: int | None = None,
    uom: str | None = None,
    is_input: bool | None = None,
    show_in_pos: bool | None = None,
    is_sellable_in_pos: bool | None = None,
    default_pos_order: int | None = None,
    sale_price: Decimal | None = None,
    standard_cost: Decimal | None = None,
    is_active: bool | None = None,
) -> Product:
    product = get_product_or_404(db, product_id=product_id)

    next_is_input = bool(product.is_input) if is_input is None else bool(is_input)
    next_show_in_pos = bool(product.show_in_pos) if show_in_pos is None else bool(show_in_pos)
    next_is_sellable_in_pos = (
        bool(product.is_sellable_in_pos) if is_sellable_in_pos is None else bool(is_sellable_in_pos)
    )
    next_sale_price = (
        product.sale_price
        if sale_price is None
        else _normalize_decimal(sale_price, field_name="sale_price")
    )

    if sku is not None:
        normalized_sku = _normalize_sku(sku)
        _ensure_unique_sku(
            db,
            sku=normalized_sku,
            exclude_product_id=int(product.id),
        )
        product.sku = normalized_sku

    if name is not None:
        product.name = _normalize_name(name)

    if quick_name is not None:
        product.quick_name = _normalize_quick_name(quick_name)

    if category_id is not None:
        category = _get_assignable_category_or_404(db, category_id=category_id)
        product.category_id = int(category.id)

    if uom is not None:
        product.uom = _normalize_uom(uom)

    if standard_cost is not None:
        product.standard_cost = _normalize_decimal(standard_cost, field_name="standard_cost")

    if default_pos_order is not None:
        if int(default_pos_order) < 0:
            raise DomainValidationError(message="default_pos_order cannot be negative.")
        product.default_pos_order = int(default_pos_order)

    if is_input is not None:
        product.is_input = bool(is_input)

    if sale_price is not None:
        product.sale_price = next_sale_price

    final_show_in_pos, final_is_sellable_in_pos = _resolve_pos_flags(
        is_input=next_is_input,
        show_in_pos=next_show_in_pos,
        is_sellable_in_pos=next_is_sellable_in_pos,
    )

    _validate_sellability_rules(
        is_input=next_is_input,
        is_sellable_in_pos=final_is_sellable_in_pos,
        sale_price=next_sale_price,
    )

    product.show_in_pos = final_show_in_pos
    product.is_sellable_in_pos = final_is_sellable_in_pos

    if is_active is not None:
        product.is_active = bool(is_active)

    db.commit()
    return get_product_or_404(db, product_id=int(product.id))


def deactivate_product(
    db: Session,
    *,
    product_id: int,
) -> Product:
    product = get_product_or_404(db, product_id=product_id)
    product.is_active = False
    db.commit()
    return get_product_or_404(db, product_id=int(product.id))
