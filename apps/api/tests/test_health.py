from fastapi.testclient import TestClient

from zeromerma_api.main import create_app


def test_health_endpoint_returns_foundation_metadata() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "zeromerma-api"
