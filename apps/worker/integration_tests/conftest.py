from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from zeromerma_api.testing.database_safety import (
    DestructiveTestDatabaseConfig,
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def worker_test_database_config() -> DestructiveTestDatabaseConfig:
    return load_destructive_test_database_config(os.environ)


@pytest.fixture(scope="session")
def migrated_worker_test_engine(
    worker_test_database_config: DestructiveTestDatabaseConfig,
) -> Iterator[Engine]:
    engine = create_engine(worker_test_database_config.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            assert_authorized_destructive_connection(connection, worker_test_database_config)
            connection.commit()
            config = Config(str(REPO_ROOT / "apps" / "api" / "alembic.ini"))
            config.attributes["connection"] = connection
            config.attributes["destructive_test_database_config"] = worker_test_database_config
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def worker_test_engine(
    migrated_worker_test_engine: Engine,
    worker_test_database_config: DestructiveTestDatabaseConfig,
) -> Iterator[Engine]:
    with migrated_worker_test_engine.begin() as connection:
        assert_authorized_destructive_connection(connection, worker_test_database_config)
        connection.execute(text("DELETE FROM outbox_events"))
    yield migrated_worker_test_engine
    with migrated_worker_test_engine.begin() as connection:
        assert_authorized_destructive_connection(connection, worker_test_database_config)
        connection.execute(text("DELETE FROM outbox_events"))
