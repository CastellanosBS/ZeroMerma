"""Read-only diagnosis and evidence-gated, resumable financial transformations."""

from __future__ import annotations

import json
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.modules.audit.application.service import AuditRecorder
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.discounts.infrastructure.models import OperationalDiscount
from zeromerma_api.modules.financial_ledger.application.recording import (
    FinancialCommandScope,
    create_financial_operation,
    record_confirmed_entry,
)
from zeromerma_api.modules.financial_ledger.domain.constants import (
    EntryState,
    EvidenceKind,
    ExecutionMode,
    OperationKind,
    PaymentMethod,
)
from zeromerma_api.modules.financial_ledger.domain.models import (
    FinancialEntrySnapshot,
    FinancialOperationSnapshot,
)
from zeromerma_api.modules.financial_ledger.domain.money import (
    ZERO,
    FinancialModelError,
    financial_calculation,
)
from zeromerma_api.modules.financial_ledger.domain.reconciliation import (
    FinancialImportManifest,
    ImportRow,
    row_digest,
)
from zeromerma_api.modules.financial_ledger.domain.rules import validate_entry, validate_operation
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
from zeromerma_api.modules.idempotency.application.context import execution
from zeromerma_api.modules.idempotency.application.schemas import (
    CommandContext,
    CommandResult,
    IdempotencyResult,
    ResponsePolicy,
)
from zeromerma_api.modules.idempotency.application.service import IdempotencyExecutor
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.schemas import AuthenticatedUser
from zeromerma_api.modules.orders.infrastructure.models import CustomerOrder, CustomerOrderPayment
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.payments.infrastructure.models import OperationalPayment
from zeromerma_api.modules.sales.infrastructure.models import Sale, SalePayment


class ImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_id: UUID
    row_key: str
    manifest_sha256: str
    row_sha256: str
    financial_operation_id: UUID
    financial_entry_ids: list[UUID]
    before_sha256: str
    after_sha256: str


