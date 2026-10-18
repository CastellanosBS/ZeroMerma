"""Prepare private credentials and rotate a database login without rebuilding artifacts."""

from __future__ import annotations

import argparse
import getpass
import json
import secrets
import sys
from pathlib import Path
from typing import Never

from psycopg import connect, sql
from sqlalchemy.engine import make_url

from zeromerma_api.core.runtime_secrets import read_private_secret, write_private_secret


class _PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        # argparse normally echoes rejected argument values, which may be secrets.
        self.print_usage(sys.stderr)
        self.exit(2, "Invalid arguments. Runtime secret values must use the private prompt.\n")


def rotate_database_credential(current_file: Path, next_file: Path) -> int:
    current_url = make_url(read_private_secret(current_file))
    if (
        current_url.drivername != "postgresql+psycopg"
        or not current_url.host
        or not current_url.database
        or not current_url.username
        or not current_url.password
    ):
        raise ValueError("Rotation requires a complete PostgreSQL runtime credential.")
    if current_file.resolve() == next_file.resolve():
        raise ValueError("Rotation requires a distinct, previously nonexistent successor file.")
    next_password = secrets.token_urlsafe(48)
    successor_url = current_url.set(password=next_password)
    write_private_secret(next_file, successor_url.render_as_string(hide_password=False))
    commit_attempted = False
    try:
        connection_url = current_url.set(drivername="postgresql").render_as_string(
            hide_password=False
        )
        with connect(connection_url, connect_timeout=5) as connection:
            connection.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(current_url.username), sql.Literal(next_password)
                )
            )
            commit_attempted = True
            connection.commit()
        successor_connection = successor_url.set(drivername="postgresql").render_as_string(
            hide_password=False
        )
        with connect(successor_connection, connect_timeout=5) as probe:
            if probe.execute("SELECT 1").fetchone() != (1,):
                raise RuntimeError("The successor connection probe did not succeed.")
    except Exception:
        if commit_attempted:
            # A lost acknowledgement cannot prove rollback; retain the only successor.
            print(
                "Rotation outcome requires reconciliation. Both private files are retained; "
                "verify which credential connects before changing service configuration.",
                file=sys.stderr,
            )
            return 2
        next_file.unlink(missing_ok=True)
        raise
    print(
        "Database login rotated and successor verified. Point the services at the private "
        "successor file, restart their pools, verify readiness, then securely retire the old file."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _PrivateArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    store = commands.add_parser("store", help="Store a value entered in a private terminal.")
    store.add_argument("--output", type=Path, required=True)
    rotate = commands.add_parser("rotate-database", help="Rotate only the login in a private DSN.")
    rotate.add_argument("--environment", choices=["staging", "production"], required=True)
    rotate.add_argument("--current-file", type=Path, required=True)
    rotate.add_argument("--next-file", type=Path, required=True)
    scan = commands.add_parser("scan", help="Scan Git and explicit unpacked artifacts.")
    scan.add_argument("--repository", type=Path, required=True)
    scan.add_argument("--secret-file", type=Path, action="append", default=[])
    scan.add_argument("--artifact", type=Path, action="append", default=[])
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "scan":
            from zeromerma_api.core.runtime_secret_scan import scan_repository

            result = scan_repository(
                arguments.repository,
                secret_files=arguments.secret_file,
                artifacts=arguments.artifact,
            )
            print(json.dumps(result, ensure_ascii=True))
            return 0 if result["passed"] else 1
        if arguments.command == "store":
            if not sys.stdin.isatty():
                raise ValueError("Secret input requires a private interactive terminal.")
            value = getpass.getpass("Runtime secret value: ")
            if value != getpass.getpass("Confirm runtime secret value: "):
                raise ValueError("Secret confirmation does not match.")
            write_private_secret(arguments.output, value)
            print("Private runtime secret file created.")
            return 0
        return rotate_database_credential(arguments.current_file, arguments.next_file)
    except Exception as error:
        # Driver, URL and validation exception messages can contain credentials.
        print(f"Runtime secret operation failed ({type(error).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
