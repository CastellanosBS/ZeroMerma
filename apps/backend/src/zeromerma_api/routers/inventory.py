# apps/backend/src/zeromerma_api/routers/inventory.py
# PURPOSE: Read-only inventory endpoints:
#   - GET /inventory/stock: aggregate SUM(qty) by (branch, product)
#   - GET /inventory/movements: list movements with filters/pagination

from __future__ import (
    annotations,
)  # Modern typing mode; prevents certain circular import issues.

from collections.abc import Generator  # Typing for query params and response lists.
from datetime import datetime  # For date range filters.

from fastapi import APIRouter, Depends, Query  # Core FastAPI constructs.
from sqlalchemy import (
    and_,
    desc,
    func,
    select,
)  # SQL builders for aggregation and sorting.
from sqlalchemy.orm import Session  # ORM Session type for the dependency.

from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.inventory_movement import InventoryMovement, MovementReason
from zeromerma_api.models.product import Product
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.inventory import MovementRow, StockRow


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that opens a Session, yields it to the handler,
    and always closes it after the request (connection returned to pool).
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(
    prefix="/inventory", tags=["inventory"]
)  # All routes mount under /inventory.


@router.get(
    "/stock",
    response_model=list[StockRow],  # We return a list of StockRow items.
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
    """
    Compute stock as SUM(qty) grouped by (branch_id, product_id, sku, name).
    Optional filters narrow the aggregation; results are paginated with stable ordering.
    """
    # Base SELECT with JOIN and GROUP BY across grouping columns.
    stmt = (
        select(
            InventoryMovement.branch_id,  # grouping key 1
            InventoryMovement.product_id,  # grouping key 2
            Product.sku,  # grouping key 3
            Product.name.label("product_name"),  # grouping key 4 (aliased for schema)
            func.sum(InventoryMovement.qty).label("qty_sum"),  # aggregated metric
        )
        .join(
            Product, Product.id == InventoryMovement.product_id
        )  # join to read sku/name
        .group_by(
            InventoryMovement.branch_id,
            InventoryMovement.product_id,
            Product.sku,
            Product.name,
        )
        .order_by(InventoryMovement.branch_id.asc(), InventoryMovement.product_id.asc())
    )

    # Dynamic filters only when specified.
    filters = []
    if branch_id is not None:
        filters.append(InventoryMovement.branch_id == branch_id)
    if product_id is not None:
        filters.append(InventoryMovement.product_id == product_id)
    if sku is not None:
        filters.append(Product.sku == sku)

    if filters:
        stmt = stmt.where(and_(*filters))

    # 1-based page → 0-based offset; apply pagination to the grouped result.
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    # Execute and fetch.
    rows = db.execute(stmt).all()

    # Map DB decimals to float for JSON.
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
):
    """
    Return a paged list of ledger movements ordered by created_at DESC, id DESC.
    """
    stmt = select(InventoryMovement).order_by(  # stable “newest first”
        desc(InventoryMovement.created_at),
        desc(InventoryMovement.id),
    )

    if branch_id is not None:
        stmt = stmt.where(InventoryMovement.branch_id == branch_id)
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

    # Map to the response model (Decimal → float for qty).
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
