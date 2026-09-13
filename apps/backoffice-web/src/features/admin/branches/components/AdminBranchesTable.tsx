import { AdminEmptyState } from "../../components/AdminEmptyState";
import { AdminRowActionsMenu } from "../../components/AdminRowActionsMenu";
import type {
  AdminBranchBackendContract,
  AdminBranchListItem,
  AdminBranchReadiness,
} from "../types";

function formatStatus(status: AdminBranchListItem["status"]): string {
  return status === "active" ? "Activa" : "Inactiva";
}

function formatReadiness(readiness: AdminBranchReadiness): string {
  const labels: Record<AdminBranchReadiness, string> = {
    inactive: "Inactiva",
    ready: "Lista",
    warning: "Revisar",
  };

  return labels[readiness];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin fecha";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
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

interface AdminBranchesTableProps {
  backendContract: AdminBranchBackendContract;
  branches: AdminBranchListItem[];
  errorMessage?: string | null;
  isLoading?: boolean;
  isUpdating?: boolean;
  onCopyCode: (item: AdminBranchListItem) => void;
  onEditBranch: (item: AdminBranchListItem) => void;
  onPageChange: (page: number) => void;
  onSelectBranch: (item: AdminBranchListItem) => void;
  onToggleStatus: (item: AdminBranchListItem) => void;
  page: number;
  pageSize: number;
  selectedBranchId?: string | null;
  total: number;
}

export function AdminBranchesTable({
  backendContract,
  branches,
  errorMessage,
  isLoading = false,
  isUpdating = false,
  onCopyCode,
  onEditBranch,
  onPageChange,
  onSelectBranch,
  onToggleStatus,
  page,
  pageSize,
  selectedBranchId,
  total,
}: AdminBranchesTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Red de sucursales">
            Red de sucursales
          </h3>
          <p className="truncate text-xs text-slate-500">
            Base operativa para POS, caja, inventario, produccion, merma y reportes.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando la red multisucursal."
            title="Cargando sucursales"
          />
        ) : errorMessage ? (
          <AdminEmptyState
            description={errorMessage}
            title="No se pudieron cargar las sucursales"
          />
        ) : branches.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {branches.map((item) => {
              const isSelected = item.id === selectedBranchId;
              const readinessTone =
                item.readiness === "ready"
                  ? "success"
                  : item.readiness === "inactive"
                    ? "neutral"
                    : "warning";
              const criticalWarning = item.warnings.some(
                (warning) => warning.severity === "critical",
              );

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.95fr)_minmax(6rem,0.55fr)_minmax(6rem,0.55fr)_auto]",
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
                    onClick={() => onSelectBranch(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.name}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.code}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.brandName} - ${item.timezone}`}
                    type="button"
                    onClick={() => onSelectBranch(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {item.brandName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.timezone}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.activeWorkstationCount} activas de ${item.workstationCount}`}
                    type="button"
                    onClick={() => onSelectBranch(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.activeWorkstationCount}/{item.workstationCount}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Estaciones</span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.assignedUserCount} usuarios activos`}
                    type="button"
                    onClick={() => onSelectBranch(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.assignedUserCount}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDate(item.updatedAt)}
                    </span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 lg:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 lg:justify-end">
                      <StatusChip tone={item.status === "active" ? "success" : "neutral"}>
                        {formatStatus(item.status)}
                      </StatusChip>
                      <StatusChip tone={readinessTone}>
                        {formatReadiness(item.readiness)}
                      </StatusChip>
                      {item.warnings.length > 0 ? (
                        <StatusChip tone={criticalWarning ? "critical" : "warning"}>
                          {`${item.warnings.length} alertas`}
                        </StatusChip>
                      ) : null}
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs lg:justify-end">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        type="button"
                        onClick={() => onSelectBranch(item)}
                      >
                        Ver
                      </button>
                      <AdminRowActionsMenu
                        actions={[
                          {
                            capability: "branches.manage",
                            branchIds: [item.id],
                            disabled: isUpdating,
                            label: "Editar",
                            onSelect: () => onEditBranch(item),
                          },
                          { label: "Copiar codigo", onSelect: () => onCopyCode(item) },
                          {
                            destructive: item.status === "active",
                            capability: "branches.manage",
                            branchIds: [item.id],
                            disabled: isUpdating,
                            label: item.status === "active" ? "Desactivar" : "Activar",
                            onSelect: () => onToggleStatus(item),
                          },
                        ]}
                        label={`Acciones para ${item.name}`}
                      />
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="No hay sucursales registradas. Crea la primera sucursal para iniciar la operacion multisucursal."
              title="Sin sucursales"
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
