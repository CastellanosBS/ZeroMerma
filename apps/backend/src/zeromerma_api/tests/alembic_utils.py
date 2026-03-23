# apps/backend/src/zeromerma_api/tests/alembic_utils.py
from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def make_alembic_config() -> Config:
    """
    Build a canonical Alembic Config for tests.

    Guarantees:
    - Always points to the backend's alembic.ini
    - Always points to the backend's migrations folder
    - Explicitly injects DATABASE_URL when present, so tests and local commands
      operate against the same configured database target
    """
    backend_root = Path(__file__).resolve().parents[3]  # tests/ -> src/zeromerma_api/ -> backend/
    ini_path = backend_root / "alembic.ini"
    migrations_path = backend_root / "migrations"

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(migrations_path))

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)

    return cfg


def alembic_upgrade_head() -> None:
    """
    Upgrade the configured database to the latest real Alembic head.
    """
    command.upgrade(make_alembic_config(), "head")


def alembic_downgrade_base() -> None:
    """
    Downgrade the configured database to base.
    Useful for rare debugging cases; not used by default in all tests.
    """
    command.downgrade(make_alembic_config(), "base")


def alembic_stamp_head() -> None:
    """
    Stamp the configured database to the current real head revision.
    Use only when the schema is already aligned and you need to recover
    Alembic state without re-running migrations.
    """
    command.stamp(make_alembic_config(), "head")
