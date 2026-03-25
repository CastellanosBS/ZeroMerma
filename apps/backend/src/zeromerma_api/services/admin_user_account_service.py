from __future__ import annotations

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from zeromerma_api.core.authz import ROLE_ADMIN
from zeromerma_api.core.domain_errors import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from zeromerma_api.core.security import hash_password
from zeromerma_api.models.branch import Branch
from zeromerma_api.models.role import Role
from zeromerma_api.models.user_account import UserAccount


def _normalize_email(raw: str) -> str:
    value = str(raw).strip().lower()
    if not value:
        raise DomainValidationError(message="Email cannot be empty.")
    return value


def _normalize_full_name(raw: str) -> str:
    value = str(raw).strip()
    if not value:
        raise DomainValidationError(message="Full name cannot be empty.")
    return value


def _get_branch_or_404(db: Session, *, branch_id: int) -> Branch:
    branch = db.get(Branch, int(branch_id))
    if branch is None:
        raise DomainNotFoundError(
            message="Branch not found.",
            details={"branch_id": int(branch_id)},
        )
    return branch


def _get_role_or_404(db: Session, *, role_id: int) -> Role:
    role = db.get(Role, int(role_id))
    if role is None:
        raise DomainNotFoundError(
            message="Role not found.",
            details={"role_id": int(role_id)},
        )
    return role


def _get_assignable_branch_or_404(db: Session, *, branch_id: int) -> Branch:
    branch = _get_branch_or_404(db, branch_id=branch_id)
    if not bool(branch.is_active):
        raise DomainValidationError(
            message="Assigned branch is inactive.",
            details={"branch_id": int(branch.id)},
        )
    return branch


def _get_assignable_role_or_404(db: Session, *, role_id: int) -> Role:
    role = _get_role_or_404(db, role_id=role_id)
    if not bool(role.is_active):
        raise DomainValidationError(
            message="Assigned role is inactive.",
            details={"role_id": int(role.id)},
        )
    return role


def _ensure_unique_email(
    db: Session,
    *,
    email: str,
    exclude_user_id: int | None = None,
) -> None:
    stmt = select(UserAccount).where(UserAccount.email == email)
    existing = db.execute(stmt).scalar_one_or_none()

    if existing is None:
        return

    if exclude_user_id is not None and int(existing.id) == int(exclude_user_id):
        return

    raise DomainConflictError(
        message="User email already exists.",
        details={"email": email},
    )


def get_user_account_or_404(
    db: Session,
    *,
    user_id: int,
) -> UserAccount:
    stmt = (
        select(UserAccount)
        .options(
            joinedload(UserAccount.role),
            joinedload(UserAccount.branch),
        )
        .where(UserAccount.id == int(user_id))
    )

    user = db.execute(stmt).scalar_one_or_none()

    if user is None:
        raise DomainNotFoundError(
            message="User account not found.",
            details={"user_id": int(user_id)},
        )

    return user


def list_user_accounts(
    db: Session,
    *,
    include_inactive: bool = True,
    q: str | None = None,
) -> list[UserAccount]:
    stmt: Select = (
        select(UserAccount)
        .options(
            joinedload(UserAccount.role),
            joinedload(UserAccount.branch),
        )
        .order_by(UserAccount.is_active.desc(), UserAccount.full_name.asc())
    )

    if not include_inactive:
        stmt = stmt.where(UserAccount.is_active.is_(True))

    if q is not None and str(q).strip():
        pattern = f"%{str(q).strip()}%"
        stmt = stmt.where(
            or_(
                UserAccount.email.ilike(pattern),
                UserAccount.full_name.ilike(pattern),
            )
        )

    return list(db.execute(stmt).scalars().all())


def _count_active_admin_users(db: Session) -> int:
    stmt = (
        select(func.count(UserAccount.id))
        .select_from(UserAccount)
        .join(Role, UserAccount.role_id == Role.id)
        .where(
            UserAccount.is_active.is_(True),
            Role.code == ROLE_ADMIN,
        )
    )
    value = db.execute(stmt).scalar_one()
    return int(value)


