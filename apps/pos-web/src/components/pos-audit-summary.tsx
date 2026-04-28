import type { ReactNode } from "react";

import type { AuditSummaryView } from "../lib/api-contracts";
import { formatLocalDateTime } from "../lib/formatters";
import { cn } from "../lib/utils";
import { PosCard, PosSectionTitle, PosStatusBadge } from "./pos-foundations";
import {
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  OperatorIcon,
} from "./pos-icons";

function hasAuditSummaryContent(auditSummary: AuditSummaryView | null | undefined): boolean {
  if (!auditSummary) {
    return false;
  }

  return Boolean(
    auditSummary.created_by ||
      auditSummary.confirmed_by ||
      auditSummary.acknowledged_by ||
      auditSummary.reason_label ||
      auditSummary.notes ||
      auditSummary.backoffice_notification,
  );
}

function getNotificationTone(
  status: string | null | undefined,
): "error" | "pending" | "success" | "warning" {
  switch (status?.toUpperCase()) {
    case "PROCESSED":
      return "success";
    case "PENDING":
      return "pending";
    case "FAILED":
      return "error";
    default:
      return "warning";
  }
}

function getNotificationLabel(status: string | null | undefined): string {
  switch (status?.toUpperCase()) {
    case "PROCESSED":
      return "Notificado";
    case "PENDING":
      return "Pendiente";
    case "FAILED":
      return "Fallido";
    default:
      return status ?? "Registrado";
  }
}

function AuditEventCard({
  actorName,
  actorSecondary,
  icon,
  label,
  timestamp,
}: {
  actorName: string;
  actorSecondary?: string | null;
  icon: ReactNode;
  label: string;
  timestamp?: string | null;
}) {
  return (
    <PosCard className="px-3 py-2.5">
      <div className="flex items-start gap-2">
        <span aria-hidden="true" className="mt-0.5 text-slate-500">
          {icon}
        </span>
        <div className="min-w-0 flex-1">
          <p className="pos-label-text">{label}</p>
          <p className="mt-1 truncate text-sm font-semibold text-slate-950" title={actorName}>
            {actorName}
          </p>
          {actorSecondary ? (
            <p className="mt-0.5 truncate text-xs text-slate-500" title={actorSecondary}>
              {actorSecondary}
            </p>
          ) : null}
          {timestamp ? <p className="mt-1 text-xs text-slate-500">{timestamp}</p> : null}
        </div>
      </div>
    </PosCard>
  );
}

export function PosAuditSummary({
  auditSummary,
  className,
  timeZone,
  title = "Resumen de auditoria",
}: {
  auditSummary: AuditSummaryView | null | undefined;
  className?: string;
  timeZone: string;
  title?: string;
}) {
  if (!hasAuditSummaryContent(auditSummary)) {
    return null;
  }

  const createdAtLabel = auditSummary?.created_at_utc
    ? formatLocalDateTime(auditSummary.created_at_utc, timeZone)
    : null;
  const confirmedAtLabel = auditSummary?.confirmed_at_utc
    ? formatLocalDateTime(auditSummary.confirmed_at_utc, timeZone)
    : null;
  const acknowledgedAtLabel = auditSummary?.acknowledged_at_utc
    ? formatLocalDateTime(auditSummary.acknowledged_at_utc, timeZone)
    : null;
  const notificationOccurredLabel = auditSummary?.backoffice_notification?.occurred_at_utc
    ? formatLocalDateTime(auditSummary.backoffice_notification.occurred_at_utc, timeZone)
    : null;
  const notificationProcessedLabel = auditSummary?.backoffice_notification?.processed_at_utc
    ? formatLocalDateTime(auditSummary.backoffice_notification.processed_at_utc, timeZone)
    : null;

  return (
    <div className={cn("grid gap-2", className)} data-pos-audit-summary="true">
      <PosSectionTitle title={title} />

      <div className="grid gap-2 sm:grid-cols-2">
        {auditSummary?.created_by ? (
          <AuditEventCard
            actorName={auditSummary.created_by.full_name}
            actorSecondary={auditSummary.created_by.email}
            icon={<OperatorIcon className="h-4 w-4" />}
            label="Creado por"
            timestamp={createdAtLabel}
          />
        ) : null}

        {auditSummary?.confirmed_by ? (
          <AuditEventCard
            actorName={auditSummary.confirmed_by.full_name}
            actorSecondary={auditSummary.confirmed_by.email}
            icon={<CheckCircleIcon className="h-4 w-4" />}
            label="Confirmado por"
            timestamp={confirmedAtLabel}
          />
        ) : null}

        {auditSummary?.acknowledged_by ? (
          <AuditEventCard
            actorName={auditSummary.acknowledged_by.full_name}
            actorSecondary={auditSummary.acknowledged_by.email}
            icon={<AlertTriangleIcon className="h-4 w-4" />}
            label={auditSummary.acknowledgement_label ?? "Validado por"}
            timestamp={acknowledgedAtLabel}
          />
        ) : null}

        {auditSummary?.backoffice_notification ? (
          <PosCard className="px-3 py-2.5">
            <div className="flex items-start gap-2">
              <span aria-hidden="true" className="mt-0.5 text-slate-500">
                <ClockIcon className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="pos-label-text">
                    {auditSummary.backoffice_notification.label}
                  </p>
                  <PosStatusBadge
                    status={getNotificationTone(auditSummary.backoffice_notification.status)}
                  >
                    {getNotificationLabel(auditSummary.backoffice_notification.status)}
                  </PosStatusBadge>
                </div>
                {notificationOccurredLabel ? (
                  <p className="mt-1 text-xs text-slate-500">
                    Registrado {notificationOccurredLabel}
                  </p>
                ) : null}
                {notificationProcessedLabel ? (
                  <p className="mt-0.5 text-xs text-slate-500">
                    Procesado {notificationProcessedLabel}
                  </p>
                ) : null}
              </div>
            </div>
          </PosCard>
        ) : null}
      </div>

      {auditSummary?.reason_label || auditSummary?.notes ? (
        <PosCard className="grid gap-2 px-3 py-3">
          {auditSummary.reason_label ? (
            <div className="grid gap-1">
              <p className="pos-label-text">Motivo</p>
              <p className="text-sm font-medium text-slate-900">{auditSummary.reason_label}</p>
            </div>
          ) : null}
          {auditSummary.notes ? (
            <div className="grid gap-1">
              <p className="pos-label-text">Notas</p>
              <p className="whitespace-pre-wrap text-sm text-slate-700">{auditSummary.notes}</p>
            </div>
          ) : null}
        </PosCard>
      ) : null}
    </div>
  );
}
