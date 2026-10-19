"""Canonical trace snapshots share a transaction without changing its commit owner."""

from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text

from zeromerma_api.bootstrap.seed_local import SEED_ADMIN_EMAIL, SEED_BRANCH_CODE
from zeromerma_api.core.operation_context import OperationContext, SourceApp
from zeromerma_api.db.operation_context import bind_operation_context, get_operation_context
from zeromerma_api.db.session import SessionLocal, engine
from zeromerma_api.modules.audit.application.admin_services import AdminAuditService
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.identity.infrastructure.session_models import AuthSession
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.quality.application.equipment_schemas import (
    AdminEquipmentCreateRequest,
    AdminMaintenanceCreateRequest,
)
from zeromerma_api.modules.quality.application.equipment_services import (
    AdminEquipmentMaintenanceService,
)
from zeromerma_api.modules.quality.infrastructure.models import EquipmentMaintenanceRecord
from zeromerma_api.testing.sessions import fixture_session_headers


def _trace_pair(session, context: OperationContext):
    audit = AuditRecorder().record(
        session,
        actor_id=context.actor_id,
        branch_id=context.branch_id,
        action="trace.test",
        resource_type="test_document",
        resource_id="safe-resource",
        request_id=context.request_id,
        metadata={"source_app": "FORGED", "password": "hidden"},
    )
    event = OutboxWriter().append(
        session,
        aggregate_type="test_document",
        aggregate_id="safe-resource",
        event_name="trace.test.v1",
        payload={"amount": "1.00"},
        headers={"source_app": "FORGED"},
    )
    return audit, event


def _assert_context(row, context: OperationContext) -> None:
    assert row.context_version == 1
    assert row.source_app == context.source_app
    assert row.actor_type == context.actor_type
    for field in (
        "operation_id",
        "correlation_id",
        "causation_id",
        "idempotency_key",
        "operation_code",
        "request_id",
        "actor_id",
        "branch_id",
        "workstation_id",
        "cash_session_id",
    ):
        assert getattr(row, field) == getattr(context, field)
    assert row.related_branch_ids == sorted(
        {
            *(str(value) for value in context.related_branch_ids),
            *([str(context.branch_id)] if context.branch_id else []),
        }
    )


def test_writers_capture_immutable_context_and_leave_commit_to_the_caller() -> None:
    context = replace(
        OperationContext.start(SourceApp.POS, request_id=str(uuid4())),
        actor_id=uuid4(),
        branch_id=uuid4(),
        workstation_id=uuid4(),
        cash_session_id=uuid4(),
        related_branch_ids=(uuid4(),),
        causation_id=uuid4(),
        idempotency_key=uuid4(),
        operation_code="trace.test",
    )
    with SessionLocal() as session:
        bind_operation_context(session, context)
        audit, event = _trace_pair(session, context)
        session.flush()
        _assert_context(audit, context)
        _assert_context(event, context)
        assert event.schema_version == 1
        assert audit.recorded_at is not None and event.recorded_at is not None
        with SessionLocal() as observer:
            assert observer.get(AuditLog, audit.id) is None
            assert observer.get(OutboxEvent, event.id) is None
        # Later context enrichment cannot reattribute events already created.
        replacement = replace(context, source_app=SourceApp.BACKOFFICE, operation_id=uuid4())
        bind_operation_context(session, replacement)
        session.commit()
        _assert_context(audit, context)
        _assert_context(event, context)
        audit_id, event_id = audit.id, event.id
    with SessionLocal() as observer:
        _assert_context(observer.get(AuditLog, audit_id), context)
        _assert_context(observer.get(OutboxEvent, event_id), context)


