"""Private runtime secret files; credentials are never accepted as command arguments."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

_ACL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$path = $env:ZEROMERMA_PRIVATE_FILE_PATH
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$acl = Get-Acl -LiteralPath $path
if ($env:ZEROMERMA_PRIVATE_FILE_ACTION -eq 'protect') {
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.Access)) { $null = $acl.RemoveAccessRuleSpecific($rule) }
    $acl.SetOwner($identity.User)
    $acl.AddAccessRule([System.Security.AccessControl.FileSystemAccessRule]::new(
        $identity.User, 'FullControl', 'Allow'))
    Set-Acl -LiteralPath $path -AclObject $acl
    $acl = Get-Acl -LiteralPath $path
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


def private_permissions(path: Path, *, protect: bool = False) -> None:
    if sys.platform == "win32":
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if executable is None:
            raise ValueError("PowerShell is required to validate private runtime files.")
        environment = dict(os.environ)
        environment["ZEROMERMA_PRIVATE_FILE_PATH"] = str(path)
        environment["ZEROMERMA_PRIVATE_FILE_ACTION"] = "protect" if protect else "check"
        result = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", _ACL_SCRIPT],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode:
            raise ValueError("Runtime secret files must be readable only by their owning account.")
    else:
        if protect:
            path.chmod(0o600)
        metadata = path.stat()
        getuid = getattr(os, "getuid", None)
        if getuid is None or metadata.st_uid != getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
            raise ValueError(
                "Runtime secret files require current-account ownership and mode 0600."
            )


def read_private_secret(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise ValueError("Runtime secret input must be a bounded regular private file.")
    private_permissions(path)
    try:
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise ValueError("Runtime secret file cannot be read.") from error
    if not value or "\n" in value or "\r" in value:
        raise ValueError("Runtime secret input must contain one nonempty value.")
    return value


def write_private_secret(path: Path, value: str) -> None:
    if not value or "\n" in value or "\r" in value:
        raise ValueError("Runtime secret output requires one nonempty value.")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        private_permissions(path, protect=True)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n", closefd=False) as stream:
            stream.write(value + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        os.close(descriptor)
        path.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)
