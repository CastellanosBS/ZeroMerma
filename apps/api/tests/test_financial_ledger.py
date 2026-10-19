"""Storage invariants independent of future financial command producers."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from threading import Event
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from zeromerma_api.bootstrap.seed_local import SEED_USER_EMAIL, SEED_WORKSTATION_CODE
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal, engine
from zeromerma_api.modules.branches.infrastructure.models import Workstation
from zeromerma_api.modules.cash.infrastructure.models import CashSession
from zeromerma_api.modules.financial_ledger.application.projections import (
    FinancialLedgerQueryService,
)
from zeromerma_api.modules.financial_ledger.infrastructure.models import (
    FinancialEntry,
    FinancialOperation,
)
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.testing.concurrency import transaction_probe, wait_until_blocked


@pytest.fixture
def context():
    with SessionLocal() as session:
        station = session.scalar(
            select(Workstation).where(Workstation.code == SEED_WORKSTATION_CODE)
        )
        user = session.scalar(select(User).where(User.email == SEED_USER_EMAIL))
        now = datetime.now(UTC)
        cash = CashSession(
            id=uuid4(),
            branch_id=station.branch_id,
            workstation_id=station.id,
            user_id=user.id,
            status="CLOSED",
            opening_amount=Decimal("0.00"),
            opened_at=now - timedelta(hours=1),
            closed_at=now,
        )
        session.add(cash)
        session.commit()
        return dict(
            branch_id=station.branch_id,
            workstation_id=station.id,
            cash_session_id=cash.id,
            actor_id=user.id,
            currency_code="MXN",
            context_version=1,
            source_app="POS",
            actor_type="USER",
            operation_id=uuid4(),
            correlation_id=uuid4(),
            related_branch_ids=[str(station.branch_id)],
            occurred_at=now,
        )


def operation(context, **overrides):
    subject = uuid4()
    values = dict(
        context,
        id=uuid4(),
        kind="SALE_COLLECTION",
        source_type="SALE",
        source_id=subject,
        effect_code="SALE_COLLECTION",
        subject_type="SALE",
        subject_id=subject,
        amount_due=Decimal("100.00"),
    )
    values.update(overrides)
    return FinancialOperation(**values)


def entry(context, parent, **overrides):
    values = dict(
        context,
        id=uuid4(),
        financial_operation_id=parent.id,
        leg_key="cash-1",
        payment_method_code="CASH",
        direction="IN",
        amount=Decimal("40.00"),
        tendered_amount=Decimal("40.00"),
        change_amount=Decimal("0.00"),
        execution_mode="LOCAL",
        state="CONFIRMED",
        confirmed_at=datetime.now(UTC),
        resolution_kind="LOCAL_CASH",
    )
    values.update(overrides)
    return FinancialEntry(**values)


def persist_parent(session, context, **values):
    parent = operation(context, **values)
    session.add(parent)
    session.flush()
    return parent


def assert_rejected(session):
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_partial_collection_keeps_unassigned_remainder_and_actual_later_cash_context(context):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        original_cash = context["cash_session_id"]
        later = CashSession(
            id=uuid4(),
            branch_id=context["branch_id"],
            workstation_id=context["workstation_id"],
            user_id=context["actor_id"],
            status="CLOSED",
            opening_amount=Decimal("0"),
            closed_at=datetime.now(UTC),
        )
        session.add(later)
        session.flush()
        first = entry(context, parent, cash_session_id=later.id)
        session.add(first)
        session.commit()
        assert parent.cash_session_id == original_cash
        assert first.cash_session_id == later.id != original_cash
        assert parent.amount_due - first.amount == Decimal("60.00")
        assert first.recorded_at >= first.occurred_at
        assert session.scalar(select(func.count()).select_from(FinancialEntry)) == 1


@pytest.mark.parametrize("state", ["PENDING", "PROCESSING", "UNKNOWN"])
def test_unconfirmed_real_legs_reserve_budget_but_have_no_confirmation(context, state):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        pending = entry(context, parent, state=state, confirmed_at=None, resolution_kind=None)
        session.add(pending)
        session.commit()
        assert pending.confirmed_at is None
        session.add(
            entry(
                context,
                parent,
                leg_key="second",
                amount=Decimal("61"),
                tendered_amount=Decimal("61"),
            )
        )
        assert_rejected(session)
        assert session.scalar(select(func.sum(FinancialEntry.amount))) == Decimal("40")


@pytest.mark.parametrize("state", ["REJECTED", "CANCELLED"])
def test_rejected_or_cancelled_leg_frees_capacity_without_erasing_history(context, state):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        session.add(entry(context, parent, state=state, confirmed_at=None, resolution_kind=None))
        session.add(
            entry(
                context,
                parent,
                leg_key="replacement",
                amount=Decimal("100"),
                tendered_amount=Decimal("100"),
            )
        )
        session.commit()
        assert session.scalar(select(func.count()).select_from(FinancialEntry)) == 2


@pytest.mark.parametrize("kind", ["CASH_OPENING", "SALE_COLLECTION"])
def test_zero_operation_is_explicit_and_never_invents_a_zero_leg(context, kind):
    with SessionLocal() as session:
        values = dict(amount_due=Decimal("0.00"))
        if kind == "CASH_OPENING":
            values.update(
                kind=kind,
                effect_code=kind,
                source_type="CASH_SESSION",
                source_id=context["cash_session_id"],
                subject_type="CASH_SESSION",
                subject_id=context["cash_session_id"],
            )
        parent = persist_parent(session, context, **values)
        session.commit()
        assert session.scalar(select(func.count()).select_from(FinancialEntry)) == 0
        session.add(entry(context, parent, amount=Decimal("0"), tendered_amount=Decimal("0")))
        assert_rejected(session)


def test_only_one_opening_per_cash_session_even_for_another_cause(context):
    with SessionLocal() as session:
        values = dict(
            kind="CASH_OPENING",
            effect_code="CASH_OPENING",
            source_type="CASH_SESSION",
            source_id=context["cash_session_id"],
            subject_type="CASH_SESSION",
            subject_id=context["cash_session_id"],
            amount_due=Decimal("0"),
        )
        persist_parent(session, context, **values)
        session.commit()
        values.update(
            source_type="OPENING_STATE",
            source_id=uuid4(),
            opening_reason_code="CUTOVER",
            source_evidence_reference=uuid4(),
            cutover_at=datetime.now(UTC),
        )
        session.add(operation(context, **values))
        assert_rejected(session)


@pytest.mark.parametrize("kind,direction", [("CASH_DEPOSIT", "IN"), ("CASH_WITHDRAWAL", "OUT")])
def test_cash_deposit_and_withdrawal_cannot_be_card_entries(context, kind, direction):
    with SessionLocal() as session:
        parent = persist_parent(
            session,
            context,
            kind=kind,
            effect_code=kind,
            source_type=kind,
            subject_type="CASH_SESSION",
            subject_id=context["cash_session_id"],
        )
        session.commit()
        session.add(
            entry(
                context,
                parent,
                payment_method_code="CARD",
                execution_mode="ACCOUNTING_ONLY",
                direction=direction,
                tendered_amount=None,
                resolution_kind="EXTERNAL_RECORDING",
                resolution_reference=uuid4(),
            )
        )
        assert_rejected(session)
        session.add(entry(context, parent, direction=direction))
        session.commit()


def test_causal_effect_and_leg_keys_are_unique_durable_identity(context):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        first = entry(context, parent)
        session.add(first)
        session.commit()
        session.add(operation(context, source_id=parent.source_id, subject_id=parent.subject_id))
        assert_rejected(session)
        session.add(entry(context, parent, amount=Decimal("1"), tendered_amount=Decimal("1")))
        assert_rejected(session)
        assert session.scalar(select(func.count()).select_from(FinancialOperation)) == 1
        assert session.scalar(select(func.count()).select_from(FinancialEntry)) == 1


@pytest.mark.parametrize(
    "subtype,subject",
    [
        ("RECEIVABLE", "OPENING_BALANCE"),
        ("PAYABLE", "OPENING_BALANCE"),
        ("CUSTOMER_ADVANCE", "ORDER"),
    ],
)
def test_opening_obligation_records_evidence_and_never_drawer_money(context, subtype, subject):
    with SessionLocal() as session:
        parent = persist_parent(
            session,
            context,
            kind="OPENING_OBLIGATION",
            effect_code="OPENING_OBLIGATION",
            source_type="OPENING_STATE",
            source_id=uuid4(),
            subject_type=subject,
            opening_obligation_kind=subtype,
            workstation_id=None,
            cash_session_id=None,
            opening_reason_code="APPROVED_CUTOVER",
            source_evidence_reference=uuid4(),
            cutover_at=datetime.now(UTC),
        )
        session.commit()
        session.add(entry(context, parent))
        assert_rejected(session)


@pytest.mark.parametrize(
    "changes",
    [
        {"amount_due": Decimal("NaN")},
        {"amount_due": Decimal("-0.01")},
        {"currency_code": "USD"},
        {"effect_code": "another-effect"},
        {"source_type": "ORDER_PAYMENT"},
        {"subject_type": "ORDER"},
        {"subject_id": uuid4()},
        {"context_version": 0},
        {"operation_id": None},
        {"actor_id": None},
        {"related_branch_ids": {}},
        {
            "kind": "OPENING_OBLIGATION",
            "effect_code": "OPENING_OBLIGATION",
            "source_type": "OPENING_STATE",
            "opening_obligation_kind": None,
        },
    ],
)
def test_invalid_operation_cannot_be_admitted(context, changes):
    with SessionLocal() as session:
        session.add(operation(context, **changes))
        assert_rejected(session)
        assert session.scalar(select(func.count()).select_from(FinancialOperation)) == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"amount": Decimal("NaN")},
        {"amount": Decimal("-1")},
        {"amount": Decimal("0")},
        {"tendered_amount": Decimal("NaN")},
        {"change_amount": Decimal("1")},
        {"tendered_amount": None},
        {"payment_method_code": "MIXED"},
        {"direction": "OUT"},
        {"execution_mode": "PROVIDER_INTEGRATED"},
        {"resolution_kind": None},
        {"cash_session_id": None},
        {"leg_key": " "},
        {"currency_code": "USD"},
    ],
)
def test_invalid_entry_rolls_back_without_a_monetary_fact(context, changes):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        session.commit()
        session.add(entry(context, parent, **changes))
        assert_rejected(session)
        assert session.scalar(select(func.count()).select_from(FinancialEntry)) == 0


@pytest.mark.parametrize("table", [FinancialOperation, FinancialEntry])
@pytest.mark.parametrize("action", ["UPDATE", "DELETE"])
def test_operation_and_confirmed_entry_cannot_be_rewritten_or_deleted(context, table, action):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        session.add(entry(context, parent))
        session.commit()
        statement = f"{action} {table.__tablename__}"
        if action == "UPDATE":
            statement += " SET currency_code = currency_code"
        else:
            statement = f"DELETE FROM {table.__tablename__}"
        with pytest.raises(IntegrityError):
            session.execute(text(statement))
        session.rollback()
        assert session.scalar(select(func.count()).select_from(table)) == 1


@pytest.mark.parametrize(
    "state,evidence",
    [
        ("CONFIRMED", "MANUAL_RECONCILIATION"),
        ("REJECTED", "PROVIDER_REJECTION"),
        ("CANCELLED", "PROVIDER_VOID"),
    ],
)
def test_unknown_resolution_requires_typed_reference_and_preserves_execution_origin(
    context, state, evidence
):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        item = entry(
            context,
            parent,
            payment_method_code="CARD",
            execution_mode="PROVIDER_INTEGRATED",
            state="UNKNOWN",
            resolution_kind=None,
            confirmed_at=None,
            cash_session_id=None,
            workstation_id=None,
            tendered_amount=None,
        )
        session.add(item)
        session.commit()
        item.state = state
        item.confirmed_at = datetime.now(UTC) if state == "CONFIRMED" else None
        assert_rejected(session)
        item.state = state
        item.confirmed_at = datetime.now(UTC) if state == "CONFIRMED" else None
        item.resolution_kind = evidence
        item.resolution_reference = uuid4()
        session.commit()
        assert item.execution_mode == "PROVIDER_INTEGRATED"
        item.state = "PENDING"
        assert_rejected(session)


def test_multiple_order_collections_share_subject_and_refund_has_no_single_payment_cap(context):
    order_id = uuid4()
    with SessionLocal() as session:
        for kind, amount in (("ORDER_ADVANCE", "30"), ("ORDER_SETTLEMENT", "70")):
            parent = persist_parent(
                session,
                context,
                kind=kind,
                effect_code=kind,
                source_type="ORDER_PAYMENT",
                source_id=uuid4(),
                subject_type="ORDER",
                subject_id=order_id,
                amount_due=Decimal(amount),
            )
            session.add(
                entry(context, parent, amount=Decimal(amount), tendered_amount=Decimal(amount))
            )
            session.flush()
        refund = persist_parent(
            session,
            context,
            kind="ORDER_REFUND",
            effect_code="ORDER_REFUND",
            source_type="ORDER_PAYMENT",
            source_id=uuid4(),
            subject_type="ORDER",
            subject_id=order_id,
            amount_due=Decimal("100"),
        )
        session.add(
            entry(context, refund, direction="OUT", amount=Decimal("40"), tendered_amount=None)
        )
        session.commit()
        assert refund.related_operation_id is None
        assert session.scalar(select(func.count()).select_from(FinancialOperation)) == 3


def test_cash_refund_can_anchor_card_collection_in_a_later_turn(context):
    with SessionLocal() as session:
        sale = persist_parent(session, context, cash_session_id=None, workstation_id=None)
        session.add(
            entry(
                context,
                sale,
                payment_method_code="CARD",
                execution_mode="ACCOUNTING_ONLY",
                resolution_kind="EXTERNAL_RECORDING",
                resolution_reference=uuid4(),
                amount=Decimal("100"),
                tendered_amount=None,
                cash_session_id=None,
                workstation_id=None,
            )
        )
        session.flush()
        refund = persist_parent(
            session,
            context,
            kind="SALE_REFUND",
            effect_code="SALE_REFUND",
            source_type="SALE_RETURN",
            source_id=uuid4(),
            subject_id=sale.subject_id,
            related_operation_id=sale.id,
            relation_kind="REFUND_OF",
        )
        session.add(entry(context, refund, direction="OUT", tendered_amount=None))
        session.commit()


@pytest.mark.parametrize("change", ["amount", "method", "direction", "state", "valid"])
def test_full_technical_reversal_preserves_original_and_is_unique(context, change):
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        original = entry(context, parent)
        session.add(original)
        session.flush()
        reversal = persist_parent(
            session,
            context,
            kind="TECHNICAL_REVERSAL",
            effect_code="TECHNICAL_REVERSAL",
            source_type="FINANCIAL_ENTRY",
            source_id=original.id,
            subject_id=parent.subject_id,
            amount_due=original.amount,
            related_operation_id=parent.id,
            relation_kind="REVERSAL_OF",
        )
        session.commit()
        values = dict(direction="OUT", tendered_amount=None, reverses_entry_id=original.id)
        if change == "amount":
            values.update(amount=Decimal("39"))
        elif change == "method":
            values.update(
                payment_method_code="CARD",
                execution_mode="ACCOUNTING_ONLY",
                resolution_kind="EXTERNAL_RECORDING",
                resolution_reference=uuid4(),
            )
        elif change == "direction":
            values.update(direction="IN", tendered_amount=original.amount)
        elif change == "state":
            values.update(state="PENDING", confirmed_at=None, resolution_kind=None)
        session.add(entry(context, reversal, **values))
        if change != "valid":
            assert_rejected(session)
            return
        session.commit()
        assert original.state == "CONFIRMED" and original.amount == Decimal("40")
        session.add(entry(context, reversal, leg_key="duplicate", **values))
        assert_rejected(session)


def test_cash_and_workstation_must_belong_to_the_entry_branch(context):
    with SessionLocal() as session:
        foreign = session.scalar(
            select(Workstation).where(Workstation.branch_id != context["branch_id"])
        )
        parent = persist_parent(session, context)
        session.commit()
        session.add(entry(context, parent, workstation_id=foreign.id))
        assert_rejected(session)
        session.add(operation(context, workstation_id=foreign.id))
        assert_rejected(session)


def test_concurrent_legs_cannot_overallocate_the_same_operation(context):
    """Different transactions wait on the operation row, not an authentication or drawer row."""
    with SessionLocal() as session:
        parent = persist_parent(session, context)
        session.commit()
    reserved, release, competitor = Event(), Event(), Event()
    probes = {}

    def first():
        with SessionLocal() as session:
            probes["first"] = transaction_probe(session)
            session.add(entry(context, parent, amount=Decimal("60"), tendered_amount=Decimal("60")))
            session.flush()
            reserved.set()
            assert release.wait(10)
            session.commit()

    def second():
        with SessionLocal() as session:
            probes["second"] = transaction_probe(session)
            competitor.set()
            session.add(
                entry(
                    context,
                    parent,
                    leg_key="second",
                    amount=Decimal("60"),
                    tendered_amount=Decimal("60"),
                )
            )
            with pytest.raises(IntegrityError, match="exceed the admitted"):
                session.commit()
            session.rollback()

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(first)
        assert reserved.wait(10)
        b = pool.submit(second)
        assert competitor.wait(10)
        try:
            wait_until_blocked(probes["second"].backend_pid, probes["first"].backend_pid)
        finally:
            release.set()
        a.result(timeout=10)
        b.result(timeout=10)
    with SessionLocal() as session:
        assert session.scalar(select(func.sum(FinancialEntry.amount))) == Decimal("60")


def _reader(session, branch_id):
    user = User(
        email=f"ledger-{uuid4()}@example.test",
        full_name="Ledger reader",
        password_hash="unusable",
        allowed_surfaces=["BACKOFFICE"],
        default_surface="BACKOFFICE",
    )
    role = Role(code=f"ledger_{uuid4().hex}", name="Ledger reader", surfaces=["BACKOFFICE"])
    session.add_all([user, role])
    session.flush()
    assignment = UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type="BRANCH_SET")
    session.add(assignment)
    session.flush()
    permission = session.scalar(select(Permission.id).where(Permission.code == "cash_finance.view"))
    session.add_all(
        [
            UserBranchAssignment(user_id=user.id, branch_id=branch_id),
            UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=branch_id),
            RolePermission(role_id=role.id, permission_id=permission),
        ]
    )
    session.commit()
    return resolve_authorization(session, user, surface="BACKOFFICE")


def test_cash_projection_rebuilds_only_canonical_facts_and_refreshes_cached_pending_entry(context):
    service = FinancialLedgerQueryService()
    with SessionLocal() as setup:
        actor = _reader(setup, context["branch_id"])
        legacy_cash = setup.get(CashSession, context["cash_session_id"])
        legacy_cash.opening_amount = Decimal("999.00")
        persist_parent(
            setup,
            context,
            kind="CASH_OPENING",
            effect_code="CASH_OPENING",
            source_type="CASH_SESSION",
            source_id=context["cash_session_id"],
            subject_type="CASH_SESSION",
            subject_id=context["cash_session_id"],
            amount_due=Decimal("0"),
        )
        sale = persist_parent(setup, context)
        pending = entry(context, sale, state="PENDING", confirmed_at=None, resolution_kind=None)
        setup.add(pending)
        setup.commit()
        entry_id = pending.id
    with SessionLocal() as reader:
        bind_authorization_scope(
            reader,
            user=actor,
            capabilities=("cash_finance.view",),
            mutation=False,
            surface="BACKOFFICE",
        )
        cached = reader.get(FinancialEntry, entry_id)
        first = service.get_cash_projection(
            reader, branch_id=context["branch_id"], cash_session_id=context["cash_session_id"]
        )
        assert first.opening_amount == first.expected_cash == Decimal("0")
        assert first.unresolved_operation_ids == (sale.id,)
        with SessionLocal() as writer:
            current = writer.get(FinancialEntry, entry_id)
            current.state = "CONFIRMED"
            current.confirmed_at = datetime.now(UTC)
            current.resolution_kind = "LOCAL_CASH"
            writer.commit()
        second = service.get_cash_projection(
            reader, branch_id=context["branch_id"], cash_session_id=context["cash_session_id"]
        )
        third = service.get_cash_projection(
            reader, branch_id=context["branch_id"], cash_session_id=context["cash_session_id"]
        )
        assert second == third
        assert second.expected_cash == second.cash_in == Decimal("40")
        assert second.opening_amount == Decimal("0")
        assert second.confirmed_entry_ids == (entry_id,)
        assert cached.state == "PENDING"  # The detached pre-read object is never projection input.


def test_financial_projection_requires_bound_current_authority_and_requested_branch(context):
    service = FinancialLedgerQueryService()
    with SessionLocal() as session:
        with pytest.raises(HTTPException) as missing:
            service.read_branch(session, branch_id=context["branch_id"])
        assert missing.value.status_code == 403
        actor = _reader(session, context["branch_id"])
        foreign = session.scalar(
            select(Workstation.branch_id).where(Workstation.branch_id != context["branch_id"])
        )
        bind_authorization_scope(
            session,
            user=actor,
            capabilities=("cash_finance.view",),
            mutation=False,
            surface="BACKOFFICE",
        )
        with pytest.raises(HTTPException) as denied:
            service.read_branch(session, branch_id=foreign)
        assert denied.value.status_code == 403
        snapshot = service.read_branch(session, branch_id=context["branch_id"])
        assert snapshot.operations == snapshot.entries == ()


def test_projection_rechecks_external_revocation_in_a_previously_authorized_session(context):
    service = FinancialLedgerQueryService()
    with SessionLocal() as reader:
        actor = _reader(reader, context["branch_id"])
        bind_authorization_scope(
            reader,
            user=actor,
            capabilities=("cash_finance.view",),
            mutation=False,
            surface="BACKOFFICE",
        )
        assert service.read_branch(reader, branch_id=context["branch_id"]).operations == ()
        with SessionLocal() as revoker:
            assignment = revoker.scalar(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == actor.id,
                )
            )
            assignment.is_active = False
            revoker.commit()
        with pytest.raises(HTTPException) as denied:
            service.read_branch(reader, branch_id=context["branch_id"])
        assert denied.value.status_code == 403


@pytest.mark.parametrize("isolation", ["REPEATABLE READ", "SERIALIZABLE"])
def test_unvalidated_isolation_cannot_bypass_the_serialized_budget(context, isolation):
    with SessionLocal() as setup:
        parent = persist_parent(setup, context)
        setup.add(entry(context, parent))
        setup.commit()
    # Establish the transaction isolation before session context callbacks issue any SQL.
    with engine.connect().execution_options(isolation_level=isolation) as connection:
        with SessionLocal(bind=connection) as session:
            session.add(entry(context, parent, leg_key="unvalidated-isolation"))
            with pytest.raises(IntegrityError, match="require READ COMMITTED isolation"):
                session.commit()
            session.rollback()
    with SessionLocal() as observer:
        assert observer.scalar(select(func.count()).select_from(FinancialOperation)) == 1
        assert observer.scalar(select(func.count()).select_from(FinancialEntry)) == 1
        assert observer.scalar(select(func.sum(FinancialEntry.amount))) == Decimal("40")
