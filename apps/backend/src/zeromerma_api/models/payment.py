# apps/backend/src/zeromerma_api/models/payment.py
# PURPOSE:
#   Immutable payment records attached to a sale.
#   A sale can have many payments (partial payments allowed by data model),
#   but for MVP we will enforce "no overpay" at the service layer.

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .sale import Sale


class PaymentMethod(str, Enum):
    """
    MVP payment methods.
    Stored as string for simplicity; we can expand later.
    """

    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    OTHER = "OTHER"


class Payment(Base):

    __table_args__ = (
        Index("ix_payment_created_at", "created_at"),
        Index("ix_payment_method", "method"),
    )
    """
    Payment record:
      - belongs to a sale
      - captures method and amount
      - optional reference for external transaction identifiers
    """

    __tablename__ = "payment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sale.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    method: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    reference: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sale: Mapped["Sale"] = relationship()