def test_explicit_trace_overrides_do_not_mutate_the_bound_context() -> None:
    context = replace(
        OperationContext.start(SourceApp.POS),
        actor_id=uuid4(),
        branch_id=uuid4(),
        workstation_id=uuid4(),
        cash_session_id=uuid4(),
    )
    other_cash = uuid4()
    with SessionLocal() as session:
        bind_operation_context(session, context)
        audit = AuditRecorder().record(
            session,
            actor_id=None,
            branch_id=None,
            action="trace.override",
            resource_type="test",
            resource_id="global",
            request_id=None,
            metadata={},
            workstation_id=None,
            cash_session_id=other_cash,
        )
        event = OutboxWriter().append(
            session,
            aggregate_type="test",
            aggregate_id="global",
            event_name="trace.override.v1",
            payload={},
            actor_id=None,
            branch_id=None,
            workstation_id=None,
            cash_session_id=other_cash,
        )
        session.flush()
        expected = replace(
            context, actor_id=None, branch_id=None, workstation_id=None, cash_session_id=other_cash
        )
        _assert_context(audit, expected)
        _assert_context(event, expected)
        assert get_operation_context(session) == context
        session.rollback()


def test_rollback_removes_both_trace_snapshots() -> None:
    context = OperationContext.start(SourceApp.BACKOFFICE)
    with SessionLocal() as session:
        bind_operation_context(session, context)
        _trace_pair(session, context)
        session.flush()
        session.rollback()
        session.commit()
    with SessionLocal() as observer:
        assert (
            observer.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.operation_id == context.operation_id)
            )
            == 0
        )
        assert (
            observer.scalar(
                select(func.count())
                .select_from(OutboxEvent)
                .where(OutboxEvent.operation_id == context.operation_id)
            )
            == 0
        )


def test_session_trigger_uses_canonical_context_for_both_records() -> None:
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == SEED_ADMIN_EMAIL)).one()
        branch = session.scalars(select(Branch).where(Branch.code == SEED_BRANCH_CODE)).one()
        context = replace(
            OperationContext.start(SourceApp.BACKOFFICE, request_id=str(uuid4())),
            actor_id=user.id,
            branch_id=branch.id,
            related_branch_ids=(branch.id,),
            causation_id=uuid4(),
            operation_code="session.fixture",
        )
        bind_operation_context(session, context)
        fixture_session_headers(session, user)
        session.commit()
    with SessionLocal() as observer:
        audit = observer.scalars(
            select(AuditLog).where(
                AuditLog.operation_id == context.operation_id, AuditLog.action == "session.created"
            )
        ).one()
        event = observer.scalars(
            select(OutboxEvent).where(
                OutboxEvent.operation_id == context.operation_id,
                OutboxEvent.event_name == "session.created",
            )
        ).one()
        _assert_context(audit, context)
        _assert_context(event, context)
        assert audit.resource_id == event.aggregate_id
        assert event.schema_version == 1
        assert audit.recorded_at is not None and event.recorded_at is not None


def test_session_trigger_without_application_context_uses_explicit_system_identity() -> None:
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == SEED_ADMIN_EMAIL)).one()
        fixture_session_headers(session, user)
        session_id = session.scalars(
            select(AuthSession.id).where(AuthSession.user_id == user.id)
        ).one()
        session.commit()
    # A direct SQL transaction has no ORM listener or inherited request context.
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE auth_sessions SET status='LOCKED' WHERE id=:id"), {"id": session_id}
        )
    with SessionLocal() as observer:
        audit = observer.scalars(
            select(AuditLog).where(
                AuditLog.resource_id == str(session_id), AuditLog.action == "session.locked"
            )
        ).one()
        event = observer.scalars(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_id == str(session_id),
                OutboxEvent.event_name == "session.locked",
            )
        ).one()
        assert audit.source_app == event.source_app == "SYSTEM"
        assert audit.actor_type == event.actor_type == "SYSTEM"
        assert audit.operation_id is not None
        assert (
            audit.operation_id == event.operation_id == audit.correlation_id == event.correlation_id
        )
        assert audit.request_id is None and event.request_id is None
        assert audit.actor_id is None and event.actor_id is None
        assert event.schema_version == 1


