# apps/backend/src/zeromerma_api/models/production_run.py
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .branch import Branch
    from .user_account import UserAccount


class ProductionRun(Base):
    __table_args__ = (Index("ix_production_run_created_at", "created_at"),)
    """
    Production event header.

    Detailed input/output rows are not stored here directly.
    They are represented in inventory_movement using:
      - ref_type = 'PRODUCTION'
      - ref_id   = production_run.id
    """

    __tablename__ = "production_run"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branch.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    branch: Mapped["Branch"] = relationship()
    created_by: Mapped["UserAccount"] = relationship()
