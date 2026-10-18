from __future__ import annotations

import os
import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from psycopg import OperationalError, connect, sql
from sqlalchemy.engine import make_url

from zeromerma_api.core.runtime_secret_cli import rotate_database_credential
from zeromerma_api.core.runtime_secrets import read_private_secret, write_private_secret
from zeromerma_api.testing.database_safety import load_destructive_test_database_config


def test_database_secret_rotation_preserves_data_and_invalidates_old_credential(
    tmp_path: Path,
) -> None:
    # The suite conftest verifies the same disposable test database before any SQL.
    config = load_destructive_test_database_config(os.environ)
    admin_url = make_url(config.database_url).set(drivername="postgresql")
    role = "rotation_" + uuid4().hex
    password = secrets.token_urlsafe(40)
    original = tmp_path / "runtime-current"
    successor = tmp_path / "runtime-successor"
    old_url = admin_url.set(username=role, password=password)
    with connect(admin_url.render_as_string(hide_password=False)) as admin:
        admin.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
                sql.Identifier(role), sql.Literal(password)
            )
        )
        admin.execute(
            sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                sql.Identifier(role), sql.Identifier(role)
            )
        )
    try:
        with connect(old_url.render_as_string(hide_password=False)) as connection:
            connection.execute(
                sql.SQL("CREATE TABLE {}.session_probe (credential_hash text)").format(
                    sql.Identifier(role)
                )
            )
            connection.execute(
                sql.SQL("INSERT INTO {}.session_probe VALUES (%s)").format(sql.Identifier(role)),
                ("persisted-session-verifier",),
            )
        write_private_secret(
            original,
            old_url.set(drivername="postgresql+psycopg").render_as_string(hide_password=False),
        )
        assert rotate_database_credential(original, successor) == 0
        new_url = make_url(read_private_secret(successor)).set(drivername="postgresql")
        with connect(new_url.render_as_string(hide_password=False)) as connection:
            assert connection.execute(
                sql.SQL("SELECT credential_hash FROM {}.session_probe").format(sql.Identifier(role))
            ).fetchone() == ("persisted-session-verifier",)
        with pytest.raises(OperationalError):
            connect(old_url.render_as_string(hide_password=False), connect_timeout=3)
    finally:
        with connect(admin_url.render_as_string(hide_password=False)) as admin:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(role)))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