def _ensure_not_removing_last_active_admin(
    db: Session,
    *,
    current_user: UserAccount,
    next_role: Role,
    next_is_active: bool,
) -> None:
    current_role_code = str(current_user.role.code).strip().upper()
    next_role_code = str(next_role.code).strip().upper()

    is_current_active_admin = bool(current_user.is_active) and current_role_code == ROLE_ADMIN
    is_next_active_admin = bool(next_is_active) and next_role_code == ROLE_ADMIN

    if not is_current_active_admin:
        return

    if is_next_active_admin:
        return

    active_admins = _count_active_admin_users(db)
    if active_admins <= 1:
        raise DomainConflictError(
            message="Cannot remove the last active ADMIN user.",
            details={"user_id": int(current_user.id)},
        )


def create_user_account(
    db: Session,
    *,
    email: str,
    full_name: str,
    branch_id: int,
    role_id: int,
    password: str,
    is_active: bool,
) -> UserAccount:
    email_norm = _normalize_email(email)
    full_name_norm = _normalize_full_name(full_name)

    if not str(password).strip():
        raise DomainValidationError(message="Password cannot be blank.")

    _ensure_unique_email(db, email=email_norm)
    branch = _get_assignable_branch_or_404(db, branch_id=branch_id)
    role = _get_assignable_role_or_404(db, role_id=role_id)

    user = UserAccount(
        email=email_norm,
        full_name=full_name_norm,
        branch_id=int(branch.id),
        role_id=int(role.id),
        password_hash=hash_password(password),
        is_active=bool(is_active),
    )

    db.add(user)
    db.commit()

    return get_user_account_or_404(db, user_id=int(user.id))


def update_user_account(
    db: Session,
    *,
    user_id: int,
    actor_user_id: int,
    email: str | None = None,
    full_name: str | None = None,
    branch_id: int | None = None,
    role_id: int | None = None,
    new_password: str | None = None,
    is_active: bool | None = None,
) -> UserAccount:
    user = get_user_account_or_404(db, user_id=user_id)

    if int(actor_user_id) == int(user.id):
        if is_active is not None and not bool(is_active):
            raise DomainConflictError(
                message="You cannot deactivate your own account from this screen.",
                details={"user_id": int(user.id)},
            )

        if role_id is not None and int(role_id) != int(user.role_id):
            raise DomainConflictError(
                message="You cannot change your own role from this screen.",
                details={"user_id": int(user.id)},
            )

    next_role = user.role
    next_is_active = bool(user.is_active)

    if role_id is not None:
        next_role = _get_assignable_role_or_404(db, role_id=role_id)

    if is_active is not None:
        next_is_active = bool(is_active)

    _ensure_not_removing_last_active_admin(
        db,
        current_user=user,
        next_role=next_role,
        next_is_active=next_is_active,
    )

    if email is not None:
        email_norm = _normalize_email(email)
        _ensure_unique_email(db, email=email_norm, exclude_user_id=int(user.id))
        user.email = email_norm

    if full_name is not None:
        user.full_name = _normalize_full_name(full_name)

    if branch_id is not None:
        branch = _get_assignable_branch_or_404(db, branch_id=branch_id)
        user.branch_id = int(branch.id)

    if role_id is not None:
        user.role_id = int(next_role.id)

    if new_password is not None:
        if not str(new_password).strip():
            raise DomainValidationError(message="New password cannot be blank.")
        user.password_hash = hash_password(new_password)

    if is_active is not None:
        user.is_active = bool(is_active)

    db.commit()
    return get_user_account_or_404(db, user_id=int(user.id))


def deactivate_user_account(
    db: Session,
    *,
    user_id: int,
    actor_user_id: int,
) -> UserAccount:
    user = get_user_account_or_404(db, user_id=user_id)

    if int(actor_user_id) == int(user.id):
        raise DomainConflictError(
            message="You cannot deactivate your own account from this screen.",
            details={"user_id": int(user.id)},
        )

    _ensure_not_removing_last_active_admin(
        db,
        current_user=user,
        next_role=user.role,
        next_is_active=False,
    )

    user.is_active = False
    db.commit()

    return get_user_account_or_404(db, user_id=int(user.id))
