from sqlalchemy import Engine, create_engine

from zeromerma_worker.core.config import WorkerSettings


def create_worker_engine(settings: WorkerSettings) -> Engine:
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )
