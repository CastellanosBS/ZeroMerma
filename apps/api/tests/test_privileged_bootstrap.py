from __future__ import annotations

import argparse
import hashlib
import json
import socket
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from zeromerma_api.bootstrap.seed_local import SEED_ADMIN_EMAIL
from zeromerma_api.db import session as database_session
from zeromerma_api.db.session import SessionLocal
from zeromerma_api.modules.audit.infrastructure.models import AuditLog
from zeromerma_api.modules.identity import cli
from zeromerma_api.modules.identity.application.authorization import resolve_authorization
from zeromerma_api.modules.identity.application.privileged_access import (
    INITIAL_SUPERADMIN_PERMISSION_CODES,
    PrivilegedAccessService,
    active_superadmin_ids,
)
from zeromerma_api.modules.identity.infrastructure.models import (
    Role,
    RolePermission,
    User,
    UserRoleAssignment,
)
from zeromerma_api.modules.identity.infrastructure.privileged_models import (
    IdentityRecoveryCredential,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


def test_owner_bootstrap_never_promotes_seed_or_runs_twice_and_recovery_is_one_use() -> None:
    service = PrivilegedAccessService()
    with SessionLocal() as session:
        with pytest.raises(ValueError, match="existing accounts cannot be promoted"):
            service.bootstrap_owner(
                session,
                email=SEED_ADMIN_EMAIL,
                full_name="Rejected",
                password="Test-owner-password-42",
                authorized_host="control-plane",
            )
        session.rollback()
        result = service.bootstrap_owner(
            session,
            email="designated@example.test",
            full_name="Designated Owner",
            password="Test-owner-password-42",
            authorized_host="control-plane",
        )
        session.commit()
        assert active_superadmin_ids(session) == {result.user_id}
        global_assignments = list(
            session.scalars(
                select(UserRoleAssignment).where(UserRoleAssignment.scope_type == "GLOBAL")
            )
        )
        assert len(global_assignments) == 1 and global_assignments[0].user_id == result.user_id
        owner = session.get(User, result.user_id)
        assert owner is not None
        assert resolve_authorization(session, owner, surface="BACKOFFICE").is_superadministrator
        assert (
            session.scalar(
                select(func.count())
                .select_from(RolePermission)
                .join(Role)
                .where(Role.code == "explicit_superadmin")
            )
            == len(INITIAL_SUPERADMIN_PERMISSION_CODES)
            == 55
        )
        with pytest.raises(ValueError, match="already occurred"):
            service.bootstrap_owner(
                session,
                email="another@example.test",
                full_name="Rejected",
                password="Test-owner-password-42",
                authorized_host="control-plane",
            )
        session.rollback()
        second_id = session.scalar(select(User.id).where(User.email == SEED_ADMIN_EMAIL))
        assert second_id is not None
        with pytest.raises(ValueError, match="unauthorized on this host"):
            service.recover_second_superadmin(
                session,
                target_user_id=second_id,
                recovery_material=result.recovery_material,
                current_host="wrong-host",
            )
        session.rollback()
        replacement = service.recover_second_superadmin(
            session,
            target_user_id=second_id,
            recovery_material=result.recovery_material,
            current_host="control-plane",
        )
        session.commit()
        assert active_superadmin_ids(session) == {result.user_id, second_id}
        assert replacement.recovery_material != result.recovery_material
        assert (
            session.scalar(
                select(func.count())
                .select_from(IdentityRecoveryCredential)
                .where(IdentityRecoveryCredential.consumed_at.is_not(None))
            )
            == 1
        )
        with pytest.raises(ValueError):
            service.recover_second_superadmin(
                session,
                target_user_id=second_id,
                recovery_material=result.recovery_material,
                current_host="control-plane",
            )
        session.rollback()
        audit = list(
            session.scalars(
                select(AuditLog).where(
                    AuditLog.action.in_(
                        ["identity.owner.provisioned", "identity.superadmin.recovered"]
                    )
                )
            )
        )
        assert {row.action for row in audit} == {
            "identity.owner.provisioned",
            "identity.superadmin.recovered",
        }
        payloads = json.dumps([row.metadata_ for row in audit]) + json.dumps(
            list(session.scalars(select(OutboxEvent.payload)))
        )
        assert result.recovery_material not in payloads
        assert replacement.recovery_material not in payloads


@pytest.mark.parametrize("publish_failure", [False, True])
def test_cli_provisions_and_rotates_private_material_without_printing_secrets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    publish_failure: bool,
) -> None:
    recovery_file = tmp_path / "owner-recovery.json"
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "Private-cli-test-password-42")
    bootstrap = argparse.Namespace(
        command="bootstrap-owner",
        designation="ZEROMERMA_OWNER",
        email="cli-owner@example.test",
        full_name="CLI Owner",
        recovery_file=recovery_file,
    )
    assert cli.run_command(bootstrap) == 0
    before = cli.read_recovery_file(recovery_file)
    assert before["authorized_host"] == socket.getfqdn().strip().lower()
    with SessionLocal() as session:
        target_id = session.scalar(select(User.id).where(User.email == SEED_ADMIN_EMAIL))
    recover = argparse.Namespace(
        command="recover-second-superadmin", target_user_id=target_id, recovery_file=recovery_file
    )
    if publish_failure:

        def reject_publish(source: Path, target: Path) -> None:
            raise OSError("Controlled publish failure")

        monkeypatch.setattr(cli.os, "replace", reject_publish)
    assert cli.run_command(recover) == (2 if publish_failure else 0)
    retained = list(tmp_path.glob("*.next-*"))
    assert len(retained) == (1 if publish_failure else 0)
    after = cli.read_recovery_file(retained[0] if publish_failure else recovery_file)
    assert before["recovery_material"] != after["recovery_material"]
    captured = capsys.readouterr()
    assert before["recovery_material"] not in captured.out + captured.err
    assert after["recovery_material"] not in captured.out + captured.err
    assert "Private-cli-test-password-42" not in captured.out + captured.err