def test_audit_projection_uses_persisted_source_and_ids_not_forged_metadata() -> None:
    with SessionLocal() as session:
        context = replace(
            OperationContext.start(SourceApp.POS),
            actor_id=uuid4(),
            branch_id=uuid4(),
            workstation_id=uuid4(),
            cash_session_id=uuid4(),
        )
        bind_operation_context(session, context)
        audit, _ = _trace_pair(session, context)
        unknown = AuditLog(
            action="pos.sale.confirmed",
            resource_type="sale",
            actor_id=uuid4(),
            metadata_={"source_app": "BACKOFFICE", "actor_type": "system"},
        )
        unknown_event = OutboxEvent(
            aggregate_type="sale",
            aggregate_id="unknown-history",
            event_name="sale.confirmed.v1",
            payload={},
        )
        session.add_all((unknown, unknown_event))
        session.commit()
        service = AdminAuditService()
        assert service._source_app(audit) == "POS"
        assert service._source_app(unknown) == "UNKNOWN"
        assert service._actor_type(audit) == "user"
        assert service._actor_type(unknown) == "unknown"
        assert unknown_event.schema_version == unknown_event.context_version == 0
        assert unknown_event.source_app == "UNKNOWN"
        view = service._build_request_context(audit)
        assert view is not None and view.operation_id == context.operation_id
        assert view.correlation_id == context.correlation_id
        assert "hidden" not in view.model_dump_json()


@pytest.mark.parametrize("start_immediately", [False, True])
def test_maintenance_traces_use_the_real_uuid_before_the_first_flush(
    start_immediately: bool,
) -> None:
    with SessionLocal() as session:
        user = session.scalars(select(User).where(User.email == SEED_ADMIN_EMAIL)).one()
        actor = resolve_authorization(session, user, surface="BACKOFFICE")
        branch_id = session.scalars(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE)).one()
        service = AdminEquipmentMaintenanceService()
        equipment = service.create_equipment(
            session,
            current_user=actor,
            request_id=None,
            command=AdminEquipmentCreateRequest(
                branch_id=branch_id,
                code="TRACE-EQUIPMENT",
                name="Trace equipment",
                risk_level="LOW",
            ),
        )
        initial_audit = session.scalars(
            select(AuditLog).where(
                AuditLog.resource_type == "equipment_asset",
                AuditLog.resource_id == str(equipment.overview.id),
            )
        ).one()
        initial_event = session.scalars(
            select(OutboxEvent).where(
                OutboxEvent.aggregate_type == "equipment_asset",
                OutboxEvent.aggregate_id == str(equipment.overview.id),
            )
        ).one()
        assert initial_audit.source_app == initial_event.source_app == "SYSTEM"
        assert initial_audit.actor_id == initial_event.actor_id == actor.id
        assert initial_audit.branch_id == initial_event.branch_id == branch_id
        assert initial_audit.operation_id == initial_event.operation_id
        context = replace(
            OperationContext.start(SourceApp.BACKOFFICE, request_id=str(uuid4())), actor_id=actor.id
        )
        bind_operation_context(session, context)
        service.create_maintenance(
            session,
            current_user=actor,
            request_id=context.request_id,
            command=AdminMaintenanceCreateRequest(
                equipment_id=equipment.overview.id,
                description="Trace maintenance",
                maintenance_type="PREVENTIVE",
                start_immediately=start_immediately,
            ),
        )
        record = session.scalars(
            select(EquipmentMaintenanceRecord).where(
                EquipmentMaintenanceRecord.equipment_id == equipment.overview.id
            )
        ).one()
        audits = session.scalars(
            select(AuditLog).where(AuditLog.operation_id == context.operation_id)
        ).all()
        events = session.scalars(
            select(OutboxEvent).where(OutboxEvent.operation_id == context.operation_id)
        ).all()
        assert len(audits) == len(events) == (2 if start_immediately else 1)
        for audit, event in zip(audits, events, strict=True):
            assert UUID(audit.resource_id) == UUID(event.aggregate_id) == record.id
            assert audit.branch_id == event.branch_id == branch_id
            assert audit.actor_id == event.actor_id == actor.id
            assert audit.operation_id == event.operation_id == context.operation_id
