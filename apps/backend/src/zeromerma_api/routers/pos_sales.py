# apps/backend/src/zeromerma_api/routers/pos_sales.py
# PURPOSE:
#   Sales endpoints under the POS area.
#   Mounted under /pos via routers/pos.py (so this file uses prefix="/sales").

from __future__ import annotations

from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.schemas.sale import SaleCreate, SaleOut
from zeromerma_api.services.sale_service import create_sale, list_sales

router = APIRouter(prefix="/sales", tags=["pos"])  # final path becomes /pos/sales


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=SaleOut)
def api_create_sale(payload: SaleCreate, db: Session = Depends(get_db)):
    """
    Create a sale + items transactionally.

    Error mapping:
      - 404 if referenced objects do not exist (cash_session/user/product missing)
      - 409 if business rules prevent action (session not OPEN / wrong branch)
      - 400 for bad payload logic (empty items, invalid qty/price)
    """
    try:
        sale = create_sale(
            db,
            branch_id=payload.branch_id,
            cash_session_id=payload.cash_session_id,
            created_by_id=payload.created_by_id,
            items=[it.model_dump() for it in payload.items],
        )
        db.commit()
        db.refresh(sale)  # ensure sale.id and timestamps are loaded
        return sale

    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e

    except ValueError as e:
        db.rollback()
        # Most ValueErrors in service are “state conflicts” (session not open / wrong branch)
        # If you prefer 400 for some cases, we can split them by message or custom exception types later.
        raise HTTPException(status_code=409, detail=str(e)) from e

    except Exception:
        db.rollback()
        raise


@router.get("", response_model=List[SaleOut])
def api_list_sales(
    branch_id: Optional[int] = Query(None, ge=1),
    cash_session_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List sales (newest first) with optional filters and paging.
    """
    return list_sales(
        db,
        branch_id=branch_id,
        cash_session_id=cash_session_id,
        limit=limit,
        offset=offset,
    )
