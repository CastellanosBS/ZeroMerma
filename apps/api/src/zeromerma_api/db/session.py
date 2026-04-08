from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from zeromerma_api.core.config import get_settings


def create_sqlalchemy_engine(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(bind: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=bind, autoflush=False, expire_on_commit=False, class_=Session)


settings = get_settings()
engine = create_sqlalchemy_engine(str(settings.database_url))
SessionLocal = create_session_factory(engine)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
