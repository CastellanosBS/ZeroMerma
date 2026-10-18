"""HTTP boundary regressions for independent browser audiences and the bearer cutover."""

from http.cookies import SimpleCookie

import pytest
from fastapi.testclient import TestClient

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_ADMIN_PASSWORD,
    SEED_USER_EMAIL,
    SEED_USER_PASSWORD,
    SEED_WORKSTATION_CODE,
)
from zeromerma_api.testing.sessions import login_headers, surface_origin


def test_login_issues_only_host_scoped_secure_http_only_cookie(client: TestClient) -> None:
    response = client.post(
        "/v1/auth/login",
        headers={"Origin": surface_origin("POS"), "X-ZeroMerma-Surface": "POS"},
        json={
            "email": SEED_USER_EMAIL,
            "password": SEED_USER_PASSWORD,
            "audience": "POS",
            "workstation_code": SEED_WORKSTATION_CODE,
        },
    )
    assert response.status_code == 200
    assert set(response.json()) == {"session", "user", "csrf_token"}
    assert response.headers["cache-control"] == "no-store"
    cookies = SimpleCookie()
    cookies.load(response.headers["set-cookie"])
    cookie = cookies["__Host-zm-pos-session"]
    assert bool(cookie["secure"])
    assert bool(cookie["httponly"])
    assert cookie["path"] == "/"
    assert cookie["domain"] == ""
    assert cookie["samesite"].lower() == "lax"
    assert 0 < int(cookie["max-age"]) <= 12 * 60 * 60


def test_coexisting_cookies_do_not_authorize_cross_surface_requests(client: TestClient) -> None:
    pos = login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    backoffice = login_headers(
        client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD, audience="BACKOFFICE"
    )
    combined_cookie = pos["Cookie"] + "; " + backoffice["Cookie"]
    pos = {**pos, "Cookie": combined_cookie}
    backoffice = {**backoffice, "Cookie": combined_cookie}
    assert client.get("/v1/auth/me", headers=pos).json()["email"] == SEED_USER_EMAIL
    assert client.get("/v1/auth/me", headers=backoffice).json()["email"] == SEED_ADMIN_EMAIL
    assert client.get("/v1/admin/products", headers=pos).status_code == 403
    assert client.get("/v1/auth/me?surface=BACKOFFICE", headers=pos).status_code == 403
    assert (
        client.get(
            "/v1/auth/session", headers={**backoffice, "Origin": surface_origin("POS")}
        ).status_code
        == 403
    )
    assert client.get("/v1/auth/session", headers={"Cookie": combined_cookie}).status_code == 401


@pytest.mark.parametrize("transport", ["bearer", "query", "wrong_csrf", "missing_csrf"])
def test_obsolete_or_forged_credentials_cannot_mutate_session(
    client: TestClient, transport: str
) -> None:
    headers = login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    invalid = dict(headers)
    path = "/v1/auth/lock"
    expected = 403
    if transport == "bearer":
        invalid["Authorization"] = "Bearer obsolete-token-must-not-be-accepted"
        expected = 401
    elif transport == "query":
        path += "?access_token=obsolete-token-must-not-be-accepted"
        expected = 401
    elif transport == "wrong_csrf":
        invalid["X-CSRF-Token"] = "invalid-csrf"
    else:
        invalid.pop("X-CSRF-Token")
    response = client.post(path, headers=invalid)
    assert response.status_code == expected
    assert client.get("/v1/auth/session", headers=headers).json()["session"]["status"] == "ACTIVE"


def test_logout_is_durable_and_does_not_log_out_other_audience(client: TestClient) -> None:
    pos = login_headers(client, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
    backoffice = login_headers(
        client, email=SEED_ADMIN_EMAIL, password=SEED_ADMIN_PASSWORD, audience="BACKOFFICE"
    )
    assert client.post("/v1/auth/logout", headers=pos).status_code == 204
    assert client.get("/v1/auth/me", headers=pos).status_code == 401
    assert client.get("/v1/auth/me", headers=backoffice).status_code == 200
