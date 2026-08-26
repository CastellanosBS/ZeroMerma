import type { ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminAuditEventDetail, AdminAuditEventListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
      <div className="mt-2 min-w-0">{children}</div>
    </section>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <span className="block truncate text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </span>
      <span className="mt-0.5 block min-w-0 truncate text-sm font-semibold text-slate-950">
        {value}
      </span>
    </div>
  );
}

function valueOrDash(value: string | number | null | undefined): string {
  if (value === 0) {
    return "0";
  }
  return value ? String(value) : "No disponible";
}

interface AdminAuditEventDetailPanelProps {
  detail: AdminAuditEventDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyCorrelationId: (value: string) => void;
  onCopyEventId: (value: string) => void;
  onSearchRelated: (item: AdminAuditEventListItem) => void;
  selectedEvent: AdminAuditEventListItem | null;
}

export function AdminAuditEventDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCopyCorrelationId,
  onCopyEventId,
  onSearchRelated,
  selectedEvent,
}: AdminAuditEventDetailPanelProps) {
  if (!selectedEvent) {
    return (
      <AdminEmptyState
        description="Selecciona un evento para revisar actor, accion, entidad afectada y detalles del cambio."
        title="Sin evento seleccionado"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando detalle, cambios, contexto tecnico y eventos relacionados."
        title="Cargando evento"
      />
    );
  }

  if (errorMessage) {
    return <AdminEmptyState description={errorMessage} title="No se pudo cargar el evento" />;
  }

  if (!detail) {
    return (
      <AdminEmptyState
        description="Selecciona un evento para revisar actor, accion, entidad afectada y detalles del cambio."
        title="Sin evento seleccionado"
      />
    );
  }

  const requestContext = detail.requestContext;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de auditoria
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.actionLabel}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.overview.id}</p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
              {detail.overview.result}
            </span>
            {detail.overview.isSensitive ? (
              <span className="rounded-full border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-1 text-xs font-semibold text-[var(--ui-color-warning)]">
                Sensible
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="ID" value={detail.overview.id} />
            <Fact label="Fecha / hora" value={formatDateTime(detail.overview.occurredAt)} />
            <Fact label="Actor" value={detail.overview.actorName} />
            <Fact label="Tipo actor" value={detail.overview.actorType} />
            <Fact label="Origen" value={detail.overview.sourceApp} />
            <Fact label="Modulo" value={detail.overview.moduleLabel} />
            <Fact label="Accion" value={detail.overview.action} />
            <Fact label="Resultado" value={detail.overview.result} />
            <Fact label="Severidad" value={detail.overview.severity} />
            <Fact label="Sensible" value={detail.overview.isSensitive ? "Si" : "No"} />
          </div>
        </Section>

        <Section title="Actor / usuario">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Nombre" value={detail.actorContext.fullName} />
            <Fact label="Correo" value={valueOrDash(detail.actorContext.email)} />
            <Fact label="Estado" value={valueOrDash(detail.actorContext.userStatus)} />
            <Fact label="Roles" value={valueOrDash(detail.actorContext.rolesSummary)} />
            <Fact
              label="Sucursales"
              value={valueOrDash(detail.actorContext.branchAssignmentsSummary)}
            />
            <Fact
              label="Abrir usuario"
              value={detail.actorContext.canOpenUser ? "Disponible desde Usuarios" : "No aplica"}
            />
          </div>
        </Section>

        <Section title="Entidad / documento">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Tipo entidad" value={detail.entityContext.entityType} />
            <Fact label="ID entidad" value={valueOrDash(detail.entityContext.entityId)} />
            <Fact label="Referencia" value={valueOrDash(detail.entityContext.entityReference)} />
            <Fact label="Sucursal" value={valueOrDash(detail.entityContext.branchName)} />
            <Fact label="Estacion" value={valueOrDash(detail.entityContext.workstationName)} />
            <Fact label="Sesion caja" value={valueOrDash(detail.entityContext.cashSessionId)} />
            <Fact label="Modulo relacionado" value={detail.entityContext.relatedModule} />
            <Fact
              label="Abrir documento"
              value={
                detail.entityContext.canOpenRelatedDocument
                  ? "Ruta disponible"
                  : "Sin ruta canonica disponible"
              }
            />
          </div>
        </Section>

        <Section title="Detalle de cambios">
          {detail.changeSummary.length > 0 ? (
            <div className="overflow-hidden rounded-[14px] border border-[var(--ui-color-border)]">
              <div className="grid grid-cols-[9rem_minmax(0,1fr)_minmax(0,1fr)_8rem] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
                <span>Campo</span>
                <span>Anterior</span>
                <span>Nuevo</span>
                <span>Tipo</span>
              </div>
              <div className="divide-y divide-[var(--ui-color-border)]">
                {detail.changeSummary.map((item) => (
                  <div
                    className="grid grid-cols-[9rem_minmax(0,1fr)_minmax(0,1fr)_8rem] px-3 py-2 text-sm"
                    key={`${item.field}-${item.changeType}`}
                  >
                    <span className="truncate font-semibold text-slate-950">{item.field}</span>
                    <span className="truncate text-slate-700" title={item.oldValueMasked ?? ""}>
                      {valueOrDash(item.oldValueMasked)}
                    </span>
                    <span className="truncate text-slate-700" title={item.newValueMasked ?? ""}>
                      {valueOrDash(item.newValueMasked)}
                    </span>
                    <span className="truncate text-slate-600">{item.changeType}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este evento no tiene detalles de cambios disponibles.
            </p>
          )}
        </Section>

        <Section title="Contexto tecnico">
          {requestContext ? (
            <div className="grid gap-2 sm:grid-cols-2">
              <Fact label="Request ID" value={valueOrDash(requestContext.requestId)} />
              <Fact label="Correlation ID" value={valueOrDash(requestContext.correlationId)} />
              <Fact label="Endpoint" value={valueOrDash(requestContext.endpoint)} />
              <Fact label="Metodo" value={valueOrDash(requestContext.method)} />
              <Fact label="IP" value={valueOrDash(requestContext.ipAddress)} />
              <Fact label="User agent" value={valueOrDash(requestContext.userAgent)} />
              <Fact label="Status code" value={valueOrDash(requestContext.statusCode)} />
              <Fact label="Error code" value={valueOrDash(requestContext.errorCode)} />
              <Fact label="Duracion" value={valueOrDash(requestContext.durationMs)} />
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este evento no tiene contexto tecnico de solicitud disponible.
            </p>
          )}
        </Section>

        <Section title="Documentos relacionados">
          {detail.relatedDocuments.length > 0 ? (
            <div className="grid gap-2">
              {detail.relatedDocuments.map((document) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2"
                  key={`${document.documentType}-${document.documentId ?? document.reference}`}
                >
                  <p className="truncate text-sm font-semibold text-slate-950">{document.label}</p>
                  <p className="truncate text-xs text-slate-500">
                    {document.documentType} - {valueOrDash(document.reference ?? document.documentId)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este evento no tiene documentos relacionados.
            </p>
          )}
        </Section>

        <Section title="Eventos cercanos">
          {detail.timelineRelatedEvents.length > 0 ? (
            <div className="grid gap-2">
              {detail.timelineRelatedEvents.map((event) => (
                <div className="rounded-[14px] bg-slate-50 px-3 py-2" key={event.id}>
                  <p className="truncate text-sm font-semibold text-slate-950">
                    {event.actionLabel}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {formatDateTime(event.occurredAt)} - {event.actorName} - {event.result}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              No hay eventos relacionados disponibles para este filtro.
            </p>
          )}
        </Section>

        <Section title="Acciones disponibles">
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={() => onCopyEventId(detail.overview.id)}
            >
              Copiar evento
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!requestContext?.correlationId}
              type="button"
              onClick={() => {
                if (requestContext?.correlationId) {
                  onCopyCorrelationId(requestContext.correlationId);
                }
              }}
            >
              Copiar correlacion
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={() => onSearchRelated(detail.overview)}
            >
              Buscar relacionados
            </button>
          </div>
        </Section>
      </div>
    </aside>
  );
}
