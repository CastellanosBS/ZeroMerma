from __future__ import annotations

import re

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.models.role import Role

PROTECTED_ROLE_CODES = {"ADMIN"}


def _normalize_code(raw: str) -> str:
    code = re.sub(r"\s+", "_", str(raw).strip().upper())
    if not code:
        raise DomainValidationError(message="Role code cannot be empty.")
    if len(code) > 40:
        raise DomainValidationError(message="Role code cannot exceed 40 characters.")
    return code


def _normalize_name(raw: str) -> str:
    name = str(raw).strip()
    if not name:
        raise DomainValidationError(message="Role name cannot be empty.")
    if len(name) > 100:
        raise DomainValidationError(message="Role name cannot exceed 100 characters.")
    return name


def _normalize_description(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def list_roles(
    db: Session,
    *,
    include_inactive: bool = True,
) -> list[Role]:
    stmt: Select = select(Role).order_by(Role.code.asc())

    if not include_inactive:
        stmt = stmt.where(Role.is_active.is_(True))

    return list(db.execute(stmt).scalars().all())


def get_role_or_404(db: Session, *, role_id: int) -> Role:
    role = db.get(Role, int(role_id))
    if role is None:
        raise DomainNotFoundError(
            message="Role not found.",
            details={"role_id": int(role_id)},
        )
    return role


def _ensure_unique_code(
    db: Session,
    *,
    code: str,
    exclude_role_id: int | None = None,
) -> None:
    stmt = select(Role).where(Role.code == code)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is None:
        return

    if exclude_role_id is not None and int(existing.id) == int(exclude_role_id):
        return

    raise DomainConflictError(
        message="Role code already exists.",
        details={"code": code},
    )


def create_role(
    db: Session,
    *,
    code: str,
    name: str,
    description: str | None,
    is_active: bool,
) -> Role:
    normalized_code = _normalize_code(code)
    normalized_name = _normalize_name(name)
    normalized_description = _normalize_description(description)

    _ensure_unique_code(db, code=normalized_code)

    role = Role(
        code=normalized_code,
        name=normalized_name,
        description=normalized_description,
        is_active=bool(is_active),
    )

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(
    db: Session,
    *,
    role_id: int,
    code: str | None = None,
    name: str | None = None,
    description: str | None = None,
    is_active: bool | None = None,
) -> Role:
    role = get_role_or_404(db, role_id=role_id)

    original_code = str(role.code).upper()

    if code is not None:
        normalized_code = _normalize_code(code)
        if original_code in PROTECTED_ROLE_CODES and normalized_code != original_code:
            raise DomainConflictError(
                message="Protected system role code cannot be changed.",
                details={"role_id": int(role.id), "code": original_code},
            )
        _ensure_unique_code(db, code=normalized_code, exclude_role_id=int(role.id))
        role.code = normalized_code

    if name is not None:
        role.name = _normalize_name(name)

    if description is not None:
        role.description = _normalize_description(description)

    if is_active is not None:
        if original_code in PROTECTED_ROLE_CODES and not bool(is_active):
            raise DomainConflictError(
                message="Protected system role cannot be deactivated.",
                details={"role_id": int(role.id), "code": original_code},
            )
        role.is_active = bool(is_active)

    db.commit()
    db.refresh(role)
    return role


def deactivate_role(
    db: Session,
    *,
    role_id: int,
) -> Role:
    role = get_role_or_404(db, role_id=role_id)

    normalized_code = str(role.code).upper()
    if normalized_code in PROTECTED_ROLE_CODES:
        raise DomainConflictError(
            message="Protected system role cannot be deactivated.",
            details={"role_id": int(role.id), "code": normalized_code},
        )

    role.is_active = False
    db.commit()
    db.refresh(role)
    return role
