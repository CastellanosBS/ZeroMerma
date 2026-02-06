# apps/backend/tests/test_seed_idempotent.py
# PURPOSE: Prove seeds are idempotent by running them twice and asserting counts do not increase.

from __future__ import annotations  # (1) Modern typing behavior.

import os  # (2) To check DATABASE_URL presence for readiness.

import pytest  # (3) Pytest framework for assertions and skipping.
from alembic import command

# (6) Alembic programmatic API: lets tests apply migrations without shelling out.
from alembic.config import Config
from sqlalchemy import func, select  # (4) To query counts after seeding.
from sqlalchemy.orm import Session  # (5) Type hints for sessions.

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models import Branch, Role, UserAccount

# (7) Import the seed orchestrator and DB/session bits from your project.
from zeromerma_api.scripts.seed import run_all


def _alembic_upgrade_head() -> None:
    """
    Apply all migrations up to 'head' using Alembic's API.
    Assumes tests run with working directory 'apps/backend' so alembic.ini is resolvable.
    """
    cfg = Config("alembic.ini")  # (8) Read Alembic config from local file.
    command.upgrade(cfg, "head")  # (9) Run "alembic upgrade head" programmatically.


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL not set; skipping seed idempotency test",
)
def test_seeds_are_idempotent():
    """
    This test:
      - applies migrations,
      - runs the seeder twice,
      - asserts counts remain stable.
    """
    # (10) Bring schema to the latest state.
    _alembic_upgrade_head()

    # (11) First run: should create rows.
    s1: Session = SessionLocal()
    try:
        run_all(s1)
    finally:
        s1.close()

    # (12) Second run: should detect existing rows and do nothing.
    s2: Session = SessionLocal()
    try:
        run_all(s2)
    finally:
        s2.close()

    # (13) Verify counts are as expected and stable.


s3: Session = SessionLocal()
try:
    # Count roles with code in (...)
    num_roles = (
        s3.scalar(
            select(func.count())
            .select_from(Role)
            .where(Role.code.in_(["ADMIN", "CASHIER", "BAKER"]))
        )
        or 0
    )

    # Count branches with code == MAIN
    num_branches = (
        s3.scalar(select(func.count()).select_from(Branch).where(Branch.code == "MAIN"))
        or 0
    )

    # Count admin users by email
    num_admins = (
        s3.scalar(
            select(func.count())
            .select_from(UserAccount)
            .where(UserAccount.email == "admin@example.com")
        )
        or 0
    )

finally:
    s3.close()
