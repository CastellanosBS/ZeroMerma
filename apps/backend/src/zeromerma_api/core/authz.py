# apps/backend/src/zeromerma_api/core/authz.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.core.auth_context import AuthContext
from zeromerma_api.core.domain_errors import (
    DomainAuthorizationError,
    DomainNotFoundError,
)
from zeromerma_api.models.role import Role
from zeromerma_api.models.sale import Sale
from zeromerma_api.models.user_account import UserAccount

ROLE_ADMIN = "ADMIN"
ROLE_CASHIER = "CASHIER"

POS_ALLOWED_ROLES: set[str] = {ROLE_ADMIN, ROLE_CASHIER}
INVENTORY_ALLOWED_ROLES: set[str] = {ROLE_ADMIN, ROLE_CASHIER}


def get_role_code(db: Session, *, role_id: int) -> str:
    """
    Resolve role.code from role.id.

    Raises:
        DomainAuthorizationError: when the role is invalid or missing.
    """
    stmt = select(Role.code).where(Role.id == int(role_id))
    code = db.scalar(stmt)

    if not code:
        raise DomainAuthorizationError(
            message="User role is invalid or missing.",
            details={"role_id": int(role_id)},
        )

    return str(code)


def is_admin(role_code: str) -> bool:
    """
    Return True when the role code is considered administrative.
    """
    return role_code == ROLE_ADMIN


def require_role_code(*, role_code: str, allowed_roles: set[str]) -> str:
    """
    Enforce that role_code is in allowed_roles.

    Use this on the fast path when role_code already comes from JWT claims.
    """
    if role_code not in allowed_roles:
        raise DomainAuthorizationError(
            message="User role is not allowed for this operation.",
            details={
                "role_code": str(role_code),
                "allowed_roles": sorted(allowed_roles),
            },
        )
    return role_code


def require_ctx_role(*, ctx: AuthContext, allowed_roles: set[str]) -> str:
    """
    Enforce allowed roles using AuthContext.
    """
    return require_role_code(role_code=ctx.role_code, allowed_roles=allowed_roles)


def require_role(
    db: Session,
    *,
    current_user: UserAccount,
    allowed_roles: set[str],
) -> str:
    """
    Backward-compatible role enforcement using DB lookup.

    Keep this helper during migration of older routers. Newer routers should
    prefer require_ctx_role() to avoid the extra query.
    """
    role_code = get_role_code(db, role_id=int(current_user.role_id))
    return require_role_code(role_code=role_code, allowed_roles=allowed_roles)


def enforce_branch_access(
    *,
    current_user: UserAccount,
    role_code: str,
    branch_id: int,
) -> None:
    """
    Enforce branch scoping for operations that take an explicit branch_id.

    Rule:
      - ADMIN  -> can operate on any branch
      - others -> only their own branch
    """
    if is_admin(role_code):
        return

    if int(current_user.branch_id) != int(branch_id):
        raise DomainAuthorizationError(
            message="User cannot operate on the requested branch.",
            details={
                "requested_branch_id": int(branch_id),
                "user_branch_id": int(current_user.branch_id),
            },
        )


def sale_branch_id(db: Session, *, sale_id: int) -> int | None:
    """
    Resolve sale.branch_id from sale id, or None if the sale does not exist.
    """
    stmt = select(Sale.branch_id).where(Sale.id == int(sale_id))
    value = db.scalar(stmt)
    return int(value) if value is not None else None


def enforce_sale_access(
    db: Session,
    *,
    current_user: UserAccount,
    role_code: str,
    sale_id: int,
) -> None:
    """
    Enforce that the requested sale belongs to a branch the user can access.
    """
    branch_id = sale_branch_id(db, sale_id=sale_id)
    if branch_id is None:
        raise DomainNotFoundError(
            message=f"Sale {sale_id} not found.",
            details={"sale_id": int(sale_id)},
        )

    if is_admin(role_code):
        return

    if int(branch_id) != int(current_user.branch_id):
        raise DomainAuthorizationError(
            message="Sale belongs to a different branch.",
            details={
                "sale_id": int(sale_id),
                "sale_branch_id": int(branch_id),
                "user_branch_id": int(current_user.branch_id),
            },
        )
