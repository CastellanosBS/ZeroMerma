from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from zeromerma_api.main import create_app

# Build a TestClient once per module to keep test fast and isolated.
client = TestClient(create_app())


def test_healthz_ok():
    """
    Liveness: service process & routing work, independent of database.
    Expected HTTP 200 and required in the JSON payload.
    """

    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()

    # shape contract
    assert data["status"] == "ok"
    assert "app" in data
    assert "env" in data
    assert "version" in data


def test_version_ok():
    """
    Version endpoint: always available, does not touch the DB.
    """
    r = client.get("/version")
    assert r.status_code == 200
    data = r.json()
    assert "version" in data
    assert isinstance(data["version"], str)


def test_readyz_ok_or_skip():
    """
    Readiness: requires a reachable PostgreSQL URL.
    If DATABASE_URL isn't set in the environment, we skip rather than fail,
    so local dev without DB is still green; CI will set it.
    """
    if not os.getenv("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; skipping /readyz test")

    r = client.get("/readyz")
    assert r.status_code == 200

    payload = r.json()
    assert isinstance(payload, dict)

    # Contract invariant:
    assert payload.get("status") == "ready"

    # Optional (non-fragile) checks:
    # If these keys exist, ensure types look correct.
    if "app" in payload:
        assert isinstance(payload["app"], str)
    if "env" in payload:
        assert isinstance(payload["env"], str)