def _digest(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


@financial_calculation
def _financial_snapshot(session: Session, branch_id: UUID) -> dict[str, Any]:
    operations = list(
        session.execute(
            select(FinancialOperation.id, FinancialOperation.kind, FinancialOperation.amount_due)
            .where(FinancialOperation.branch_id == branch_id)
            .order_by(FinancialOperation.id)
        )
    )
    entries = list(
        session.execute(
            select(
                FinancialEntry.id,
                FinancialEntry.state,
                FinancialEntry.payment_method_code,
                FinancialEntry.direction,
                FinancialEntry.amount,
            )
            .where(FinancialEntry.branch_id == branch_id)
            .order_by(FinancialEntry.id)
        )
    )
    totals: dict[str, Decimal] = {}
    for _id, state, method, direction, amount in entries:
        if state == "CONFIRMED":
            key = f"{method}_{direction}"
            totals[key] = totals.get(key, ZERO) + amount
    return {
        "operation_count": len(operations),
        "entry_count": len(entries),
        "confirmed_totals": {key: str(value) for key, value in sorted(totals.items())},
        "sha256": _digest(
            {
                "operations": [tuple(row) for row in operations],
                "entries": [tuple(row) for row in entries],
            }
        ),
    }


def diagnose_financial_state(session: Session, *, branch_id: UUID) -> dict[str, Any]:
    """Never flush, modify a source or infer productive authority from its contents."""
    with session.no_autoflush:
        snapshot = _financial_snapshot(session, branch_id)
        differences: list[dict[str, Any]] = []
        for model, source_type in (
            (Sale, "SALE"),
            (OperationalPayment, "OPERATIONAL_PAYMENT"),
            (OperationalDiscount, "OPERATIONAL_DISCOUNT"),
            (CashSession, "CASH_SESSION"),
        ):
            causal_match = (
                (FinancialOperation.kind == "CASH_OPENING")
                & (FinancialOperation.cash_session_id == model.id)
                if model is CashSession
                else (FinancialOperation.source_type == source_type)
                & (FinancialOperation.source_id == model.id)
            )
            missing = (
                session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(
                        model.branch_id == branch_id,
                        ~select(FinancialOperation.id)
                        .where(
                            causal_match,
                        )
                        .exists(),
                    )
                )
                or 0
            )
            if missing:
                differences.append(
                    {
                        "source_type": source_type,
                        "count": missing,
                        "cause": "SOURCE_WITHOUT_CANONICAL_FINANCIAL_CAUSE",
                        "treatment": "CLASSIFY_EVIDENCE_BEFORE_TRANSFORMATION",
                    }
                )
        missing_orders = (
            session.scalar(
                select(func.count())
                .select_from(CustomerOrderPayment)
                .join(CustomerOrder, CustomerOrder.id == CustomerOrderPayment.customer_order_id)
                .where(
                    CustomerOrder.branch_id == branch_id,
                    CustomerOrderPayment.payment_type.in_(["ADVANCE", "SETTLEMENT"]),
                    ~select(FinancialOperation.id)
                    .where(
                        FinancialOperation.source_type == "ORDER_PAYMENT",
                        FinancialOperation.source_id == CustomerOrderPayment.id,
                    )
                    .exists(),
                )
            )
            or 0
        )
        if missing_orders:
            differences.append(
                {
                    "source_type": "ORDER_PAYMENT",
                    "count": missing_orders,
                    "cause": "RECEIPT_WITHOUT_CANONICAL_FINANCIAL_CAUSE",
                    "treatment": "CLASSIFY_EVIDENCE_BEFORE_TRANSFORMATION",
                }
            )
        unresolved = (
            session.scalar(
                select(func.count())
                .select_from(FinancialEntry)
                .where(
                    FinancialEntry.branch_id == branch_id,
                    FinancialEntry.state.in_(["PENDING", "PROCESSING", "UNKNOWN"]),
                )
            )
            or 0
        )
        if unresolved:
            differences.append(
                {
                    "source_type": "FINANCIAL_ENTRY",
                    "count": unresolved,
                    "cause": "UNRESOLVED_EXECUTION",
                    "treatment": "MANUAL_RECONCILIATION",
                }
            )
        return {
            "branch_id": str(branch_id),
            "read_only": True,
            "snapshot": snapshot,
            "differences": differences,
            "production_reconciliation_signed": False,
        }


