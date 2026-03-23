# apps/backend/src/zeromerma_api/tests/conftest.py
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

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
