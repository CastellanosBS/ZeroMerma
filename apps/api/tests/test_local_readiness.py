from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from zeromerma_api.main import create_app
from zeromerma_api.presentation.health import readiness_session


def test_readiness_uses_real_postgresql_without_creating_business_data(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "READY"


@pytest.mark.parametrize(
    ("recovery", "read_only", "expected_status"),
    [(False, "off", 200), (True, "off", 503), (False, "on", 503)],
)
def test_readiness_requires_writable_local_database(
    recovery: bool, read_only: str, expected_status: int
) -> None:
    session = Mock(spec=Session)
    session.execute.return_value.one.return_value = (recovery, read_only)
    app = create_app()
    app.dependency_overrides[readiness_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == expected_status
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": "READY" if expected_status == 200 else "UNAVAILABLE",
        "database": "READY" if expected_status == 200 else "UNAVAILABLE",
        "internet": "UNKNOWN",
        "transactional_mode": "LOCAL_FIRST",
        "browser_offline_mutations": False,
    }
    session.commit.assert_not_called()
    assert session.execute.call_count == 1


def test_readiness_hides_database_error_and_keeps_liveness_separate() -> None:
    session = Mock(spec=Session)
    session.execute.side_effect = OperationalError(
        "sensitive statement", {}, RuntimeError("private database credentials")
    )
    app = create_app()
    app.dependency_overrides[readiness_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/ready")
        liveness = client.get("/health")
    assert response.status_code == 503
    assert "private" not in response.text
    assert "sensitive" not in response.text
    assert liveness.status_code == 200
    assert response.json()["database"] == "UNAVAILABLE"
    session.commit.assert_not_called()
