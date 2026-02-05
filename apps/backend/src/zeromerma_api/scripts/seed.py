# apps/backend/seed.py
# PURPOSE: Idempotent, transactional bootstrapping of core admin data.
#          Safe to run repeatedly (locally, in CI, in staging). Never creates duplicates.

from __future__ import (
    annotations,  # (1) Let Python postpone type-hint evaluation (cleaner imports / no runtime cycles).
)

import logging  # (2) Standard logging so we can see "created" vs "exists" in CI and locally.
from collections.abc import (
    Iterator,  # (4) Type hint for the context manager's yield value.
)
from contextlib import (
    contextmanager,  # (3) Build a transactional "session_scope" context manager.
)

from sqlalchemy import (  # (5) SQLAlchemy Core helpers: SELECT query builder + raw SQL execution.
    select,
    text,
)
from sqlalchemy.orm import (
    Session,  # (6) The SQLAlchemy ORM Session type (for explicit, typed session code).
)

# Optional: If you want to demonstrate Postgres "UPSERT", we import the dialect insert. We'll keep it commented to avoid confusion.
# from sqlalchemy.dialects.postgresql import insert as pg_insert
# (7) Load application settings and the shared DB engine/session from YOUR project modules (as you already set up).
from zeromerma_api.core.settings import get_settings
from zeromerma_api.db.engine import SessionLocal, engine

# (8) Import your three admin models FROM THEIR FILES (matching your current layout).
from zeromerma_api.models import Branch, Role, UserAccount

