"""Durable device deduplication and FIFO without storing receipt or customer data locally."""

import os
import re
import sqlite3
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Literal, Protocol
from uuid import UUID

from zeromerma_api.modules.hardware.domain.commands import (
    DeviceCommand,
    DeviceCommandResult,
    SignedDeviceCommand,
    command_digest,
    verify_device_command,
)


class DeviceAdapter(Protocol):
    def execute(self, command: DeviceCommand, *, timeout_seconds: float) -> DeviceCommandResult: ...


@dataclass(frozen=True)
class PairedDevice:
    device_id: UUID
    branch_id: UUID
    workstation_id: UUID
    binding_version: int
    environment: Literal["SANDBOX", "PRODUCTION"]
    origin: str
    capabilities: frozenset[str]
    adapter: DeviceAdapter


class LocalHardwareBridge:
    def __init__(
        self, database_path: Path, pairing_key: bytes, devices: list[PairedDevice]
    ) -> None:
        if len(pairing_key) < 32:
            raise ValueError("Pairing keys require at least 256 bits.")
        self._key = pairing_key
        self._path = database_path
        self._devices = {item.device_id: item for item in devices}
        if len(self._devices) != len(devices):
            raise ValueError("Each local device must have one explicit pairing.")
        self._locks = {item.device_id: Lock() for item in devices}
        descriptor = os.open(str(database_path) + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        self._owner = os.fdopen(descriptor, "r+b")
        if sys.platform == "win32":
            import msvcrt

            if os.fstat(self._owner.fileno()).st_size == 0:
                self._owner.write(b"0")
                self._owner.flush()
            self._owner.seek(0)
            try:
                msvcrt.locking(self._owner.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                self._owner.close()
                raise ValueError("Another bridge owns this device spool.") from None
        else:
            import fcntl

            try:
                fcntl.flock(self._owner.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self._owner.close()
                raise ValueError("Another bridge owns this device spool.") from None
        with self._connection() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS device_jobs (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL UNIQUE, device_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL, state TEXT NOT NULL,
                evidence_reference TEXT)""")
            # A crash after claiming may have performed the physical action. Never resend it.
            connection.execute("UPDATE device_jobs SET state='UNKNOWN' WHERE state='PROCESSING'")

    def close(self) -> None:
        self._owner.close()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self._path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA synchronous=FULL")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def submit(self, grant: SignedDeviceCommand, *, origin: str) -> DeviceCommandResult:
        command, device = self._authorize(grant, origin)
        return self._execute(command, device)

    def status(self, grant: SignedDeviceCommand, *, origin: str) -> DeviceCommandResult:
        command, _ = self._authorize(grant, origin)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM device_jobs WHERE id=?", (str(command.id),)
            ).fetchone()
            if row is None:
                return DeviceCommandResult(command_id=command.id, state="UNKNOWN")
            if row["fingerprint"] != command_digest(command):
                raise ValueError("The command identity has different content.")
            return DeviceCommandResult.model_validate(
                {
                    "command_id": command.id,
                    "state": row["state"],
                    "evidence_reference": row["evidence_reference"],
                }
            )

    def _authorize(
        self, grant: SignedDeviceCommand, origin: str
    ) -> tuple[DeviceCommand, PairedDevice]:
        verify_device_command(grant, self._key)
        command = grant.command
        device = self._devices.get(command.device_id)
        if device is None or (
            origin != device.origin
            or command.origin != device.origin
            or command.branch_id != device.branch_id
            or command.workstation_id != device.workstation_id
            or command.binding_version != device.binding_version
            or command.environment != device.environment
            or command.kind not in device.capabilities
        ):
            raise ValueError("The device authorization does not match this pairing.")
        return command, device

    def _execute(self, command: DeviceCommand, device: PairedDevice) -> DeviceCommandResult:
        digest = command_digest(command)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT OR IGNORE INTO device_jobs(id,device_id,fingerprint,state) "
                "VALUES(?,?,?,'QUEUED')",
                (str(command.id), str(command.device_id), digest),
            )
            row = connection.execute(
                "SELECT * FROM device_jobs WHERE id=?", (str(command.id),)
            ).fetchone()
            if row["fingerprint"] != digest:
                raise ValueError(
                    "A device command identity cannot be reused with different content."
                )
        lock = self._locks[command.device_id]
        if row["state"] not in {"QUEUED", "PROCESSING"}:
            return DeviceCommandResult.model_validate(
                {
                    "command_id": command.id,
                    "state": row["state"],
                    "evidence_reference": row["evidence_reference"],
                }
            )
        if not lock.acquire(blocking=False):
            return DeviceCommandResult(
                command_id=command.id,
                state="PROCESSING" if row["state"] == "PROCESSING" else "QUEUED",
            )
        try:
            with self._connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    "SELECT * FROM device_jobs WHERE id=?", (str(command.id),)
                ).fetchone()
                if row["state"] != "QUEUED":
                    return DeviceCommandResult.model_validate(
                        {
                            "command_id": command.id,
                            "state": row["state"],
                            "evidence_reference": row["evidence_reference"],
                        }
                    )
                first = connection.execute(
                    "SELECT id FROM device_jobs WHERE device_id=? AND state='QUEUED' "
                    "ORDER BY sequence LIMIT 1",
                    (str(command.device_id),),
                ).fetchone()
                if first["id"] != str(command.id):
                    return DeviceCommandResult(command_id=command.id, state="QUEUED")
                connection.execute(
                    "UPDATE device_jobs SET state='PROCESSING' WHERE id=?", (str(command.id),)
                )
            try:
                result = device.adapter.execute(command, timeout_seconds=5.0)
                if result.command_id != command.id or result.state in {"QUEUED", "PROCESSING"}:
                    raise ValueError("The adapter returned an invalid result.")
                if result.state in {"PRINTED", "OPENED"} and (
                    (result.state == "PRINTED") != (command.kind == "PRINT")
                    or not result.evidence_reference
                ):
                    raise ValueError("Physical completion requires matching device evidence.")
                if result.evidence_reference is not None and not re.fullmatch(
                    r"[A-Za-z0-9_.:-]{1,120}", result.evidence_reference
                ):
                    raise ValueError("Adapter diagnostics must be opaque and sanitized.")
            except Exception:
                # Driver exceptions can contain device/customer data. Persist only uncertainty.
                result = DeviceCommandResult(command_id=command.id, state="UNKNOWN")
            with self._connection() as connection:
                connection.execute(
                    "UPDATE device_jobs SET state=?, evidence_reference=? WHERE id=?",
                    (result.state, result.evidence_reference, str(command.id)),
                )
            return result
        finally:
            lock.release()
