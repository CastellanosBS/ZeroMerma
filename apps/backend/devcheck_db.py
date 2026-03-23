from __future__ import annotations

import json
import logging
import os

from zeromerma_api.scripts.bootstrap_db import (
    get_current_revision,
    get_head_revision,
    ping_database,
)

log = logging.getLogger(__name__)


def redact_database_url(url: str | None) -> str | None:
    """
    Redact credentials from DATABASE_URL for safe console output.
    """
    if not url:
        return None

    # Very small pragmatic redaction:
    # postgresql+psycopg://user:password@host/db -> postgresql+psycopg://***:***@host/db
    if "@" in url and "://" in url:
        scheme, rest = url.split("://", 1)
        if "@" in rest and ":" in rest.split("@", 1)[0]:
            creds, tail = rest.split("@", 1)
            return f"{scheme}://***:***@{tail}"
    return url


def main() -> None:
    ping_database()

    payload = {
        "database_url": redact_database_url(os.getenv("DATABASE_URL")),
        "current_revision": get_current_revision(),
        "head_revision": get_head_revision(),
        "db_ok": True,
    }

    log.info("Database connectivity and Alembic state look healthy.")
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
