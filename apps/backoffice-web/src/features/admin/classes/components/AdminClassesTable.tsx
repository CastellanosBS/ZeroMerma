import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminProductClass, AdminProductClassBackendContract } from "../types";

function formatStatus(item: AdminProductClass): string {
  if (item.status === "inactive") {
    return "Inactiva";
  }

  return item.isSellable ? "Activa" : "No vendible";
}

function formatCaptureMode(value: AdminProductClass["captureModeDefault"]): string {
  return value === "PRODUCT_DIRECT" ? "Producto directo" : "Captura por clase";
}

function formatReadiness(status: AdminProductClass["readiness"]): string {
  const labels: Record<AdminProductClass["readiness"], string> = {
    incomplete: "Incompleta",
    pending_integration: "Integracion parcial",
    ready: "Lista",
    requires_attention: "Revisar",
    unknown: "Sin evaluar",
  };

  return labels[status];
}

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "No aplica";
  }

  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }

  return new Intl.NumberFormat("es-MX", {
    currency: currencyCode,
    style: "currency",
  }).format(numericValue);
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
  tone?: "neutral" | "success" | "warning";
}) {
  const toneClass = {
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

interface AdminClassesTableProps {
  backendContract: AdminProductClassBackendContract;
  classes: AdminProductClass[];
  errorMessage?: string | null;
  isLoading?: boolean;
  isUpdating?: boolean;
  onEditClass: (item: AdminProductClass) => void;
  onMoveClass: (item: AdminProductClass, direction: "up" | "down") => void;
  onPageChange: (page: number) => void;
  onSelectClass: (item: AdminProductClass) => void;
  onToggleStatus: (item: AdminProductClass) => void;
  page: number;
  pageSize: number;
  selectedClassId?: string | null;
  total: number;
}

export function AdminClassesTable({
  backendContract,
  classes,
  errorMessage,
  isLoading = false,
  isUpdating = false,
  onEditClass,
  onMoveClass,
  onPageChange,
  onSelectClass,
  onToggleStatus,
  page,
  pageSize,
  selectedClassId,
  total,
}: AdminClassesTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Clases operativas">
            Clases operativas
          </h3>
          <p className="truncate text-xs text-slate-500">
            Estructura que define comportamiento POS, precio de clase y orden visual.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando clases operativas del catalogo."
            title="Cargando clases"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar las clases" />
        ) : classes.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {classes.map((item) => {
              const isSelected = item.id === selectedClassId;
              const readinessTone =
                item.readiness === "ready"
                  ? "success"
                  : item.readiness === "unknown" || item.readiness === "pending_integration"
                    ? "neutral"
                    : "warning";

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition lg:grid-cols-[minmax(0,1.3fr)_minmax(0,0.9fr)_minmax(6rem,0.5fr)_minmax(6rem,0.5fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.id}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.name}
                    type="button"
                    onClick={() => onSelectClass(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.name}
                    </span>
                    <span className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
                      <span className="truncate" title={item.code}>
                        {item.code}
                      </span>
                      <span aria-hidden="true">-</span>
                      <span className="truncate" title={item.quickName ?? "Sin nombre corto"}>
                        {item.quickName ?? "Sin nombre corto"}
                      </span>
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${formatCaptureMode(item.captureModeDefault)} - ${item.brandName}`}
                    type="button"
                    onClick={() => onSelectClass(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {formatCaptureMode(item.captureModeDefault)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.brandName}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.classCaptureUnitPrice, item.currencyCode)}
                    type="button"
                    onClick={() => onSelectClass(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.classCaptureUnitPrice, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Orden {item.displayOrder}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.productCount} productos`}
                    type="button"
                    onClick={() => onSelectClass(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.productCount} productos
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatDate(item.updatedAt)}
                    </span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 lg:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 lg:justify-end">
                      <StatusChip
                        tone={item.status === "active" && item.isSellable ? "success" : "neutral"}
                      >
                        {formatStatus(item)}
                      </StatusChip>
                      <StatusChip tone={readinessTone}>
                        {formatReadiness(item.readiness)}
                      </StatusChip>
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs lg:justify-end">
                      <AdminActionButton
                        globalOnly
                        capability="catalog.manage"
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onEditClass(item)}
                      >
                        Editar
                      </AdminActionButton>
                      <AdminActionButton
                        globalOnly
                        capability="catalog.manage"
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onMoveClass(item, "up")}
                      >
                        Subir
                      </AdminActionButton>
                      <AdminActionButton
                        globalOnly
                        capability="catalog.manage"
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onMoveClass(item, "down")}
                      >
                        Bajar
                      </AdminActionButton>
                      <AdminActionButton
                        globalOnly
                        capability="catalog.manage"
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onToggleStatus(item)}
                      >
                        {item.status === "active" ? "Desactivar" : "Activar"}
                      </AdminActionButton>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="Aqui se mostraran las clases cuando existan registros que coincidan con el alcance y los filtros."
              title="Sin clases operativas"
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
