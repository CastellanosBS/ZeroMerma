import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminPriceBackendContract, AdminPriceHealth, AdminPriceRow } from "../types";

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

function formatOwner(item: AdminPriceRow): string {
  return item.priceOwner === "product_unit_price" ? "Producto" : "Clase";
}

function formatCaptureMode(item: AdminPriceRow): string {
  return item.captureMode === "PRODUCT_DIRECT" ? "Producto directo" : "Captura por clase";
}

function formatHealth(value: AdminPriceHealth): string {
  const labels: Record<AdminPriceHealth, string> = {
    healthy: "Saludable",
    low_margin: "Margen bajo",
    missing_price: "Sin precio",
    negative_margin: "Margen negativo",
    warning: "Revisar",
  };

  return labels[value];
}

function healthToneClass(value: AdminPriceHealth): string {
  if (value === "healthy") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "missing_price" || value === "negative_margin") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function formatMargin(item: AdminPriceRow): string {
  if (!item.marginPercent) {
    return "N/A";
  }

  return `${Number(item.marginPercent).toFixed(1)}%`;
}

interface AdminPricesTableProps {
  backendContract: AdminPriceBackendContract;
  errorMessage?: string | null;
  isLoading?: boolean;
  onEditPrice: (item: AdminPriceRow) => void;
  onPageChange: (page: number) => void;
  onSelectPrice: (item: AdminPriceRow) => void;
  page: number;
  pageSize: number;
  prices: AdminPriceRow[];
  selectedPriceKey?: string | null;
  total: number;
}

export function AdminPricesTable({
  backendContract,
  errorMessage,
  isLoading = false,
  onEditPrice,
  onPageChange,
  onSelectPrice,
  page,
  pageSize,
  prices,
  selectedPriceKey,
  total,
}: AdminPricesTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Precios comerciales">
            Precios comerciales
          </h3>
          <p className="truncate text-xs text-slate-500">
            Precio vigente, propietario del dato, costo y salud comercial.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState description="Consultando precios efectivos desde catalogo." title="Cargando precios" />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar los precios" />
        ) : prices.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {prices.map((item) => {
              const priceKey = `${item.entityType}:${item.entityId}`;
              const isSelected = priceKey === selectedPriceKey;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.85fr)_minmax(7rem,0.55fr)_minmax(7rem,0.55fr)_auto]",
                    isSelected
                      ? "border-[var(--ui-color-info)] bg-[var(--ui-color-info-soft)]"
                      : "border-[var(--ui-color-border)] bg-white hover:bg-slate-50",
                  ].join(" ")}
                  key={priceKey}
                >
                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.entityName}
                    type="button"
                    onClick={() => onSelectPrice(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.entityName}
                    </span>
                    <span className="mt-0.5 flex min-w-0 items-center gap-1.5 text-xs text-slate-500">
                      <span className="truncate" title={item.entityCode}>
                        {item.entityCode}
                      </span>
                      <span aria-hidden="true">-</span>
                      <span className="truncate" title={item.className}>
                        {item.className}
                      </span>
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${formatCaptureMode(item)} - ${formatOwner(item)}`}
                    type="button"
                    onClick={() => onSelectPrice(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">
                      {formatCaptureMode(item)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Fuente: {formatOwner(item)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={formatMoney(item.currentPrice, item.currencyCode)}
                    type="button"
                    onClick={() => onSelectPrice(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.currentPrice, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{item.currencyCode}</span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`Costo ${formatMoney(item.standardCost, item.currencyCode)} - margen ${formatMargin(item)}`}
                    type="button"
                    onClick={() => onSelectPrice(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {formatMoney(item.standardCost, item.currencyCode)}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">Margen {formatMargin(item)}</span>
                  </button>

                  <div className="flex min-w-0 flex-col gap-1.5 lg:items-end">
                    <div className="flex min-w-0 flex-wrap gap-1.5 lg:justify-end">
                      <span
                        className={`max-w-full truncate rounded-full border px-2 py-0.5 text-[0.72rem] font-semibold ${healthToneClass(item.health)}`}
                        title={formatHealth(item.health)}
                      >
                        {formatHealth(item.health)}
                      </span>
                      <span className="max-w-full truncate rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-0.5 text-[0.72rem] font-semibold text-slate-600">
                        {item.status === "active" ? "Activo" : "Inactivo"}
                      </span>
                    </div>
                    <button
                      className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      type="button"
                      onClick={() => onEditPrice(item)}
                    >
                      Editar precio
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="grid gap-2">
            <AdminEmptyState
              description="Aqui se mostraran precios efectivos cuando existan productos directos o clases de captura que coincidan con los filtros."
              title="Sin precios comerciales"
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
