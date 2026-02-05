from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import (
    Base,
    created_at_col,
    updated_at_col,
)  # single Declarative Base shared by all models

# Type-only import to avoid runtime circular imports while keeping IDE type hints
if TYPE_CHECKING:
    from .user_account import UserAccount


class Branch(Base):
    """Physical store / location (e.g., MAIN, NORTH-01)."""

    __tablename__ = "branch"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    # Bidirectional relation: one branch → many users
    users: Mapped[list[UserAccount]] = relationship(back_populates="branch")
