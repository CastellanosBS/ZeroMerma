"""Create disposable browser fixtures only after both canonical database guards."""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from zeromerma_api.testing.database_safety import (
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)


def main() -> None:
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
            SEED_USER_EMAIL,
            seed_local_data,
        )
        from zeromerma_api.modules.identity.application.security import PasswordHasher
        from zeromerma_api.modules.identity.infrastructure.models import (
            User,
            UserRoleAssignment,
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
            session.execute(
                delete(UserRoleAssignment).where(UserRoleAssignment.user_id == reader.id)
            )
            # Surface access characterizes the current baseline. It is not a claim
            # that capability enforcement (ZM-FIN-015 onward) is implemented.
            session.commit()
        print(f"Browser fixtures ready for isolated run {config.run_id}; credentials redacted")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
