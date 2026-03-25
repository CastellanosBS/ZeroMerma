from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from zeromerma_api.models.branch import Branch


def list_branches(
    db: Session,
    *,
    include_inactive: bool = True,
) -> list[Branch]:
    stmt: Select = select(Branch).order_by(Branch.code.asc())

    if not include_inactive:
        stmt = stmt.where(Branch.is_active.is_(True))

    return list(db.execute(stmt).scalars().all())
