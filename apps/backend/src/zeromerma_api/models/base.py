# apps/backend/src/zeromerma_api/models/base.py
from __future__ import annotations

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Naming convention helps Alembic autogenerate stable, predictable names.
metadata_obj = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class Base(DeclarativeBase):
    """
    Single declarative base shared by all ORM models.
    Alembic uses Base.metadata as the canonical metadata registry.
    """

    metadata = metadata_obj


class IdMixin:
    """
    Optional future mixin for simple integer primary keys.
    Not used universally yet because several models already define BIGINT PKs explicitly.
    """

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


def created_at_col():
    """
    Standard created_at column:
    - timezone-aware
    - non-null
    - database-generated default timestamp
    """
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


def updated_at_col():
    """
    Standard updated_at column:
    - timezone-aware
    - non-null
    - database-generated insert timestamp
    - ORM-side update hook for modifications made through SQLAlchemy
    """
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