def _validate_row_source(
    session: Session, manifest: FinancialImportManifest, row: ImportRow
) -> None:
    if row.treatment not in {"OPENING_ADJUSTMENT", "BACKFILL"}:
        raise FinancialModelError("This row requires manual reconciliation or read-only archival.")
    operation = FinancialOperationSnapshot(
        id=row.evidence_reference,
        kind=row.kind,
        source_type=row.source_type,
        source_id=row.source_id,
        effect_code=row.kind.value,
        subject_type=row.subject_type,
        subject_id=row.subject_id,
        amount_due=row.amount_due,
        branch_id=manifest.branch_id,
        currency_code=row.currency_code,
        cash_session_id=row.cash_session_id,
        opening_obligation_kind=row.opening_obligation_kind,
        opening_reason_code=row.reason_code if row.treatment == "OPENING_ADJUSTMENT" else None,
        source_evidence_reference=row.evidence_reference
        if row.treatment == "OPENING_ADJUSTMENT"
        else None,
        cutover_at=manifest.cutover_at if row.treatment == "OPENING_ADJUSTMENT" else None,
    )
    validate_operation(operation)
    for leg in row.legs:
        cash_method = leg.payment_method == PaymentMethod.CASH
        validate_entry(
            operation,
            FinancialEntrySnapshot(
                id=uuid4(),
                financial_operation_id=operation.id,
                leg_key=leg.leg_key,
                payment_method_code=leg.payment_method,
                direction=leg.direction,
                amount=leg.amount,
                state=EntryState.CONFIRMED,
                branch_id=manifest.branch_id,
                currency_code=row.currency_code,
                cash_session_id=row.cash_session_id,
                tendered_amount=leg.tendered_amount,
                change_amount=leg.change_amount,
                execution_mode=ExecutionMode.LOCAL
                if cash_method
                else ExecutionMode.ACCOUNTING_ONLY,
                confirmed_at=row.occurred_at,
                resolution_kind=EvidenceKind.LOCAL_CASH
                if cash_method
                else EvidenceKind.EXTERNAL_RECORDING,
                resolution_reference=leg.external_recording_reference,
            ),
        )
    if row.cash_session_id:
        cash = session.get(CashSession, row.cash_session_id)
        if (
            cash is None
            or cash.branch_id != manifest.branch_id
            or cash.workstation_id != row.workstation_id
        ):
            raise FinancialModelError(
                "The actual cash session or workstation is missing or mismatched."
            )
        if cash.status != "OPEN":
            raise FinancialModelError(
                "Closed or closing sessions require manual reconciliation; history is immutable."
            )
        if row.occurred_at < cash.opened_at:
            raise FinancialModelError("The source time precedes its actual cash session.")
    elif row.kind != OperationKind.OPENING_OBLIGATION:
        raise FinancialModelError("A financial effect requires its actual open session.")
    if row.treatment == "OPENING_ADJUSTMENT":
        if row.kind == OperationKind.OPENING_OBLIGATION and session.scalar(
            select(FinancialOperation.id)
            .where(
                FinancialOperation.kind == "OPENING_OBLIGATION",
                FinancialOperation.branch_id == manifest.branch_id,
                FinancialOperation.subject_type == row.subject_type,
                FinancialOperation.subject_id == row.subject_id,
                FinancialOperation.opening_obligation_kind == row.opening_obligation_kind,
            )
            .limit(1)
        ):
            raise FinancialModelError("This subject already has its opening obligation.")
        if row.kind == OperationKind.CASH_OPENING:
            if session.scalar(
                select(FinancialOperation.id).where(
                    FinancialOperation.kind == "CASH_OPENING",
                    FinancialOperation.cash_session_id == row.cash_session_id,
                )
            ):
                raise FinancialModelError(
                    "This session already has an opening; never add a second fund."
                )
            assert cash is not None
            if cash.opening_amount != row.amount_due or cash.opened_at != row.occurred_at:
                raise FinancialModelError(
                    "Opening evidence must match the real session fund and time."
                )
        elif row.subject_type == "ORDER":
            order = session.get(CustomerOrder, row.subject_id)
            if (
                order is None
                or order.branch_id != manifest.branch_id
                or order.status in {"DELIVERED", "CANCELED"}
            ):
                raise FinancialModelError(
                    "An opening order obligation requires a verified open order."
                )
        return
    source: Any
    expected: set[tuple[str, str, str, Decimal, Decimal | None, Decimal, UUID | None]]
    if row.source_type == "SALE":
        source = session.get(Sale, row.source_id)
        if (
            source is None
            or row.kind != OperationKind.SALE_COLLECTION
            or source.status != "CONFIRMED"
        ):
            raise FinancialModelError("A backfilled sale must already exist and be confirmed.")
        expected = {
            (
                str(p.id),
                p.payment_method_code,
                "IN",
                p.applied_amount,
                p.tendered_amount,
                p.change_amount,
                p.id if p.payment_method_code == "CARD" else None,
            )
            for p in session.scalars(select(SalePayment).where(SalePayment.sale_id == source.id))
            if p.applied_amount > ZERO
        }
        expected_subject, amount, occurred, cash_id = (
            source.id,
            source.total_amount,
            source.confirmed_at,
            source.cash_session_id,
        )
    elif row.source_type in {"OPERATIONAL_PAYMENT", "OPERATIONAL_DISCOUNT"}:
        source = session.get(
            OperationalPayment if row.source_type == "OPERATIONAL_PAYMENT" else OperationalDiscount,
            row.source_id,
        )
        payment = row.source_type == "OPERATIONAL_PAYMENT"
        if (
            source is None
            or source.status != "COMMITTED"
            or row.kind
            != (OperationKind.OPERATIONAL_PAYMENT if payment else OperationKind.OPERATIONAL_CHARGE)
        ):
            raise FinancialModelError("An operating source must already exist and be committed.")
        expected = {
            (
                "payment" if payment else "charge",
                source.payment_method_code,
                "OUT" if payment else "IN",
                source.total_amount,
                source.total_amount
                if not payment and source.payment_method_code == "CASH"
                else None,
                ZERO,
                source.id if source.payment_method_code == "CARD" else None,
            )
        }
        expected_subject, amount, occurred, cash_id = (
            source.id,
            source.total_amount,
            source.committed_at_utc,
            source.active_cash_session_id,
        )
    elif row.source_type == "ORDER_PAYMENT":
        source = session.get(CustomerOrderPayment, row.source_id)
        if (
            source is None
            or source.payment_type not in {"ADVANCE", "SETTLEMENT"}
            or row.kind.value != f"ORDER_{source.payment_type}"
        ):
            raise FinancialModelError(
                "An order source must be an actual advance or settlement receipt."
            )
        order = session.get(CustomerOrder, source.customer_order_id)
        if order is None or order.branch_id != manifest.branch_id:
            raise FinancialModelError("The order source branch is inconsistent.")
        expected = {
            (
                "payment",
                source.payment_method_code,
                "IN",
                source.amount,
                source.amount if source.payment_method_code == "CASH" else None,
                ZERO,
                source.id if source.payment_method_code == "CARD" else None,
            )
        }
        expected_subject, amount, occurred, cash_id = (
            source.customer_order_id,
            source.amount,
            source.recorded_at_utc,
            source.cash_session_id,
        )
    else:
        raise FinancialModelError("No approved causal adapter exists; use manual reconciliation.")
    actual = {
        (
            leg.leg_key,
            leg.payment_method.value,
            leg.direction.value,
            leg.amount,
            leg.tendered_amount,
            leg.change_amount,
            leg.external_recording_reference,
        )
        for leg in row.legs
    }
    if (
        getattr(source, "branch_id", manifest.branch_id) != manifest.branch_id
        or source.workstation_id != row.workstation_id
        or source.currency_code != row.currency_code
        or expected_subject != row.subject_id
        or amount != row.amount_due
        or occurred != row.occurred_at
        or cash_id != row.cash_session_id
        or expected != actual
    ):
        raise FinancialModelError(
            "Financial source identity, amount, time, scope or legs do not reconcile."
        )


