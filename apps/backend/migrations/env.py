from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

# --- Import your project's metadata (SQLAlchemy Declarative Base) ---
# Adjust the import path to YOUR package name under src/
from zeromerma_api.models.base import Base  # <-- this must exist

# --- Make sure Python can import your package from the src/ layout ---
# env.py is .../backend/migrations/env.py
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # .../backend
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


# If you already have a typed settings object, you could import it here.
# For now we read DATABASE_URL from env with a safe default:
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://zeromerma:zeromerma@localhost:5432/zeromerma",
)

# This provides access to values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Tell Alembic what to diff against ---
target_metadata = Base.metadata  # the single source of truth for your tables

# --- Override sqlalchemy.url dynamically (don’t hardcode in alembic.ini) ---
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    url = config.get_main_option(
        "sqlalchemy.url"
    )  # DSN set earlier via set_main_option

    # Guard clause: narrow Optional[str] -> str for Pylance and fail fast if missing
    if not url:
        raise RuntimeError(
            "sqlalchemy.url is not set. Check DATABASE_URL or the call to "
            "config.set_main_option('sqlalchemy.url', DATABASE_URL)."
        )

    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
