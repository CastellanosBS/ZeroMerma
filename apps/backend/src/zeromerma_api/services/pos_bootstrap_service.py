from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
)
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.cash_session import CashSession
from zeromerma_api.models.product import Product
from zeromerma_api.models.product_category import ProductCategory
from zeromerma_api.models.product_price import ProductPrice
from zeromerma_api.services.cash_session_service import get_current_open_session


@dataclass(frozen=True)
class _PaymentMethodDef:
    code: str
    label: str


PAYMENT_METHODS: tuple[_PaymentMethodDef, ...] = (
    _PaymentMethodDef(code="CASH", label="Cash"),
    _PaymentMethodDef(code="CARD", label="Card"),
    _PaymentMethodDef(code="OTHER", label="Other"),
)


def _require_branch(db: Session, *, branch_id: int) -> Branch:
    """
    Ensure the requested branch exists and is active.
    """
    branch = db.get(Branch, int(branch_id))
    if branch is None:
        raise DomainNotFoundError(
            message=f"Branch {branch_id} not found.",
            details={"branch_id": int(branch_id)},
        )

    if not bool(branch.is_active):
        raise DomainConflictError(
            message=f"Branch {branch_id} is inactive.",
            details={"branch_id": int(branch_id)},
        )

    return branch


def _serialize_cash_session(cash_session: CashSession | None) -> dict | None:
    """
    Convert current open cash session into the minimal bootstrap shape.
    """
    if cash_session is None:
        return None

    return {
        "id": int(cash_session.id),
        "status": str(cash_session.status),
        "opened_at": cash_session.opened_at,
        "opening_amount": Decimal(str(cash_session.opening_amount)),
    }


def _payment_methods_payload() -> list[dict]:
    """
    Static payment methods exposed to POS bootstrap.

    Note:
    This is intentionally simple for 2A.1. If payment methods become configurable
    later, this function can be replaced by a DB-backed implementation.
    """
    return [{"code": pm.code, "label": pm.label} for pm in PAYMENT_METHODS]


def _capabilities_payload() -> dict:
    """
    Feature flags exposed to the POS client.

    For 2A.1 we expose the current kernel capabilities conservatively:
    - keyboard_first: yes
    - orders / delivery flows: not yet active until the order kernel is built
    """
    return {
        "can_take_orders": False,
        "can_deliver_orders": False,
        "keyboard_first": True,
    }


def _fetch_visible_catalog_rows(db: Session, *, branch_id: int):
    """
    Fetch POS-visible categories and sellable products with effective price.

    Effective pricing policy:
        effective_price = COALESCE(product_price.price, product.sale_price)

    Visibility / sellability rules:
    - category.is_active = true
    - category.show_in_pos = true
    - product.is_active = true
    - product.show_in_pos = true
    - product.is_sellable_in_pos = true
    - product.is_input = false
    """
    stmt = (
        select(
            ProductCategory.id.label("category_id"),
            ProductCategory.code.label("category_code"),
            ProductCategory.name.label("category_name"),
            ProductCategory.quick_name.label("category_quick_name"),
            ProductCategory.default_pos_order.label("category_default_pos_order"),
            Product.id.label("product_id"),
            Product.sku.label("product_sku"),
            Product.name.label("product_name"),
            Product.quick_name.label("product_quick_name"),
            Product.default_pos_order.label("product_default_pos_order"),
            Product.uom.label("product_uom"),
            func.coalesce(ProductPrice.price, Product.sale_price).label("effective_price"),
        )
        .join(Product, Product.category_id == ProductCategory.id)
        .outerjoin(
            ProductPrice,
            and_(
                ProductPrice.product_id == Product.id,
                ProductPrice.branch_id == int(branch_id),
            ),
        )
        .where(
            ProductCategory.is_active.is_(True),
            ProductCategory.show_in_pos.is_(True),
            Product.is_active.is_(True),
            Product.show_in_pos.is_(True),
            Product.is_sellable_in_pos.is_(True),
            Product.is_input.is_(False),
        )
        .order_by(
            ProductCategory.default_pos_order.asc(),
            ProductCategory.id.asc(),
            Product.default_pos_order.asc(),
            Product.id.asc(),
        )
    )

    return db.execute(stmt).all()


def _build_categories_payload(rows) -> list[dict]:
    """
    Group flat query rows into the hierarchical bootstrap category/product shape.
    """
    categories: "OrderedDict[int, dict]" = OrderedDict()

    for row in rows:
        category_id = int(row.category_id)

        if category_id not in categories:
            categories[category_id] = {
                "id": category_id,
                "code": str(row.category_code),
                "name": str(row.category_name),
                "quick_name": row.category_quick_name,
                "default_pos_order": int(row.category_default_pos_order),
                "products": [],
            }

        effective_price = (
            Decimal(str(row.effective_price)) if row.effective_price is not None else None
        )

        categories[category_id]["products"].append(
            {
                "id": int(row.product_id),
                "sku": row.product_sku,
                "name": str(row.product_name),
                "quick_name": row.product_quick_name,
                "default_pos_order": int(row.product_default_pos_order),
                "uom": str(row.product_uom),
                "effective_price": effective_price,
            }
        )

    return list(categories.values())


def get_pos_bootstrap(db: Session, *, branch_id: int) -> dict:
    """
    Build the POS bootstrap payload for one branch.

    Output includes:
    - branch_id
    - current open cash session (if any)
    - available payment methods
    - capability flags
    - visible categories with visible/sellable products
    - effective price resolved per branch

    This service intentionally does NOT define:
    - final frontend layout
    - keyboard mapping
    - touch arrangement
    - user-specific personalization

    Those remain frontend concerns for now.
    """
    _require_branch(db, branch_id=int(branch_id))

    cash_session = get_current_open_session(db, branch_id=int(branch_id))
    rows = _fetch_visible_catalog_rows(db, branch_id=int(branch_id))
    categories = _build_categories_payload(rows)

    return {
        "branch_id": int(branch_id),
        "cash_session": _serialize_cash_session(cash_session),
        "payment_methods": _payment_methods_payload(),
        "capabilities": _capabilities_payload(),
        "categories": categories,
    }