def test_two_concurrent_initial_owner_provisions_create_exactly_one_authority() -> None:
    barrier = Barrier(2)

    def provision(index: int) -> str:
        with SessionLocal() as session:
            barrier.wait(timeout=10)
            try:
                PrivilegedAccessService().bootstrap_owner(
                    session,
                    email=f"racing-owner-{index}@example.test",
                    full_name="Concurrent Owner",
                    password="Concurrent-test-password-42",
                    authorized_host="test-control-plane",
                )
                session.commit()
                return "created"
            except ValueError as error:
                session.rollback()
                assert "already occurred" in str(error)
                return "rejected"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(provision, index) for index in range(2)]
        assert sorted(future.result(timeout=20) for future in futures) == ["created", "rejected"]
    with SessionLocal() as session:
        assert len(active_superadmin_ids(session)) == 1
        assert (
            session.scalar(
                select(func.count()).select_from(User).where(User.email.like("racing-owner-%"))
            )
            == 1
        )
        assert session.scalar(select(func.count()).select_from(IdentityRecoveryCredential)) == 1


@pytest.mark.parametrize("recover", [False, True])
def test_cli_preserves_private_material_when_committed_transaction_loses_acknowledgement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    recover: bool,
) -> None:
    recovery_file = tmp_path / "uncertain-recovery.json"
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "Private-cli-test-password-42")
    command = argparse.Namespace(
        command="bootstrap-owner",
        designation="ZEROMERMA_OWNER",
        email="uncertain-owner@example.test",
        full_name="Uncertain Commit Owner",
        recovery_file=recovery_file,
    )
    if recover:
        assert cli.run_command(command) == 0
        with SessionLocal() as session:
            target_id = session.scalar(select(User.id).where(User.email == SEED_ADMIN_EMAIL))
        command = argparse.Namespace(
            command="recover-second-superadmin",
            target_user_id=target_id,
            recovery_file=recovery_file,
        )

    class LostAcknowledgementSession(Session):
        def commit(self) -> None:
            super().commit()
            raise OSError("Controlled failure after PostgreSQL committed")

    monkeypatch.setattr(
        database_session,
        "SessionLocal",
        sessionmaker(bind=database_session.engine, class_=LostAcknowledgementSession),
    )
    assert cli.run_command(command) == 2
    candidates = list(tmp_path.glob("*.next-*")) if recover else [recovery_file]
    assert len(candidates) == 1
    retained = cli.read_recovery_file(candidates[0])
    digest = hashlib.sha256(retained["recovery_material"].encode()).hexdigest()
    with SessionLocal() as session:
        credential = session.scalar(
            select(IdentityRecoveryCredential).where(
                IdentityRecoveryCredential.token_sha256 == digest
            )
        )
        assert credential is not None
        assert credential.consumed_at is None
        assert len(active_superadmin_ids(session)) == (2 if recover else 1)
    captured = capsys.readouterr()
    assert "outcome requires verification" in captured.err
    assert retained["recovery_material"] not in captured.out + captured.err
    assert "Private-cli-test-password-42" not in captured.out + captured.err
