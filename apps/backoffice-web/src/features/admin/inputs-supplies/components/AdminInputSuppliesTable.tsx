import { AdminEmptyState } from "../../components/AdminEmptyState";
import type {
  AdminInputSupplyBackendContract,
  AdminInputSupplyKind,
  AdminInputSupplyListItem,
  AdminInputSupplyStockState,
  AdminInputSupplyWarningState,
} from "../types";

function formatKind(kind: AdminInputSupplyKind): string {
  const labels: Record<AdminInputSupplyKind, string> = {
    CONSUMABLE: "Consumible",
    DISPOSABLE: "Desechable",
    RAW_MATERIAL: "Materia prima",
  };
  return labels[kind];
}

function formatStockState(state: AdminInputSupplyStockState): string {
  const labels: Record<AdminInputSupplyStockState, string> = {
    in_stock: "Con existencia",
    low_stock: "Stock bajo",
    negative_stock: "Stock negativo",
    no_inventory: "Sin inventario",
    out_of_stock: "Sin existencia",
  };
  return labels[state];
}

function warningTone(
  state: AdminInputSupplyWarningState,
): "critical" | "neutral" | "success" | "warning" {
  if (state === "critical") {
    return "critical";
  }
  if (state === "warning" || state === "info") {
    return "warning";
  }
  return "success";
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

function copyCode(code: string) {
  if (typeof navigator !== "undefined" && navigator.clipboard) {
    void navigator.clipboard.writeText(code);
  }
}

interface AdminInputSuppliesTableProps {
  backendContract: AdminInputSupplyBackendContract;
  errorMessage?: string | null;
  inputs: AdminInputSupplyListItem[];
  isLoading?: boolean;
  isSubmitting?: boolean;
  onChangeStatus: (item: AdminInputSupplyListItem, isActive: boolean) => void;
  onOpenInventory: (productId: string) => void;
  onOpenProduct: (productId: string) => void;
  onOpenSuppliers: (productId: string) => void;
  onPageChange: (page: number) => void;
  onSelectInput: (item: AdminInputSupplyListItem) => void;
  page: number;
  pageSize: number;
  selectedInputId?: string | null;
  total: number;
}

export function AdminInputSuppliesTable({
  backendContract,
  errorMessage,
  inputs,
  isLoading = false,
  isSubmitting = false,
  onChangeStatus,
  onOpenInventory,
  onOpenProduct,
  onOpenSuppliers,
  onPageChange,
  onSelectInput,
  page,
  pageSize,
  selectedInputId,
  total,
}: AdminInputSuppliesTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3
            className="truncate text-base font-semibold text-slate-950"
            title="Insumos y consumibles"
          >
            Insumos y consumibles
          </h3>
          <p className="truncate text-xs text-slate-500">
            Catalogo comprable e inventariable sin editar stock directamente.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} insumos
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando insumos y consumibles del backend."
            title="Cargando insumos"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar insumos" />
        ) : inputs.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            <div className="hidden min-w-0 grid-cols-[minmax(8rem,0.75fr)_minmax(0,1.15fr)_minmax(8rem,0.8fr)_minmax(8rem,0.75fr)_minmax(8rem,0.7fr)_auto] gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 xl:grid">
              <span>Codigo / tipo</span>
              <span>Nombre / categoria</span>
              <span>Unidades</span>
              <span className="text-right">Costo</span>
              <span className="text-right">Proveedor / recetas</span>
              <span className="text-right">Estado / acciones</span>
            </div>
            {inputs.map((item) => {
              const isSelected = item.id === selectedInputId;
              const warningLabel =
                item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas";
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition xl:grid-cols-[minmax(8rem,0.75fr)_minmax(0,1.15fr)_minmax(8rem,0.8fr)_minmax(8rem,0.75fr)_minmax(8rem,0.7fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.id}
                >
                  <button
                    className="min-w-0 text-left"
                    type="button"
                    onClick={() => onSelectInput(item)}
                  >
                    <span
                      className="block truncate font-mono text-sm font-semibold text-slate-950"
                      title={item.code}
                    >
                      {item.code}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {formatKind(item.productKind)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left"
                    title={item.name}
                    type="button"
                    onClick={() => onSelectInput(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.name}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.categoryName}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left"
                    type="button"
                    onClick={() => onSelectInput(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-900">
                      {item.baseUom} / {item.purchaseUom ?? "sin compra"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Unidad base / compra
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right"
                    type="button"
                    onClick={() => onSelectInput(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.standardCost ?? "Sin costo"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Ult. {item.lastPurchaseCost ?? "N/D"}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left xl:text-right"
                    type="button"
                    onClick={() => onSelectInput(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.primarySupplierName ?? "Sin proveedor"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.supplierCount} proveedores - {item.recipeUsageCount} recetas
                    </span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 xl:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 xl:justify-end">
                      <StatusChip tone={item.isActive ? "success" : "neutral"}>
                        {item.isActive ? "Activo" : "Inactivo"}
                      </StatusChip>
                      <StatusChip
                        tone={
                          item.stockState === "negative_stock"
                            ? "critical"
                            : item.stockState === "low_stock"
                              ? "warning"
                              : "neutral"
                        }
                      >
                        {formatStockState(item.stockState)}
                      </StatusChip>
                      <StatusChip tone={warningTone(item.warningState)}>{warningLabel}</StatusChip>
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 text-xs xl:justify-end">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
                        type="button"
                        onClick={() => onSelectInput(item)}
                      >
                        Ver
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
                        type="button"
                        onClick={() => copyCode(item.code)}
                      >
                        Copiar codigo
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
                        type="button"
                        onClick={() => onChangeStatus(item, !item.isActive)}
                        disabled={isSubmitting}
                      >
                        {item.isActive ? "Desactivar" : "Activar"}
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
                        type="button"
                        onClick={() => onOpenSuppliers(item.id)}
                      >
                        Proveedores
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
                        type="button"
                        onClick={() => onOpenInventory(item.id)}
                      >
                        Inventario
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 font-semibold text-slate-600"
                        type="button"
                        onClick={() => onOpenProduct(item.id)}
                      >
                        Producto
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
              description="No hay insumos o consumibles registrados para los filtros seleccionados."
              title="Sin insumos registrados"
            />
            <p className="rounded-[16px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-600">
              Contrato activo: {backendContract.listEndpoint}. Los cambios se guardan sobre el
              catalogo canonico de productos.
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
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 disabled:opacity-50"
            disabled={page <= 1}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 disabled:opacity-50"
            disabled={page >= totalPages}
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
