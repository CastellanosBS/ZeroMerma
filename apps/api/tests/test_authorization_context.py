from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from zeromerma_api.bootstrap.seed_local import SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
from zeromerma_api.db.access_scope import bind_authorization_scope
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.application.admin_services import AdminAuditService
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.authorization import (
    require_branches,
    require_capability,
    resolve_authorization,
)
from zeromerma_api.modules.identity.application.permissions import (
    PERMISSION_CODES,
    SUPERADMIN_ROLE_CODE,
)
from zeromerma_api.modules.identity.application.schemas import ScopeType
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.outbox.application.service import OutboxWriter
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent
from zeromerma_worker.outbox.poller import OutboxPoller


def test_delayed_worker_observation_preserves_causal_scope_after_revocation() -> None:
    with SessionLocal() as session:
        branch_id = session.scalars(select(Branch.id)).first()
        assert branch_id is not None
        user = _user(session)
        session.add(UserBranchAssignment(user_id=user.id, branch_id=branch_id))
        role, _ = _grant(session, user, ["inventory.adjust"], [branch_id])
        session.commit()
        actor = resolve_authorization(session, user, surface="BACKOFFICE")
        role_id = role.id
    with SessionLocal() as session:
        bind_authorization_scope(
            session,
            user=actor,
            capabilities=("inventory.adjust",),
            mutation=True,
            surface="BACKOFFICE",
            request_id="delayed-worker-scope",
        )
        event = OutboxWriter().append(
            session,
            aggregate_type="authorization_test",
            aggregate_id=str(branch_id),
            event_name="authorization.scope_recorded.v1",
            payload={"branch_id": str(branch_id)},
        )
        # Make the delayed event due independently of host/container clock skew.
        event.available_at = datetime(2000, 1, 1, tzinfo=UTC)
        session.commit()
        event_id = event.id
        provenance = event.headers["authorization"]
        assert provenance["branch_ids"] == [str(branch_id)]
        assert provenance["actor_id"] == str(actor.id)
    with SessionLocal() as session:
        session.execute(update(Role).where(Role.id == role_id).values(is_active=False))
        session.commit()
        assert OutboxPoller(session.get_bind(), batch_size=100).poll_once() >= 1
        delayed = session.get(OutboxEvent, event_id)
        assert delayed is not None
        assert delayed.headers["authorization"] == provenance
        assert delayed.status == "pending"
        assert delayed.processed_at is None
        assert resolve_authorization(session, actor, surface="BACKOFFICE").effective_grants == []
    with SessionLocal() as session, pytest.raises(HTTPException) as denied:
        bind_authorization_scope(
            session,
            user=actor,
            capabilities=("inventory.adjust",),
            mutation=True,
            surface="BACKOFFICE",
        )
    assert denied.value.status_code == 403


def _user(session: Session) -> User:
    user = User(
        email=f"authorization-{uuid.uuid4()}@example.test",
        full_name="Authorization test",
        password_hash="unusable",
        allowed_surfaces=["BACKOFFICE"],
        default_surface="BACKOFFICE",
    )
    session.add(user)
    session.flush()
    return user


def _grant(
    session: Session,
    user: User,
    codes: Sequence[str],
    branch_ids: Sequence[uuid.UUID],
    *,
    scope_type: ScopeType = "BRANCH_SET",
    superadmin: bool = False,
) -> tuple[Role, UserRoleAssignment]:
    role = Role(
        code=SUPERADMIN_ROLE_CODE if superadmin else f"test_{uuid.uuid4().hex}",
        name="Test role",
        surfaces=["BACKOFFICE"],
        is_system=superadmin,
    )
    session.add(role)
    session.flush()
    assignment = UserRoleAssignment(user_id=user.id, role_id=role.id, scope_type=scope_type)
    session.add(assignment)
    session.flush()
    session.add_all(
        [
            RolePermission(role_id=role.id, permission_id=permission.id)
            for permission in session.scalars(select(Permission).where(Permission.code.in_(codes)))
        ]
    )
    session.add_all(
        [
            UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=branch_id)
            for branch_id in branch_ids
        ]
    )
    session.flush()
    return role, assignment


