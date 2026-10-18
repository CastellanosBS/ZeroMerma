"""Exercise the first authenticated scoped request in a fresh application interpreter."""

from __future__ import annotations

import subprocess
import sys
from textwrap import dedent


def test_cold_api_login_and_first_scoped_cash_query_do_not_change_event_listeners() -> None:
    # A separate interpreter prevents executor imports from other tests masking startup defects.
    script = dedent(
        """
        import os

        from zeromerma_api.testing.database_safety import load_destructive_test_database_config

        load_destructive_test_database_config(os.environ)

        from fastapi.testclient import TestClient
        from zeromerma_api.bootstrap.seed_local import (
            SEED_USER_EMAIL, SEED_USER_PASSWORD, SEED_WORKSTATION_CODE,
        )
        from zeromerma_api.main import create_app

        headers = {"Origin": "http://localhost:5173", "X-ZeroMerma-Surface": "POS"}
        with TestClient(create_app(), base_url="https://testserver") as client:
            login = client.post(
                "/v1/auth/login",
                headers=headers,
                json={
                    "email": SEED_USER_EMAIL,
                    "password": SEED_USER_PASSWORD,
                    "audience": "POS",
                    "workstation_code": SEED_WORKSTATION_CODE,
                },
            )
            assert login.status_code == 200, f"Login status: {login.status_code}"
            current = client.get(
                "/v1/cash-sessions/current",
                params={"workstation_code": SEED_WORKSTATION_CODE},
                headers=headers,
            )
            assert current.status_code == 200, f"Current cash status: {current.status_code}"
            assert current.json() is None
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
