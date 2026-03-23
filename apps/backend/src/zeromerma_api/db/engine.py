from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from zeromerma_api.core.settings import get_settings

settings = get_settings()

db_url = settings.database_url
if not db_url:
    raise RuntimeError("database_url is not configured (check DATABASE_URL and your .env file).")

engine = create_engine(
    db_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_session():
    """
    Yield a SQLAlchemy Session.

    FastAPI will use this as a dependency to create one Session per request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
