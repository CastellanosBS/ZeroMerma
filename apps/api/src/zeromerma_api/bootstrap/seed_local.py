from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.branches.infrastructure.models import Branch, Workstation
from zeromerma_api.modules.identity.application.security import PasswordHasher
from zeromerma_api.modules.identity.infrastructure.models import User, UserBranchAssignment

SEED_BRANCH_CODE = "MAIN"
SEED_BRANCH_NAME = "Main Branch"
SEED_BRANCH_TIMEZONE = "America/Hermosillo"

SEED_WORKSTATION_CODE = "POS-01"
SEED_WORKSTATION_NAME = "Front Register 01"

SEED_USER_EMAIL = "cashier@zeromerma.local"
SEED_USER_FULL_NAME = "Main Branch Cashier"
SEED_USER_PASSWORD = "ChangeMe123!"


def _upsert_branch(session: Session) -> Branch:
    branch = session.execute(
        select(Branch).where(Branch.code == SEED_BRANCH_CODE)
    ).scalar_one_or_none()
    if branch is None:
        branch = Branch(
            code=SEED_BRANCH_CODE,
            name=SEED_BRANCH_NAME,
            timezone=SEED_BRANCH_TIMEZONE,
            is_active=True,
        )
        session.add(branch)
        session.flush()
        return branch

    branch.name = SEED_BRANCH_NAME
    branch.timezone = SEED_BRANCH_TIMEZONE
    branch.is_active = True
    session.flush()
    return branch


def _upsert_workstation(session: Session, *, branch_id: uuid.UUID) -> Workstation:
    workstation = session.execute(
        select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
    ).scalar_one_or_none()
    if workstation is None:
        workstation = Workstation(
            branch_id=branch_id,
            code=SEED_WORKSTATION_CODE,
            name=SEED_WORKSTATION_NAME,
            is_active=True,
        )
        session.add(workstation)
        session.flush()
        return workstation

    workstation.branch_id = branch_id
    workstation.name = SEED_WORKSTATION_NAME
    workstation.is_active = True
    session.flush()
    return workstation


def _upsert_user(session: Session, *, password_hasher: PasswordHasher) -> User:
    user = session.execute(select(User).where(User.email == SEED_USER_EMAIL)).scalar_one_or_none()
    password_hash = password_hasher.hash_password(SEED_USER_PASSWORD)

    if user is None:
        user = User(
            email=SEED_USER_EMAIL,
            full_name=SEED_USER_FULL_NAME,
            password_hash=password_hash,
            is_active=True,
        )
        session.add(user)
        session.flush()
        return user

    user.full_name = SEED_USER_FULL_NAME
    user.password_hash = password_hash
    user.is_active = True
    session.flush()
    return user


def _upsert_assignment(
    session: Session,
    *,
    user_id: uuid.UUID,
    branch_id: uuid.UUID,
) -> UserBranchAssignment:
    assignment = session.execute(
        select(UserBranchAssignment).where(
            UserBranchAssignment.user_id == user_id,
            UserBranchAssignment.branch_id == branch_id,
        )
    ).scalar_one_or_none()
    if assignment is None:
        assignment = UserBranchAssignment(
            user_id=user_id,
            branch_id=branch_id,
            is_active=True,
        )
        session.add(assignment)
        session.flush()
        return assignment

    assignment.is_active = True
    session.flush()
    return assignment


def seed_local_data(session: Session) -> None:
    password_hasher = PasswordHasher()

    branch = _upsert_branch(session)
    _upsert_workstation(session, branch_id=branch.id)
    user = _upsert_user(session, password_hasher=password_hasher)
    _upsert_assignment(session, user_id=user.id, branch_id=branch.id)


def main() -> int:
    with SessionLocal() as session:
        seed_local_data(session)
        session.commit()

    print(f"Seeded branch {SEED_BRANCH_CODE} and workstation {SEED_WORKSTATION_CODE}.")
    print(f"Seeded cashier {SEED_USER_EMAIL} with password {SEED_USER_PASSWORD}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
