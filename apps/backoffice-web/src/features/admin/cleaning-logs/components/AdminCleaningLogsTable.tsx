import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminCleaningLogListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Pendiente";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    CANCELLED: "Cancelada",
    COMPLETED: "Completada",
    IN_PROGRESS: "En proceso",
    MISSED: "Vencida",
    PENDING: "Pendiente",
    REQUIRES_REVIEW: "Por revisar",
    SCHEDULED: "Programada",
  };
  return labels[value] ?? value;
}

function statusClass(value: string): string {
  if (value === "COMPLETED") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "MISSED" || value === "REQUIRES_REVIEW") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "CANCELLED") {
    return "border-slate-200 bg-slate-100 text-slate-500";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function riskClass(value: string): string {
  if (value === "HIGH" || value === "CRITICAL") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "MEDIUM") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

function checklistLabel(item: AdminCleaningLogListItem): string {
  return `${item.checklistCompletedCount}/${item.checklistTotalCount}`;
}

interface AdminCleaningLogsTableProps {
  cleaningLogs: AdminCleaningLogListItem[];
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminCleaningLogListItem) => void;
  onPageChange: (page: number) => void;
  onRegisterCompletion: (item: AdminCleaningLogListItem) => void;
  onSelectCleaningLog: (item: AdminCleaningLogListItem) => void;
  page: number;
  pageSize: number;
  selectedCleaningLogId?: string | null;
  total: number;
}

export function AdminCleaningLogsTable({
  cleaningLogs,
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onPageChange,
  onRegisterCompletion,
  onSelectCleaningLog,
  page,
  pageSize,
  selectedCleaningLogId,
  total,
}: AdminCleaningLogsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Bitacoras de limpieza</h3>
          <p className="truncate text-xs text-slate-500">
            Folio, fechas, sucursal, zona, responsable, checklist, evidencia y riesgo.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando registros de higiene persistidos en backend."
            title="Cargando bitacoras"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar las bitacoras" />
        ) : cleaningLogs.length > 0 ? (
          <div className="min-w-[86rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[7rem_9rem_9rem_9rem_9rem_7rem_9rem_10rem_10rem_6rem_7rem_7rem_7rem_7rem_9rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Folio</span>
              <span>Programada</span>
              <span>Realizada</span>
              <span>Sucursal</span>
              <span>Zona / area</span>
              <span>Equipo</span>
              <span>Turno</span>
              <span>Responsable</span>
              <span>Tipo limpieza</span>
              <span>Checklist</span>
              <span>Estado</span>
              <span>Evidencia</span>
              <span>Obs.</span>
              <span>Riesgo</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {cleaningLogs.map((item) => {
                const isSelected = item.id === selectedCleaningLogId;
                return (
                  <article
                    className={[
                      "grid grid-cols-[7rem_9rem_9rem_9rem_9rem_7rem_9rem_10rem_10rem_6rem_7rem_7rem_7rem_7rem_9rem] items-center gap-0 px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={item.folio}
                      type="button"
                      onClick={() => onSelectCleaningLog(item)}
                    >
                      {item.folio}
                    </button>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.scheduledAt)}
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.completedAt)}
                    </span>
                    <span className="truncate font-medium text-slate-950" title={item.branchName}>
                      {item.branchName}
                    </span>
                    <span className="truncate text-slate-700" title={item.areaName}>
                      {item.areaName}
                    </span>
                    <span
                      className="truncate text-slate-500"
                      title={item.equipmentName ?? "Sin equipo"}
                    >
                      {item.equipmentName ?? "N/A"}
                    </span>
                    <span className="truncate text-slate-700">{item.shiftCode}</span>
                    <span className="truncate text-slate-700" title={item.responsibleUserName}>
                      {item.responsibleUserName}
                    </span>
                    <span className="truncate text-slate-700" title={item.taskName}>
                      {item.taskName}
                    </span>
                    <span className="truncate font-semibold text-slate-950">
                      {checklistLabel(item)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${statusClass(
                        item.status,
                      )}`}
                      title={statusLabel(item.status)}
                    >
                      <span className="truncate">{statusLabel(item.status)}</span>
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.hasEvidence ? "Con evidencia" : "Sin evidencia"}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.hasObservations ? "Con obs." : "Sin obs."}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${riskClass(
                        item.riskLevel,
                      )}`}
                    >
                      {item.riskLevel}
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectCleaningLog(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
                        disabled={item.status === "COMPLETED" || item.status === "CANCELLED"}
                        type="button"
                        onClick={() => onRegisterCompletion(item)}
                      >
                        Completar
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onCopyFolio(item)}
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
            description="No hay bitacoras de limpieza para los filtros seleccionados."
            title="Sin bitacoras"
          />
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-[var(--ui-color-border)] px-3 py-2 text-xs text-slate-500">
        <span>
          Pagina {page} de {totalPages}
        </span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
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
