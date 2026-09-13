import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminSanitaryVerificationListItem } from "../types";

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
    PENDING: "Pendiente",
    REQUIRES_FOLLOW_UP: "Por seguimiento",
    SCHEDULED: "Programada",
  };
  return labels[value] ?? value;
}

function resultLabel(value: string): string {
  const labels: Record<string, string> = {
    FAILED: "Fallida",
    NOT_EVALUATED: "Sin evaluar",
    PARTIAL: "Parcial",
    PASSED: "Aprobada",
  };
  return labels[value] ?? value;
}

function badgeClass(value: string): string {
  if (value === "PASSED" || value === "COMPLETED") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "FAILED" || value === "REQUIRES_FOLLOW_UP" || value === "CRITICAL") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "HIGH" || value === "PARTIAL" || value === "IN_PROGRESS") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  if (value === "CANCELLED") {
    return "border-slate-200 bg-slate-100 text-slate-500";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

interface AdminSanitaryVerificationsTableProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyFolio: (item: AdminSanitaryVerificationListItem) => void;
  onExecute: (item: AdminSanitaryVerificationListItem) => void;
  onPageChange: (page: number) => void;
  onSelectVerification: (item: AdminSanitaryVerificationListItem) => void;
  page: number;
  pageSize: number;
  selectedVerificationId?: string | null;
  total: number;
  verifications: AdminSanitaryVerificationListItem[];
}

export function AdminSanitaryVerificationsTable({
  errorMessage,
  isLoading = false,
  onCopyFolio,
  onExecute,
  onPageChange,
  onSelectVerification,
  page,
  pageSize,
  selectedVerificationId,
  total,
  verifications,
}: AdminSanitaryVerificationsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">
            Verificaciones sanitarias
          </h3>
          <p className="truncate text-xs text-slate-500">
            Folio, fechas, sucursal, zona, equipo, inspector, checklist, resultado y riesgo.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando verificaciones sanitarias persistidas en backend."
            title="Cargando verificaciones"
          />
        ) : errorMessage ? (
          <AdminEmptyState
            description={errorMessage}
            title="No se pudieron cargar las verificaciones"
          />
        ) : verifications.length > 0 ? (
          <div className="min-w-[90rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[7rem_9rem_9rem_9rem_9rem_9rem_10rem_11rem_7rem_8rem_7rem_8rem_8rem_9rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Folio</span>
              <span>Programada</span>
              <span>Realizada</span>
              <span>Sucursal</span>
              <span>Zona / area</span>
              <span>Equipo / proceso</span>
              <span>Inspector</span>
              <span>Checklist</span>
              <span>Resultado</span>
              <span>Estado</span>
              <span>Riesgo</span>
              <span>Incidencia</span>
              <span>Evidencia</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {verifications.map((item) => {
                const isSelected = item.id === selectedVerificationId;
                return (
                  <article
                    className={[
                      "grid grid-cols-[7rem_9rem_9rem_9rem_9rem_9rem_10rem_11rem_7rem_8rem_7rem_8rem_8rem_9rem] items-center gap-0 px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={item.folio}
                      type="button"
                      onClick={() => onSelectVerification(item)}
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
                      className="truncate text-slate-700"
                      title={item.equipmentName ?? item.processName ?? "Sin equipo"}
                    >
                      {item.equipmentName ?? item.processName ?? "N/A"}
                    </span>
                    <span className="truncate text-slate-700" title={item.inspectorUserName}>
                      {item.inspectorUserName}
                    </span>
                    <span className="truncate text-slate-700" title={item.templateName}>
                      {item.passedCount}/{item.checklistTotalCount} {item.templateName}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.result,
                      )}`}
                      title={resultLabel(item.result)}
                    >
                      <span className="truncate">{resultLabel(item.result)}</span>
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
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.riskLevel,
                      )}`}
                    >
                      {item.riskLevel}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.hasIncident ? "Con incidencia" : "Sin incidencia"}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.hasEvidence ? "Con evidencia" : "Sin evidencia"}
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectVerification(item)}
                      >
                        Ver
                      </button>
                      <AdminActionButton
                        capability="quality_hygiene.manage"
                        branchIds={[item.branchId]}
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:cursor-not-allowed disabled:opacity-40"
                        disabled={
                          item.status === "COMPLETED" ||
                          item.status === "CANCELLED" ||
                          item.status === "REQUIRES_FOLLOW_UP"
                        }
                        type="button"
                        onClick={() => onExecute(item)}
                      >
                        Ejecutar
                      </AdminActionButton>
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
            description="No hay verificaciones sanitarias para los filtros seleccionados."
            title="Sin verificaciones"
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
