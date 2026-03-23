from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Query
from sqlalchemy import and_, desc, func, select

from zeromerma_api.core.authz import (
    INVENTORY_ALLOWED_ROLES,
    enforce_branch_access,
    require_ctx_role,
)
from zeromerma_api.core.dependency_aliases import ActiveAuthContextDep, DbSessionDep
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product
from zeromerma_api.schemas.inventory import MovementRow, StockRow

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get(
    "/stock",
    response_model=list[StockRow],
    summary="Aggregated stock by (branch, product).",
)
def get_stock(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int | None = Query(None, description="Filter by branch id"),
    product_id: int | None = Query(None, description="Filter by product id"),
    sku: str | None = Query(None, description="Filter by product SKU"),
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page (max 200)"),
) -> list[StockRow]:
    """
    Compute stock as SUM(qty) grouped by (branch_id, product_id, sku, name).

    Security:
      - Role check via ctx.role_code (JWT claim).
      - Branch scoping enforced (ADMIN any branch, CASHIER own branch).
      - If branch_id is omitted, we default to ctx.user.branch_id.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=INVENTORY_ALLOWED_ROLES)

    effective_branch_id = int(branch_id) if branch_id is not None else int(ctx.user.branch_id)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=effective_branch_id,
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
        .where(InventoryMovement.branch_id == effective_branch_id)
        .group_by(
            InventoryMovement.branch_id,
            InventoryMovement.product_id,
            Product.sku,
            Product.name,
        )
        .order_by(InventoryMovement.branch_id.asc(), InventoryMovement.product_id.asc())
    )

    filters = []
    if product_id is not None:
        filters.append(InventoryMovement.product_id == int(product_id))
    if sku is not None:
        filters.append(Product.sku == sku)

    if filters:
        stmt = stmt.where(and_(*filters))

    offset = (int(page) - 1) * int(page_size)
    stmt = stmt.offset(offset).limit(int(page_size))

    rows = db.execute(stmt).all()

    return [
        StockRow(
            branch_id=int(r.branch_id),
            product_id=int(r.product_id),
            sku=r.sku,
            product_name=str(r.product_name),
            qty=Decimal(str(r.qty_sum or 0)),
        )
        for r in rows
    ]


@router.get(
    "/movements",
    response_model=list[MovementRow],
    summary="List inventory movements (newest first).",
)
def list_movements(
    db: DbSessionDep,
    ctx: ActiveAuthContextDep,
    branch_id: int | None = Query(None, description="Filter by branch id"),
    product_id: int | None = Query(None, description="Filter by product id"),
    reason: MovementReason | None = Query(None, description="Filter by reason"),
    date_from: datetime | None = Query(None, description="created_at ≥ this UTC datetime"),
    date_to: datetime | None = Query(None, description="created_at ≤ this UTC datetime"),
    limit: int = Query(50, ge=1, le=200, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Rows to skip (for paging)"),
) -> list[MovementRow]:
    """
    Return a paged list of ledger movements ordered by created_at DESC, id DESC.
    """
    role_code = require_ctx_role(ctx=ctx, allowed_roles=INVENTORY_ALLOWED_ROLES)

    effective_branch_id = int(branch_id) if branch_id is not None else int(ctx.user.branch_id)
    enforce_branch_access(
        current_user=ctx.user,
        role_code=role_code,
        branch_id=effective_branch_id,
    )

    stmt = (
        select(InventoryMovement)
        .where(InventoryMovement.branch_id == effective_branch_id)
        .order_by(desc(InventoryMovement.created_at), desc(InventoryMovement.id))
    )

    if product_id is not None:
        stmt = stmt.where(InventoryMovement.product_id == int(product_id))
    if reason is not None:
        stmt = stmt.where(InventoryMovement.reason == reason.value)
    if date_from is not None:
        stmt = stmt.where(InventoryMovement.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(InventoryMovement.created_at <= date_to)

    stmt = stmt.offset(int(offset)).limit(int(limit))
    rows = db.execute(stmt).scalars().all()

    return [
        MovementRow(
            id=int(mv.id),
            branch_id=int(mv.branch_id),
            product_id=int(mv.product_id),
            qty=Decimal(str(mv.qty)),
            reason=str(mv.reason),
            ref_type=mv.ref_type,
            ref_id=mv.ref_id,
            note=mv.note,
            created_by_id=mv.created_by_id,
            created_at=mv.created_at,
        )
        for mv in rows
    ]
