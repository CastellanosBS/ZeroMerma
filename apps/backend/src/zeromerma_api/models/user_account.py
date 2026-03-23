from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, created_at_col, updated_at_col

# Type-only imports to avoid runtime circular imports
if TYPE_CHECKING:
    from .branch import Branch
    from .role import Role


class UserAccount(Base):
    """Application user / employee (belongs to exactly one Branch and one Role)."""

    __tablename__ = "user_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign keys (NOT NULL): every user must have a branch and a role
    branch_id: Mapped[int] = mapped_column(ForeignKey("branch.id"), index=True, nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("role.id"), index=True, nullable=False)

    # Identity
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text)

    # Auth (nullable until you wire password flows)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = created_at_col()
    updated_at: Mapped[datetime] = updated_at_col()

    # Bidirectional relations (string targets avoid import cycles at runtime)
    branch: Mapped[Branch] = relationship(back_populates="users")
    role: Mapped[Role] = relationship(back_populates="users")
