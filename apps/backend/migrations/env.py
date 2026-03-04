# apps/backend/migrations/env.py

from __future__ import annotations  # allow postponed annotations; safe and modern

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import (  # Alembic uses these to create an Engine
    engine_from_config,
    pool,
)

# ------------- NEW: import your Base to expose metadata to Alembic -------------
# We import the project's Declarative Base, which aggregates all table metadata.
# Alembic uses this 'target_metadata' to understand tables/columns when autogenerating,
# and it's also a good sanity anchor for migrations.
from zeromerma_api.models.base import Base

# ------------- Optional: load DB URL from your app settings for single source of truth -------------
# If your alembic.ini has sqlalchemy.url unset, we set it at runtime from your app's settings.
# This keeps local/CI configs consistent.
try:
    from zeromerma_api.core.settings import get_settings

    _S = get_settings()
    _APP_DATABASE_URL = (
        _S.database_url
    )  # e.g., "postgresql+psycopg://user:pass@host:5432/dbname"
except Exception:
    # Fallback to env or alembic.ini if settings import fails (e.g., in bare CI bootstrap).
    _APP_DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("database_url")

# this is the Alembic Config object, which provides access to the .ini file values.
config = context.config

# If we have an app-provided URL, push it into Alembic's config so 'engine_from_config' uses it.
if _APP_DATABASE_URL:
    config.set_main_option("sqlalchemy.url", _APP_DATABASE_URL)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ------------- This is the single most important line for Alembic to "see" your models -------------
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection)."""
    url = config.get_main_option(
        "sqlalchemy.url"
    )  # Alembic pulls the URL we set above or from alembic.ini
    context.configure(
        url=url,
        target_metadata=target_metadata,  # <-- so autogenerate knows your models
        literal_binds=True,  # render values inline in SQL (useful for offline)
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()  # emits SQL to stdout or file (no DB execution)


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""

    # 1) Obtener la sección [alembic] del alembic.ini
    #    Si no existe, usamos {} para evitar None.
    section = config.get_section(config.config_ini_section) or {}

    # 2) Crear engine a partir de esa configuración
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
