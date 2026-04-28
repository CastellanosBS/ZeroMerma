from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from zeromerma_api.modules.audit.application.schemas import (
    AuditActorSummaryView,
    AuditNotificationSummaryView,
    AuditSummaryView,
)
from zeromerma_api.modules.outbox.infrastructure.models import OutboxEvent


@dataclass(frozen=True)
class AuditActorSnapshot:
    user_id: UUID
    full_name: str
    email: str | None = None


@dataclass(frozen=True)
class BackofficeNotificationConfig:
    aggregate_id: str
    aggregate_type: str
    event_names: tuple[str, ...]
    label: str


def build_audit_actor_snapshot(
    *,
    user_id: UUID,
    full_name: str,
    email: str | None = None,
) -> AuditActorSnapshot:
    return AuditActorSnapshot(
        user_id=user_id,
        full_name=full_name,
        email=email,
    )


class AuditVisibilityQueryService:
    def build_summary(
        self,
        session: Session,
        *,
        created_actor: AuditActorSnapshot | None,
        created_at_utc: datetime | None,
        confirmed_actor: AuditActorSnapshot | None = None,
        confirmed_at_utc: datetime | None = None,
        acknowledged_actor: AuditActorSnapshot | None = None,
        acknowledged_at_utc: datetime | None = None,
        acknowledgement_label: str | None = None,
        reason_label: str | None = None,
        notes: str | None = None,
        notification_config: BackofficeNotificationConfig | None = None,
    ) -> AuditSummaryView:
        notification = (
            self._get_backoffice_notification(session, config=notification_config)
            if notification_config is not None
            else None
        )
        resolved_confirmed_actor = confirmed_actor or created_actor
        resolved_confirmed_at = confirmed_at_utc or created_at_utc
        resolved_acknowledged_actor = acknowledged_actor
        resolved_acknowledged_at = acknowledged_at_utc

        if (
            notification is not None
            and acknowledgement_label is not None
            and resolved_acknowledged_actor is None
        ):
            resolved_acknowledged_actor = resolved_confirmed_actor
            resolved_acknowledged_at = resolved_confirmed_at

        return AuditSummaryView(
            created_by=_to_actor_view(created_actor),
            created_at_utc=created_at_utc,
            confirmed_by=_to_actor_view(resolved_confirmed_actor),
            confirmed_at_utc=resolved_confirmed_at,
            acknowledged_by=_to_actor_view(resolved_acknowledged_actor),
            acknowledged_at_utc=resolved_acknowledged_at,
            acknowledgement_label=acknowledgement_label
            if resolved_acknowledged_actor is not None
            else None,
            reason_label=reason_label,
            notes=notes,
            backoffice_notification=notification,
        )

    def _get_backoffice_notification(
        self,
        session: Session,
        *,
        config: BackofficeNotificationConfig,
    ) -> AuditNotificationSummaryView | None:
        event = session.execute(
            select(
                OutboxEvent.status,
                OutboxEvent.occurred_at,
                OutboxEvent.processed_at,
            )
            .where(
                OutboxEvent.aggregate_type == config.aggregate_type,
                OutboxEvent.aggregate_id == config.aggregate_id,
                OutboxEvent.event_name.in_(config.event_names),
            )
            .order_by(OutboxEvent.occurred_at.desc())
            .limit(1)
        ).mappings().first()

        if event is None:
            return None

        return AuditNotificationSummaryView(
            label=config.label,
            status=str(event["status"]).upper(),
            occurred_at_utc=event["occurred_at"],
            processed_at_utc=event["processed_at"],
        )


def _to_actor_view(actor: AuditActorSnapshot | None) -> AuditActorSummaryView | None:
    if actor is None:
        return None

    return AuditActorSummaryView(
        user_id=actor.user_id,
        full_name=actor.full_name,
        email=actor.email,
    )
