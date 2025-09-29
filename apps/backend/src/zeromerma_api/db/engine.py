from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zeromerma_api.core.settings import get_settings

s = get_settings()

url = s.database_url
if url is None:
    raise RuntimeError("DATABASE_URL no está configurada en el entorno")


# Engine: manages connections and talks to the DB (database)
engine = create_engine(
    url,
    pool_pre_ping=True,
)

# Session factory: creates Session objects (units of work)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,  # we control when to flush
    autocommit=False,  # we commit explicitly
    future=True,
)


def get_session():
    """
    Yields a SQLAlchemy Session inside a context-like generator.
    Later, FastAPI (web framework) can use this as a dependency to
    inject a per-request Session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
