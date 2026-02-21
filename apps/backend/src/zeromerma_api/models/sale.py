# PURPOSE: Sale header table for POS.
#          Holds branch/session linkage, totals, status, and audit fields.

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .cash_session import CashSession
    from .sale_item import SaleItem
    from .user_account import UserAccount


class SaleStatus(str, Enum):
    """
    Allowed sale statuses.
    For MVP we’ll use only OPEN and CANCELED later.
    """

    OPEN = "OPEN"
    CANCELED = "CANCELED"


class Sale(Base):
    """
    Sale header:
      - belongs to one branch
      - belongs to one cash session (required for POS flow)
      - created_by for auditing
      - totals computed by backend (subtotal/tax/total)
    """

    __tablename__ = "sale"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    cash_session_id: Mapped[int] = mapped_column(
        ForeignKey("cash_session.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Totals: NUMERIC to avoid float rounding errors in DB
    subtotal: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    tax: Mapped[float] = mapped_column(
        Numeric(18, 2), nullable=False, server_default="0"
    )
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="OPEN",
    )

    updated_at: Mapped[datetime] = updated_at_col()

    # Relationships
    branch: Mapped["Branch"] = relationship()
    cash_session: Mapped["CashSession"] = relationship()
    created_by: Mapped["UserAccount"] = relationship()

    items: Mapped[List["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",  # if a sale is removed (dev only), items go too
    )
