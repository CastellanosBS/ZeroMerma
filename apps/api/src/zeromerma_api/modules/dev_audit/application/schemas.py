from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

ScopeStatus = Literal["direct", "partial", "global", "unavailable"]


class DevAuditDatabaseOverview(BaseModel):
    dev_audit_feature_enabled: bool
    scope_summary: str
    total_tracked_tables: int
    available_tables: int
    warnings: list[str] = Field(default_factory=list)


class DevAuditFiltersApplied(BaseModel):
    requested_branch_code: str | None = None
    requested_workstation_code: str | None = None
    resolved_branch_id: UUID | None = None
    resolved_branch_code: str | None = None
    resolved_workstation_id: UUID | None = None
    resolved_workstation_code: str | None = None
    scope_inferred_from_workstation: bool = False
    include_recent_rows: bool = True
    recent_limit: int = Field(default=5, ge=1, le=20)


class DevAuditTableSnapshot(BaseModel):
    table_name: str
    row_count: int
    scoped_row_count: int | None = None
    latest_timestamp_field_used: str | None = None
    latest_timestamp_value: datetime | None = None
    scope_status: ScopeStatus = "global"
    scope_note: str | None = None
    recent_rows: list[dict[str, Any]] = Field(default_factory=list)


class DevAuditSnapshotResponse(BaseModel):
    generated_at: datetime
    environment: str
    snapshot_version: str
    database_overview: DevAuditDatabaseOverview
    filters_applied: DevAuditFiltersApplied
    tables: list[DevAuditTableSnapshot]