@financial_calculation
def dry_run_financial_import(
    session: Session, *, manifest: FinancialImportManifest
) -> dict[str, Any]:
    with session.no_autoflush:
        source_error = None
        try:
            manifest.require_productive_source()
        except FinancialModelError as source_issue:
            source_error = str(source_issue)
        rows = []
        for row in manifest.rows:
            error = source_error
            applied = session.scalar(
                select(FinancialImportRow).where(
                    FinancialImportRow.manifest_id == manifest.manifest_id,
                    FinancialImportRow.row_key == row.row_key,
                )
            )
            if not error:
                try:
                    if applied is None:
                        _validate_row_source(session, manifest, row)
                        duplicate = session.scalar(
                            select(FinancialOperation.id).where(
                                FinancialOperation.source_type == row.source_type,
                                FinancialOperation.source_id == row.source_id,
                                FinancialOperation.kind == row.kind.value,
                            )
                        )
                        if duplicate:
                            raise FinancialModelError(
                                "The cause exists outside this manifest; reconcile it manually."
                            )
                    elif applied.row_sha256 != row_digest(row):
                        raise FinancialModelError("An applied manifest row cannot change.")
                except FinancialModelError as issue:
                    error = str(issue)
            rows.append(
                {
                    "row_key": row.row_key,
                    "row_sha256": row_digest(row),
                    "status": "REJECTED" if error else "APPLIED" if applied else "READY",
                    "reason": error,
                    "treatment": row.treatment,
                    "required_treatment": "MANUAL_RECONCILIATION" if error else row.treatment,
                }
            )
        existing = session.get(ManifestRecord, manifest.manifest_id)
        conflict = existing is not None and existing.manifest_sha256 != manifest.digest()
        return {
            "read_only": True,
            "manifest_id": str(manifest.manifest_id),
            "manifest_sha256": manifest.digest(),
            "manifest_conflict": conflict,
            "expected_row_count": manifest.expected_row_count,
            "expected_amount_due": str(manifest.expected_amount_due),
            "applied_row_count": sum(row["status"] == "APPLIED" for row in rows),
            "applied_amount_due": str(
                sum(
                    (
                        source.amount_due
                        for source, result in zip(manifest.rows, rows, strict=True)
                        if result["status"] == "APPLIED"
                    ),
                    ZERO,
                )
            ),
            "can_apply": not conflict
            and all(row["status"] in {"READY", "APPLIED"} for row in rows),
            "rows": rows,
            "before": diagnose_financial_state(session, branch_id=manifest.branch_id),
            "approval_authenticity_verified": False,
        }


