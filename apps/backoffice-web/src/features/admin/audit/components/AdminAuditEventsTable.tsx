import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminAuditEventListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function badgeClass(value: string): string {
  if (value === "success" || value === "info" || value === "none") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (
    value === "failed"
    || value === "blocked"
    || value === "rejected"
    || value === "critical"
    || value === "high"
    || value === "high_risk"
  ) {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function valueOrDash(value: string | null | undefined): string {
  return value && value.trim().length > 0 ? value : "Sin dato";
}

interface AdminAuditEventsTableProps {
  errorMessage?: string | null;
  events: AdminAuditEventListItem[];
  isLoading?: boolean;
  onCopyEventId: (item: AdminAuditEventListItem) => void;
  onPageChange: (page: number) => void;
  onSelectEvent: (item: AdminAuditEventListItem) => void;
  page: number;
  pageSize: number;
  selectedEventId?: string | null;
  total: number;
}

export function AdminAuditEventsTable({
  errorMessage,
  events,
  isLoading = false,
  onCopyEventId,
  onPageChange,
  onSelectEvent,
  page,
  pageSize,
  selectedEventId,
  total,
}: AdminAuditEventsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">
            Eventos de auditoria
          </h3>
          <p className="truncate text-xs text-slate-500">
            Actor, modulo, entidad, resultado, sensibilidad, sucursal y trazabilidad.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} eventos
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando eventos de auditoria persistidos en backend."
            title="Cargando auditoria"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo cargar auditoria" />
        ) : events.length > 0 ? (
          <div className="min-w-[96rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[10rem_13rem_8rem_10rem_13rem_11rem_10rem_8rem_8rem_10rem_10rem_8rem_9rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Fecha / hora</span>
              <span>Usuario / actor</span>
              <span>Origen</span>
              <span>Modulo</span>
              <span>Accion</span>
              <span>Entidad</span>
              <span>Documento</span>
              <span>Resultado</span>
              <span>Sensible</span>
              <span>Sucursal</span>
              <span>Estacion</span>
              <span>Severidad</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {events.map((item) => {
                const isSelected = item.id === selectedEventId;
                return (
                  <article
                    className={[
                      "grid grid-cols-[10rem_13rem_8rem_10rem_13rem_11rem_10rem_8rem_8rem_10rem_10rem_8rem_9rem] items-center px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left text-xs font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onSelectEvent(item)}
                    >
                      {formatDateTime(item.occurredAt)}
                    </button>
                    <span className="truncate text-slate-700" title={item.actorEmail ?? item.actorName}>
                      {item.actorName}
                    </span>
                    <span className="truncate font-semibold text-slate-700">{item.sourceApp}</span>
                    <span className="truncate text-slate-700">{item.moduleLabel}</span>
                    <span className="truncate text-slate-700" title={item.action}>
                      {item.actionLabel}
                    </span>
                    <span className="truncate text-slate-700" title={item.entityId ?? ""}>
                      {item.entityType}
                    </span>
                    <span className="truncate text-slate-700" title={item.entityReference ?? item.entityId ?? ""}>
                      {valueOrDash(item.entityReference ?? item.entityId)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.result,
                      )}`}
                    >
                      <span className="truncate">{item.result}</span>
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${
                        item.isSensitive ? badgeClass("high") : badgeClass("none")
                      }`}
                    >
                      <span className="truncate">{item.isSensitive ? "Si" : "No"}</span>
                    </span>
                    <span className="truncate text-slate-700">{valueOrDash(item.branchName)}</span>
                    <span className="truncate text-slate-700">
                      {valueOrDash(item.workstationName)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.severity,
                      )}`}
                    >
                      <span className="truncate">{item.severity}</span>
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectEvent(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onCopyEventId(item)}
                      >
                        Copiar
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        ) : (
          <AdminEmptyState
            description="No hay eventos de auditoria para los filtros seleccionados."
            title="Sin eventos"
          />
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-[var(--ui-color-border)] px-3 py-2">
        <span className="text-xs font-semibold text-slate-500">
          Pagina {page} de {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoNext}
            type="button"
            onClick={() => onPageChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
}
