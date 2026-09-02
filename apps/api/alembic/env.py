from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from zeromerma_api.core.config import get_settings
from zeromerma_api.db.base import Base
from zeromerma_api.db.wait import wait_for_database
from zeromerma_api.modules.audit.infrastructure import models as audit_models
from zeromerma_api.modules.branches.infrastructure import models as branch_models
from zeromerma_api.modules.cash.infrastructure import models as cash_models
from zeromerma_api.modules.cash_close.infrastructure import models as cash_close_models
from zeromerma_api.modules.catalog.infrastructure import models as catalog_models
from zeromerma_api.modules.configuration.infrastructure import models as configuration_models
from zeromerma_api.modules.corrections.infrastructure import models as corrections_models
from zeromerma_api.modules.discounts.infrastructure import models as discounts_models
from zeromerma_api.modules.identity.infrastructure import models as identity_models
from zeromerma_api.modules.inventory.infrastructure import models as inventory_models
from zeromerma_api.modules.operations.infrastructure import models as operations_models
from zeromerma_api.modules.orders.infrastructure import models as orders_models
from zeromerma_api.modules.outbox.infrastructure import models as outbox_models
from zeromerma_api.modules.payments.infrastructure import models as payments_models
from zeromerma_api.modules.production.infrastructure import models as production_models
from zeromerma_api.modules.purchases.infrastructure import models as purchases_models
from zeromerma_api.modules.quality.infrastructure import models as quality_models
from zeromerma_api.modules.returns.infrastructure import models as returns_models
from zeromerma_api.modules.sales.infrastructure import models as sales_models
from zeromerma_api.modules.suppliers.infrastructure import models as suppliers_models
from zeromerma_api.testing.database_safety import (
    TEST_CONFIRMATION_VARIABLE,
    TEST_DATABASE_URL_VARIABLE,
    TEST_ENVIRONMENT_VARIABLE,
    TEST_RUN_ID_VARIABLE,
    DestructiveTestDatabaseConfig,
    assert_authorized_destructive_connection,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

TEST_GUARD_VARIABLES = (
    TEST_ENVIRONMENT_VARIABLE,
    TEST_DATABASE_URL_VARIABLE,
    TEST_RUN_ID_VARIABLE,
    TEST_CONFIRMATION_VARIABLE,
)

_ = (
    audit_models,
    branch_models,
    catalog_models,
    cash_models,
    cash_close_models,
    configuration_models,
    corrections_models,
    discounts_models,
    identity_models,
    inventory_models,
    operations_models,
    orders_models,
    payments_models,
    production_models,
    purchases_models,
    quality_models,
    outbox_models,
    returns_models,
    sales_models,
    suppliers_models,
)


def run_migrations_offline() -> None:
    settings = get_settings()
    context.configure(
        url=str(settings.database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def _run_migrations_with_connection(connection: Connection) -> None:
    test_database_config = config.attributes.get("destructive_test_database_config")
    if test_database_config is not None:
        if not isinstance(test_database_config, DestructiveTestDatabaseConfig):
            raise RuntimeError("Invalid destructive test database configuration.")
        assert_authorized_destructive_connection(connection, test_database_config)
        connection.commit()

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        if config.attributes.get("destructive_test_database_config") is None:
            raise RuntimeError(
                "Injected Alembic connections require the ZeroMerma destructive-test guard."
            )
        _run_migrations_with_connection(supplied_connection)
        return

    if any(name in os.environ for name in TEST_GUARD_VARIABLES):
        raise RuntimeError(
            "Destructive test migrations must use the guarded injected-connection path."
        )

    settings = get_settings()
    wait_for_database(str(settings.database_url))
    config.set_main_option("sqlalchemy.url", str(settings.database_url))

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _run_migrations_with_connection(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
