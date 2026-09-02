from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from zeromerma_api.testing.database_safety import (
    CONFIRMATION_PREFIX,
    TEST_CONFIRMATION_VARIABLE,
    TEST_DATABASE_URL_VARIABLE,
    TEST_ENVIRONMENT_VARIABLE,
    TEST_RUN_ID_VARIABLE,
    DestructiveTestDatabaseSafetyError,
    assert_authorized_destructive_connection,
    load_destructive_test_database_config,
    run_after_preconnect_guard,
)

LOCAL_RUN_ID = "a" * 32
TEST_PASSWORD = "unit-only-password"


def _valid_environment(
    *,
    host: str = "127.0.0.1",
    run_id: str = LOCAL_RUN_ID,
) -> dict[str, str]:
    database = f"zeromerma_test_{run_id}"
    rendered_host = f"[{host}]" if ":" in host else host
    return {
        TEST_ENVIRONMENT_VARIABLE: "test",
        TEST_DATABASE_URL_VARIABLE: (
            f"postgresql+psycopg://zeromerma_test_runner:{TEST_PASSWORD}"
            f"@{rendered_host}:55432/{database}?application_name={database}"
        ),
        TEST_RUN_ID_VARIABLE: run_id,
        TEST_CONFIRMATION_VARIABLE: f"{CONFIRMATION_PREFIX}{run_id}",
    }


@dataclass
class DownstreamCalls:
    engine_created: int = 0
    connect_called: int = 0
    alembic_called: int = 0
    truncate_called: int = 0
    seed_called: int = 0


def _record_all_downstream_calls(calls: DownstreamCalls) -> Callable[[object], None]:
    def operation(_: object) -> None:
        calls.engine_created += 1
        calls.connect_called += 1
        calls.alembic_called += 1
        calls.truncate_called += 1
        calls.seed_called += 1

    return operation


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_preconnect_allows_explicit_loopback_ephemeral_database(host: str) -> None:
    config = load_destructive_test_database_config(_valid_environment(host=host))

    assert config.host == host
    assert config.database == f"zeromerma_test_{LOCAL_RUN_ID}"
    assert config.user == "zeromerma_test_runner"
    assert TEST_PASSWORD not in config.redacted_summary()


def test_preconnect_allows_ci_style_unique_run_identity() -> None:
    run_id = "gha_12345678_1"
    config = load_destructive_test_database_config(_valid_environment(run_id=run_id))

    assert config.run_id == run_id
    assert config.database.endswith(run_id)


def _deny_cases() -> list[tuple[str, dict[str, str]]]:
    base = _valid_environment()
    cases: list[tuple[str, dict[str, str]]] = []

    def changed(**values: str) -> dict[str, str]:
        candidate = dict(base)
        candidate.update(values)
        return candidate

    missing_environment = dict(base)
    missing_environment.pop(TEST_ENVIRONMENT_VARIABLE)
    cases.append(("missing environment", missing_environment))
    cases.append(("wrong environment", changed(**{TEST_ENVIRONMENT_VARIABLE: "local"})))

    missing_url = dict(base)
    missing_url.pop(TEST_DATABASE_URL_VARIABLE)
    missing_url["ZEROMERMA_API_DATABASE_URL"] = (
        "postgresql+psycopg://operational-user:never-log-this@localhost:5432/zeromerma"
    )
    cases.append(("application URL fallback", missing_url))

    cases.append(
        (
            "non PostgreSQL scheme",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: (
                        f"mysql://zeromerma_test_runner:{TEST_PASSWORD}@127.0.0.1:55432/"
                        f"zeromerma_test_{LOCAL_RUN_ID}?application_name=zeromerma_test_{LOCAL_RUN_ID}"
                    )
                }
            ),
        )
    )
    cases.append(
        (
            "remote host",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        "127.0.0.1", "db.example.invalid"
                    )
                }
            ),
        )
    )
    cases.append(
        (
            "normal database",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        f"zeromerma_test_{LOCAL_RUN_ID}", "zeromerma"
                    )
                }
            ),
        )
    )
    cases.append(
        (
            "misleading database",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        f"/zeromerma_test_{LOCAL_RUN_ID}", f"/copy_test_{LOCAL_RUN_ID}"
                    )
                }
            ),
        )
    )

    missing_run_id = dict(base)
    missing_run_id.pop(TEST_RUN_ID_VARIABLE)
    cases.append(("missing run id", missing_run_id))
    cases.append(("invalid run id", changed(**{TEST_RUN_ID_VARIABLE: "BAD-RUN"})))
    cases.append(
        (
            "database run id mismatch",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        f"/zeromerma_test_{LOCAL_RUN_ID}", f"/zeromerma_test_{'b' * 32}"
                    )
                }
            ),
        )
    )

    missing_confirmation = dict(base)
    missing_confirmation.pop(TEST_CONFIRMATION_VARIABLE)
    cases.append(("missing confirmation", missing_confirmation))
    cases.append(
        (
            "confirmation mismatch",
            changed(**{TEST_CONFIRMATION_VARIABLE: f"{CONFIRMATION_PREFIX}{'b' * 32}"}),
        )
    )
    cases.append(
        (
            "wrong user",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        "zeromerma_test_runner", "zeromerma"
                    )
                }
            ),
        )
    )
    cases.append(
        (
            "unexpected URL parameter",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: (
                        f"{base[TEST_DATABASE_URL_VARIABLE]}&sslmode=require"
                    )
                }
            ),
        )
    )
    cases.append(("malformed URL", changed(**{TEST_DATABASE_URL_VARIABLE: "not a URL"})))
    cases.append(
        (
            "missing dedicated password",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        f":{TEST_PASSWORD}@", "@"
                    )
                }
            ),
        )
    )
    cases.append(
        (
            "missing explicit port",
            changed(
                **{
                    TEST_DATABASE_URL_VARIABLE: base[TEST_DATABASE_URL_VARIABLE].replace(
                        ":55432/", "/"
                    )
                }
            ),
        )
    )
    return cases


