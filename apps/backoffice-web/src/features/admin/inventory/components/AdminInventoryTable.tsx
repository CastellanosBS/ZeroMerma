import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminInventoryBackendContract,
  AdminInventoryListItem,
  AdminInventoryProductKind,
  AdminInventoryStockState,
  AdminInventoryWarningSeverity,
} from "../types";

function formatProductKind(kind: AdminInventoryProductKind): string {
  const labels: Record<AdminInventoryProductKind, string> = {
    CONSUMABLE: "Consumible",
    DISPOSABLE: "Desechable",
    FINISHED_GOOD: "Producto terminado",
    RAW_MATERIAL: "Materia prima",
  };

  return labels[kind];
}

function formatStockState(state: AdminInventoryStockState): string {
  const labels: Record<AdminInventoryStockState, string> = {
    in_stock: "Con existencia",
    low_stock: "Stock bajo",
    negative_stock: "Stock negativo",
    out_of_stock: "Sin existencia",
  };

  return labels[state];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin movimiento";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function stockTone(
  state: AdminInventoryStockState,
): "critical" | "neutral" | "success" | "warning" {
  if (state === "negative_stock") {
    return "critical";
  }
  if (state === "out_of_stock" || state === "low_stock") {
    return "warning";
  }
  return "success";
}

function warningTone(severity: AdminInventoryWarningSeverity | null | undefined) {
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

interface AdminInventoryTableProps {
  backendContract: AdminInventoryBackendContract;
  errorMessage?: string | null;
  inventory: AdminInventoryListItem[];
  isLoading?: boolean;
  isSubmitting?: boolean;
  onAdjust: (item: AdminInventoryListItem) => void;
  onOpenBranch: (branchId: string) => void;
  onOpenProduct: (productId: string) => void;
  onPageChange: (page: number) => void;
  onSelectInventory: (item: AdminInventoryListItem) => void;
  page: number;
  pageSize: number;
  selectedBalanceId?: string | null;
  total: number;
}

export function AdminInventoryTable({
  backendContract,
  errorMessage,
  inventory,
  isLoading = false,
  isSubmitting = false,
  onAdjust,
  onOpenBranch,
  onOpenProduct,
  onPageChange,
  onSelectInventory,
  page,
  pageSize,
  selectedBalanceId,
  total,
}: AdminInventoryTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-950"
            title="Inventario por sucursal"
          >
            Inventario por sucursal
          </h3>
          <p className="truncate text-xs text-slate-500">
            Existencias reales por producto, sucursal y ubicacion soportada.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando existencias reales del backend."
            title="Cargando inventario"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudo cargar inventario" />
        ) : inventory.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {inventory.map((item) => {
              const isSelected = item.balanceId === selectedBalanceId;
              const warningLabel =
                item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas";

              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(0,1.25fr)_minmax(0,0.9fr)_minmax(0,0.9fr)_minmax(7rem,0.65fr)_minmax(8rem,0.7fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.balanceId}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.productName} - ${item.productCode}`}
                    type="button"
                    onClick={() => onSelectInventory(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.productName}
                    </span>
                    <span className="mt-0.5 block truncate font-mono text-xs text-slate-500">
                      {item.productCode}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${formatProductKind(item.productKind)} - ${item.className}`}
                    type="button"
                    onClick={() => onSelectInventory(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {formatProductKind(item.productKind)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.className}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.branchName} - ${item.locationName}`}
                    type="button"
                    onClick={() => onSelectInventory(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {item.branchName}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.locationName}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${item.quantityOnHand} ${item.unitOfMeasure}`}
                    type="button"
                    onClick={() => onSelectInventory(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.quantityOnHand}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.unitOfMeasure}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatDate(item.lastMovementAt)}
                    type="button"
                    onClick={() => onSelectInventory(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatDate(item.lastMovementAt)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Ultimo movimiento
                    </span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 xl:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 xl:justify-end">
                      <StatusChip tone={stockTone(item.stockState)}>
                        {formatStockState(item.stockState)}
                      </StatusChip>
                      <StatusChip tone={warningTone(item.warningState)}>{warningLabel}</StatusChip>
                      {!item.productIsActive ? (
                        <StatusChip tone="warning">Producto inactivo</StatusChip>
                      ) : null}
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs xl:justify-end">
                      <AdminActionButton
                        capability="inventory.adjust"
                        branchIds={[item.branchId]}
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
                        disabled={isSubmitting}
                        type="button"
                        onClick={() => onAdjust(item)}
                      >
                        Ajuste
                      </AdminActionButton>
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
                        onClick={() => onOpenBranch(item.branchId)}
                      >
                        Sucursal
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
              description="No hay existencias registradas para los filtros seleccionados."
              title="Sin registros de inventario"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}. Las existencias aparecen cuando hay
              balances creados por movimientos auditados.
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