def test_scoped_audit_actor_does_not_expose_global_identity_administration() -> None:
    with SessionLocal() as session:
        branch_id = session.scalars(select(Branch.id)).first()
        assert branch_id is not None
        reader, recorded_actor = _user(session), _user(session)
        session.add_all(
            [
                UserBranchAssignment(user_id=user.id, branch_id=branch_id)
                for user in (reader, recorded_actor)
            ]
        )
        _grant(session, reader, ["audit.view", "users.view"], [branch_id])
        _grant(session, recorded_actor, ["inventory.view"], [], scope_type="GLOBAL")
        audit = AuditLog(
            actor_id=recorded_actor.id,
            action="inventory.reviewed",
            resource_type="branch",
            resource_id=str(branch_id),
            branch_id=branch_id,
            metadata_={},
        )
        session.add(audit)
        session.commit()
        event_id = audit.id
        actor_id = recorded_actor.id
        actor = resolve_authorization(session, reader, surface="BACKOFFICE")
        bind_authorization_scope(
            session, user=actor, capabilities=("audit.view",), mutation=False, surface="BACKOFFICE"
        )
        detail = AdminAuditService().get_event_detail(session, event_id=event_id)
        assert detail.actor_context.user_id == actor_id
        assert detail.actor_context.roles_summary is None
        assert detail.actor_context.branch_assignments_summary is None
        assert detail.actor_context.user_status is None
        assert detail.actor_context.can_open_user is False
        assert detail.available_actions.can_open_user is False


def test_effective_grants_union_per_capability_and_intersect_active_user_branches() -> None:
    with SessionLocal() as session:
        north, south, main = list(session.scalars(select(Branch).order_by(Branch.code)))
        user = _user(session)
        session.add_all(
            [
                UserBranchAssignment(user_id=user.id, branch_id=branch.id, is_active=active)
                for branch, active in [(north, True), (south, True), (main, False)]
            ]
        )
        _grant(session, user, ["sales_tickets.view"], [north.id, main.id])
        _grant(session, user, ["sales_tickets.view"], [south.id])
        _grant(session, user, ["inventory.adjust"], [north.id])
        session.commit()
        context = resolve_authorization(session, user)
        sales = require_capability(context, "sales_tickets.view")
        assert set(sales.branch_ids) == {north.id, south.id}
        assert require_capability(context, "inventory.adjust").branch_ids == [north.id]
        with pytest.raises(HTTPException) as denied:
            require_branches(context, "inventory.adjust", [south.id])
        assert denied.value.status_code == 403
        with pytest.raises(HTTPException):
            require_branches(context, "sales_tickets.view", [north.id, main.id])
        with pytest.raises(HTTPException):
            require_branches(context, "sales_tickets.view", [], global_only=True)
        assert context == resolve_authorization(session, user)


@pytest.mark.parametrize(
    "inactive", ["user", "locked", "role", "assignment", "permission", "branch"]
)
def test_inactive_authority_is_removed_immediately(inactive: str) -> None:
    with SessionLocal() as session:
        user = _user(session)
        branch = session.scalars(select(Branch)).first()
        assert branch is not None
        membership = UserBranchAssignment(user_id=user.id, branch_id=branch.id)
        session.add(membership)
        role, assignment = _grant(session, user, ["inventory.adjust"], [branch.id])
        session.commit()
        before = resolve_authorization(session, user)
        require_capability(before, "inventory.adjust")
        match inactive:
            case "user":
                user.is_active = False
            case "locked":
                user.is_locked = True
            case "role":
                role.is_active = False
            case "assignment":
                assignment.is_active = False
            case "permission":
                permission = session.scalar(
                    select(Permission).where(Permission.code == "inventory.adjust")
                )
                assert permission is not None
                permission.is_active = False
            case "branch":
                membership.is_active = False
        session.commit()
        after = resolve_authorization(session, user)
        assert after.effective_grants == []
        assert after.authorization_version != before.authorization_version


def test_explicit_global_superadmin_has_only_explicit_permissions_and_needs_no_branch() -> None:
    with SessionLocal() as session:
        user = _user(session)
        _grant(session, user, ["roles.view"], [], scope_type="GLOBAL", superadmin=True)
        session.commit()
        context = resolve_authorization(session, user)
        assert context.is_superadministrator
        assert require_capability(context, "roles.view").scope_type == "GLOBAL"
        with pytest.raises(HTTPException):
            require_capability(context, "roles.manage")
        assert len(context.effective_grants) == 1


