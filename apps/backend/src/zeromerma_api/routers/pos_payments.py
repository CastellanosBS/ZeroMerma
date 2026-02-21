# apps/backend/src/zeromerma_api/routers/pos_payments.py
# PURPOSE:
#   Payments endpoints under POS.
#   Mounted under /pos via routers/pos.py.

from __future__ import annotations

from typing import Generator

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.schemas.payment import PaymentCreate, PaymentOut
from zeromerma_api.schemas.sale import SaleDetailOut
from zeromerma_api.services.payment_service import add_payment, get_sale_detail

router = APIRouter(prefix="/sales", tags=["pos"])  # paths: /pos/sales/{id}/...


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/{sale_id}/payments", response_model=PaymentOut)
def api_add_payment(
    sale_id: int, payload: PaymentCreate, db: Session = Depends(get_db)
):
    """
    Append a payment to a sale.

    Error mapping:
      - 404 if sale not found
      - 409 for business conflicts (sale not OPEN, overpay)
      - 400 for invalid method/amount logic
    """
    try:
        p = add_payment(
            db,
            sale_id=sale_id,
            method=payload.method,
            amount=payload.amount,
            reference=payload.reference,
        )
        db.commit()
        db.refresh(p)
        return p

    except LookupError as e:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(e)) from e

    except ValueError as e:
        db.rollback()
        # In MVP we use 409 for domain conflicts; method errors could be 400 later.
        raise HTTPException(status_code=409, detail=str(e)) from e

    except Exception:
        db.rollback()
        raise


@router.get("/{sale_id}", response_model=SaleDetailOut)
def api_get_sale_detail(sale_id: int, db: Session = Depends(get_db)):
    """
    Return a sale with items, payments, and computed paid/balance.
    """
    try:
        return get_sale_detail(db, sale_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
