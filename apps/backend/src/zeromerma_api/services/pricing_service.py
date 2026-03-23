# apps/backend/src/zeromerma_api/services/pricing_service.py
# PURPOSE:
#   Pricing Policy service layer:
#     - Upsert/delete branch overrides (product_price)
#     - List effective prices for a branch
#
# IMPORTANT (PostgreSQL + psycopg NULL typing):
#   Optional filters must CAST parameters to explicit types to avoid "AmbiguousParameter".

from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


def upsert_price_override(
    db: Session,
    *,
    branch_id: int,
    product_id: int,
    price: Decimal,
    currency: str,
    created_by_id: Optional[int],
) -> dict[str, Any]:
    """
    Create or update an override row in product_price.

    Raises:
      - LookupError if branch/product does not exist
      - ValueError for conflicts/invalid inputs
    """
    # Ensure branch exists
    b = db.execute(
        text("SELECT 1 FROM branch WHERE id=:id"), {"id": int(branch_id)}
    ).scalar_one_or_none()
    if b is None:
        raise LookupError(f"Branch {branch_id} not found.")

    # Ensure product exists
    p = db.execute(
        text("SELECT 1 FROM product WHERE id=:id"), {"id": int(product_id)}
    ).scalar_one_or_none()
    if p is None:
        raise LookupError(f"Product {product_id} not found.")

    try:
        row = (
            db.execute(
                text(
                    """
                INSERT INTO product_price
                    (branch_id, product_id, price, currency, created_by_id, created_at, updated_at)
                VALUES
                    (:b, :p, :price, :cur, :u, now(), now())
                ON CONFLICT (branch_id, product_id)
                DO UPDATE SET
                    price = EXCLUDED.price,
                    currency = EXCLUDED.currency,
                    created_by_id = EXCLUDED.created_by_id,
                    updated_at = now()
                RETURNING id, branch_id, product_id, price, currency
                """
                ),
                {
                    "b": int(branch_id),
                    "p": int(product_id),
                    "price": Decimal(price),
                    "cur": str(currency).upper(),
                    "u": int(created_by_id) if created_by_id is not None else None,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)
    except IntegrityError as e:
        raise ValueError("Failed to upsert price override (integrity error).") from e


def delete_price_override(db: Session, *, branch_id: int, product_id: int) -> bool:
    """
    Delete override row for (branch_id, product_id).

    Returns:
      True  -> at least one row deleted
      False -> nothing matched
    """
    res = db.execute(
        text("DELETE FROM product_price WHERE branch_id=:b AND product_id=:p"),
        {"b": int(branch_id), "p": int(product_id)},
    )

    # SQLAlchemy typing stubs may not expose .rowcount, but runtime Result does.
    # Normalize None -> 0 and return a boolean.
    deleted = int(getattr(res, "rowcount", 0) or 0)
    return deleted > 0


def list_effective_prices(
    db: Session,
    *,
    branch_id: int,
    include_inactive: bool = False,
    category_id: Optional[int] = None,
    is_input: Optional[bool] = None,
    q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """
    List products with effective price for a branch.

    Effective price = COALESCE(product_price.price, product.sale_price)

    Filters:
      - include_inactive
      - category_id
      - is_input
      - q (sku/name substring)
    """
    sql = """
    SELECT
        CAST(:branch_id AS BIGINT) AS branch_id,
        p.id AS product_id,
        p.sku,
        p.name,
        p.category_id,
        c.name AS category_name,
        p.is_input,
        p.uom,
        p.sale_price AS base_price,
        pp.price AS override_price,
        COALESCE(pp.currency, 'MXN') AS currency,
        COALESCE(pp.price, p.sale_price) AS effective_price
    FROM product p
    JOIN product_category c ON c.id = p.category_id
    LEFT JOIN product_price pp
        ON pp.branch_id = CAST(:branch_id AS BIGINT)
       AND pp.product_id = p.id
    WHERE
        (:include_inactive = TRUE OR p.is_active = TRUE)
        AND (CAST(:category_id AS BIGINT) IS NULL OR p.category_id = CAST(:category_id AS BIGINT))
        AND (CAST(:is_input AS BOOLEAN) IS NULL OR p.is_input = CAST(:is_input AS BOOLEAN))
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
                "branch_id": int(branch_id),
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


def get_effective_price(
    db: Session,
    *,
    branch_id: int,
    product_id: int,
) -> dict[str, Any]:
    """
    Get effective price row for a single product at a branch.
    """

    # list_effective_prices returns all products; for single fetch, do a direct query
    row = (
        db.execute(
            text(
                """
            SELECT
                CAST(:branch_id AS BIGINT) AS branch_id,
                p.id AS product_id,
                p.sku,
                p.name,
                p.category_id,
                c.name AS category_name,
                p.is_input,
                p.uom,
                p.sale_price AS base_price,
                pp.price AS override_price,
                COALESCE(pp.currency, 'MXN') AS currency,
                COALESCE(pp.price, p.sale_price) AS effective_price
            FROM product p
            JOIN product_category c ON c.id = p.category_id
            LEFT JOIN product_price pp
                ON pp.branch_id = CAST(:branch_id AS BIGINT)
            AND pp.product_id = p.id
            WHERE p.id = CAST(:product_id AS BIGINT)
            """
            ),
            {"branch_id": int(branch_id), "product_id": int(product_id)},
        )
        .mappings()
        .one_or_none()
    )

    if row is None:
        raise LookupError(f"Product {product_id} not found.")

    return dict(row)


# -----------------------------------------------------------------------------
# Phase 6.4-D helper
# -----------------------------------------------------------------------------


def resolve_effective_sale_prices(
    db: Session, *, branch_id: int, product_ids: Iterable[int]
) -> dict[int, Decimal | None]:
    """
    Resolve effective sale prices for a set of product_ids at a given branch.

    Effective price policy:
      effective_price = COALESCE(product_price.price, product.sale_price)

    Returns:
      Dict[product_id] -> Decimal price OR None if neither override nor base price exists.

    Why this function exists:
      - Avoid N+1 queries when sale payload has multiple items with missing unit_price.
      - Keep the pricing policy in one place.
    """
    ids = [int(x) for x in product_ids]
    if not ids:
        return {}

    stmt = text(
        """
        SELECT
            p.id AS product_id,
            COALESCE(pp.price, p.sale_price) AS effective_price
        FROM product p
        LEFT JOIN product_price pp
            ON pp.branch_id = CAST(:branch_id AS BIGINT)
           AND pp.product_id = p.id
        WHERE p.id IN :ids
        """
    ).bindparams(bindparam("ids", expanding=True))

    rows = db.execute(stmt, {"branch_id": int(branch_id), "ids": ids}).mappings().all()

    out: dict[int, Decimal | None] = {pid: None for pid in ids}
    for r in rows:
        pid = int(r["product_id"])
        price = r["effective_price"]
        out[pid] = Decimal(str(price)) if price is not None else None

    return out
