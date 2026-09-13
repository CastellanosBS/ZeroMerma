"""Create disposable browser fixtures only after both canonical database guards."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)


def main(argv: Sequence[str] = ()) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revoke-reader", action="store_true")
    arguments = parser.parse_args(argv)
    config = load_destructive_test_database_config(os.environ)
    if os.environ.get("ZM_WEB_INTEGRATION_ISOLATED") != "1":
        raise RuntimeError("Browser fixtures require the isolated integration harness")
    if os.environ.get("ZM_E2E_RUN_ID") != config.run_id:
        raise RuntimeError("Browser run identity must match the authorized test database")
    password = os.environ["ZM_E2E_PASSWORD"]
    if len(password) < 24:
        raise RuntimeError("Browser credentials must be generated per run")
    os.environ["ZEROMERMA_API_ENVIRONMENT"] = "test"
    os.environ["ZEROMERMA_API_DATABASE_URL"] = config.database_url

    engine = create_engine(config.database_url)
    try:
        if arguments.revoke_reader:
            from zeromerma_api.modules.identity.infrastructure.models import Role

            with Session(engine) as session:
                assert_authorized_destructive_connection(session.connection(), config)
                role = session.scalar(select(Role).where(Role.code == "integration_reader"))
                if role is None:
                    raise RuntimeError("Isolated browser reader role is missing")
                role.is_active = False
                session.commit()
            print("Isolated browser reader grants revoked")
            return

        with engine.connect() as connection:
            assert_authorized_destructive_connection(connection, config)
            connection.rollback()
            alembic = Config(str(Path("apps/api/alembic.ini").resolve()))
            alembic.attributes["connection"] = connection
            alembic.attributes["destructive_test_database_config"] = config
            command.upgrade(alembic, "head")

        # Imports follow the guard and explicit test environment configuration.
        from zeromerma_api.bootstrap.seed_local import (
            SEED_ADMIN_EMAIL,
            SEED_BRANCH_CODE,
            SEED_DESTINATION_BRANCH_CODE,
            SEED_USER_EMAIL,
            seed_local_data,
        )
        from zeromerma_api.modules.branches.infrastructure.models import Branch
        from zeromerma_api.modules.identity.application.security import PasswordHasher
        from zeromerma_api.modules.identity.infrastructure.models import (
            Permission,
            Role,
            RolePermission,
            User,
            UserBranchAssignment,
            UserRoleAssignment,
            UserRoleAssignmentBranchScope,
        )

        with Session(engine) as session:
            assert_authorized_destructive_connection(session.connection(), config)
            seed_local_data(session)
            cashier = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
            reader = session.scalar(select(User).where(User.email == SEED_ADMIN_EMAIL))
            if cashier is None or reader is None:
                raise RuntimeError("Canonical seed did not create browser fixture users")
            cashier.email = os.environ["ZM_E2E_POS_EMAIL"]
            reader.email = os.environ["ZM_E2E_BACKOFFICE_EMAIL"]
            cashier.password_hash = PasswordHasher().hash_password(password)
            reader.password_hash = PasswordHasher().hash_password(password)
            reader.full_name = "Integration Backoffice Reader"
            branch = session.scalar(select(Branch).where(Branch.code == SEED_BRANCH_CODE))
            other_branch = session.scalar(
                select(Branch).where(Branch.code == SEED_DESTINATION_BRANCH_CODE)
            )
            if branch is None or other_branch is None:
                raise RuntimeError("Canonical seed did not create both fixture branches")
            session.execute(
                delete(UserRoleAssignment).where(UserRoleAssignment.user_id == reader.id)
            )
            for assignment in session.scalars(
                select(UserBranchAssignment).where(UserBranchAssignment.user_id == reader.id)
            ):
                assignment.is_active = assignment.branch_id == branch.id
            if (
                session.scalar(
                    select(UserBranchAssignment).where(
                        UserBranchAssignment.user_id == reader.id,
                        UserBranchAssignment.branch_id == branch.id,
                    )
                )
                is None
            ):
                session.add(
                    UserBranchAssignment(user_id=reader.id, branch_id=branch.id, is_default=True)
                )
            reader_role = Role(
                code="integration_reader",
                name="Integration reader",
                surfaces=["BACKOFFICE"],
                is_active=True,
            )
            session.add(reader_role)
            session.flush()
            capabilities = {
                "catalog.view",
                "sales_tickets.view",
                "branches.view",
                "suppliers.view",
                "cash_finance.view",
                "quality_hygiene.view",
                "audit.view",
            }
            permissions = list(
                session.scalars(select(Permission).where(Permission.code.in_(capabilities)))
            )
            if {permission.code for permission in permissions} != capabilities:
                raise RuntimeError("Canonical reader capabilities were not seeded")
            for permission in permissions:
                session.add(RolePermission(role_id=reader_role.id, permission_id=permission.id))
            assignment = UserRoleAssignment(
                user_id=reader.id, role_id=reader_role.id, scope_type="BRANCH_SET"
            )
            session.add(assignment)
            session.flush()
            session.add(
                UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=branch.id)
            )
            session.add(
                User(
                    email=f"denied-{config.run_id}@example.invalid",
                    full_name="Integration denied account",
                    password_hash=PasswordHasher().hash_password(password),
                    allowed_surfaces=["BACKOFFICE"],
                    default_surface="BACKOFFICE",
                )
            )
            session.commit()
            artifact = Path(os.environ["ZM_E2E_ARTIFACT_DIR"]) / "fixture-scope.json"
            artifact.write_text(
                json.dumps(
                    {
                        "allowed_branch_id": str(branch.id),
                        "other_branch_id": str(other_branch.id),
                    }
                ),
                encoding="utf-8",
            )
        print(f"Browser fixtures ready for isolated run {config.run_id}; credentials redacted")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main(sys.argv[1:])
