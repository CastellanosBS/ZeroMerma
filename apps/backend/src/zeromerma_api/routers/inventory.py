# apps/backend/src/zeromerma_api/routers/inventory.py
# PURPOSE: Read-only inventory endpoints:
#   - GET /inventory/stock
#   - GET /inventory/movements
#
# AUTHORIZATION:
#   - Allowed roles: ADMIN, CASHIER
#   - Branch scoping:
#       * ADMIN -> can query any branch_id (if provided)
#       * CASHIER -> only their own branch_id
#   - If branch_id is omitted, we default to current_user.branch_id for safety.

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session

from zeromerma_api.core.authz import (
    INVENTORY_ALLOWED_ROLES,
    enforce_branch_access,
    require_role,
)
from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.inventory import MovementRow, StockRow


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get(
    "/stock",
    response_model=list[StockRow],
    summary="Aggregated stock by (branch, product).",
)
def get_stock(
    branch_id: int | None = Query(None, description="Filter by branch id"),
    product_id: int | None = Query(None, description="Filter by product id"),
    sku: str | None = Query(None, description="Filter by product SKU"),
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    role_code = require_role(
        db, current_user=current_user, allowed_roles=INVENTORY_ALLOWED_ROLES
    )

    effective_branch_id = (
        branch_id if branch_id is not None else int(current_user.branch_id)
    )
    enforce_branch_access(
        current_user=current_user,
        role_code=role_code,
        branch_id=int(effective_branch_id),
    )

    stmt = (
        select(
            InventoryMovement.branch_id,
            InventoryMovement.product_id,
            Product.sku,
            Product.name.label("product_name"),
            func.sum(InventoryMovement.qty).label("qty_sum"),
        )
        .join(Product, Product.id == InventoryMovement.product_id)
        .group_by(
            InventoryMovement.branch_id,
            InventoryMovement.product_id,
            Product.sku,
            Product.name,
        )
        .order_by(InventoryMovement.branch_id.asc(), InventoryMovement.product_id.asc())
        .where(InventoryMovement.branch_id == int(effective_branch_id))
    )

    filters = []
    if product_id is not None:
        filters.append(InventoryMovement.product_id == product_id)
    if sku is not None:
        filters.append(Product.sku == sku)
    if filters:
        stmt = stmt.where(and_(*filters))

    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    rows = db.execute(stmt).all()

    return [
        StockRow(
            branch_id=r.branch_id,
            product_id=r.product_id,
            sku=r.sku,
            product_name=r.product_name,
            qty=float(r.qty_sum or 0),
        )
        for r in rows
    ]


@router.get(
    "/movements",
    response_model=list[MovementRow],
    summary="List inventory movements (newest first).",
)
def list_movements(
    branch_id: int | None = Query(None, description="Filter by branch id"),
    product_id: int | None = Query(None, description="Filter by product id"),
    reason: MovementReason | None = Query(None, description="Filter by reason"),
    date_from: datetime | None = Query(
        None, description="created_at ≥ this UTC datetime"
    ),
    date_to: datetime | None = Query(
        None, description="created_at ≤ this UTC datetime"
    ),
    limit: int = Query(50, ge=1, le=200, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Rows to skip (for paging)"),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
):
    role_code = require_role(
        db, current_user=current_user, allowed_roles=INVENTORY_ALLOWED_ROLES
    )

    effective_branch_id = (
        branch_id if branch_id is not None else int(current_user.branch_id)
    )
    enforce_branch_access(
        current_user=current_user,
        role_code=role_code,
        branch_id=int(effective_branch_id),
    )

    stmt = (
        select(InventoryMovement)
        .where(InventoryMovement.branch_id == int(effective_branch_id))
        .order_by(
            desc(InventoryMovement.created_at),
            desc(InventoryMovement.id),
        )
    )

    if product_id is not None:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    if reason is not None:
        stmt = stmt.where(InventoryMovement.reason == reason.value)
    if date_from is not None:
        stmt = stmt.where(InventoryMovement.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(InventoryMovement.created_at <= date_to)

    stmt = stmt.offset(offset).limit(limit)

    rows = db.execute(stmt).scalars().all()

    return [
        MovementRow(
            id=mv.id,
            branch_id=mv.branch_id,
            product_id=mv.product_id,
            qty=float(mv.qty),
            reason=mv.reason,
            ref_type=mv.ref_type,
            ref_id=mv.ref_id,
            note=mv.note,
            created_by_id=mv.created_by_id,
            created_at=mv.created_at,
        )
        for mv in rows
    ]
