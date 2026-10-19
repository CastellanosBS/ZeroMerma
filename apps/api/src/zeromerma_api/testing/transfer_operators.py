"""Explicit second cashier fixture for transfer tests on disposable PostgreSQL."""

from __future__ import annotations

import os

from sqlalchemy import select

from zeromerma_api.bootstrap.seed_local import SEED_USER_EMAIL, SEED_WORKSTATION_CODE
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.identity.infrastructure.models import (
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)

DESTINATION_CASHIER_EMAIL = "destination-cashier@zeromerma.local"


def transfer_cashier_email(workstation_code: str) -> str:
    if workstation_code == SEED_WORKSTATION_CODE:
        return SEED_USER_EMAIL
    config = load_destructive_test_database_config(os.environ)
    with SessionLocal() as session:
        assert_authorized_destructive_connection(session.connection(), config)
        existing = session.scalar(select(User).where(User.email == DESTINATION_CASHIER_EMAIL))
        if existing is not None:
            return existing.email
        source = session.scalars(select(User).where(User.email == SEED_USER_EMAIL)).one()
        target = User(
            email=DESTINATION_CASHIER_EMAIL,
            full_name="Destination Branch Cashier",
            password_hash=source.password_hash,
            allowed_surfaces=list(source.allowed_surfaces),
            default_surface=source.default_surface,
        )
        session.add(target)
        session.flush()
        for membership in session.scalars(
            select(UserBranchAssignment).where(UserBranchAssignment.user_id == source.id)
        ).all():
            session.add(
                UserBranchAssignment(
                    user_id=target.id,
                    branch_id=membership.branch_id,
                    is_active=membership.is_active,
                    is_default=membership.is_default,
                )
            )
        for assignment in session.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id == source.id)
        ).all():
            copy = UserRoleAssignment(
                user_id=target.id,
                role_id=assignment.role_id,
                scope_type=assignment.scope_type,
                is_active=assignment.is_active,
            )
            session.add(copy)
            session.flush()
            for branch_id in session.scalars(
                select(UserRoleAssignmentBranchScope.branch_id).where(
                    UserRoleAssignmentBranchScope.assignment_id == assignment.id
                )
            ).all():
                session.add(
                    UserRoleAssignmentBranchScope(assignment_id=copy.id, branch_id=branch_id)
                )
        session.commit()
    return DESTINATION_CASHIER_EMAIL
