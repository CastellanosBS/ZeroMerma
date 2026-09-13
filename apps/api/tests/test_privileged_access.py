from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.branches.infrastructure.models import Branch
from zeromerma_api.modules.identity.application.permissions import SUPERADMIN_ROLE_CODE
from zeromerma_api.modules.identity.application.privileged_access import (
    PrivilegedAccessService,
    active_superadmin_ids,
)
from zeromerma_api.modules.identity.application.security import TokenService
from zeromerma_api.modules.identity.infrastructure.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserBranchAssignment,
    UserRoleAssignment,
    UserRoleAssignmentBranchScope,
)
from zeromerma_api.modules.identity.infrastructure.privileged_models import IdentityPrivilegedChange
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent

PREFIX = "/v1/admin/roles/privileged-changes"


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {TokenService().issue_access_token(user.id)}"}


def _new_user(email: str, *, surfaces: list[str] | None = None) -> User:
    return User(
        email=email,
        full_name=email.split("@")[0],
        password_hash="unused-test-password-hash",
        allowed_surfaces=surfaces or ["BACKOFFICE"],
        default_surface="BACKOFFICE",
        is_active=True,
        is_locked=False,
    )


def _pair() -> tuple[uuid.UUID, dict[str, str], uuid.UUID, dict[str, str], uuid.UUID]:
    with SessionLocal() as session:
        service = PrivilegedAccessService()
        owner = service.bootstrap_owner(
            session,
            email="first-owner@example.test",
            full_name="First owner",
            password="Only-test-password-123!",
            authorized_host="isolated-control-plane",
        )
        second = _new_user("second-owner@example.test")
        session.add(second)
        session.flush()
        service.recover_second_superadmin(
            session,
            target_user_id=second.id,
            recovery_material=owner.recovery_material,
            current_host="isolated-control-plane",
        )
        first = session.get(User, owner.user_id)
        assert first is not None
        role = session.scalars(select(Role).where(Role.code == SUPERADMIN_ROLE_CODE)).one()
        result = (first.id, _headers(first), second.id, _headers(second), role.id)
        session.commit()
        return result


