from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from zeromerma_api.db.session import SessionLocal

ISOLATION_MARKER = "zm-fin-005-isolation-marker"


def test_01_controlled_write_is_visible_only_in_current_test() -> None:
    with SessionLocal() as session:
        session.execute(
            text(
                """
                INSERT INTO audit_log (
                  id, occurred_at, action, resource_type, request_id, metadata
                ) VALUES (
                  :id, :occurred_at, :action, :resource_type, :request_id, CAST(:metadata AS JSONB)
                )
                """
            ),
            {
                "id": uuid4(),
                "occurred_at": datetime.now(UTC),
                "action": "test.database_isolation",
                "resource_type": "test_marker",
                "request_id": ISOLATION_MARKER,
                "metadata": "{}",
            },
        )
        session.commit()

        count = session.scalar(
            text("SELECT COUNT(*) FROM audit_log WHERE request_id = :request_id"),
            {"request_id": ISOLATION_MARKER},
        )

    assert count == 1


def test_02_previous_test_write_was_removed_by_protected_fixture() -> None:
    with SessionLocal() as session:
        count = session.scalar(
            text("SELECT COUNT(*) FROM audit_log WHERE request_id = :request_id"),
            {"request_id": ISOLATION_MARKER},
        )

    assert count == 0
