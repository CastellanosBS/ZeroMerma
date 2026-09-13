import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminProductionBackendContract,
  AdminProductionListItem,
  AdminProductionStatus,
  AdminProductionWarningSeverity,
} from "../types";

function formatStatus(status: AdminProductionStatus): string {
  const labels: Record<AdminProductionStatus, string> = {
    CANCELLED: "Cancelada",
    COMPLETED: "Completada",
    DRAFT: "Pendiente",
    IN_PROGRESS: "En proceso",
  };
  return labels[status];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Pendiente";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusTone(status: AdminProductionStatus): "critical" | "neutral" | "success" | "warning" {
  if (status === "CANCELLED") {
    return "critical";
  }
  if (status === "COMPLETED") {
    return "success";
  }
  if (status === "IN_PROGRESS") {
    return "warning";
  }
  return "neutral";
}

function warningTone(severity: AdminProductionWarningSeverity | null | undefined) {
  if (severity === "critical") {
    return "critical";
  }
  if (severity === "warning") {
    return "warning";
  }
  return "neutral";
}

function StatusChip({
  children,
  tone = "neutral",
}: {
  children: string;
  tone?: "critical" | "neutral" | "success" | "warning";
}) {
  const toneClass = {
    critical: "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]",
    neutral: "border-[var(--ui-color-border)] bg-white text-slate-600",
    success: "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]",
    warning: "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]",
  }[tone];

  return (
    <span
      className={`max-w-full truncate rounded-full border px-2 py-0.5 text-[0.72rem] font-semibold ${toneClass}`}
      title={children}
    >
      {children}
    </span>
  );
}

interface AdminProductionTableProps {
  backendContract: AdminProductionBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  isSubmitting?: boolean;
  onCancel: (item: AdminProductionListItem) => void;
  onComplete: (item: AdminProductionListItem) => void;
  onOpenProduct: (productId: string) => void;
  onOpenRecipe: (productId: string) => void;
  onPageChange: (page: number) => void;
  onSelectProduction: (item: AdminProductionListItem) => void;
  onStart: (item: AdminProductionListItem) => void;
  page: number;
  pageSize: number;
  productions: AdminProductionListItem[];
  selectedProductionId?: string | null;
  total: number;
}

export function AdminProductionTable({
  backendContract,
  errorMessage,
  isLoading = false,
  isSubmitting = false,
  onCancel,
  onComplete,
  onOpenProduct,
  onOpenRecipe,
  onPageChange,
  onSelectProduction,
  onStart,
  page,
  pageSize,
  productions,
  selectedProductionId,
  total,
}: AdminProductionTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-950"
            title="Lotes de produccion"
          >
            Lotes de produccion
          </h3>
          <p className="truncate text-xs text-slate-500">
            Planeacion, avance, cierre, faltantes e impacto de inventario.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando producciones reales del backend."
            title="Cargando producciones"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo cargar produccion" />
        ) : productions.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {productions.map((item) => {
              const isSelected = item.id === selectedProductionId;
              const warningLabel =
                item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas";
              const varianceLabel =
                item.varianceQty && item.varianceQty !== "0.000"
                  ? `Var. ${item.varianceQty}`
                  : "Sin variacion";

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.65fr)_minmax(0,1.1fr)_minmax(0,0.95fr)_minmax(8rem,0.75fr)_minmax(7rem,0.55fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.id}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.folio}
                    type="button"
                    onClick={() => onSelectProduction(item)}
                  >
                    <span className="block truncate font-mono text-sm font-semibold text-slate-950">
                      {item.folio}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDate(item.plannedAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.productName} - ${item.productCode}`}
                    type="button"
                    onClick={() => onSelectProduction(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {item.productName}
                    </span>
                    <span className="mt-0.5 block truncate font-mono text-xs text-slate-500">
                      {item.productCode}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.recipeName} - ${item.branchName}`}
                    type="button"
                    onClick={() => onSelectProduction(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {item.recipeName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.branchName}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`Inicio: ${formatDate(item.startedAt)}. Cierre: ${formatDate(item.completedAt)}`}
                    type="button"
                    onClick={() => onSelectProduction(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {formatDate(item.startedAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Cierre {formatDate(item.completedAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] xl:text-right"
                    title={`Planeado ${item.plannedOutputQty}. Producido ${item.actualOutputQty ?? "Pendiente"}`}
                    type="button"
                    onClick={() => onSelectProduction(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.actualOutputQty ?? "Pend."}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Plan {item.plannedOutputQty}
                    </span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 xl:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 xl:justify-end">
                      <StatusChip tone={statusTone(item.status)}>
                        {formatStatus(item.status)}
                      </StatusChip>
                      <StatusChip
                        tone={
                          item.varianceQty && item.varianceQty !== "0.000" ? "warning" : "neutral"
                        }
                      >
                        {varianceLabel}
                      </StatusChip>
                      <StatusChip tone={warningTone(item.warningState)}>{warningLabel}</StatusChip>
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs xl:justify-end">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenProduct(item.productId)}
                      >
                        Producto
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenRecipe(item.productId)}
                      >
                        Receta
                      </button>
                      {item.status === "DRAFT" ? (
                        <AdminActionButton
                          capability="production.execute"
                          branchIds={[item.branchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onStart(item)}
                        >
                          Iniciar
                        </AdminActionButton>
                      ) : null}
                      {item.status === "IN_PROGRESS" ? (
                        <AdminActionButton
                          capability="production.execute"
                          branchIds={[item.branchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onComplete(item)}
                        >
                          Completar
                        </AdminActionButton>
                      ) : null}
                      {item.status === "DRAFT" || item.status === "IN_PROGRESS" ? (
                        <AdminActionButton
                          capability="production.cancel"
                          branchIds={[item.branchId]}
                          className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                          disabled={isSubmitting}
                          type="button"
                          onClick={() => onCancel(item)}
                        >
                          Cancelar
                        </AdminActionButton>
                      ) : null}
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="No hay producciones para los filtros seleccionados."
              title="Sin producciones"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}. Las producciones aparecen cuando
              existen lotes persistidos en backend.
            </p>
          </div>
        )}
      </div>

      <div className="flex min-w-0 shrink-0 flex-wrap items-center justify-between gap-2 border-t border-[var(--ui-color-border)] px-3 py-2 text-xs text-slate-500">
        <span className="truncate">
          Pagina {page} de {totalPages} - {pageSize} por pagina
        </span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
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