def _propose(
    client: TestClient,
    headers: dict[str, str],
    *,
    operation: str,
    user_id: uuid.UUID | None = None,
    role_id: uuid.UUID | None = None,
    payload: dict[str, object],
) -> dict[str, object]:
    response = client.post(
        PREFIX,
        headers=headers,
        json={
            "operation": operation,
            "target_user_id": str(user_id) if user_id else None,
            "target_role_id": str(role_id) if role_id else None,
            "payload": payload,
            "reason": "Verified privileged lifecycle test",
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def _approve(client: TestClient, change: dict[str, object], headers: dict[str, str]) -> None:
    response = client.post(
        f"{PREFIX}/{change['id']}/approve",
        headers=headers,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert response.status_code == 200, response.text


def _trace_counts() -> tuple[int, int]:
    with SessionLocal() as session:
        return (
            session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.action != "authorization.denied")
            )
            or 0,
            session.scalar(select(func.count()).select_from(OutboxEvent)) or 0,
        )


def test_dual_approval_binds_payload_requires_distinct_actor_and_is_single_use(
    client: TestClient,
) -> None:
    first_id, first, second_id, second, _role = _pair()
    benign_profile = client.patch(
        f"/v1/admin/users/{second_id}",
        headers=first,
        json={
            "full_name": "Reviewed display name",
            "email": "second-owner@example.test",
            "allowed_surfaces": ["BACKOFFICE"],
            "default_surface": "BACKOFFICE",
        },
    )
    assert benign_profile.status_code == 200, benign_profile.text
    change = _propose(
        client,
        first,
        operation="USER_UPDATE",
        user_id=second_id,
        payload={"email": "second-approved@example.test"},
    )
    review = client.get(f"{PREFIX}/{change['id']}", headers=second)
    assert review.status_code == 200
    assert review.json()["payload"] == {"email": "second-approved@example.test"}
    self_approval = client.post(
        f"{PREFIX}/{change['id']}/approve",
        headers=first,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert self_approval.status_code == 403
    bad_hash = client.post(
        f"{PREFIX}/{change['id']}/approve", headers=second, json={"payload_sha256": "0" * 64}
    )
    assert bad_hash.status_code == 409
    _approve(client, change, second)
    before = _trace_counts()
    response = client.post(
        f"{PREFIX}/{change['id']}/execute",
        headers=first,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["consumed_at"] is not None
    assert response.json()["initiator_user_id"] == str(first_id)
    assert response.json()["approver_user_id"] == str(second_id)
    assert _trace_counts() == (before[0] + 2, before[1] + 2)
    replay_counts = _trace_counts()
    replay = client.post(
        f"{PREFIX}/{change['id']}/execute",
        headers=first,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert replay.status_code == 409
    assert _trace_counts() == replay_counts
    with SessionLocal() as session:
        target = session.get(User, second_id)
        assert target is not None and target.email == "second-approved@example.test"


@pytest.mark.parametrize("invalidator", ["expired", "approver_revoked", "payload_modified"])
def test_approval_revalidates_expiry_authority_and_persisted_payload(
    client: TestClient, invalidator: str
) -> None:
    _first_id, first, second_id, second, _role = _pair()
    change = _propose(
        client,
        first,
        operation="USER_UPDATE",
        user_id=second_id,
        payload={"email": "must-not-change@example.test"},
    )
    _approve(client, change, second)
    with SessionLocal() as session:
        row = session.get(IdentityPrivilegedChange, uuid.UUID(str(change["id"])))
        assert row is not None
        if invalidator == "expired":
            row.created_at = datetime.now(tz=UTC) - timedelta(hours=2)
            row.expires_at = datetime.now(tz=UTC) - timedelta(hours=1)
        elif invalidator == "approver_revoked":
            user = session.get(User, second_id)
            assert user is not None
            user.is_active = False
        else:
            row.payload = {"email": "tampered@example.test"}
        session.commit()
    before = _trace_counts()
    response = client.post(
        f"{PREFIX}/{change['id']}/execute",
        headers=first,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert response.status_code in {403, 409}, response.text
    assert _trace_counts() == before
    with SessionLocal() as session:
        user = session.get(User, second_id)
        row = session.get(IdentityPrivilegedChange, uuid.UUID(str(change["id"])))
        assert user is not None and user.email == "second-owner@example.test"
        assert row is not None and row.consumed_at is None


@pytest.mark.parametrize("removed", ["users.manage", "roles.manage", "role_assignments.manage"])
def test_approved_role_change_cannot_remove_privileged_administration(
    client: TestClient, removed: str
) -> None:
    _first_id, first, _second_id, second, role_id = _pair()
    with SessionLocal() as session:
        original = set(
            session.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role_id)
            )
        )
    change = _propose(
        client,
        first,
        operation="ROLE_UPDATE",
        role_id=role_id,
        payload={
            "permission_codes": sorted(original - {removed}),
            "confirmed_high_risk_change": True,
        },
    )
    _approve(client, change, second)
    before = _trace_counts()
    response = client.post(
        f"{PREFIX}/{change['id']}/execute",
        headers=first,
        json={"payload_sha256": change["payload_sha256"]},
    )
    assert response.status_code == 409, response.text
    assert _trace_counts() == before
    with SessionLocal() as session:
        after = set(
            session.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role_id)
            )
        )
        assert after == original
        row = session.get(IdentityPrivilegedChange, uuid.UUID(str(change["id"])))
        assert row is not None and row.consumed_at is None


def test_concurrent_cross_revocations_leave_one_active_superadministrator(
    client: TestClient,
) -> None:
    first_id, first, second_id, second, role_id = _pair()
    remove_second = _propose(
        client, first, operation="ROLE_REMOVAL", user_id=second_id, role_id=role_id, payload={}
    )
    remove_first = _propose(
        client, second, operation="ROLE_REMOVAL", user_id=first_id, role_id=role_id, payload={}
    )
    _approve(client, remove_second, second)
    _approve(client, remove_first, first)

    def execute(pair: tuple[dict[str, object], dict[str, str]]) -> int:
        change, headers = pair
        return client.post(
            f"{PREFIX}/{change['id']}/execute",
            headers=headers,
            json={"payload_sha256": change["payload_sha256"]},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(execute, [(remove_second, first), (remove_first, second)]))
    assert statuses.count(200) == 1, statuses
    assert all(status in {200, 403, 409} for status in statuses), statuses
    with SessionLocal() as session:
        assert len(active_superadmin_ids(session)) == 1
        assert (
            session.scalar(
                select(func.count())
                .select_from(IdentityPrivilegedChange)
                .where(IdentityPrivilegedChange.consumed_at.is_not(None))
            )
            == 1
        )


def _scoped_actor() -> tuple[dict[str, str], uuid.UUID, uuid.UUID, uuid.UUID]:
    with SessionLocal() as session:
        branches = list(
            session.scalars(select(Branch).where(Branch.is_active.is_(True)).order_by(Branch.code))
        )
        north, south = branches[:2]
        actor = _new_user("scoped-identity@example.test")
        role = Role(
            code="scoped_identity_test",
            name="Scoped identity",
            surfaces=["BACKOFFICE"],
            is_active=True,
            is_system=False,
        )
        session.add_all([actor, role])
        session.flush()
        capabilities = ["users.view", "users.manage", "roles.view", "role_assignments.manage"]
        session.add_all(
            [
                RolePermission(role_id=role.id, permission_id=permission.id)
                for permission in session.scalars(
                    select(Permission).where(Permission.code.in_(capabilities))
                )
            ]
        )
        membership = UserBranchAssignment(
            user_id=actor.id, branch_id=north.id, is_active=True, is_default=True
        )
        assignment = UserRoleAssignment(
            user_id=actor.id, role_id=role.id, scope_type="BRANCH_SET", is_active=True
        )
        session.add_all([membership, assignment])
        session.flush()
        session.add(UserRoleAssignmentBranchScope(assignment_id=assignment.id, branch_id=north.id))
        result = (_headers(actor), actor.id, north.id, south.id)
        session.commit()
        return result


def test_user_scope_is_applied_before_list_count_and_checks_full_target_boundary(
    client: TestClient,
) -> None:
    headers, _actor_id, north, south = _scoped_actor()
    with SessionLocal() as session:
        local, both, global_user = [
            _new_user(f"boundary-{name}@example.test") for name in ["north", "both", "global"]
        ]
        session.add_all([local, both, global_user])
        session.flush()
        session.add_all(
            [
                UserBranchAssignment(
                    user_id=user.id, branch_id=branch, is_active=True, is_default=branch == north
                )
                for user, branch in [
                    (local, north),
                    (both, north),
                    (both, south),
                    (global_user, north),
                ]
            ]
        )
        role = session.scalars(select(Role).where(Role.code == "scoped_identity_test")).one()
        session.add(
            UserRoleAssignment(
                user_id=global_user.id, role_id=role.id, scope_type="GLOBAL", is_active=True
            )
        )
        ids = (local.id, both.id, global_user.id)
        session.commit()
    response = client.get("/v1/admin/users?search=boundary-&page_size=1", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1
    assert response.json()["metrics"]["total_users"] == 1
    assert response.json()["items"][0]["id"] == str(ids[0])
    role_response = client.get("/v1/admin/roles", headers=headers)
    assert role_response.status_code == 200, role_response.text
    before = _trace_counts()
    for target in ids[1:]:
        assert client.get(f"/v1/admin/users/{target}", headers=headers).status_code == 403
        response = client.patch(
            f"/v1/admin/users/{target}",
            headers=headers,
            json={"full_name": "Denied", "notes": "sensitive-denied-body-value"},
        )
        assert response.status_code == 403, response.text
    assert _trace_counts() == before
    with SessionLocal() as session:
        denial_records = list(
            session.scalars(select(AuditLog).where(AuditLog.action == "authorization.denied"))
        )
        assert len(denial_records) >= 4
        assert all(
            "sensitive-denied-body-value" not in str(row.metadata_) for row in denial_records
        )
    assert (
        client.patch(
            f"/v1/admin/users/{ids[0]}",
            headers=headers,
            json={"full_name": "Authorized local edit"},
        ).status_code
        == 200
    )


def test_branch_and_role_assignment_cannot_self_elevate_or_infer_global(client: TestClient) -> None:
    headers, actor_id, north, south = _scoped_actor()
    with SessionLocal() as session:
        role_id = session.scalars(select(Role.id).where(Role.code == "scoped_identity_test")).one()
    before = _trace_counts()
    missing_scope = client.post(
        f"/v1/admin/users/{actor_id}/roles", headers=headers, json={"role_id": str(role_id)}
    )
    assert missing_scope.status_code == 422
    for payload in [
        {"scope_type": "GLOBAL", "branch_ids": []},
        {"scope_type": "BRANCH_SET", "branch_ids": [str(north), str(south)]},
    ]:
        response = client.post(
            f"/v1/admin/users/{actor_id}/roles",
            headers=headers,
            json={"role_id": str(role_id), **payload},
        )
        assert response.status_code == 403, response.text
    response = client.post(
        f"/v1/admin/users/{actor_id}/branch-assignments",
        headers=headers,
        json={"branch_id": str(south)},
    )
    assert response.status_code == 403
    response = client.patch(
        f"/v1/admin/users/{actor_id}",
        headers=headers,
        json={"allowed_surfaces": ["BACKOFFICE", "POS"]},
    )
    assert response.status_code == 403
    assert _trace_counts() == before


def test_users_manage_cannot_grant_roles_or_application_access(client: TestClient) -> None:
    headers, actor_id, north, _south = _scoped_actor()
    with SessionLocal() as session:
        role = session.scalars(select(Role).where(Role.code == "scoped_identity_test")).one()
        grant = session.scalars(
            select(RolePermission)
            .join(Permission)
            .where(RolePermission.role_id == role.id, Permission.code == "role_assignments.manage")
        ).one()
        session.delete(grant)
        target = _new_user("profile-only-target@example.test")
        session.add(target)
        session.flush()
        session.add(
            UserBranchAssignment(
                user_id=target.id, branch_id=north, is_active=True, is_default=True
            )
        )
        target_id, role_id = target.id, role.id
        session.commit()
    before = _trace_counts()
    response = client.patch(
        f"/v1/admin/users/{target_id}",
        headers=headers,
        json={"allowed_surfaces": ["BACKOFFICE", "POS"]},
    )
    assert response.status_code == 403
    response = client.post(
        f"/v1/admin/users/{target_id}/roles",
        headers=headers,
        json={"role_id": str(role_id), "scope_type": "BRANCH_SET", "branch_ids": [str(north)]},
    )
    assert response.status_code == 403
    assert _trace_counts() == before
    response = client.get(f"/v1/admin/users/{actor_id}", headers=headers)
    assert response.status_code == 200
    actions = response.json()["available_actions"]
    assert actions["can_edit_profile"] is True
    assert actions["can_edit_app_access"] is False
    assert actions["can_edit_role_assignments"] is False


def test_global_identity_manager_cannot_add_own_role_authority_or_membership(
    client: TestClient,
) -> None:
    headers, actor_id, _north, south = _scoped_actor()
    with SessionLocal() as session:
        role = session.scalars(select(Role).where(Role.code == "scoped_identity_test")).one()
        assignment = session.scalars(
            select(UserRoleAssignment).where(UserRoleAssignment.user_id == actor_id)
        ).one()
        assignment.scope_type = "GLOBAL"
        session.execute(
            delete(UserRoleAssignmentBranchScope).where(
                UserRoleAssignmentBranchScope.assignment_id == assignment.id
            )
        )
        permission = session.scalars(
            select(Permission).where(Permission.code == "roles.manage")
        ).one()
        session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        role_id = role.id
        session.commit()
    before = _trace_counts()
    response = client.patch(
        f"/v1/admin/roles/{role_id}",
        headers=headers,
        json={
            "permission_codes": [
                "users.view",
                "users.manage",
                "roles.view",
                "roles.manage",
                "role_assignments.manage",
                "catalog.view",
            ],
            "confirmed_high_risk_change": True,
        },
    )
    assert response.status_code == 403, response.text
    response = client.post(
        f"/v1/admin/users/{actor_id}/branch-assignments",
        headers=headers,
        json={"branch_id": str(south)},
    )
    assert response.status_code == 403, response.text
    assert _trace_counts() == before
    with SessionLocal() as session:
        assert (
            session.scalar(
                select(RolePermission.id)
                .join(Permission)
                .where(RolePermission.role_id == role_id, Permission.code == "catalog.view")
            )
            is None
        )
        assert (
            session.scalar(
                select(UserBranchAssignment.id).where(
                    UserBranchAssignment.user_id == actor_id,
                    UserBranchAssignment.branch_id == south,
                )
            )
            is None
        )


def test_user_assignment_endpoints_persist_explicit_scope_and_revoke_authority(
    client: TestClient,
) -> None:
    headers, _actor_id, north, _south = _scoped_actor()
    with SessionLocal() as session:
        target = _new_user("explicit-assignment-target@example.test")
        session.add(target)
        session.flush()
        session.add(
            UserBranchAssignment(
                user_id=target.id, branch_id=north, is_active=True, is_default=True
            )
        )
        role_id = session.scalars(select(Role.id).where(Role.code == "scoped_identity_test")).one()
        target_id, target_headers = target.id, _headers(target)
        session.commit()
    before = _trace_counts()
    response = client.post(
        f"/v1/admin/users/{target_id}/roles",
        headers=headers,
        json={"role_id": str(role_id), "scope_type": "BRANCH_SET", "branch_ids": [str(north)]},
    )
    assert response.status_code == 200, response.text
    item = response.json()["role_assignments"]["items"][0]
    assert item["scope_type"] == "BRANCH_SET" and item["branch_ids"] == [str(north)]
    assert client.get("/v1/admin/users", headers=target_headers).status_code == 200
    response = client.post(f"/v1/admin/users/{target_id}/roles/{role_id}/remove", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["role_assignments"]["items"] == []
    assert client.get("/v1/admin/users", headers=target_headers).status_code == 403
    assert _trace_counts() == (before[0] + 2, before[1] + 2)
    with SessionLocal() as session:
        records = list(
            session.scalars(
                select(AuditLog)
                .where(
                    AuditLog.resource_id == str(target_id),
                    AuditLog.action == "admin.user.role_assignment_changed",
                )
                .order_by(AuditLog.occurred_at)
            )
        )
        assert records[0].metadata_["previous_assignment"] is None
        assert records[0].metadata_["current_assignment"]["branch_ids"] == [str(north)]
        assert records[1].metadata_["previous_assignment"]["is_active"] is True
        assert records[1].metadata_["current_assignment"]["is_active"] is False
