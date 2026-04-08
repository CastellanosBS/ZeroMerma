from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from zeromerma_api.bootstrap.seed_local import seed_local_data
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[3]
TRUNCATE_SQL = """
TRUNCATE TABLE
  cash_sessions,
  user_branch_assignments,
  workstations,
  branches,
  users,
  audit_log,
  outbox_events
RESTART IDENTITY CASCADE
"""


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    alembic_config = Config(str(REPO_ROOT / "apps" / "api" / "alembic.ini"))
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session", autouse=True)
def restore_seeded_database_state() -> Iterator[None]:
    yield

    with SessionLocal() as session:
        session.execute(text(TRUNCATE_SQL))
        session.commit()
        seed_local_data(session)
        session.commit()


@pytest.fixture(autouse=True)
def seeded_database() -> Iterator[None]:
    with SessionLocal() as session:
        session.execute(text(TRUNCATE_SQL))
        session.commit()
        seed_local_data(session)
        session.commit()

    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
