import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminRecipeCostBackendContract, AdminRecipeCostProduct } from "../types";

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "Pendiente";
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

function formatHealth(value: AdminRecipeCostProduct["healthStatus"]): string {
  const labels: Record<AdminRecipeCostProduct["healthStatus"], string> = {
    healthy: "Saludable",
    incomplete: "Incompleta",
    no_recipe: "Sin receta",
    warning: "Revisar",
  };

  return labels[value];
}

function StatusChip({ item }: { item: AdminRecipeCostProduct }) {
  const toneClass =
    item.healthStatus === "healthy"
      ? "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
      : item.healthStatus === "no_recipe"
        ? "border-[var(--ui-color-border)] bg-white text-slate-600"
        : "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";

  return (
    <span
      className={`max-w-full truncate rounded-full border px-2 py-0.5 text-[0.72rem] font-semibold ${toneClass}`}
      title={formatHealth(item.healthStatus)}
    >
      {formatHealth(item.healthStatus)}
    </span>
  );
}

interface AdminRecipeCostsTableProps {
  backendContract: AdminRecipeCostBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  onPageChange: (page: number) => void;
  onSelectProduct: (item: AdminRecipeCostProduct) => void;
  page: number;
  pageSize: number;
  products: AdminRecipeCostProduct[];
  selectedProductId?: string | null;
  total: number;
}

export function AdminRecipeCostsTable({
  backendContract,
  errorMessage,
  isLoading = false,
  onPageChange,
  onSelectProduct,
  page,
  pageSize,
  products,
  selectedProductId,
  total,
}: AdminRecipeCostsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Productos y receta activa">
            Productos y receta activa
          </h3>
          <p className="truncate text-xs text-slate-500">
            Vista centrada en producto terminado, costo calculado y variacion.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando productos terminados y su estado de receta."
            title="Cargando recetas"
          />
        ) : errorMessage ? (
          <AdminEmptyState
            description={errorMessage}
            title="No se pudieron cargar recetas"
          />
        ) : products.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {products.map((item) => {
              const isSelected = item.productId === selectedProductId;
              return (
                <button
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 text-left transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.85fr)_minmax(7rem,0.55fr)_minmax(8rem,0.7fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={item.productId}
                  title={item.productName}
                  type="button"
                  onClick={() => onSelectProduct(item)}
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.productName}
                    </span>
                    <span className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
                      <span className="truncate" title={item.productCode}>
                        {item.productCode}
                      </span>
                      <span aria-hidden="true">-</span>
                      <span className="truncate" title={item.className}>
                        {item.className}
                      </span>
                    </span>
                  </span>

                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {item.activeRecipeId ? item.activeRecipeVersionName ?? "Receta activa" : "Sin receta activa"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.recipeInputCount} insumos - rendimiento {item.yieldQty ?? "-"} {item.yieldUom ?? ""}
                    </span>
                  </span>

                  <span className="min-w-0 text-left lg:text-right">
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.calculatedUnitCost, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Costo calculado</span>
                  </span>

                  <span className="min-w-0 text-left lg:text-right">
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.productStandardCost, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Var. {item.costVariancePercent ? `${Number(item.costVariancePercent).toFixed(1)}%` : "N/A"}
                    </span>
                  </span>

                  <span className="flex min-w-0 flex-wrap items-start gap-1.5 lg:justify-end">
                    <StatusChip item={item} />
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="Aqui se mostraran productos terminados cuando existan registros que coincidan con el alcance y los filtros."
              title="Sin productos para recetas"
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
