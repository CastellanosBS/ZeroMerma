from __future__ import annotations

from fastapi import APIRouter, Query

from zeromerma_api.core.authz import POS_ALLOWED_ROLES, ROLE_ADMIN, require_ctx_role
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
)
from zeromerma_api.schemas.catalog import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCreate,
    ProductOut,
    ProductUpdate,
)
from zeromerma_api.services.catalog_service import (
    create_category,
    create_product,
    list_categories,
    list_products,
    update_category,
    update_product,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])


def _require_catalog_read(ctx: ActiveAuthContextDep) -> str:
    """
    Read endpoints are allowed for ADMIN and CASHIER.
    """
    return require_ctx_role(ctx=ctx, allowed_roles=POS_ALLOWED_ROLES)


def _require_catalog_write(ctx: ActiveAuthContextDep) -> str:
    """
    Write endpoints are ADMIN-only.
    """
    return require_ctx_role(ctx=ctx, allowed_roles={ROLE_ADMIN})


@router.get("/categories", response_model=list[CategoryOut])
def api_list_categories(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    include_inactive: bool = Query(False),
) -> list[CategoryOut]:
    """
    List catalog categories.

    Catalog is global in v1 (no branch scoping).
    """
    _require_catalog_read(ctx)
    rows = list_categories(db, include_inactive=include_inactive)
    return [CategoryOut.model_validate(r) for r in rows]


@router.get("/products", response_model=list[ProductOut])
def api_list_products(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    category_id: int | None = Query(None, ge=1),
    is_input: bool | None = Query(None),
    include_inactive: bool = Query(False),
    q: str | None = Query(None, min_length=1, max_length=200),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[ProductOut]:
    """
    List catalog products.

    Catalog is global in v1 (no branch scoping).
    """
    _require_catalog_read(ctx)

    rows = list_products(
        db,
        category_id=category_id,
        is_input=is_input,
        include_inactive=include_inactive,
        q=q,
        limit=limit,
        offset=offset,
    )
    return [ProductOut.model_validate(r) for r in rows]


@router.post("/categories", response_model=CategoryOut)
def api_create_category(
    payload: CategoryCreate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> CategoryOut:
    """
    Create a category (ADMIN only).
    """
    _require_catalog_write(ctx)

    try:
        row = create_category(
            db,
            code=payload.code,
            name=payload.name,
            is_active=payload.is_active,
        )
        db.commit()
        return CategoryOut.model_validate(row)
    except ValueError as e:
        db.rollback()
        raise DomainConflictError(message=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.put("/categories/{category_id}", response_model=CategoryOut)
def api_update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> CategoryOut:
    """
    Update a category (ADMIN only).
    """
    _require_catalog_write(ctx)

    try:
        row = update_category(
            db,
            category_id=category_id,
            code=payload.code,
            name=payload.name,
            is_active=payload.is_active,
        )
        db.commit()
        return CategoryOut.model_validate(row)
    except LookupError as e:
        db.rollback()
        raise DomainNotFoundError(message=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise DomainConflictError(message=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.post("/products", response_model=ProductOut)
def api_create_product(
    payload: ProductCreate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> ProductOut:
    """
    Create a product (ADMIN only).
    """
    _require_catalog_write(ctx)

    try:
        row = create_product(
            db,
            sku=payload.sku,
            name=payload.name,
            category_id=payload.category_id,
            uom=payload.uom,
            is_input=payload.is_input,
            sale_price=payload.sale_price,
            standard_cost=payload.standard_cost,
            is_active=payload.is_active,
        )
        db.commit()
        return ProductOut.model_validate(row)
    except ValueError as e:
        db.rollback()
        raise DomainConflictError(message=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.put("/products/{product_id}", response_model=ProductOut)
def api_update_product(
    product_id: int,
    payload: ProductUpdate,
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
) -> ProductOut:
    """
    Update a product (ADMIN only).
    """
    _require_catalog_write(ctx)

    try:
        row = update_product(
            db,
            product_id=product_id,
            sku=payload.sku,
            name=payload.name,
            category_id=payload.category_id,
            uom=payload.uom,
            is_input=payload.is_input,
            sale_price=payload.sale_price,
            standard_cost=payload.standard_cost,
            is_active=payload.is_active,
        )
        db.commit()
        return ProductOut.model_validate(row)
    except LookupError as e:
        db.rollback()
        raise DomainNotFoundError(message=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise DomainConflictError(message=str(e)) from e
    except Exception:
        db.rollback()
        raise
