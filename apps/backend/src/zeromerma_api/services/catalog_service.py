# apps/backend/src/zeromerma_api/services/catalog_service.py
# PURPOSE:
#   Catalog service layer:
#     - list categories/products
#     - admin create/update categories/products
#
# IMPORTANT (PostgreSQL + psycopg NULL typing):
#   psycopg3 can send NULL parameters as type "unknown".
#   PostgreSQL may reject predicates like (:x IS NULL OR col = :x) when :x is NULL.
#   We fix this by casting nullable parameters:
#       CAST(:category_id AS BIGINT)
#       CAST(:q AS TEXT)
#       CAST(:is_input AS BOOLEAN)

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
)


def list_categories(
    db: Session,
    *,
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    sql = """
        SELECT *
        FROM product_category
        WHERE (:include_inactive = TRUE OR is_active = TRUE)
        ORDER BY name ASC
    """
    rows = (
        db.execute(
            text(sql),
            {"include_inactive": bool(include_inactive)},
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def list_products(
    db: Session,
    *,
    category_id: int | None = None,
    is_input: bool | None = None,
    include_inactive: bool = False,
    q: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    sql = """
        SELECT
            p.*,
            c.name AS category_name
        FROM product p
        LEFT JOIN product_category c ON c.id = p.category_id
        WHERE
            (:include_inactive = TRUE OR p.is_active = TRUE)
            AND (
                CAST(:category_id AS BIGINT) IS NULL
                OR p.category_id = CAST(:category_id AS BIGINT)
            )
            AND (
                CAST(:is_input AS BOOLEAN) IS NULL
                OR p.is_input = CAST(:is_input AS BOOLEAN)
            )
            AND (
                CAST(:q AS TEXT) IS NULL
                OR p.name ILIKE '%' || CAST(:q AS TEXT) || '%'
                OR COALESCE(p.sku, '') ILIKE '%' || CAST(:q AS TEXT) || '%'
            )
        ORDER BY p.name ASC
        LIMIT :limit
        OFFSET :offset
    """
    rows = (
        db.execute(
            text(sql),
            {
                "include_inactive": bool(include_inactive),
                "category_id": int(category_id) if category_id is not None else None,
                "is_input": bool(is_input) if is_input is not None else None,
                "q": q,
                "limit": int(limit),
                "offset": int(offset),
            },
        )
        .mappings()
        .all()
    )
    return [dict(r) for r in rows]


def _require_category_exists(db: Session, *, category_id: int) -> None:
    exists = db.execute(
        text("SELECT 1 FROM product_category WHERE id = :id"),
        {"id": int(category_id)},
    ).scalar_one_or_none()
    if exists is None:
        raise DomainNotFoundError(
            message=f"Category {category_id} not found.",
            details={"category_id": int(category_id)},
        )


def create_category(
    db: Session,
    *,
    code: str,
    name: str,
    is_active: bool = True,
) -> dict[str, Any]:
    try:
        row = (
            db.execute(
                text(
                    """
                    INSERT INTO product_category
                        (code, name, is_active, created_at, updated_at)
                    VALUES
                        (:code, :name, :is_active, now(), now())
                    RETURNING *
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "is_active": bool(is_active),
                },
            )
            .mappings()
            .one()
        )
        return dict(row)
    except IntegrityError as exc:
        raise DomainConflictError(
            message="Category already exists (duplicate code).",
            details={"code": code},
        ) from exc


def update_category(
    db: Session,
    *,
    category_id: int,
    code: str | None,
    name: str | None,
    is_active: bool | None,
) -> dict[str, Any]:
    try:
        row = (
            db.execute(
                text(
                    """
                    UPDATE product_category
                    SET
                        code = COALESCE(:code, code),
                        name = COALESCE(:name, name),
                        is_active = COALESCE(:is_active, is_active),
                        updated_at = now()
                    WHERE id = :id
                    RETURNING *
                    """
                ),
                {
                    "id": int(category_id),
                    "code": code,
                    "name": name,
                    "is_active": is_active,
                },
            )
            .mappings()
            .one_or_none()
        )
    except IntegrityError as exc:
        raise DomainConflictError(
            message="Category update conflict.",
            details={"category_id": int(category_id)},
        ) from exc

    if row is None:
        raise DomainNotFoundError(
            message=f"Category {category_id} not found.",
            details={"category_id": int(category_id)},
        )

    return dict(row)


def create_product(
    db: Session,
    *,
    sku: str | None,
    name: str,
    category_id: int,
    uom: str,
    is_input: bool,
    sale_price: Decimal | None,
    standard_cost: Decimal | None,
    is_active: bool = True,
) -> dict[str, Any]:
    _require_category_exists(db, category_id=int(category_id))

    try:
        row = (
            db.execute(
                text(
                    """
                    INSERT INTO product (
                        sku,
                        name,
                        category_id,
                        uom,
                        is_input,
                        sale_price,
                        standard_cost,
                        is_active,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        :sku,
                        :name,
                        :category_id,
                        :uom,
                        :is_input,
                        :sale_price,
                        :standard_cost,
                        :is_active,
                        now(),
                        now()
                    )
                    RETURNING *
                    """
                ),
                {
                    "sku": sku,
                    "name": name,
                    "category_id": int(category_id),
                    "uom": uom,
                    "is_input": bool(is_input),
                    "sale_price": sale_price,
                    "standard_cost": standard_cost,
                    "is_active": bool(is_active),
                },
            )
            .mappings()
            .one()
        )
        return dict(row)
    except IntegrityError as exc:
        raise DomainConflictError(
            message="Product already exists (duplicate sku).",
            details={"sku": sku},
        ) from exc


def update_product(
    db: Session,
    *,
    product_id: int,
    sku: str | None,
    name: str | None,
    category_id: int | None,
    uom: str | None,
    is_input: bool | None,
    sale_price: Decimal | None,
    standard_cost: Decimal | None,
    is_active: bool | None,
) -> dict[str, Any]:
    if category_id is not None:
        _require_category_exists(db, category_id=int(category_id))

    try:
        row = (
            db.execute(
                text(
                    """
                    UPDATE product
                    SET
                        sku = COALESCE(:sku, sku),
                        name = COALESCE(:name, name),
                        category_id = COALESCE(:category_id, category_id),
                        uom = COALESCE(:uom, uom),
                        is_input = COALESCE(:is_input, is_input),
                        sale_price = COALESCE(:sale_price, sale_price),
                        standard_cost = COALESCE(:standard_cost, standard_cost),
                        is_active = COALESCE(:is_active, is_active),
                        updated_at = now()
                    WHERE id = :id
                    RETURNING *
                    """
                ),
                {
                    "id": int(product_id),
                    "sku": sku,
                    "name": name,
                    "category_id": (int(category_id) if category_id is not None else None),
                    "uom": uom,
                    "is_input": is_input,
                    "sale_price": sale_price,
                    "standard_cost": standard_cost,
                    "is_active": is_active,
                },
            )
            .mappings()
            .one_or_none()
        )
    except IntegrityError as exc:
        raise DomainConflictError(
            message="Product update conflict (duplicate sku).",
            details={"product_id": int(product_id), "sku": sku},
        ) from exc

    if row is None:
        raise DomainNotFoundError(
            message=f"Product {product_id} not found.",
            details={"product_id": int(product_id)},
        )

    return dict(row)
