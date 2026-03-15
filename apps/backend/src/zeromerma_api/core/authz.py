# apps/backend/src/zeromerma_api/core/authz.py
# PURPOSE:
#   Central authorization helpers (roles + branch scoping).
#
# WHY THIS MODULE EXISTS:
#   We want a single source of truth for authorization rules so that:
#     - Routers remain thin and consistent
#     - Branch scoping is enforced everywhere the same way
#     - Role checks are explicit and auditable
#
# SECURITY PRINCIPLES:
#   - Authentication answers: "who are you?"
#   - Authorization answers: "what are you allowed to do?"
#   - Clients must never be trusted to decide scope (e.g., branch_id for non-admin).

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from zeromerma_api.models.user_account import UserAccount

ROLE_ADMIN = "ADMIN"
ROLE_CASHIER = "CASHIER"

POS_ALLOWED_ROLES: set[str] = {ROLE_ADMIN, ROLE_CASHIER}
INVENTORY_ALLOWED_ROLES: set[str] = {ROLE_ADMIN, ROLE_CASHIER}


def get_role_code(db: Session, *, role_id: int) -> str:
    """
    Resolve role.code from role.id.

    We use a DB lookup instead of trusting client input or duplicating role code
    into the user table.
    """
    code = db.execute(
        text("SELECT code FROM role WHERE id = :id"),
        {"id": int(role_id)},
    ).scalar_one_or_none()

    if not code:
        # This indicates corrupted data: user has a role_id that doesn't exist.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is invalid or missing.",
        )

    return str(code)


def is_admin(role_code: str) -> bool:
    """
    Return True if the role code is considered an administrator role.
    """
    return role_code == ROLE_ADMIN


def require_role(
    db: Session, *, current_user: UserAccount, allowed_roles: set[str]
) -> str:
    """
    Enforce that current_user.role is in allowed_roles.

    Returns:
      role_code (string) to avoid re-querying in the caller.

    Raises:
      HTTP 403 if not allowed.
    """
    role_code = get_role_code(db, role_id=int(current_user.role_id))

    if role_code not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: user role is not allowed for this operation.",
        )

    return role_code


def enforce_branch_access(
    *,
    current_user: UserAccount,
    role_code: str,
    branch_id: int,
) -> None:
    """
    Enforce branch scoping for operations that take an explicit branch_id.

    Rule v1:
      - ADMIN can operate on any branch_id
      - Others can only operate on their own branch_id
    """
    if is_admin(role_code):
        return

    if int(current_user.branch_id) != int(branch_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: user cannot operate on the requested branch.",
        )


def sale_branch_id(db: Session, *, sale_id: int) -> int | None:
    """
    Get sale.branch_id from sale id, or None if sale doesn't exist.
    """
    return db.execute(
        text("SELECT branch_id FROM sale WHERE id = :id"),
        {"id": int(sale_id)},
    ).scalar_one_or_none()


def enforce_sale_access(
    db: Session,
    *,
    current_user: UserAccount,
    role_code: str,
    sale_id: int,
) -> None:
    """
    Enforce that the requested sale belongs to a branch the user can access.

    Rule v1:
      - If sale doesn't exist -> 404
      - ADMIN -> allowed
      - Others -> sale.branch_id must equal current_user.branch_id
    """
    b = sale_branch_id(db, sale_id=sale_id)
    if b is None:
        raise HTTPException(status_code=404, detail=f"Sale {sale_id} not found.")

    if is_admin(role_code):
        return

    if int(b) != int(current_user.branch_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: sale belongs to a different branch.",
        )