@financial_calculation
def apply_financial_import_row(
    session: Session,
    *,
    current_user: AuthenticatedUser,
    manifest: FinancialImportManifest,
    row_key: str,
    expected_manifest_sha256: str,
    controlled_window_confirmed: bool,
) -> IdempotencyResult:
    manifest.require_productive_source()
    if not controlled_window_confirmed or expected_manifest_sha256 != manifest.digest():
        raise FinancialModelError(
            "Apply requires the reviewed exact manifest and an explicit controlled window."
        )
    row = next((item for item in manifest.rows if item.row_key == row_key), None)
    if row is None:
        raise FinancialModelError("The row is not part of the reviewed manifest.")
    if current_user.authorization_surface != "BACKOFFICE":
        raise HTTPException(403, "Financial imports require authenticated Backoffice authority.")
    bind_authorization_scope(
        session,
        user=current_user,
        capabilities=("cash_finance.manage",),
        mutation=True,
        global_only=True,
        surface="BACKOFFICE",
    )

    def authorize(current: Session, context: CommandContext) -> None:
        refreshed = resolve_authorization(current, current_user, surface="BACKOFFICE")
        require_branches(refreshed, "cash_finance.manage", [manifest.branch_id], global_only=True)
        if not refreshed.is_superadministrator or refreshed.password_reset_required:
            raise HTTPException(
                403, "An explicitly authorized superadministrator must apply financial imports."
            )

    def action(current: Session) -> CommandResult:
        owner = execution(current)
        assert owner is not None and owner.record is not None
        # Reservations hold FK KEY SHARE; serialize without upgrading those locks.
        branch = current.scalar(
            select(Branch).where(Branch.id == manifest.branch_id).with_for_update(key_share=True)
        )
        if branch is None or not branch.is_active:
            raise FinancialModelError("The import branch must be active and explicitly approved.")
        if row.cash_session_id:
            current.scalar(
                select(CashSession)
                .where(CashSession.id == row.cash_session_id)
                .with_for_update(key_share=True)
            )
        existing = current.scalar(
            select(ManifestRecord)
            .where(ManifestRecord.id == manifest.manifest_id)
            .with_for_update()
        )
        if existing is not None and existing.manifest_sha256 != manifest.digest():
            raise FinancialModelError("The admitted manifest is immutable.")
        report = dry_run_financial_import(current, manifest=manifest)
        if not report["can_apply"]:
            raise FinancialModelError(
                "Dry-run differences require reconciliation before applying any row."
            )
        if existing is None:
            current.add(
                ManifestRecord(
                    id=manifest.manifest_id,
                    branch_id=manifest.branch_id,
                    manifest_sha256=manifest.digest(),
                    evidence=manifest.model_dump(mode="json"),
                    admitted_by_user_id=current_user.id,
                )
            )
            current.flush()
        before = _financial_snapshot(current, manifest.branch_id)
        scope = FinancialCommandScope(
            manifest.branch_id, row.workstation_id, row.cash_session_id, current_user.id
        )
        operation = create_financial_operation(
            current,
            kind=row.kind,
            source_type=row.source_type,
            source_id=row.source_id,
            subject_type=row.subject_type,
            subject_id=row.subject_id,
            amount_due=row.amount_due,
            currency_code=row.currency_code,
            scope=scope,
            occurred_at=row.occurred_at,
            opening_obligation_kind=row.opening_obligation_kind,
            opening_reason_code=row.reason_code if row.treatment == "OPENING_ADJUSTMENT" else None,
            source_evidence_reference=row.evidence_reference
            if row.treatment == "OPENING_ADJUSTMENT"
            else None,
            cutover_at=manifest.cutover_at if row.treatment == "OPENING_ADJUSTMENT" else None,
        )
        entries = [
            record_confirmed_entry(
                current,
                operation=operation,
                leg_key=leg.leg_key,
                payment_method=leg.payment_method,
                direction=leg.direction,
                amount=leg.amount,
                scope=scope,
                occurred_at=row.occurred_at,
                tendered_amount=leg.tendered_amount,
                change_amount=leg.change_amount,
                external_recording_reference=leg.external_recording_reference,
            )
            for leg in row.legs
        ]
        after = _financial_snapshot(current, manifest.branch_id)
        if after["operation_count"] != before["operation_count"] + 1 or after[
            "entry_count"
        ] != before["entry_count"] + len(entries):
            raise FinancialModelError("Financial import counts do not reconcile.")
        expected_totals = {key: Decimal(value) for key, value in before["confirmed_totals"].items()}
        for entry in entries:
            total_key = f"{entry.payment_method_code}_{entry.direction}"
            expected_totals[total_key] = expected_totals.get(total_key, ZERO) + entry.amount
        if expected_totals != {
            key: Decimal(value) for key, value in after["confirmed_totals"].items()
        }:
            raise FinancialModelError("Financial import totals do not reconcile.")
        current.add(
            FinancialImportRow(
                id=uuid4(),
                manifest_id=manifest.manifest_id,
                branch_id=manifest.branch_id,
                row_key=row.row_key,
                row_sha256=row_digest(row),
                financial_operation_id=operation.id,
                operation_id=owner.record.id,
                reconciliation={"before": before, "after": after},
            )
        )
        trace = {
            "manifest_id": str(manifest.manifest_id),
            "manifest_sha256": manifest.digest(),
            "row_key": row.row_key,
            "row_sha256": row_digest(row),
            "financial_operation_id": str(operation.id),
            "financial_entry_ids": [str(entry.id) for entry in entries],
            "approval_reference": manifest.approval_reference,
            "approval_evidence_sha256": manifest.approval_evidence_sha256,
            "approval_authenticity_verified": False,
            "source_evidence_reference": str(row.evidence_reference),
            "source_evidence_sha256": row.evidence_sha256,
            "treatment": row.treatment,
            "before": before,
            "after": after,
        }
        AuditRecorder().record(
            current,
            actor_id=current_user.id,
            action="financial_import.row_applied",
            resource_type="financial_import",
            resource_id=str(manifest.manifest_id),
            branch_id=manifest.branch_id,
            request_id=None,
            metadata=trace,
        )
        OutboxWriter().append(
            current,
            aggregate_type="financial_import",
            aggregate_id=str(manifest.manifest_id),
            event_name="financial_import.row_applied.v1",
            payload=trace,
        )
        current.flush()
        return CommandResult(
            status_code=201,
            snapshot=ImportResult(
                manifest_id=manifest.manifest_id,
                row_key=row.row_key,
                manifest_sha256=manifest.digest(),
                row_sha256=row_digest(row),
                financial_operation_id=operation.id,
                financial_entry_ids=[entry.id for entry in entries],
                before_sha256=before["sha256"],
                after_sha256=after["sha256"],
            ),
            resource_type="financial_import",
            resource_id=str(manifest.manifest_id),
        )

    return IdempotencyExecutor().execute(
        session,
        key=row.idempotency_key,
        operation_code="financial_import.apply_row",
        payload={
            "manifest_sha256": manifest.digest(),
            "row_key": row.row_key,
            "row_sha256": row_digest(row),
        },
        resolve_context=lambda current, saved: CommandContext(
            actor_user_id=current_user.id,
            surface="BACKOFFICE",
            branch_id=manifest.branch_id,
            workstation_id=row.workstation_id,
            cash_session_id=row.cash_session_id,
        ),
        authorize=authorize,
        action=action,
        response_policy=ResponsePolicy(snapshot_model=ImportResult),
    )
