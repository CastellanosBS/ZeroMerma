import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminWorkstationBackendContract,
  AdminWorkstationListItem,
  AdminWorkstationReadiness,
} from "../types";

function formatStatus(status: AdminWorkstationListItem["status"]): string {
  return status === "active" ? "Activa" : "Inactiva";
}

function formatReadiness(readiness: AdminWorkstationReadiness): string {
  const labels: Record<AdminWorkstationReadiness, string> = {
    blocked: "Bloqueada",
    ready: "Lista",
    warning: "Revisar",
  };

  return labels[readiness];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
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

interface AdminWorkstationsTableProps {
  backendContract: AdminWorkstationBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  isUpdating?: boolean;
  onCopyCode: (item: AdminWorkstationListItem) => void;
  onEditWorkstation: (item: AdminWorkstationListItem) => void;
  onOpenBranch: (item: AdminWorkstationListItem) => void;
  onPageChange: (page: number) => void;
  onSelectWorkstation: (item: AdminWorkstationListItem) => void;
  onToggleStatus: (item: AdminWorkstationListItem) => void;
  page: number;
  pageSize: number;
  selectedWorkstationId?: string | null;
  total: number;
  workstations: AdminWorkstationListItem[];
}

export function AdminWorkstationsTable({
  backendContract,
  errorMessage,
  isLoading = false,
  isUpdating = false,
  onCopyCode,
  onEditWorkstation,
  onOpenBranch,
  onPageChange,
  onSelectWorkstation,
  onToggleStatus,
  page,
  pageSize,
  selectedWorkstationId,
  total,
  workstations,
}: AdminWorkstationsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Estaciones POS">
            Estaciones POS
          </h3>
          <p className="truncate text-xs text-slate-500">
            Codigos operativos usados por POS para resolver sucursal, caja y acceso.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState description="Consultando estaciones y contexto de caja." title="Cargando estaciones" />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar las estaciones" />
        ) : workstations.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {workstations.map((item) => {
              const isSelected = item.id === selectedWorkstationId;
              const readinessTone =
                item.readiness === "ready" ? "success" : item.readiness === "blocked" ? "critical" : "warning";
              const criticalWarning = item.warnings.some((warning) => warning.severity === "critical");

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)_minmax(8rem,0.75fr)_minmax(9rem,0.8fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.id}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.name} - ${item.code}`}
                    type="button"
                    onClick={() => onSelectWorkstation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.name}</span>
                    <span className="mt-0.5 block truncate font-mono text-xs text-slate-500">{item.code}</span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.branchName} - ${item.branchCode}`}
                    type="button"
                    onClick={() => onSelectWorkstation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">{item.branchName}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{item.branchCode}</span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.hasActiveCashSession ? "Caja abierta" : "Sin caja abierta"}
                    type="button"
                    onClick={() => onSelectWorkstation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.hasActiveCashSession ? "Abierta" : "Sin caja"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDate(item.lastOpenedAt)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`Ultimo cierre: ${formatDate(item.lastClosedAt)}`}
                    type="button"
                    onClick={() => onSelectWorkstation(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatDate(item.lastClosedAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Ultimo cierre</span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 xl:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 xl:justify-end">
                      <StatusChip tone={item.status === "active" ? "success" : "neutral"}>
                        {formatStatus(item.status)}
                      </StatusChip>
                      <StatusChip tone={readinessTone}>{formatReadiness(item.readiness)}</StatusChip>
                      {item.warnings.length > 0 ? (
                        <StatusChip tone={criticalWarning ? "critical" : "warning"}>
                          {`${item.warnings.length} alertas`}
                        </StatusChip>
                      ) : null}
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs xl:justify-end">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onEditWorkstation(item)}
                      >
                        Editar
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onCopyCode(item)}
                      >
                        Copiar
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onOpenBranch(item)}
                      >
                        Sucursal
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isUpdating || (item.status === "active" && item.hasActiveCashSession)}
                        title={
                          item.status === "active" && item.hasActiveCashSession
                            ? "Cierra la caja antes de desactivar esta estacion."
                            : undefined
                        }
                        type="button"
                        onClick={() => onToggleStatus(item)}
                      >
                        {item.status === "active" ? "Desactivar" : "Activar"}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="No hay cajas o estaciones registradas. Crea una estacion para habilitar operacion POS en una sucursal."
              title="Sin estaciones"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}.
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
