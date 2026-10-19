"""Standalone administrative owners roll back failures before their Session is reused."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.bootstrap.seed_local import (
    SEED_ADMIN_EMAIL,
    SEED_BRANCH_CODE,
    SEED_PRODUCT_CLASS_PAN_DULCE_CODE,
    SEED_PRODUCT_COCA_355_CODE,
)
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.application.admin_schemas import (
    AdminPriceUpdateRequest,
    AdminProductCreateRequest,
)
from zeromerma_api.modules.catalog.application.admin_services import (
    AdminPriceCatalogService,
    AdminProductCatalogService,
    AdminProductValidationError,
)
from zeromerma_api.modules.catalog.infrastructure.models import Product, ProductClass
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.identity.infrastructure.models import User
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.modules.quality.application.cleaning_schemas import (
    AdminCleaningChecklistItemInput,
    AdminCleaningLogCreateRequest,
)
from zeromerma_api.modules.quality.application.cleaning_services import AdminCleaningLogService
from zeromerma_api.modules.quality.application.equipment_schemas import AdminEquipmentCreateRequest
from zeromerma_api.modules.quality.application.equipment_services import (
    AdminEquipmentMaintenanceService,
)
from zeromerma_api.modules.quality.application.incident_schemas import AdminIncidentCreateRequest
from zeromerma_api.modules.quality.application.incident_services import AdminIncidentService
from zeromerma_api.modules.quality.application.sanitary_schemas import (
    AdminSanitaryChecklistItemInput,
    AdminSanitaryVerificationCreateRequest,
)
from zeromerma_api.modules.quality.application.sanitary_services import (
    AdminSanitaryVerificationService,
)
from zeromerma_api.modules.quality.domain.exceptions import (
    CleaningLogValidationError,
    EquipmentMaintenanceValidationError,
    IncidentValidationError,
    SanitaryVerificationValidationError,
)
from zeromerma_api.modules.quality.infrastructure.models import (
    CleaningLog,
    CleaningLogChecklistItem,
    EquipmentAsset,
    QualityIncident,
    SanitaryVerification,
    SanitaryVerificationChecklistItem,
)
from zeromerma_api.modules.reports.application.admin_services import AdminReportService
from zeromerma_api.testing.authorization import provision_test_owner


def _actor(session: Session) -> AuthenticatedUser:
    user = session.scalars(select(User).where(User.email == SEED_ADMIN_EMAIL)).one()
    return resolve_authorization(session, user, surface="BACKOFFICE")


def _product_command(session: Session, *, code: str = "TX-BOUNDARY-PRODUCT"):
    product = session.scalars(
        select(Product).where(Product.code == SEED_PRODUCT_COCA_355_CODE)
    ).one()
    return AdminProductCreateRequest(
        code=code,
        name="Transaction boundary product",
        product_class_id=product.product_class_id,
        unit_price=Decimal("25.00"),
    )


def _counts(*models: type[Any]) -> tuple[int, ...]:
    with SessionLocal() as independent:
        return tuple(
            independent.scalar(select(func.count()).select_from(model)) for model in models
        )


def _assert_reusable(session: Session) -> None:
    assert session.is_active
    assert not session.in_transaction()
    assert not session.new and not session.dirty and not session.deleted
    assert session.scalar(select(1)) == 1


def _fail_after(original: Callable[..., Any]) -> Callable[..., Any]:
    def fail(*args: Any, **kwargs: Any) -> Any:
        original(*args, **kwargs)
        raise RuntimeError("Injected transaction boundary failure")

    return fail


@pytest.mark.parametrize("stage", ["before_flush", "after_flush", "audit", "outbox"])
def test_catalog_failure_rolls_back_business_and_traces_before_session_reuse(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    baseline = _counts(Product, AuditLog, OutboxEvent)
    with SessionLocal() as session:
        actor = _actor(session)
        command = _product_command(session)
        service = AdminProductCatalogService()
        with monkeypatch.context() as patch:
            if stage == "audit":
                patch.setattr(
                    service._audit_recorder, "record", _fail_after(service._audit_recorder.record)
                )
            elif stage == "outbox":
                patch.setattr(
                    service._outbox_writer, "append", _fail_after(service._outbox_writer.append)
                )

            def fail_flush(*_args: Any) -> None:
                raise RuntimeError("Injected transaction boundary failure")

            flush_event = "before_flush" if stage == "before_flush" else "after_flush_postexec"
            if stage.endswith("flush"):
                event.listen(session, flush_event, fail_flush)
            try:
                with pytest.raises(RuntimeError, match="Injected transaction boundary failure"):
                    service.create_product(
                        session, current_user=actor, command=command, request_id="admin-boundary"
                    )
            finally:
                if stage.endswith("flush"):
                    event.remove(session, flush_event, fail_flush)

        _assert_reusable(session)
        assert _counts(Product, AuditLog, OutboxEvent) == baseline
        created = service.create_product(
            session, current_user=actor, command=command, request_id="admin-boundary-retry"
        )
        assert created.code == command.code
    assert _counts(Product, AuditLog, OutboxEvent) == tuple(value + 1 for value in baseline)


def test_unrelated_real_outbox_integrity_failure_is_not_a_catalog_validation_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = _counts(Product, AuditLog, OutboxEvent)
    with SessionLocal() as session:
        actor, command = _actor(session), _product_command(session)
        service = AdminProductCatalogService()
        original = service._outbox_writer.append

        def invalid_event(*args: Any, **kwargs: Any) -> OutboxEvent:
            record = original(*args, **kwargs)
            record.event_name = None
            return record

        with monkeypatch.context() as patch:
            patch.setattr(service._outbox_writer, "append", invalid_event)
            with pytest.raises(IntegrityError) as caught:
                service.create_product(
                    session, current_user=actor, command=command, request_id="outbox-integrity"
                )
        assert caught.value.orig.sqlstate == "23502"
        assert caught.value.orig.diag.table_name == "outbox_events"
        _assert_reusable(session)
        assert _counts(Product, AuditLog, OutboxEvent) == baseline
        service.create_product(session, current_user=actor, command=command, request_id=None)
    assert _counts(Product, AuditLog, OutboxEvent) == tuple(value + 1 for value in baseline)


def test_actual_catalog_unique_conflict_preserves_domain_error_and_cleans_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = _counts(Product, AuditLog, OutboxEvent)
    with SessionLocal() as session:
        actor = _actor(session)
        service = AdminProductCatalogService()
        command = _product_command(session, code=SEED_PRODUCT_COCA_355_CODE)
        # Simulate the race after a successful preflight: PostgreSQL must decide uniqueness.
        with monkeypatch.context() as patch:
            patch.setattr(service, "_ensure_unique_code", lambda *_args, **_kwargs: None)
            with pytest.raises(AdminProductValidationError) as caught:
                service.create_product(
                    session, current_user=actor, command=command, request_id=None
                )
        error = caught.value.__cause__
        assert isinstance(error, IntegrityError)
        assert error.orig.sqlstate == "23505"
        assert error.orig.diag.constraint_name == "uq_products_code"
        _assert_reusable(session)
        assert _counts(Product, AuditLog, OutboxEvent) == baseline
        service.create_product(
            session, current_user=actor, command=_product_command(session), request_id=None
        )


@pytest.mark.parametrize("entity_type", ["product", "class"])
def test_nested_price_delegate_has_one_commit_and_rolls_back_failed_traces(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, entity_type: str
) -> None:
    baseline = _counts(AuditLog, OutboxEvent)
    with SessionLocal() as session:
        actor = _actor(session)
        entity = (
            session.scalars(select(Product).where(Product.code == SEED_PRODUCT_COCA_355_CODE)).one()
            if entity_type == "product"
            else session.scalars(
                select(ProductClass).where(ProductClass.code == SEED_PRODUCT_CLASS_PAN_DULCE_CODE)
            ).one()
        )
        entity_id = entity.id
        field = "unit_price" if entity_type == "product" else "class_capture_unit_price"
        previous = getattr(entity, field)
        commits: list[bool] = []

        def committed(_session: Session) -> None:
            commits.append(True)

        event.listen(session, "after_commit", committed)
        try:
            with monkeypatch.context() as patch:
                patch.setattr(OutboxWriter, "append", _fail_after(OutboxWriter.append))
                with pytest.raises(RuntimeError, match="Injected transaction boundary failure"):
                    AdminPriceCatalogService().update_price(
                        session,
                        current_user=actor,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        command=AdminPriceUpdateRequest(price=Decimal("33.25")),
                        request_id=None,
                    )
            _assert_reusable(session)
            assert commits == []
            assert getattr(session.get(type(entity), entity_id), field) == previous
            assert _counts(AuditLog, OutboxEvent) == baseline
            AdminPriceCatalogService().update_price(
                session,
                current_user=actor,
                entity_type=entity_type,
                entity_id=entity_id,
                command=AdminPriceUpdateRequest(price=Decimal("33.25")),
                request_id=None,
            )
            assert commits == [True]
            assert getattr(session.get(type(entity), entity_id), field) == Decimal("33.25")
        finally:
            event.remove(session, "after_commit", committed)
    assert _counts(AuditLog, OutboxEvent) == tuple(value + 1 for value in baseline)


@pytest.mark.parametrize("failure", ["known_unique", "unexpected_not_null"])
def test_quality_flush_error_cleans_session_and_only_translates_known_constraint(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    with SessionLocal() as session:
        actor = _actor(session)
        branch_id = session.scalars(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE)).one()
        service = AdminIncidentService()
        command = AdminIncidentCreateRequest(
            branch_id=branch_id,
            description="Transaction boundary incident",
            incident_type="SANITATION_ISSUE",
            severity="LOW",
            source_type="MANUAL",
            title="Boundary incident",
        )
        existing = service.create_incident(
            session, current_user=actor, command=command, request_id=None
        )
        baseline = _counts(QualityIncident, AuditLog, OutboxEvent)
        invalid_folio = existing.overview.folio if failure == "known_unique" else None
        with monkeypatch.context() as patch:
            patch.setattr(service, "_generate_folio", lambda _session: invalid_folio)
            error_type = IncidentValidationError if failure == "known_unique" else IntegrityError
            with pytest.raises(error_type) as caught:
                service.create_incident(
                    session, current_user=actor, command=command, request_id=None
                )
        error = caught.value.__cause__ if failure == "known_unique" else caught.value
        assert isinstance(error, IntegrityError)
        assert error.orig.sqlstate == ("23505" if failure == "known_unique" else "23502")
        if failure == "known_unique":
            assert error.orig.diag.constraint_name == "uq_quality_incidents_folio"
        _assert_reusable(session)
        assert _counts(QualityIncident, AuditLog, OutboxEvent) == baseline
        recovered = service.create_incident(
            session, current_user=actor, command=command, request_id=None
        )
        assert recovered.overview.id != existing.overview.id
    assert _counts(QualityIncident, AuditLog, OutboxEvent) == tuple(value + 1 for value in baseline)


@pytest.mark.parametrize("family", ["cleaning", "sanitary", "equipment"])
def test_quality_create_unique_constraint_at_first_flush_is_classified_and_rolled_back(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, family: str
) -> None:
    with SessionLocal() as session:
        actor = _actor(session)
        branch_id = session.scalars(select(Branch.id).where(Branch.code == SEED_BRANCH_CODE)).one()
        service: Any
        command: Any
        create: Callable[..., Any]
        models: tuple[type[Any], ...]
        if family == "cleaning":
            service = AdminCleaningLogService()
            command = AdminCleaningLogCreateRequest(
                area_name="Boundary preparation area",
                branch_id=branch_id,
                checklist_items=[AdminCleaningChecklistItemInput(label="Clean preparation area")],
                responsible_user_id=actor.id,
                risk_level="LOW",
                scheduled_at=datetime.now(UTC),
                task_name="Boundary cleaning task",
            )
            create = service.create_log
            models = (CleaningLog, CleaningLogChecklistItem, AuditLog, OutboxEvent)
            error_type = CleaningLogValidationError
            constraint = "uq_cleaning_logs_folio"
        elif family == "sanitary":
            service = AdminSanitaryVerificationService()
            command = AdminSanitaryVerificationCreateRequest(
                area_name="Boundary preparation area",
                branch_id=branch_id,
                checklist_results=[
                    AdminSanitaryChecklistItemInput(
                        label="Check preparation area", risk_level="LOW"
                    )
                ],
                inspector_user_id=actor.id,
                risk_level="LOW",
                scheduled_at=datetime.now(UTC),
                template_name="Boundary sanitary checklist",
            )
            create = service.create_verification
            models = (
                SanitaryVerification,
                SanitaryVerificationChecklistItem,
                AuditLog,
                OutboxEvent,
            )
            error_type = SanitaryVerificationValidationError
            constraint = "uq_sanitary_verifications_folio"
        else:
            service = AdminEquipmentMaintenanceService()
            command = AdminEquipmentCreateRequest(
                branch_id=branch_id,
                code="TX-BOUNDARY-EQUIPMENT",
                name="Boundary equipment",
                risk_level="LOW",
            )
            create = service.create_equipment
            models = (EquipmentAsset, AuditLog, OutboxEvent)
            error_type = EquipmentMaintenanceValidationError
            constraint = "uq_equipment_assets_code"

        existing = create(session, current_user=actor, command=command, request_id=None)
        baseline = _counts(*models)
        with monkeypatch.context() as patch:
            if family == "equipment":
                # A concurrent writer can win after preflight; the real INSERT decides uniqueness.
                patch.setattr(service, "_ensure_unique_code", lambda *_args, **_kwargs: None)
            else:
                patch.setattr(service, "_generate_folio", lambda _session: existing.overview.folio)
            with pytest.raises(error_type) as caught:
                create(session, current_user=actor, command=command, request_id=None)

        error = caught.value.__cause__
        assert isinstance(error, IntegrityError)
        assert error.orig.sqlstate == "23505"
        assert error.orig.diag.constraint_name == constraint
        _assert_reusable(session)
        # Committing the reused Session cannot resurrect the failed create or its traces.
        session.commit()
        assert _counts(*models) == baseline
        if family == "equipment":
            command = command.model_copy(update={"code": "TX-BOUNDARY-EQUIPMENT-RETRY"})
        recovered = create(session, current_user=actor, command=command, request_id=None)
        assert recovered.overview.id != existing.overview.id
    assert _counts(*models) == tuple(value + 1 for value in baseline)


def test_report_export_audit_failure_does_not_leak_into_reused_session(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    with SessionLocal() as session:
        owner = provision_test_owner(session)
        session.commit()
        actor = resolve_authorization(session, owner, surface="BACKOFFICE")
        baseline = _counts(AuditLog)
        bind_authorization_scope(
            session,
            user=actor,
            capabilities=("reports.export",),
            mutation=True,
            surface="BACKOFFICE",
        )
        service = AdminReportService()
        arguments = {
            "current_user": actor,
            "report_code": "user_access_summary",
            "filters": {},
            "export_format": "json",
            "request_id": None,
        }
        with monkeypatch.context() as patch:
            patch.setattr(
                service._audit_recorder, "record", _fail_after(service._audit_recorder.record)
            )
            with pytest.raises(RuntimeError, match="Injected transaction boundary failure"):
                service.export_report(session, **arguments)
        _assert_reusable(session)
        assert _counts(AuditLog) == baseline
        assert service.export_report(session, **arguments).report_code == "user_access_summary"
    assert _counts(AuditLog) == (baseline[0] + 1,)
