"""Local owner provisioning and one-use recovery; never exposed through HTTP."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import uuid
from pathlib import Path

from zeromerma_api.modules.identity.application.permissions import INITIAL_OWNER_DESIGNATION

_ACL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$materialPath = $env:ZEROMERMA_RECOVERY_MATERIAL_PATH
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$acl = Get-Acl -LiteralPath $materialPath
if ($env:ZEROMERMA_RECOVERY_ACL_ACTION -eq 'protect') {
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { $acl.RemoveAccessRuleSpecific($rule) }
    $acl.SetOwner($identity.User)
    $rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
        $identity.User, 'FullControl', 'Allow')
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $materialPath -AclObject $acl
    $acl = Get-Acl -LiteralPath $materialPath
}
if ($acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value -ne $identity.User.Value) {
    exit 2
}
foreach ($rule in $acl.GetAccessRules(
    $true, $true, [System.Security.Principal.SecurityIdentifier])) {
    if ($rule.AccessControlType -eq 'Allow' -and
        $rule.IdentityReference.Value -ne $identity.User.Value -and
        ([int]$rule.FileSystemRights -band 1) -ne 0) { exit 3 }
}
"""


def _private_permissions(path: Path, *, protect: bool) -> None:
    if os.name == "nt":
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if executable is None:
            raise ValueError("PowerShell is required to enforce private recovery-file permissions.")
        environment = dict(os.environ)
        environment["ZEROMERMA_RECOVERY_MATERIAL_PATH"] = str(path)
        environment["ZEROMERMA_RECOVERY_ACL_ACTION"] = "protect" if protect else "check"
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", _ACL_SCRIPT],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise ValueError(
                "Recovery-file permissions must allow only the current account to read it."
            )
    else:
        if protect:
            path.chmod(0o600)
        metadata = path.stat()
        getuid = getattr(os, "getuid", None)
        if getuid is None or metadata.st_uid != getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError("Recovery files must be owned by the current account with mode 0600.")


def read_recovery_file(path: Path) -> dict[str, str]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Recovery input must be a regular private file, not a symbolic link.")
    _private_permissions(path, protect=False)
    if path.stat().st_size > 8192:
        raise ValueError("Recovery file is invalid.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError("Recovery file is invalid.") from error
    if (
        not isinstance(payload, dict)
        or payload.get("version") != 1
        or not isinstance(payload.get("authorized_host"), str)
        or not isinstance(payload.get("recovery_material"), str)
        or not 48 <= len(payload["recovery_material"]) <= 512
    ):
        raise ValueError("Recovery file is invalid.")
    return {
        "authorized_host": payload["authorized_host"],
        "recovery_material": payload["recovery_material"],
    }


def write_recovery_file(path: Path, *, host: str, material: str) -> None:
    """Reserve a new file, restrict access before writing, and durably flush its contents."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o600)
    try:
        _private_permissions(path, protect=True)
        payload = json.dumps({"version": 1, "authorized_host": host, "recovery_material": material})
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n", closefd=False) as stream:
            stream.write(payload + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser(
        "bootstrap-owner", help="Provision the designated initial owner once."
    )
    bootstrap.add_argument("--designation", required=True, choices=[INITIAL_OWNER_DESIGNATION])
    bootstrap.add_argument("--email", required=True)
    bootstrap.add_argument("--full-name", required=True)
    bootstrap.add_argument("--recovery-file", type=Path, required=True)
    recover = commands.add_parser(
        "recover-second-superadmin", help="Consume recovery material to promote a second owner."
    )
    recover.add_argument("--target-user-id", type=uuid.UUID, required=True)
    recover.add_argument("--recovery-file", type=Path, required=True)
    return parser


def run_command(arguments: argparse.Namespace) -> int:
    from zeromerma_api.db.session import SessionLocal
    from zeromerma_api.modules.identity.application.privileged_access import PrivilegedAccessService

    host = socket.getfqdn().strip().lower()
    recovery_path = arguments.recovery_file.absolute()
    if recovery_path.is_symlink():
        raise ValueError("Recovery paths cannot be symbolic links.")
    if not recovery_path.parent.is_dir():
        raise ValueError("Create the private recovery directory before provisioning.")
    service = PrivilegedAccessService()
    output_path = recovery_path
    recovery_input: dict[str, str] | None = None
    password: str | None = None
    if arguments.command == "bootstrap-owner":
        if recovery_path.exists():
            raise ValueError("Initial recovery output must be a new file.")
        if not sys.stdin.isatty():
            raise ValueError(
                "Owner passwords must be entered through an interactive private terminal."
            )
        password = getpass.getpass("Initial owner password: ")
        if password != getpass.getpass("Confirm initial owner password: "):
            raise ValueError("Password confirmation does not match.")
    else:
        recovery_input = read_recovery_file(recovery_path)
        if recovery_input["authorized_host"] != host:
            raise ValueError("This host is not authorized to use the recovery material.")
        output_path = recovery_path.with_name(recovery_path.name + f".next-{uuid.uuid4().hex}")
    file_written = False
    commit_attempted = False
    try:
        with SessionLocal() as session:
            if arguments.command == "bootstrap-owner":
                assert password is not None
                result = service.bootstrap_owner(
                    session,
                    email=arguments.email,
                    full_name=arguments.full_name,
                    password=password,
                    authorized_host=host,
                    designation=arguments.designation,
                )
            else:
                assert recovery_input is not None
                result = service.recover_second_superadmin(
                    session,
                    target_user_id=arguments.target_user_id,
                    recovery_material=recovery_input["recovery_material"],
                    current_host=host,
                )
            write_recovery_file(output_path, host=host, material=result.recovery_material)
            file_written = True
            commit_attempted = True
            session.commit()
        if output_path != recovery_path:
            try:
                os.replace(output_path, recovery_path)
                output_path = recovery_path
            except OSError:
                print(
                    f"Recovery committed. Rotated material is retained in {output_path}; "
                    "the previous material is consumed. Secure this file before continuing.",
                    file=sys.stderr,
                )
                return 2
        print(
            f"Privileged access recorded for user {result.user_id}. Recovery file: {recovery_path}"
        )
        return 0
    except Exception:
        if file_written and commit_attempted:
            # A lost commit acknowledgement does not prove rollback. Keep the only successor.
            print(
                f"Database commit outcome requires verification. Private recovery material "
                f"is retained in {output_path}. The previous material may be consumed; "
                "verify the recorded owner and recovery credential before retrying.",
                file=sys.stderr,
            )
            return 2
        raise
    finally:
        if file_written and not commit_attempted:
            output_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        return run_command(arguments)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        # Driver exceptions may include parameters; never echo them on this CLI.
        print(
            "Privileged access was not completed. "
            "Verify database access and private file permissions.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
