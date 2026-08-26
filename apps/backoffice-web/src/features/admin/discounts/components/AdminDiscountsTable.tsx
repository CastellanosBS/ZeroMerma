import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminDiscount, AdminDiscountBackendContract, AdminDiscountHealth } from "../types";

function formatMoney(value: string | null | undefined, currencyCode: string): string {
  if (!value) {
    return "N/A";
  }
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(numericValue);
}

function formatDiscountValue(item: AdminDiscount): string {
  if (item.discountType === "PERCENTAGE") {
    return `${Number(item.value).toFixed(2)}%`;
  }
  return formatMoney(item.value, item.currencyCode);
}

function formatScope(item: AdminDiscount): string {
  if (item.targetScope === "PRODUCT") {
    return "Producto";
  }
  if (item.targetScope === "CLASS") {
    return "Clase";
  }
  return "Global";
}

function formatHealth(value: AdminDiscountHealth): string {
  const labels: Record<AdminDiscountHealth, string> = {
    expired: "Expirado",
    healthy: "Saludable",
    invalid: "Invalido",
    warning: "Revisar",
  };
  return labels[value];
}

function healthToneClass(value: AdminDiscountHealth): string {
  if (value === "healthy") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "invalid" || value === "expired") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

function validityLabel(item: AdminDiscount): string {
  const labels = {
    current: "Vigente",
    expired: "Expirada",
    not_scheduled: "Sin calendario",
    upcoming: "Proxima",
  } as const;
  return labels[item.validityStatus];
}

interface AdminDiscountsTableProps {
  backendContract: AdminDiscountBackendContract;
  discounts: AdminDiscount[];
  errorMessage?: string | null;
  isLoading?: boolean;
  isUpdating?: boolean;
  onDuplicateDiscount: (item: AdminDiscount) => void;
  onEditDiscount: (item: AdminDiscount) => void;
  onPageChange: (page: number) => void;
  onSelectDiscount: (item: AdminDiscount) => void;
  onToggleStatus: (item: AdminDiscount) => void;
  page: number;
  pageSize: number;
  selectedDiscountId?: string | null;
  total: number;
}

export function AdminDiscountsTable({
  backendContract,
  discounts,
  errorMessage,
  isLoading = false,
  isUpdating = false,
  onDuplicateDiscount,
  onEditDiscount,
  onPageChange,
  onSelectDiscount,
  onToggleStatus,
  page,
  pageSize,
  selectedDiscountId,
  total,
}: AdminDiscountsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title="Descuentos comerciales">
            Descuentos comerciales
          </h3>
          <p className="truncate text-xs text-slate-500">
            Reglas comerciales, alcance, vigencia y salud operativa.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState description="Consultando definiciones comerciales desde backend." title="Cargando descuentos" />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar los descuentos" />
        ) : discounts.length > 0 ? (
          <div className="grid min-w-0 gap-1.5">
            {discounts.map((item) => {
              const isSelected = item.id === selectedDiscountId;
              return (
                <article
                  className={[
                    "grid min-w-0 gap-2 rounded-[16px] border px-3 py-2 transition lg:grid-cols-[minmax(0,1.25fr)_minmax(0,0.8fr)_minmax(0,0.8fr)_minmax(7rem,0.55fr)_auto]",
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
                    onClick={() => onSelectDiscount(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{item.name}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.code ?? "Sin codigo"} - {item.discountType === "PERCENTAGE" ? "Porcentaje" : "Monto fijo"}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={item.targetName ?? formatScope(item)}
                    type="button"
                    onClick={() => onSelectDiscount(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-800">{formatScope(item)}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      {item.targetName ?? item.brandName ?? "Sin objetivo especifico"}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={`${formatDiscountValue(item)} sobre ${formatMoney(item.basePrice, item.currencyCode)}`}
                    type="button"
                    onClick={() => onSelectDiscount(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">{formatDiscountValue(item)}</span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">
                      Resultado {formatMoney(item.previewPrice, item.currencyCode)}
                    </span>
                  </button>

                  <button
                    className="min-w-0 text-left lg:text-right focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                    title={validityLabel(item)}
                    type="button"
                    onClick={() => onSelectDiscount(item)}
                  >
                    <span className="block truncate text-sm font-semibold text-slate-950">
                      {item.status === "ACTIVE" ? "Activo" : item.status === "INACTIVE" ? "Inactivo" : "Archivado"}
                    </span>
                    <span className="mt-0.5 block truncate text-xs text-slate-500">{validityLabel(item)}</span>
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
                        Prioridad {item.priority}
                      </span>
                    </div>
                    <div className="flex min-w-0 flex-wrap gap-1.5 lg:justify-end">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                        type="button"
                        onClick={() => onEditDiscount(item)}
                      >
                        Editar
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onToggleStatus(item)}
                      >
                        {item.status === "ACTIVE" ? "Desactivar" : "Activar"}
                      </button>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100"
                        disabled={isUpdating}
                        type="button"
                        onClick={() => onDuplicateDiscount(item)}
                      >
                        Duplicar
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
              description="Crea una definicion para productos, clases o alcance global cuando exista una regla comercial real."
              title="Sin descuentos comerciales"
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
