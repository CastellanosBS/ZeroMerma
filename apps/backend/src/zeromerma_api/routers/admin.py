# apps/backend/src/zeromerma_api/routers/admin.py
# PURPOSE:
#   Administrative endpoints to manage Roles/Branches/Users.
#
# ACCESS CONTROL:
#   - ADMIN only.
#
# USER PROVISIONING:
#   - Create users with an initial password (hashed server-side).
#   - Reset passwords (hashed server-side).

from __future__ import annotations

from typing import Generator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.core.authz import ROLE_ADMIN, require_role
from zeromerma_api.core.deps_auth import get_current_active_user
from zeromerma_api.core.security import hash_password
from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount
from zeromerma_api.schemas.admin import (
    AdminBranchOut,
    AdminPasswordResetIn,
    AdminRoleOut,
    AdminUserCreateIn,
    AdminUserOut,
    AdminUserUpdateIn,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI DB dependency: open a session, yield it, always close it.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_admin(db: Session, current_user: UserAccount) -> None:
    """
    Enforce ADMIN role for /admin endpoints.
    """
    require_role(db, current_user=current_user, allowed_roles={ROLE_ADMIN})


def _basic_email_shape_ok(email: str) -> bool:
    """
    Minimal email shape validation.

    Why minimal:
    - We avoid strict validators that may reject special-use domains (.local).
    - We still prevent clearly invalid values.
    """
    if not email or "@" not in email:
        return False
    left, _, right = email.partition("@")
    if not left.strip() or not right.strip():
        return False
    return True


@router.get("/whoami")
def whoami(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> dict:
    """
    Convenience endpoint to verify auth + role resolution works.
    """
    _require_admin(db, current_user)

    role = db.execute(
        select(Role).where(Role.id == current_user.role_id)
    ).scalar_one_or_none()

    return {
        "id": int(current_user.id),
        "email": current_user.email,
        "branch_id": int(current_user.branch_id),
        "role_id": int(current_user.role_id),
        "role_code": role.code if role else None,
        "is_active": bool(current_user.is_active),
    }


@router.get("/roles", response_model=List[AdminRoleOut])
def list_roles(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> List[Role]:
    """
    List roles (ADMIN only).
    """
    _require_admin(db, current_user)
    return list(db.execute(select(Role).order_by(Role.code.asc())).scalars().all())


@router.get("/branches", response_model=List[AdminBranchOut])
def list_branches(
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> List[Branch]:
    """
    List branches (ADMIN only).
    """
    _require_admin(db, current_user)
    return list(db.execute(select(Branch).order_by(Branch.code.asc())).scalars().all())


@router.get("/users", response_model=List[AdminUserOut])
def list_users(
    branch_id: Optional[int] = Query(None, ge=1, description="Optional branch filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> List[UserAccount]:
    """
    List users (ADMIN only), optionally filtered by branch_id.
    """
    _require_admin(db, current_user)

    stmt = select(UserAccount).order_by(UserAccount.id.asc())

    if branch_id is not None:
        stmt = stmt.where(UserAccount.branch_id == int(branch_id))

    stmt = stmt.offset(int(offset)).limit(int(limit))

    return list(db.execute(stmt).scalars().all())


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreateIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> UserAccount:
    """
    Create a new user (ADMIN only).

    Validations:
    - branch_id must exist.
    - role_id must exist.
    - email must be unique.
    - password is hashed server-side using PBKDF2.
    """
    _require_admin(db, current_user)

    email = payload.email.strip().lower()
    if not _basic_email_shape_ok(email):
        raise HTTPException(status_code=422, detail="Invalid email format.")

    # Validate branch exists
    branch = db.execute(
        select(Branch).where(Branch.id == int(payload.branch_id))
    ).scalar_one_or_none()
    if branch is None:
        raise HTTPException(
            status_code=404, detail=f"Branch {payload.branch_id} not found."
        )

    # Validate role exists
    role = db.execute(
        select(Role).where(Role.id == int(payload.role_id))
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=404, detail=f"Role {payload.role_id} not found."
        )

    # Check email uniqueness (pre-check; still handle IntegrityError for race safety)
    existing = db.execute(
        select(UserAccount).where(UserAccount.email == email)
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already exists.")

    user = UserAccount(
        branch_id=int(payload.branch_id),
        role_id=int(payload.role_id),
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=bool(payload.is_active),
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # If unique constraint is enforced at DB level, race conditions land here.
        raise HTTPException(status_code=409, detail="Email already exists.") from e

    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdateIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> UserAccount:
    """
    Update user fields (ADMIN only).
    """
    _require_admin(db, current_user)

    user = db.execute(
        select(UserAccount).where(UserAccount.id == int(user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    if payload.role_id is not None:
        role = db.execute(
            select(Role).where(Role.id == int(payload.role_id))
        ).scalar_one_or_none()
        if role is None:
            raise HTTPException(
                status_code=404, detail=f"Role {payload.role_id} not found."
            )
        user.role_id = int(payload.role_id)

    if payload.branch_id is not None:
        branch = db.execute(
            select(Branch).where(Branch.id == int(payload.branch_id))
        ).scalar_one_or_none()
        if branch is None:
            raise HTTPException(
                status_code=404, detail=f"Branch {payload.branch_id} not found."
            )
        user.branch_id = int(payload.branch_id)

    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()

    if payload.is_active is not None:
        user.is_active = bool(payload.is_active)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=AdminUserOut)
def reset_password(
    user_id: int,
    payload: AdminPasswordResetIn,
    db: Session = Depends(get_db),
    current_user: UserAccount = Depends(get_current_active_user),
) -> UserAccount:
    """
    Reset a user's password (ADMIN only).

    Implementation:
    - Hash the new password with PBKDF2 (hash_password).
    - Store it in password_hash.
    """
    _require_admin(db, current_user)

    user = db.execute(
        select(UserAccount).where(UserAccount.id == int(user_id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")

    user.password_hash = hash_password(payload.new_password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user
