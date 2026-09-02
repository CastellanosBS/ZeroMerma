from __future__ import annotations

import os
from collections.abc import Iterator
from importlib import import_module
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

from zeromerma_api.core.config import get_settings
from zeromerma_api.testing.database_safety import (
    DestructiveTestDatabaseConfig,
    assert_authorized_destructive_connection,
    run_after_preconnect_guard,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _initialize_test_runtime(config: DestructiveTestDatabaseConfig) -> tuple[Any, ...]:
    os.environ["ZEROMERMA_API_ENVIRONMENT"] = "test"
    os.environ["ZEROMERMA_API_DATABASE_URL"] = config.database_url
    get_settings.cache_clear()

    database_session = import_module("zeromerma_api.db.session")
    seed_module = import_module("zeromerma_api.bootstrap.seed_local")
    main_module = import_module("zeromerma_api.main")
    return (
        database_session.engine,
        database_session.SessionLocal,
        seed_module.seed_local_data,
        main_module.create_app,
    )


TEST_DATABASE_CONFIG, TEST_RUNTIME = run_after_preconnect_guard(
    os.environ,
    _initialize_test_runtime,
)
TEST_ENGINE, SessionLocal, seed_local_data, create_app = TEST_RUNTIME

TRUNCATE_SQL = """
TRUNCATE TABLE
  system_setting_history,
  system_settings,
  quality_incident_follow_ups,
  quality_incidents,
  equipment_maintenance_records,
  equipment_assets,
  sanitary_verification_checklist_items,
  sanitary_verifications,
  sanitary_verification_template_items,
  sanitary_verification_templates,
  cleaning_log_checklist_items,
  cleaning_logs,
  cleaning_template_items,
  cleaning_templates,
  purchase_receipt_lines,
  purchase_receipts,
  purchase_document_lines,
  purchase_documents,
  supplier_branches,
  supplier_products,
  supplier_contacts,
  suppliers,
  production_batch_inputs,
  production_batches,
  recipe_inputs,
  recipes,
  cash_session_close_reconciliation_attributions,
  cash_session_close_class_reconciliations,
  cash_session_close_discrepancy_resolutions,
  cash_session_close_issues,
  cash_session_close_payment_method_counts,
  cash_session_close_product_counts,
  branch_counter_snapshot_lines,
  branch_counter_snapshots,
  financial_reconciliations,
  cash_session_closes,
  commercial_discounts,
  correction_document_lines,
  correction_documents,
  correction_reasons,
  operational_discounts,
  operational_discount_categories,
  operational_payments,
  operational_payment_categories,
  operation_document_lines,
  operation_documents,
  waste_reasons,
  cash_movements,
  customer_order_payments,
  customer_order_items,
  customer_orders,
  sale_return_lines,
  sale_returns,
  sale_payments,
  sale_lines,
  sales,
  inventory_movements,
  inventory_adjustments,
  inventory_balances,
  products,
  product_classes,
  cash_sessions,
  user_role_assignments,
  role_permissions,
  permissions,
  roles,
  user_branch_assignments,
  workstations,
  branches,
  brands,
  users,
  audit_log,
  outbox_events
RESTART IDENTITY CASCADE
"""


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    with TEST_ENGINE.connect() as connection:
        assert_authorized_destructive_connection(connection, TEST_DATABASE_CONFIG)

    alembic_config = Config(str(REPO_ROOT / "apps" / "api" / "alembic.ini"))
    command.upgrade(alembic_config, "head")


@pytest.fixture(scope="session", autouse=True)
def restore_seeded_database_state(migrated_database: None) -> Iterator[None]:
    yield

    _reset_seeded_database()


def _reset_seeded_database() -> None:
    with SessionLocal() as session:
        assert_authorized_destructive_connection(session.connection(), TEST_DATABASE_CONFIG)
        session.execute(text(TRUNCATE_SQL))
        seed_local_data(session)
        session.commit()


@pytest.fixture(autouse=True)
def seeded_database(migrated_database: None) -> Iterator[None]:
    _reset_seeded_database()

    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client