@pytest.mark.parametrize(("case_name", "environment"), _deny_cases())
def test_denied_preconnect_configuration_calls_no_downstream_operation(
    case_name: str,
    environment: dict[str, str],
) -> None:
    calls = DownstreamCalls()

    with pytest.raises(DestructiveTestDatabaseSafetyError) as error:
        run_after_preconnect_guard(environment, _record_all_downstream_calls(calls))

    assert case_name
    assert calls == DownstreamCalls()
    assert TEST_PASSWORD not in str(error.value)
    assert "never-log-this" not in str(error.value)
    assert "postgresql" not in str(error.value)


def test_preconnect_calls_engine_phase_once_after_valid_authorization() -> None:
    calls = DownstreamCalls()

    run_after_preconnect_guard(_valid_environment(), _record_all_downstream_calls(calls))

    assert calls == DownstreamCalls(1, 1, 1, 1, 1)


class FakeResult:
    def __init__(self, identity: dict[str, str]) -> None:
        self.identity = identity

    def mappings(self) -> FakeResult:
        return self

    def one(self) -> dict[str, str]:
        return self.identity


class FakeConnection:
    def __init__(self, identity: dict[str, str]) -> None:
        self.identity = identity
        self.execute_calls = 0

    def execute(self, _: object) -> FakeResult:
        self.execute_calls += 1
        return FakeResult(self.identity)


def _connected_identity() -> dict[str, str]:
    database = f"zeromerma_test_{LOCAL_RUN_ID}"
    return {
        "database_name": database,
        "database_user": "zeromerma_test_runner",
        "application_name": database,
        "server_version_num": "160013",
    }


def test_postconnect_allows_exact_ephemeral_identity() -> None:
    config = load_destructive_test_database_config(_valid_environment())
    connection = FakeConnection(_connected_identity())

    assert_authorized_destructive_connection(connection, config)  # type: ignore[arg-type]

    assert connection.execute_calls == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("database_name", "zeromerma"),
        ("database_user", "zeromerma"),
        ("application_name", "unbound-test-run"),
        ("server_version_num", "150012"),
    ],
)
def test_postconnect_rejects_mismatched_real_identity(field: str, value: str) -> None:
    config = load_destructive_test_database_config(_valid_environment())
    identity = _connected_identity()
    identity[field] = value
    connection = FakeConnection(identity)

    with pytest.raises(DestructiveTestDatabaseSafetyError) as error:
        assert_authorized_destructive_connection(connection, config)  # type: ignore[arg-type]

    assert connection.execute_calls == 1
    assert TEST_PASSWORD not in str(error.value)


def test_two_run_ids_cannot_resolve_to_the_same_database() -> None:
    first = load_destructive_test_database_config(_valid_environment(run_id="a" * 32))
    second = load_destructive_test_database_config(_valid_environment(run_id="b" * 32))

    assert first.run_id != second.run_id
    assert first.database != second.database
    assert first.confirmation != second.confirmation
