from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditActorSummaryView(BaseModel):
    user_id: UUID
    full_name: str
    email: str | None = None


class AuditNotificationSummaryView(BaseModel):
    label: str
    status: str
    occurred_at_utc: datetime
    processed_at_utc: datetime | None = None


class AuditSummaryView(BaseModel):
    created_by: AuditActorSummaryView | None = None
    created_at_utc: datetime | None = None
    confirmed_by: AuditActorSummaryView | None = None
    confirmed_at_utc: datetime | None = None
    acknowledged_by: AuditActorSummaryView | None = None
    acknowledged_at_utc: datetime | None = None
    acknowledgement_label: str | None = None
    reason_label: str | None = None
    notes: str | None = None
    backoffice_notification: AuditNotificationSummaryView | None = None
