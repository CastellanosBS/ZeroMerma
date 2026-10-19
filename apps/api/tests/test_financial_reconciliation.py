"""Synthetic evidence proves cutover mechanics without claiming production approval."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Barrier
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.financial_ledger.application.reconciliation import (
    apply_financial_import_row,
    diagnose_financial_state,
    dry_run_financial_import,
)
from zeromerma_api.modules.financial_ledger.domain.money import FinancialModelError
from zeromerma_api.modules.financial_ledger.domain.reconciliation import FinancialImportManifest
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.financial_ledger.infrastructure.reconciliation_models import (
    FinancialImportManifest as ManifestRecord,
)
from zeromerma_api.modules.financial_ledger.infrastructure.reconciliation_models import (
    FinancialImportRow,
)
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import provision_test_owner
from zeromerma_api.testing.idempotency import new_idempotency_key


def _setup() -> tuple[AuthenticatedUser, FinancialImportManifest]:
    with SessionLocal() as session:
        owner = provision_test_owner(session)
        session.commit()
        user = resolve_authorization(session, owner, surface="BACKOFFICE")
        branch_id = session.scalar(select(Branch.id).where(Branch.code == "MAIN"))
    now = datetime.now(UTC)
    rows = []
    for index, amount in enumerate(("25.00", "15.00")):
        evidence = uuid4()
        rows.append(
            {
                "row_key": f"receivable-{index}",
                "idempotency_key": new_idempotency_key(),
                "treatment": "OPENING_ADJUSTMENT",
                "kind": "OPENING_OBLIGATION",
                "source_type": "OPENING_STATE",
                "source_id": evidence,
                "subject_type": "OPENING_BALANCE",
                "subject_id": uuid4(),
                "amount_due": amount,
                "occurred_at": now,
                "evidence_reference": evidence,
                "evidence_sha256": "c" * 64,
                "reason_code": "SYNTHETIC_ACCEPTANCE",
                "opening_obligation_kind": "RECEIVABLE",
            }
        )
    manifest = FinancialImportManifest.model_validate(
        {
            "manifest_id": uuid4(),
            "branch_id": branch_id,
            "source_id": "SYNTHETIC_ACCEPTANCE_ONLY",
            "source_classification": "REAL_OPERATIONAL",
            "source_authority": "closed_and_reconcilable_economic_evidence",
            "source_evidence_sha256": "a" * 64,
            "approval_reference": "synthetic-test-not-real-approval",
            "approval_evidence_sha256": "b" * 64,
            "controlled_window_reference": "ephemeral-database",
            "cutover_at": now + timedelta(seconds=1),
            "expected_row_count": 2,
            "expected_amount_due": "40.00",
            "rows": rows,
        }
    )
    return user, manifest


def _state() -> tuple[int | None, ...]:
    with SessionLocal() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                ManifestRecord,
                FinancialImportRow,
                FinancialOperation,
                FinancialEntry,
                IdempotencyRecord,
                AuditLog,
                OutboxEvent,
            )
        )


def _apply(user: AuthenticatedUser, manifest: FinancialImportManifest, index: int = 0) -> Any:
    with SessionLocal() as session:
        return apply_financial_import_row(
            session,
            current_user=user,
            manifest=manifest,
            row_key=manifest.rows[index].row_key,
            expected_manifest_sha256=manifest.digest(),
            controlled_window_confirmed=True,
        )


def test_diagnosis_and_dry_run_execute_in_database_read_only_transaction() -> None:
    _, manifest = _setup()
    before = _state()
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        diagnosis = diagnose_financial_state(session, branch_id=manifest.branch_id)
        report = dry_run_financial_import(session, manifest=manifest)
    assert diagnosis["read_only"] and not diagnosis["production_reconciliation_signed"]
    assert report["can_apply"] and report["manifest_sha256"] == manifest.digest()
    assert all(row["status"] == "READY" for row in report["rows"])
    assert not report["approval_authenticity_verified"] and _state() == before


def test_opening_obligations_resume_and_replay_with_immutable_auditable_evidence() -> None:
    user, manifest = _setup()
    first = _apply(user, manifest)
    assert first.status_code == 201 and not first.replayed
    checkpoint = _state()
    replay = _apply(user, manifest)
    assert replay.replayed and replay.payload == first.payload and _state() == checkpoint
    with SessionLocal() as session:
        report = dry_run_financial_import(session, manifest=manifest)
    assert [row["status"] for row in report["rows"]] == ["APPLIED", "READY"]
    second = _apply(user, manifest, 1)
    assert not second.replayed
    with SessionLocal() as session:
        operations = list(session.scalars(select(FinancialOperation)).all())
        assert len(operations) == 2 and sum(
            operation.amount_due for operation in operations
        ) == Decimal("40.00")
        assert session.scalar(select(func.count()).select_from(FinancialEntry)) == 0
        assert session.scalar(select(func.count()).select_from(ManifestRecord)) == 1
        progress = list(session.scalars(select(FinancialImportRow)).all())
        assert len(progress) == 2
        stored = session.get(ManifestRecord, manifest.manifest_id)
        assert stored is not None and stored.manifest_sha256 == manifest.digest()
        assert stored.evidence == manifest.model_dump(mode="json")
        for operation in operations:
            assert (
                operation.kind == "OPENING_OBLIGATION" and operation.source_type == "OPENING_STATE"
            )
            assert operation.cash_session_id is None and operation.cutover_at == manifest.cutover_at
            assert operation.source_id == operation.source_evidence_reference
            assert operation.actor_id == user.id and operation.recorded_at >= operation.occurred_at
            audit = session.scalar(
                select(AuditLog).where(
                    AuditLog.operation_id == operation.operation_id,
                    AuditLog.action == "financial_import.row_applied",
                )
            )
            event = session.scalar(
                select(OutboxEvent).where(
                    OutboxEvent.operation_id == operation.operation_id,
                    OutboxEvent.event_name == "financial_import.row_applied.v1",
                )
            )
            assert audit is not None and event is not None
            assert {key: audit.metadata_[key] for key in event.payload} == event.payload
            assert audit.metadata_["authorization"]["capabilities"] == ["cash_finance.manage"]
            assert audit.metadata_["approval_authenticity_verified"] is False
            assert (
                audit.metadata_["after"]["operation_count"]
                == audit.metadata_["before"]["operation_count"] + 1
            )
        stored.evidence = {"tampered": True}
        with pytest.raises(IntegrityError, match="immutable"):
            session.flush()
        session.rollback()


def test_interrupted_second_row_rolls_back_only_that_row_and_resumes_same_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, manifest = _setup()
    _apply(user, manifest)
    checkpoint = _state()
    original = OutboxWriter.append

    def fail_after_flush(self: Any, session: Any, **kwargs: Any) -> Any:
        result = original(self, session, **kwargs)
        if kwargs["event_name"] == "financial_import.row_applied.v1":
            session.flush()
            assert session.scalar(select(func.count()).select_from(FinancialImportRow)) == 2
            raise RuntimeError("Injected import interruption")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail_after_flush)
        with pytest.raises(RuntimeError, match="Injected import interruption"):
            _apply(user, manifest, 1)
    assert _state() == checkpoint
    resumed = _apply(user, manifest, 1)
    assert not resumed.replayed
    after = _state()
    assert _apply(user, manifest, 1).replayed and _state() == after


@pytest.mark.parametrize("reason", ["demo", "unknown", "window", "hash", "owner"])
def test_import_gates_reject_without_partial_financial_writes(reason: str) -> None:
    user, manifest = _setup()
    if reason in {"demo", "unknown"}:
        manifest = FinancialImportManifest.model_validate(
            {
                **manifest.model_dump(),
                "source_classification": "DEVELOPMENT_DEMO_TEST" if reason == "demo" else "UNKNOWN",
            }
        )
    if reason == "owner":
        from zeromerma_api.bootstrap.seed_local import SEED_USER_EMAIL
        from zeromerma_api.modules.identity.infrastructure.models import User

        with SessionLocal() as session:
            seed_user = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
            assert seed_user is not None
            user = resolve_authorization(session, seed_user, surface="BACKOFFICE")
    before = _state()
    with SessionLocal() as session, pytest.raises((FinancialModelError, HTTPException)):
        apply_financial_import_row(
            session,
            current_user=user,
            manifest=manifest,
            row_key=manifest.rows[0].row_key,
            expected_manifest_sha256="0" * 64 if reason == "hash" else manifest.digest(),
            controlled_window_confirmed=reason != "window",
        )
    assert _state() == before


def test_new_manifest_cannot_duplicate_a_cause_and_tampered_manifest_is_rejected() -> None:
    user, manifest = _setup()
    _apply(user, manifest)
    before = _state()
    changed = manifest.model_dump()
    changed["approval_reference"] = "different-evidence"
    revised = FinancialImportManifest.model_validate(changed)
    with SessionLocal() as session:
        report = dry_run_financial_import(session, manifest=revised)
    assert report["manifest_conflict"] and not report["can_apply"]
    changed["manifest_id"] = uuid4()
    changed["rows"][0]["idempotency_key"] = new_idempotency_key()
    duplicate = FinancialImportManifest.model_validate(changed)
    with SessionLocal() as session:
        report = dry_run_financial_import(session, manifest=duplicate)
    assert not report["can_apply"] and report["rows"][0]["status"] == "REJECTED"
    with pytest.raises(FinancialModelError, match="Dry-run"):
        _apply(user, duplicate)
    assert _state() == before


@pytest.mark.parametrize("difference", ["none", "closed_session", "amount", "missing_source"])
def test_backfill_requires_exact_real_causality_and_never_changes_closed_history(
    client: TestClient, difference: str
) -> None:
    from test_financial_producers import _setup as setup_operating_context

    from zeromerma_api.modules.cash.infrastructure.models import CashSession
    from zeromerma_api.modules.payments.infrastructure.models import OperationalPayment

    _, context = setup_operating_context(client, "payment")
    user, opening_manifest = _setup()
    now = datetime.now(UTC)
    with SessionLocal() as session:
        cash = session.get(CashSession, UUID(context["cash_session_id"]))
        assert cash is not None
        source = OperationalPayment(
            id=uuid4(),
            branch_id=cash.branch_id,
            workstation_id=cash.workstation_id,
            created_by_user_id=cash.user_id,
            active_cash_session_id=cash.id,
            payee_name="Synthetic causal source",
            concept="Verified source adapter fixture",
            payment_method_code="CASH",
            currency_code="MXN",
            total_amount=Decimal("10.00"),
            cash_amount=Decimal("10.00"),
            non_cash_amount=Decimal("0.00"),
            status="COMMITTED",
            created_at_utc=now,
            committed_at_utc=now,
        )
        session.add(source)
        if difference == "closed_session":
            cash.status = "CLOSED"
        session.commit()
        source_id, cash_id, workstation_id = source.id, cash.id, cash.workstation_id
        original = {
            column.name: getattr(source, column.name) for column in source.__table__.columns
        }
    amount = "20.00" if difference == "amount" else "10.00"
    evidence = uuid4()
    payload = opening_manifest.model_dump()
    payload.update(
        cutover_at=now + timedelta(seconds=1),
        expected_row_count=1,
        expected_amount_due=amount,
        rows=[
            {
                "row_key": "verified-operating-payment",
                "idempotency_key": new_idempotency_key(),
                "treatment": "BACKFILL",
                "kind": "OPERATIONAL_PAYMENT",
                "source_type": "OPERATIONAL_PAYMENT",
                "source_id": uuid4() if difference == "missing_source" else source_id,
                "subject_type": "OPERATIONAL_PAYMENT",
                "subject_id": source_id,
                "amount_due": amount,
                "occurred_at": now,
                "cash_session_id": cash_id,
                "workstation_id": workstation_id,
                "evidence_reference": evidence,
                "evidence_sha256": "d" * 64,
                "reason_code": "CAUSALLY_VERIFIED_SOURCE",
                "legs": [
                    {
                        "leg_key": "payment",
                        "payment_method": "CASH",
                        "direction": "OUT",
                        "amount": amount,
                    }
                ],
            }
        ],
    )
    manifest = FinancialImportManifest.model_validate(payload)
    before = _state()
    with SessionLocal() as session:
        report = dry_run_financial_import(session, manifest=manifest)
    if difference != "none":
        assert not report["can_apply"] and report["rows"][0]["status"] == "REJECTED"
        with pytest.raises(FinancialModelError, match="Dry-run"):
            _apply(user, manifest)
        assert _state() == before
    else:
        assert report["can_apply"]
        result = _apply(user, manifest)
        after = _state()
        assert _apply(user, manifest).payload == result.payload and _state() == after
        with SessionLocal() as session:
            entry = session.scalar(
                select(FinancialEntry).where(
                    FinancialEntry.financial_operation_id
                    == UUID(result.payload["financial_operation_id"])
                )
            )
            assert (
                entry is not None and entry.amount == Decimal("10.00") and entry.direction == "OUT"
            )
            assert entry.cash_session_id == cash_id and entry.workstation_id == workstation_id
    with SessionLocal() as session:
        unchanged = session.get(OperationalPayment, source_id)
        assert unchanged is not None
        assert {
            column.name: getattr(unchanged, column.name) for column in unchanged.__table__.columns
        } == original


@pytest.mark.parametrize("amount", ["0.00", "50.00"])
def test_evidenced_cash_opening_transformation_matches_actual_session_and_no_zero_entry(
    amount: str,
) -> None:
    from zeromerma_api.bootstrap.seed_local import SEED_USER_EMAIL, SEED_WORKSTATION_CODE
    from zeromerma_api.modules.branches.infrastructure.models import Workstation
    from zeromerma_api.modules.cash.infrastructure.models import CashSession
    from zeromerma_api.modules.identity.infrastructure.models import User

    user, baseline = _setup()
    now, evidence = datetime.now(UTC), uuid4()
    with SessionLocal() as session:
        workstation = session.scalar(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
        )
        operator_id = session.scalar(select(User.id).where(User.email == SEED_USER_EMAIL))
        assert workstation is not None and operator_id is not None
        cash = CashSession(
            id=uuid4(),
            branch_id=baseline.branch_id,
            workstation_id=workstation.id,
            user_id=operator_id,
            status="OPEN",
            opening_amount=Decimal(amount),
            opened_at=now,
        )
        session.add(cash)
        session.commit()
        cash_id, workstation_id = cash.id, workstation.id
    payload = baseline.model_dump()
    payload.update(
        expected_row_count=1,
        expected_amount_due=amount,
        cutover_at=now + timedelta(seconds=1),
        rows=[
            {
                "row_key": "verified-opening",
                "idempotency_key": new_idempotency_key(),
                "treatment": "OPENING_ADJUSTMENT",
                "kind": "CASH_OPENING",
                "source_type": "OPENING_STATE",
                "source_id": evidence,
                "subject_type": "CASH_SESSION",
                "subject_id": cash_id,
                "cash_session_id": cash_id,
                "workstation_id": workstation_id,
                "amount_due": amount,
                "occurred_at": now,
                "evidence_reference": evidence,
                "evidence_sha256": "c" * 64,
                "reason_code": "VERIFIED_OPENING_COUNT",
                "legs": [
                    {
                        "leg_key": "opening",
                        "payment_method": "CASH",
                        "direction": "IN",
                        "amount": amount,
                        "tendered_amount": amount,
                    }
                ]
                if Decimal(amount) > 0
                else [],
            }
        ],
    )
    manifest = FinancialImportManifest.model_validate(payload)
    _apply(user, manifest)
    with SessionLocal() as session:
        operation = session.scalars(select(FinancialOperation)).one()
        entries = list(session.scalars(select(FinancialEntry)).all())
        assert operation.kind == "CASH_OPENING" and operation.source_type == "OPENING_STATE"
        assert operation.cash_session_id == cash_id and operation.amount_due == Decimal(amount)
        assert sum((entry.amount for entry in entries), Decimal("0.00")) == Decimal(amount)
        assert len(entries) == int(Decimal(amount) > 0)
        report = diagnose_financial_state(session, branch_id=manifest.branch_id)
        assert not any(item["source_type"] == "CASH_SESSION" for item in report["differences"])


def test_two_distinct_rows_of_one_manifest_serialize_without_lost_progress() -> None:
    user, manifest = _setup()
    barrier = Barrier(2)

    def submit(index: int) -> Any:
        barrier.wait(timeout=5)
        return _apply(user.model_copy(deep=True), manifest, index)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(submit, (0, 1)))
    assert all(result.status_code == 201 and not result.replayed for result in results)
    with SessionLocal() as session:
        assert session.scalar(select(func.count()).select_from(ManifestRecord)) == 1
        assert session.scalar(select(func.count()).select_from(FinancialImportRow)) == 2
        report = dry_run_financial_import(session, manifest=manifest)
        assert report["applied_row_count"] == 2 and report["applied_amount_due"] == "40.00"
