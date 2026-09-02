from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import NoReturn

from sqlalchemy import text
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.exc import ArgumentError

TEST_ENVIRONMENT_VARIABLE = "ZEROMERMA_TEST_ENVIRONMENT"
TEST_DATABASE_URL_VARIABLE = "ZEROMERMA_TEST_DATABASE_URL"
TEST_RUN_ID_VARIABLE = "ZEROMERMA_TEST_RUN_ID"
TEST_CONFIRMATION_VARIABLE = "ZEROMERMA_TEST_DESTRUCTIVE_CONFIRMATION"

EXPECTED_TEST_ENVIRONMENT = "test"
EXPECTED_TEST_USER = "zeromerma_test_runner"
DATABASE_PREFIX = "zeromerma_test_"
APPLICATION_NAME_PREFIX = "zeromerma_test_"
CONFIRMATION_PREFIX = "ALLOW_ZEROMERMA_DESTRUCTIVE_TESTS:"
ALLOWED_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
PROHIBITED_DATABASES = frozenset({"postgres", "template0", "template1", "zeromerma"})
ALLOWED_DRIVERS = frozenset({"postgresql", "postgresql+psycopg"})
RUN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_]{7,39}$")
SAFE_COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_.:-]+$")


class DestructiveTestDatabaseSafetyError(RuntimeError):
    """Raised before unsafe test database work can begin."""


@dataclass(frozen=True)
class DestructiveTestDatabaseConfig:
    environment: str
    database_url: str = field(repr=False)
    run_id: str
    confirmation: str = field(repr=False)
    driver: str
    host: str
    port: int
    database: str
    user: str
    application_name: str

    def redacted_summary(self) -> str:
        return (
            f"environment={self.environment}; host={self.host}; port={self.port}; "
            f"database={self.database}; user={self.user}; run_id={self.run_id}"
        )


def _safe_component(value: object) -> str:
    if value is None:
        return "<missing>"
    rendered = str(value)
    if SAFE_COMPONENT_PATTERN.fullmatch(rendered):
        return rendered
    return "<invalid>"


def _reject(
    reason: str,
    *,
    environment: object = None,
    host: object = None,
    port: object = None,
    database: object = None,
    user: object = None,
) -> NoReturn:
    context = (
        f"environment={_safe_component(environment)}; "
        f"host={_safe_component(host)}; port={_safe_component(port)}; "
        f"database={_safe_component(database)}; user={_safe_component(user)}"
    )
    raise DestructiveTestDatabaseSafetyError(
        f"Destructive test database rejected: {context}; reason={reason}"
    )


def load_destructive_test_database_config(
    environment: Mapping[str, str],
) -> DestructiveTestDatabaseConfig:
    test_environment = environment.get(TEST_ENVIRONMENT_VARIABLE, "")
    if test_environment != EXPECTED_TEST_ENVIRONMENT:
        _reject(
            f"{TEST_ENVIRONMENT_VARIABLE} must be exactly 'test'",
            environment=test_environment,
        )

    database_url = environment.get(TEST_DATABASE_URL_VARIABLE, "")
    if not database_url:
        _reject(
            f"{TEST_DATABASE_URL_VARIABLE} is required; "
            "application DATABASE_URL fallback is forbidden",
            environment=test_environment,
        )

    try:
        parsed_url = make_url(database_url)
        port = parsed_url.port
    except (ArgumentError, TypeError, ValueError):
        _reject("test database URL is malformed", environment=test_environment)

    driver = parsed_url.drivername.lower()
    host = (parsed_url.host or "").lower()
    database = parsed_url.database or ""
    user = parsed_url.username or ""
    run_id = environment.get(TEST_RUN_ID_VARIABLE, "")
    confirmation = environment.get(TEST_CONFIRMATION_VARIABLE, "")

    context = {
        "environment": test_environment,
        "host": host,
        "port": port,
        "database": database,
        "user": user,
    }

    if driver not in ALLOWED_DRIVERS:
        _reject("scheme must be PostgreSQL with the supported psycopg driver", **context)
    if host not in ALLOWED_HOSTS:
        _reject("host is not an explicitly allowed loopback test endpoint", **context)
    if port is None or not 1 <= port <= 65535:
        _reject("an explicit valid test port is required", **context)
    if not RUN_ID_PATTERN.fullmatch(run_id):
        _reject("run id must be 8-40 lowercase alphanumeric/underscore characters", **context)

    expected_database = f"{DATABASE_PREFIX}{run_id}"
    if database in PROHIBITED_DATABASES:
        _reject("database name is explicitly prohibited", **context)
    if database != expected_database:
        _reject("database name is not exactly bound to the declared run id", **context)
    if user != EXPECTED_TEST_USER:
        _reject("database user is not the dedicated test-only role", **context)
    if not parsed_url.password:
        _reject("a dedicated ephemeral test credential is required", **context)

    expected_application_name = f"{APPLICATION_NAME_PREFIX}{run_id}"
    query_keys = set(parsed_url.query)
    if query_keys != {"application_name"}:
        _reject("only the required application_name URL parameter is allowed", **context)
    application_name = parsed_url.query.get("application_name")
    if not isinstance(application_name, str) or application_name != expected_application_name:
        _reject("application_name is not exactly bound to the declared run id", **context)

    expected_confirmation = f"{CONFIRMATION_PREFIX}{run_id}"
    if confirmation != expected_confirmation:
        _reject("destructive confirmation is missing or not bound to the run id", **context)

    return DestructiveTestDatabaseConfig(
        environment=test_environment,
        database_url=database_url,
        run_id=run_id,
        confirmation=confirmation,
        driver=driver,
        host=host,
        port=port,
        database=database,
        user=user,
        application_name=application_name,
    )


def run_after_preconnect_guard[T](
    environment: Mapping[str, str],
    operation: Callable[[DestructiveTestDatabaseConfig], T],
) -> tuple[DestructiveTestDatabaseConfig, T]:
    """Authorize first; only then allow engine/import/connection work."""
    config = load_destructive_test_database_config(environment)
    return config, operation(config)


def assert_authorized_destructive_connection(
    connection: Connection,
    config: DestructiveTestDatabaseConfig,
) -> None:
    """Verify the real server identity before DDL or destructive SQL."""
    identity = (
        connection.execute(
            text(
                """
                SELECT
                  current_database() AS database_name,
                  current_user AS database_user,
                  current_setting('application_name') AS application_name,
                  current_setting('server_version_num') AS server_version_num
                """
            )
        )
        .mappings()
        .one()
    )

    actual_database = str(identity["database_name"])
    actual_user = str(identity["database_user"])
    actual_application_name = str(identity["application_name"])
    actual_server_version = str(identity["server_version_num"])

    if actual_database != config.database:
        _reject(
            "connected database does not match the authorized ephemeral database",
            environment=config.environment,
            host=config.host,
            port=config.port,
            database=actual_database,
            user=actual_user,
        )
    if actual_user != config.user:
        _reject(
            "connected user does not match the dedicated test-only role",
            environment=config.environment,
            host=config.host,
            port=config.port,
            database=actual_database,
            user=actual_user,
        )
    if actual_application_name != config.application_name:
        _reject(
            "connected application_name is not bound to the authorized run id",
            environment=config.environment,
            host=config.host,
            port=config.port,
            database=actual_database,
            user=actual_user,
        )
    if not actual_server_version.isdigit() or not 160000 <= int(actual_server_version) < 170000:
        _reject(
            "connected server is not PostgreSQL 16",
            environment=config.environment,
            host=config.host,
            port=config.port,
            database=actual_database,
            user=actual_user,
        )
