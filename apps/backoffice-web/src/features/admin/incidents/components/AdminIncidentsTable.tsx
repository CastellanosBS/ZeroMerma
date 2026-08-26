import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminIncidentListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Sin fecha";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    CANCELLED: "Cancelada",
    CLOSED: "Cerrada",
    IN_PROGRESS: "En seguimiento",
    IN_REVIEW: "En revision",
    OPEN: "Abierta",
    RESOLVED: "Resuelta",
    WAITING_ACTION: "Esperando accion",
  };
  return labels[value] ?? value;
}

function incidentTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    CLEANING_NON_COMPLIANCE: "Limpieza",
    CUSTOMER_COMPLAINT: "Cliente",
    EQUIPMENT_FAILURE: "Equipo",
    INVENTORY_ISSUE: "Inventario",
    OTHER: "Otra",
    PROCESS_DEVIATION: "Proceso",
    PRODUCTION_ISSUE: "Produccion",
    SAFETY_ISSUE: "Seguridad",
    SANITATION_ISSUE: "Sanitaria",
    TRANSFER_ISSUE: "Transferencia",
    WASTE_ISSUE: "Merma",
  };
  return labels[value] ?? value;
}

function sourceTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    CLEANING_LOG: "Bitacora",
    CORRECTION: "Correccion",
    CUSTOMER_REPORT: "Cliente",
    EQUIPMENT: "Equipo",
    INVENTORY: "Inventario",
    MANUAL: "Manual",
    PRODUCTION: "Produccion",
    SANITARY_VERIFICATION: "Verificacion",
    TRANSFER: "Transferencia",
    WASTE_MERMA: "Merma",
  };
  return labels[value] ?? value;
}

function badgeClass(value: string): string {
  if (value === "RESOLVED" || value === "CLOSED" || value === "LOW") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "CRITICAL" || value === "CANCELLED") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (
    value === "HIGH" ||
    value === "OPEN" ||
    value === "IN_PROGRESS" ||
    value === "WAITING_ACTION"
  ) {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

interface AdminIncidentsTableProps {
  errorMessage?: string | null;
  incidents: AdminIncidentListItem[];
  isLoading?: boolean;
  onAddFollowUp: (item: AdminIncidentListItem) => void;
  onCopyFolio: (item: AdminIncidentListItem) => void;
  onPageChange: (page: number) => void;
  onResolve: (item: AdminIncidentListItem) => void;
  onSelectIncident: (item: AdminIncidentListItem) => void;
  page: number;
  pageSize: number;
  selectedIncidentId?: string | null;
  total: number;
}

export function AdminIncidentsTable({
  errorMessage,
  incidents,
  isLoading = false,
  onAddFollowUp,
  onCopyFolio,
  onPageChange,
  onResolve,
  onSelectIncident,
  page,
  pageSize,
  selectedIncidentId,
  total,
}: AdminIncidentsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Incidencias</h3>
          <p className="truncate text-xs text-slate-500">
            Folio, sucursal, origen, severidad, responsable, seguimiento y documentos.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando incidencias persistidas en backend."
            title="Cargando incidencias"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar incidencias" />
        ) : incidents.length > 0 ? (
          <div className="min-w-[94rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[8rem_9rem_10rem_9rem_8rem_9rem_8rem_9rem_10rem_9rem_8rem_9rem_9rem_11rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Folio</span>
              <span>Fecha</span>
              <span>Sucursal</span>
              <span>Zona / area</span>
              <span>Tipo</span>
              <span>Origen</span>
              <span>Severidad</span>
              <span>Estado</span>
              <span>Responsable</span>
              <span>Vencimiento</span>
              <span>Evidencia</span>
              <span>Documentos</span>
              <span>Advertencias</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {incidents.map((item) => {
                const isSelected = item.id === selectedIncidentId;
                const canResolve = !["RESOLVED", "CLOSED", "CANCELLED"].includes(item.status);
                return (
                  <article
                    className={[
                      "grid grid-cols-[8rem_9rem_10rem_9rem_8rem_9rem_8rem_9rem_10rem_9rem_8rem_9rem_9rem_11rem] items-center gap-0 px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={item.folio}
                      type="button"
                      onClick={() => onSelectIncident(item)}
                    >
                      {item.folio}
                    </button>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.createdAt)}
                    </span>
                    <span className="truncate font-medium text-slate-950" title={item.branchName}>
                      {item.branchName}
                    </span>
                    <span className="truncate text-slate-700" title={item.areaName ?? "N/A"}>
                      {item.areaName ?? "N/A"}
                    </span>
                    <span className="truncate text-slate-700" title={incidentTypeLabel(item.incidentType)}>
                      {incidentTypeLabel(item.incidentType)}
                    </span>
                    <span className="truncate text-slate-700" title={sourceTypeLabel(item.sourceType)}>
                      {sourceTypeLabel(item.sourceType)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.severity,
                      )}`}
                      title={item.severity}
                    >
                      <span className="truncate">{item.severity}</span>
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.status,
                      )}`}
                      title={statusLabel(item.status)}
                    >
                      <span className="truncate">{statusLabel(item.status)}</span>
                    </span>
                    <span
                      className="truncate text-slate-700"
                      title={item.responsibleUserName ?? "Sin responsable"}
                    >
                      {item.responsibleUserName ?? "Sin responsable"}
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {item.dueAt ? formatDateTime(item.dueAt) : "Sin fecha"}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.hasEvidence ? "Con evidencia" : "Sin evidencia"}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.relatedDocumentCount} vinculados
                    </span>
                    <span
                      className="truncate text-xs font-semibold text-slate-700"
                      title={item.warnings.map((warning) => warning.message).join(" | ")}
                    >
                      {item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas"}
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectIncident(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
                        disabled={item.status === "CLOSED" || item.status === "CANCELLED"}
                        type="button"
                        onClick={() => onAddFollowUp(item)}
                      >
                        Nota
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
                        disabled={!canResolve}
                        type="button"
                        onClick={() => onResolve(item)}
                      >
                        Resolver
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
            description="No hay incidencias para los filtros seleccionados."
            title="Sin incidencias"
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
