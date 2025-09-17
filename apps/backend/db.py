from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings

# Engine: manages connections and talks to the DB (database)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # checks connections before using (avoids stale connections)
    future=True,  # SQLAlchemy 2.x style
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
