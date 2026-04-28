from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from zeromerma_api.core.config import get_settings
from zeromerma_api.db.base import Base
from zeromerma_api.modules.audit.infrastructure import models as audit_models
from zeromerma_api.modules.branches.infrastructure import models as branch_models
from zeromerma_api.modules.cash.infrastructure import models as cash_models
from zeromerma_api.modules.cash_close.infrastructure import models as cash_close_models
from zeromerma_api.modules.catalog.infrastructure import models as catalog_models
from zeromerma_api.modules.corrections.infrastructure import models as corrections_models
from zeromerma_api.modules.discounts.infrastructure import models as discounts_models
from zeromerma_api.modules.identity.infrastructure import models as identity_models
from zeromerma_api.modules.operations.infrastructure import models as operations_models
from zeromerma_api.modules.orders.infrastructure import models as orders_models
from zeromerma_api.modules.payments.infrastructure import models as payments_models
from zeromerma_api.modules.outbox.infrastructure import models as outbox_models
from zeromerma_api.modules.returns.infrastructure import models as returns_models
from zeromerma_api.modules.sales.infrastructure import models as sales_models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_ = (
    audit_models,
    branch_models,
    catalog_models,
    cash_models,
    cash_close_models,
    corrections_models,
    discounts_models,
    identity_models,
    operations_models,
    orders_models,
    payments_models,
    outbox_models,
    returns_models,
    sales_models,
)


def run_migrations_offline() -> None:
    settings = get_settings()
    context.configure(
        url=str(settings.database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = get_settings()
    config.set_main_option("sqlalchemy.url", str(settings.database_url))

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
