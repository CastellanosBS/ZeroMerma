"""Synthetic acceptance for opening, immutable evidence and resumable projection rebuild."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.catalog.infrastructure.models import Product
from zeromerma_api.modules.idempotency.infrastructure.models import IdempotencyRecord
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.inventory.application.reconciliation import (
    apply_inventory_reconciliation_row,
    diagnose_inventory_state,
    dry_run_inventory_reconciliation,
)
from zeromerma_api.modules.inventory.domain.exceptions import InventoryValidationError
from zeromerma_api.modules.inventory.domain.reconciliation import InventoryReconciliationManifest
from zeromerma_api.modules.inventory.infrastructure.models import (
    InventoryBalance,
    InventoryMovement,
)
from zeromerma_api.modules.inventory.infrastructure.reconciliation_models import (
    InventoryReconciliationManifest as ManifestRecord,
)
from zeromerma_api.modules.inventory.infrastructure.reconciliation_models import (
    InventoryReconciliationRow,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_api.testing.authorization import provision_test_owner
from zeromerma_api.testing.idempotency import new_idempotency_key


def _setup() -> tuple[AuthenticatedUser, InventoryReconciliationManifest]:
    with SessionLocal() as session:
        owner = provision_test_owner(session)
        session.commit()
        user = resolve_authorization(session, owner, surface="BACKOFFICE")
        branch_id = session.scalar(select(Branch.id).where(Branch.code == "MAIN"))
        products = list(
            session.scalars(
                select(Product)
                .where(Product.is_inventory_tracked.is_(True))
                .order_by(Product.id)
                .limit(2)
            )
        )
        rows = [
            {
                "row_key": f"physical-count-{index}",
                "idempotency_key": new_idempotency_key(),
                "action": "OPENING",
                "product_id": product.id,
                "location_code": "BACKROOM",
                "unit_of_measure": product.unit_of_measure,
                "quantity": "10.000",
                "inventory_value": "25.00000000",
                "evidence_reference": "synthetic-count-sheet",
                "evidence_sha256": "c" * 64,
                "reason": "Synthetic opening acceptance",
            }
            for index, product in enumerate(products)
        ]
    manifest = InventoryReconciliationManifest.model_validate(
        {
            "manifest_id": uuid4(),
            "branch_id": branch_id,
            "source_id": "SYNTHETIC_ACCEPTANCE_ONLY",
            "source_classification": "REAL_OPERATIONAL",
            "source_evidence_sha256": "a" * 64,
            "approval_reference": "synthetic-not-real-production-approval",
            "approval_evidence_sha256": "b" * 64,
            "controlled_window_reference": "ephemeral-database",
            "cutover_at": datetime.now(UTC) - timedelta(seconds=1),
            "expected_row_count": len(rows),
            "rows": rows,
        }
    )
    return user, manifest


def _apply(
    user: AuthenticatedUser, manifest: InventoryReconciliationManifest, index: int = 0
) -> Any:
    with SessionLocal() as session:
        return apply_inventory_reconciliation_row(
            session,
            current_user=user,
            manifest=manifest,
            row_key=manifest.rows[index].row_key,
            expected_manifest_sha256=manifest.digest(),
            controlled_window_confirmed=True,
        )


def _counts() -> tuple[int | None, ...]:
    with SessionLocal() as session:
        return tuple(
            session.scalar(select(func.count()).select_from(model))
            for model in (
                InventoryBalance,
                InventoryMovement,
                ManifestRecord,
                InventoryReconciliationRow,
                IdempotencyRecord,
                AuditLog,
                OutboxEvent,
            )
        )


def test_read_only_diagnosis_opening_resume_replay_and_immutable_approval_evidence() -> None:
    user, manifest = _setup()
    before = _counts()
    with SessionLocal() as session:
        session.execute(text("SET TRANSACTION READ ONLY"))
        report = dry_run_inventory_reconciliation(session, manifest=manifest)
        assert report["can_apply"] and not report["approval_authenticity_verified"]
        assert diagnose_inventory_state(session, branch_id=manifest.branch_id)["read_only"]
    assert _counts() == before
    first = _apply(user, manifest)
    checkpoint = _counts()
    replay = _apply(user, manifest)
    assert replay.replayed and first.payload == replay.payload and _counts() == checkpoint
    with SessionLocal() as session:
        report = dry_run_inventory_reconciliation(session, manifest=manifest)
        assert [row["status"] for row in report["rows"]] == ["APPLIED", "READY"]
    _apply(user, manifest, 1)
    with SessionLocal() as session:
        balances = list(session.scalars(select(InventoryBalance)))
        assert len(balances) == 2
        assert all(item.quantity_on_hand == 10 and item.inventory_value == 25 for item in balances)
        assert (
            diagnose_inventory_state(session, branch_id=manifest.branch_id)["difference_count"] == 0
        )
        for row in session.scalars(select(InventoryReconciliationRow)):
            assert row.reconciliation["approval_authenticity_verified"] is False
            assert session.scalar(
                select(AuditLog.id).where(AuditLog.operation_id == row.idempotency_record_id)
            )
            assert session.scalar(
                select(OutboxEvent.id).where(OutboxEvent.operation_id == row.idempotency_record_id)
            )
        stored = session.get(ManifestRecord, manifest.manifest_id)
        assert stored is not None and stored.evidence == manifest.model_dump(mode="json")
        stored.evidence = {"tampered": True}
        with pytest.raises(IntegrityError, match="immutable"):
            session.flush()


def test_rebuild_restores_projection_without_fabricating_or_changing_movements() -> None:
    user, opening = _setup()
    _apply(user, opening)
    with SessionLocal() as session:
        original = session.scalars(select(InventoryMovement)).one()
        original_id, original_quantity, original_cost = (
            original.id,
            original.quantity,
            original.total_cost,
        )
        balance = session.scalars(select(InventoryBalance)).one()
        balance.quantity_on_hand = Decimal(8)
        balance.inventory_value = Decimal(23)
        session.commit()
        diagnosed = diagnose_inventory_state(session, branch_id=opening.branch_id)["keys"][0]
        assert not diagnosed["matches"] and diagnosed["rebuildable"]
    row = opening.rows[0].model_dump()
    row.update(
        action="REBUILD",
        quantity=None,
        inventory_value=None,
        idempotency_key=new_idempotency_key(),
        expected_ledger_sha256=diagnosed["ledger_sha256"],
    )
    rebuild = InventoryReconciliationManifest.model_validate(
        {**opening.model_dump(), "manifest_id": uuid4(), "expected_row_count": 1, "rows": [row]}
    )
    result = _apply(user, rebuild)
    assert result.payload["inventory_movement_id"] is None
    assert _apply(user, rebuild).replayed
    with SessionLocal() as session:
        original = session.scalars(select(InventoryMovement)).one()
        assert (original.id, original.quantity, original.total_cost) == (
            original_id,
            original_quantity,
            original_cost,
        )
        balance = session.scalars(select(InventoryBalance)).one()
        assert balance.quantity_on_hand == 10 and balance.inventory_value == 25


def test_opening_interruption_rolls_back_ledger_projection_and_evidence_and_resumes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, manifest = _setup()
    _apply(user, manifest)
    checkpoint = _counts()
    original = OutboxWriter.append

    def fail(self: Any, session: Any, **kwargs: Any) -> Any:
        original(self, session, **kwargs)
        session.flush()
        raise RuntimeError("Injected inventory reconciliation interruption")

    with monkeypatch.context() as patch:
        patch.setattr(OutboxWriter, "append", fail)
        with pytest.raises(RuntimeError, match="Injected"):
            _apply(user, manifest, 1)
    assert _counts() == checkpoint
    assert not _apply(user, manifest, 1).replayed


@pytest.mark.parametrize(
    "reason", ["demo", "known_demo", "unknown", "hash", "window", "owner", "uom"]
)
def test_untrusted_or_unauthorized_manifest_never_mutates_inventory(reason: str) -> None:
    user, manifest = _setup()
    data = manifest.model_dump()
    if reason in {"demo", "unknown"}:
        data["source_classification"] = "DEVELOPMENT_DEMO_TEST" if reason == "demo" else "UNKNOWN"
    elif reason == "known_demo":
        data["source_id"] = "PG-ZM-CURRENT"
    elif reason == "uom":
        data["rows"][0]["unit_of_measure"] = "INVALID_UNIT"
    elif reason == "owner":
        user = user.model_copy(update={"is_superadministrator": False})
        # Refresh authoritative ownership rather than trusting a caller-supplied bool.
        from zeromerma_api.modules.identity.infrastructure.models import User

        with SessionLocal() as session:
            other = session.scalar(select(User).where(User.id != user.id))
            assert other is not None
            user = resolve_authorization(session, other, surface="BACKOFFICE")
    manifest = InventoryReconciliationManifest.model_validate(data)
    checkpoint = _counts()
    with SessionLocal() as session, pytest.raises((InventoryValidationError, HTTPException)):
        apply_inventory_reconciliation_row(
            session,
            current_user=user,
            manifest=manifest,
            row_key=manifest.rows[0].row_key,
            expected_manifest_sha256="0" * 64 if reason == "hash" else manifest.digest(),
            controlled_window_confirmed=reason != "window",
        )
    assert _counts() == checkpoint


def test_unexplained_balance_is_rejected_instead_of_becoming_opening_authority() -> None:
    user, manifest = _setup()
    row = manifest.rows[0]
    with SessionLocal() as session:
        session.add(
            InventoryBalance(
                product_id=row.product_id,
                branch_id=manifest.branch_id,
                location_code=row.location_code,
                quantity_on_hand=Decimal(99),
            )
        )
        session.commit()
    before = _counts()
    with SessionLocal() as session:
        diagnosis = diagnose_inventory_state(session, branch_id=manifest.branch_id)
        assert diagnosis["difference_count"] == 1 and diagnosis["unrebuildable_count"] == 1
    with pytest.raises(InventoryValidationError, match="empty stock"):
        _apply(user, manifest)
    assert _counts() == before


def test_lot_projection_rebuild_uses_immutable_allocations_and_rejects_stale_ledger_hash() -> None:
    user, manifest = _setup()
    row = manifest.rows[0].model_dump()
    with SessionLocal() as session:
        product = session.get(Product, row["product_id"])
        assert product is not None
        product.lot_tracking_enabled = True
        product.expiry_required = True
        session.commit()
    row["lots"] = [
        {
            "lot_code": "OPENING-LOT",
            "quantity": "10.000",
            "expires_at": datetime.now(UTC) + timedelta(days=30),
        }
    ]
    manifest = InventoryReconciliationManifest.model_validate(
        {**manifest.model_dump(), "expected_row_count": 1, "rows": [row]}
    )
    _apply(user, manifest)
    from zeromerma_api.modules.inventory.infrastructure.lot_models import InventoryLotBalance

    with SessionLocal() as session:
        lot_balance = session.scalars(select(InventoryLotBalance)).one()
        lot_balance.quantity_on_hand = Decimal(7)
        session.commit()
        state = diagnose_inventory_state(session, branch_id=manifest.branch_id)["keys"][0]
        assert not state["matches"] and state["rebuildable"]
    row.update(
        action="REBUILD",
        quantity=None,
        inventory_value=None,
        lots=[],
        idempotency_key=new_idempotency_key(),
        expected_ledger_sha256=state["ledger_sha256"],
    )
    rebuild = InventoryReconciliationManifest.model_validate(
        {**manifest.model_dump(), "manifest_id": uuid4(), "rows": [row]}
    )
    _apply(user, rebuild)
    with SessionLocal() as session:
        assert session.scalars(select(InventoryLotBalance)).one().quantity_on_hand == 10
    from zeromerma_api.testing.inventory import seed_test_inventory

    with SessionLocal() as session:
        seed_test_inventory(
            session,
            branch_id=manifest.branch_id,
            actor_user_id=user.id,
            product_quantities={row["product_id"]: Decimal(1)},
            location_code="BACKROOM",
            fixture_reference="Concurrent stock change after reviewed dry run",
        )
    stale = InventoryReconciliationManifest.model_validate(
        {
            **rebuild.model_dump(),
            "manifest_id": uuid4(),
            "rows": [{**row, "idempotency_key": new_idempotency_key()}],
        }
    )
    before = _counts()
    with pytest.raises(InventoryValidationError, match="unchanged"):
        _apply(user, stale)
    assert _counts() == before
