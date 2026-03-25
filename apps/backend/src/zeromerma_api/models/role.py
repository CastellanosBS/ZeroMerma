from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

if TYPE_CHECKING:
    from .user_account import UserAccount


class Role(Base):
    """
    Administrative role catalog.

    Important semantics:
    - code: stable internal identifier used by auth/RBAC logic
    - name: user-facing display label
    - description: optional explanatory text for admins
    - is_active: soft-delete flag; inactive roles remain historically valid
    """

    __tablename__ = "role"
    __table_args__ = (Index("ix_role_is_active", "is_active"),)

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    code: Mapped[str] = mapped_column(
        String(40),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("true"),
        default=True,
    )

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    # IMPORTANT:
    # This reverse relationship must exist because UserAccount.role
    # declares back_populates="users".
    users: Mapped[list["UserAccount"]] = relationship(back_populates="role")
