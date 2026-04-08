from sqlalchemy import Engine, create_engine

from zeromerma_worker.core.config import WorkerSettings


def create_worker_engine(settings: WorkerSettings) -> Engine:
    return create_engine(str(settings.database_url), pool_pre_ping=True)
