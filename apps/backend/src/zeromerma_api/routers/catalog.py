# apps/backend/src/zeromerma_api/routers/catalog.py
# PURPOSE:
#   Catalog API:
#     GET /catalog/categories
#     GET /catalog/products
#     ADMIN:
#       POST /catalog/categories
#       PUT  /catalog/categories/{id}
#       POST /catalog/products
#       PUT  /catalog/products/{id}
#
# AUTHZ:
#   - Read endpoints: ADMIN or CASHIER
#   - Write endpoints: ADMIN only
#
# NOTE:
#   Catalog is global (no branch scoping) in v1.

from __future__ import annotations

from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from zeromerma_api.core.authz import POS_ALLOWED_ROLES, ROLE_ADMIN, require_role
from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.user_account import UserAccount
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


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a DB session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_catalog_read(db: Session, current_user: UserAccount) -> str:
    """
    Enforce read permissions for the Catalog module.
    """
    return require_role(db, current_user=current_user, allowed_roles=POS_ALLOWED_ROLES)


def _require_admin(db: Session, current_user: UserAccount) -> str:
    """
    Enforce admin role.
    """
    return require_role(db, current_user=current_user, allowed_roles={ROLE_ADMIN})


@router.get("/categories", response_model=List[CategoryOut])
def api_get_categories(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    List product categories.

    Query params:
      - include_inactive: if True, return inactive categories too

    Security:
      - Requires authenticated user with allowed role (ADMIN/CASHIER).
    """
    _require_catalog_read(db, current_user)
    return list_categories(db, include_inactive=include_inactive)


@router.get("/products", response_model=List[ProductOut])
def api_get_products(
    category_id: Optional[int] = Query(None, ge=1),
    is_input: Optional[bool] = Query(None),
    include_inactive: bool = Query(False),
    q: Optional[str] = Query(None, min_length=1, max_length=200),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    List products.

    Query params:
      - category_id: filter by category
      - is_input: filter inputs (true) vs sellables (false)
      - q: substring search on name/sku
      - include_inactive: include disabled products
      - limit/offset: pagination

    Security:
      - Requires authenticated user with allowed role (ADMIN/CASHIER).
    """
    _require_catalog_read(db, current_user)
    return list_products(
        db,
        category_id=category_id,
        is_input=is_input,
        include_inactive=include_inactive,
        q=q,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# ADMIN endpoints
# ---------------------------------------------------------------------------


@router.post("/categories", response_model=CategoryOut)
def api_create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Create a category (ADMIN only).
    """
    _require_admin(db, current_user)
    try:
        row = create_category(
            db,
            code=payload.code,
            name=payload.name,
            is_active=payload.is_active,
        )
        db.commit()
        return row
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.put("/categories/{category_id}", response_model=CategoryOut)
def api_update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Update a category (ADMIN only).
    """
    _require_admin(db, current_user)
    try:
        row = update_category(
            db,
            category_id=category_id,
            code=payload.code,
            name=payload.name,
            is_active=payload.is_active,
        )
        db.commit()
        return row
    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.post("/products", response_model=ProductOut)
def api_create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Create a product (ADMIN only).
    """
    _require_admin(db, current_user)
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
        return row
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise


@router.put("/products/{product_id}", response_model=ProductOut)
def api_update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    """
    Update a product (ADMIN only).
    """
    _require_admin(db, current_user)
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
        return row
    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception:
        db.rollback()
        raise