def test_no_role_or_no_effective_branch_never_becomes_global() -> None:
    with SessionLocal() as session:
        user = _user(session)
        assert resolve_authorization(session, user).effective_grants == []
        branch_id = session.scalars(select(Branch.id)).first()
        assert branch_id is not None
        _grant(session, user, ["users.manage"], [branch_id])
        session.commit()
        assert resolve_authorization(session, user).effective_grants == []


@pytest.mark.parametrize("scope_type,with_branch", [("GLOBAL", True), ("BRANCH_SET", False)])
def test_database_rejects_invalid_scope_cardinality(
    scope_type: ScopeType, with_branch: bool
) -> None:
    with SessionLocal() as session:
        user = _user(session)
        branch_id = session.scalars(select(Branch.id)).first()
        assert branch_id is not None
        _grant(
            session, user, ["roles.view"], [branch_id] if with_branch else [], scope_type=scope_type
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_shared_capability_does_not_merge_scopes_between_pos_and_backoffice_roles() -> None:
    with SessionLocal() as session:
        user = _user(session)
        user.allowed_surfaces = ["POS", "BACKOFFICE"]
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        session.add_all(
            [
                UserBranchAssignment(user_id=user.id, branch_id=branch_id)
                for branch_id in branches[:2]
            ]
        )
        pos_role, _ = _grant(session, user, ["orders.view"], [branches[0]])
        pos_role.surfaces = ["POS"]
        _grant(session, user, ["orders.view"], [branches[1]])
        session.commit()
        pos = resolve_authorization(session, user, surface="POS")
        backoffice = resolve_authorization(session, user, surface="BACKOFFICE")
        assert require_capability(pos, "orders.view").branch_ids == [branches[0]]
        assert require_capability(backoffice, "orders.view").branch_ids == [branches[1]]
        assert pos.authorization_version != backoffice.authorization_version


def test_resolver_reads_revocation_without_overwriting_pending_identity_edits() -> None:
    with SessionLocal() as session:
        user = _user(session)
        role, _ = _grant(session, user, ["orders.view"], [], scope_type="GLOBAL")
        session.commit()
        require_capability(
            resolve_authorization(session, user, surface="BACKOFFICE"), "orders.view"
        )
        user.full_name = "Pending profile edit"
        with SessionLocal() as other_session:
            other_session.execute(update(Role).where(Role.id == role.id).values(surfaces=["POS"]))
            other_session.commit()
        assert resolve_authorization(session, user, surface="BACKOFFICE").effective_grants == []
        assert user.full_name == "Pending profile edit"
        assert session.is_modified(user)


def test_moving_scope_row_cannot_leave_its_previous_assignment_empty() -> None:
    with SessionLocal() as session:
        user = _user(session)
        branches = list(session.scalars(select(Branch.id).order_by(Branch.code)))
        _, first = _grant(session, user, ["orders.view"], [branches[0]])
        _, second = _grant(session, user, ["orders.view"], [branches[1]])
        session.commit()
        session.execute(
            update(UserRoleAssignmentBranchScope)
            .where(
                UserRoleAssignmentBranchScope.assignment_id == first.id,
            )
            .values(assignment_id=second.id)
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_me_exposes_canonical_scopes_without_promoting_seed_administrator(
    client: TestClient,
) -> None:
    login = client.post(
        "/v1/auth/login", json={"email": SEED_ADMIN_EMAIL, "password": SEED_ADMIN_PASSWORD}
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/v1/auth/me", headers=headers)
    assert response.status_code == 200
    context = response.json()
    assert context == login.json()["user"]
    assert not context["is_superadministrator"]
    assert len(context["authorization_version"]) == 64
    assert context["effective_grants"]
    assert all(
        grant["scope_type"] == "BRANCH_SET" and grant["branch_ids"]
        for grant in context["effective_grants"]
    )
    with SessionLocal() as session:
        codes = set(session.scalars(select(Permission.code)))
        assert codes == set(PERMISSION_CODES)
        assert len(codes) == 55