# (9) Configure a module logger. __name__ resolves to "seed" when executed as a script.
log = logging.getLogger(__name__)


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Transaction scope:
      - Open a Session (DB connection + unit-of-work boundary).
      - Yield it to the caller to perform writes.
      - On success: COMMIT (make changes durable).
      - On exception: ROLLBACK (undo partial changes).
      - Always: CLOSE the session (release connection back to the pool).
    """
    s = SessionLocal()  # (10) Create a new Session bound to your shared Engine.
    try:
        yield s  # (11) Hand control to the caller (Your seeding functions run inside this block).
        s.commit()  # (12) If nothing raised an exception, persist all changes atomically.
    except Exception:
        s.rollback()  # (13) Undo partial work so the DB is never left half-changed.
        raise  # (14) Bubble the error up so CI/dev sees a failure.
    finally:
        s.close()  # (15) Free resources (connection) deterministically.


# ----------------------------
# "Ensure" helpers (idempotent)
# ----------------------------


def ensure_roles(s: Session) -> None:
    """
    Ensure the canonical roles exist: ADMIN, CASHIER, BAKER.
    IDPOTENCY MECHANISM:
      - Query by UNIQUE(Role.code).
      - If missing -> INSERT once.
      - If present -> do nothing.
    NOTES:
      - This is a "get-or-create" style (portable across DBs).
      - If you expect high concurrency, a Postgres UPSERT is also shown below (commented).
    """
    # (16) Prepare the reference set in code; easy to read and test.
    desired = [
        {"code": "ADMIN", "name": "Administrator"},
        {"code": "CASHIER", "name": "Cashier"},
        {"code": "BAKER", "name": "Baker"},
    ]

    for row in desired:  # (17) Iterate deterministically so logs are stable.
        code = row["code"]  # (18) Pull the unique business key.
        # (19) Try to find an existing role by its UNIQUE code.
        existing = s.scalar(select(Role).where(Role.code == code))
        if existing is None:
            # (20) Not present -> create a new Role object and add it to the session.
            s.add(Role(code=row["code"], name=row["name"]))
            log.info("Role created: %s", code)
        else:
            # (21) Already present -> leave it as is (idempotent behavior).
            log.info("Role exists: %s", code)

    # ---- OPTIONAL: Postgres UPSERT (efficient & race-safe) ----
    # stmt = pg_insert(Role).values(desired).on_conflict_do_nothing(index_elements=[Role.code])
    # s.execute(stmt)
    # log.info("Roles upserted via ON CONFLICT DO NOTHING.")


def ensure_branch_main(s: Session) -> Branch:
    """
    Ensure the canonical MAIN branch exists.
    Returns the Branch row (new or existing) so callers can link FKs.
    IDPOTENCY: query by UNIQUE(Branch.code) before inserting.
    """
    # (22) Look for the MAIN branch by its UNIQUE code.
    branch = s.scalar(select(Branch).where(Branch.code == "MAIN"))
    if branch is None:
        # (23) Not present -> create and add.
        branch = Branch(code="MAIN", name="Main Branch", is_active=True)
        s.add(branch)
        s.flush()  # (24) Flush assigns a DB-generated primary key (id) WITHOUT committing the transaction.
        log.info("Branch created: MAIN (id=%s)", branch.id)
    else:
        log.info("Branch exists: MAIN (id=%s)", branch.id)
    return branch


def ensure_admin_user(
    s: Session,
    *,
    admin_email: str = "admin@example.com",
    full_name: str = "System Admin",
) -> UserAccount:
    """
    Ensure a single admin user exists, associated with Role('ADMIN') and Branch('MAIN').
    PRECONDITIONS: ensure_roles() and ensure_branch_main() have been called first.
    IDPOTENCY: query by UNIQUE(UserAccount.email) before inserting.
    """
    # (25) Try to find the user by UNIQUE email.
    user = s.scalar(select(UserAccount).where(UserAccount.email == admin_email))
    if user:
        log.info("Admin user exists: %s (id=%s)", admin_email, user.id)
        return user

    # (26) Resolve FK dependencies: Role('ADMIN') and Branch('MAIN') must exist.
    role_admin = s.scalar(select(Role).where(Role.code == "ADMIN"))
    if role_admin is None:
        raise RuntimeError(
            "Invariant violated: Role(code='ADMIN') not found. Run ensure_roles first."
        )

    branch_main = s.scalar(select(Branch).where(Branch.code == "MAIN"))
    if branch_main is None:
        raise RuntimeError(
            "Invariant violated: Branch(code='MAIN') not found. Run ensure_branch_main first."
        )

    # (27) Create the user. We set password_hash=None for now (no auth yet).
    user = UserAccount(
        email=admin_email,
        full_name=full_name,
        role_id=role_admin.id,
        branch_id=branch_main.id,
        password_hash=None,  # TODO: once auth is wired, set a real hash or an initial random password.
        is_active=True,
    )
    s.add(user)
    s.flush()  # (28) Get DB-generated primary key (id) now (still inside the same transaction).
    log.info("Admin user created: %s (id=%s)", admin_email, user.id)
    return user


def run_all(s: Session) -> None:
    """
    High-level orchestrator:
      1) Roles (no dependencies)
      2) MAIN branch (no dependencies)
      3) Admin user (depends on both)
    Running order guarantees foreign keys are resolvable.
    """
    ensure_roles(s)  # (29) Create/confirm ADMIN/CASHIER/BAKER
    ensure_branch_main(s)  # (30) Create/confirm MAIN
    ensure_admin_user(s)  # (31) Create/confirm admin@example.com


def main() -> None:
    """
    Script entry point. Safe to run multiple times.
    - Forces settings load (env/.env)
    - Pings DB (fast failure if misconfigured)
    - Opens a transaction scope and runs all seeds
    """
    get_settings()  # (32) Ensure .env/env vars are loaded so engine has a valid URL.

    # (33) Quick DB ping: raises if DB is unreachable -> good signal in CI.
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    # (34) Transactional run: all-or-nothing.
    with session_scope() as s:
        run_all(s)

    log.info("Seed completed successfully (idempotent).")


if __name__ == "__main__":
    # (35) Basic console logging format; you can later unify with your app logger if desired.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    main()
