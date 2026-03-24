# apps/backend/src/zeromerma_api/tests/conftest.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Generator

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from zeromerma_api.db.engine import SessionLocal
from zeromerma_api.main import create_app
from zeromerma_api.tests.alembic_utils import alembic_upgrade_head

# Load environment variables once for the whole test session.
# Priority is the backend-local .env file if present.
BACKEND_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = BACKEND_ROOT / ".env"

load_dotenv(dotenv_path=ENV_FILE if ENV_FILE.exists() else None)


@pytest.fixture(scope="session")
def database_url() -> str:
    """
    Canonical DATABASE_URL fixture for tests.

    We keep it explicit so every DB-related helper can rely on the same source.
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set; DB-backed tests are skipped")
    return url


@pytest.fixture(scope="session")
def app(database_url: str) -> FastAPI:
    """
    Session-scoped FastAPI app fixture.

    The database_url fixture is included deliberately so DB-backed test runs
    skip cleanly when DATABASE_URL is missing.
    """
    _ = database_url
    return create_app()


@pytest.fixture()
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """
    Function-scoped TestClient fixture.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(database_url: str) -> Generator[Session, None, None]:
    """
    Function-scoped SQLAlchemy session fixture.

    Policy:
    - Alembic is upgraded to head before yielding the session.
    - The fixture does not automatically reset data; each test or helper
      remains responsible for explicit reset/seed semantics.
    """
    _ = database_url
    alembic_upgrade_head()

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
