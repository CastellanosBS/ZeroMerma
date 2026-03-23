# apps/backend/tests/test_seed_idempotent.py
# PURPOSE: Prove seeds are idempotent by running them twice and asserting counts do not increase.

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.models import Branch, Role, UserAccount
from zeromerma_api.scripts.seed import run_all


def make_alembic_config() -> Config:
    backend_dir = Path(__file__).resolve().parents[1]  # apps/backend
    alembic_ini = backend_dir / "alembic.ini"
    migrations_dir = backend_dir / "migrations"

    cfg = Config(str(alembic_ini))
    cfg.set_main_option("script_location", str(migrations_dir))
    return cfg


def _alembic_upgrade_head() -> None:
    # __file__ = .../apps/backend/src/zeromerma_api/tests/test_xxx.py
    # parents[0]=tests, [1]=zeromerma_api, [2]=src, [3]=backend
    backend_dir = Path(__file__).resolve().parents[3]

    cfg = Config(str(backend_dir / "alembic.ini"))

    # IMPORTANT: point to the real migrations folder
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))

    # Make sure we use the DB from env var (the tests skip otherwise)
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])

    command.upgrade(cfg, "head")


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
    _alembic_upgrade_head()

    # First run
    s1: Session = SessionLocal()
    try:
        run_all(s1)
        s1.commit()
    finally:
        s1.close()

    # Second run (must be idempotent)
    s2: Session = SessionLocal()
    try:
        run_all(s2)
        s2.commit()
    finally:
        s2.close()

    # Verify stable counts
    s3: Session = SessionLocal()
    try:
        num_roles = (
            s3.scalar(
                select(func.count())
                .select_from(Role)
                .where(Role.code.in_(["ADMIN", "CASHIER", "BAKER"]))
            )
            or 0
        )
        num_branches = (
            s3.scalar(select(func.count()).select_from(Branch).where(Branch.code == "MAIN")) or 0
        )
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

    assert int(num_roles) == 3
    assert int(num_branches) == 1
    assert int(num_admins) == 1
