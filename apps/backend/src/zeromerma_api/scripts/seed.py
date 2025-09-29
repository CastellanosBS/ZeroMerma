from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import SessionLocal, engine

# from zeromerma_api.models import Branch, Role, User  # example

log = logging.getLogger(__name__)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Transactional scope for seeds:
      - Open a session.
      - Yield it to the caller.
      - Commit on success; rollback on any exception; always close.

    Why:
      - Seeds often touch multiple tables; we want all-or-nothing semantics.
      - Keeps the session lifecycle explicit and testable.
    """
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def main() -> None:
    """
    Idempotent seed entrypoint.

    Today:
      - No domain tables exist yet ⇒ we only ping the DB and report schema.
    B1:
      - We'll gate on required tables and insert defaults only if missing.
    """
    # Ensure .env/envvars are loaded (if your engine depends on them).
    get_settings()

    # Fail-fast ping (useful in CI to detect bad DB config).
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    insp = inspect(engine)
    existing = set(insp.get_table_names())
    log.info("Detected tables: %s", sorted(existing))

    # --- B1 EXAMPLES (keep commented until models+migrations exist) ---

    # with session_scope() as s:
    #     needed = {"branch", "role", "user_account"}
    #     if needed.issubset(existing):
    #         seed_roles(s)                 # idempotent
    #         admin = seed_admin_user(s)    # idempotent, returns the admin row
    #         seed_branch_main(s, created_by_id=admin.id)  # idempotent

    log.info("Seed: no-op (no domain tables to seed yet).")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
