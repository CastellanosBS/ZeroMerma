import type { ReactNode } from "react";

import type {
  AdminProductClassCaptureMode,
  AdminProductClassFilterOptions,
  AdminProductClassListFilters,
  AdminProductClassProductPresence,
  AdminProductClassStatus,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const statusOptions: Array<{ label: string; value: AdminProductClassStatus | "all" }> = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activo" },
  { value: "inactive", label: "Inactivo" },
];

const captureModeOptions: Array<{ label: string; value: AdminProductClassCaptureMode | "all" }> = [
  { value: "all", label: "Todos" },
  { value: "PRODUCT_DIRECT", label: "Producto directo" },
  { value: "CLASS_CAPTURE", label: "Captura por clase" },
];

const productPresenceOptions: Array<{ label: string; value: AdminProductClassProductPresence }> = [
  { value: "all", label: "Todas" },
  { value: "with_products", label: "Con productos" },
  { value: "without_products", label: "Sin productos" },
];

const resetFilters: Partial<AdminProductClassListFilters> = {
  brandId: null,
  captureMode: "all",
  page: 1,
  productPresence: "all",
  search: "",
  status: "all",
};

function Field({
  children,
  className = "",
  id,
  label,
}: {
  children: ReactNode;
  className?: string;
  id: string;
  label: string;
}) {
  return (
    <label
      className={`grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 ${className}`}
      htmlFor={id}
      title={label}
    >
      <span className="truncate">{label}</span>
      {children}
    </label>
  );
}

interface AdminClassesFiltersProps {
  filters: AdminProductClassListFilters;
  isBackendConnected: boolean;
  options: AdminProductClassFilterOptions;
  onChange: (patch: Partial<AdminProductClassListFilters>) => void;
}

export function AdminClassesFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminClassesFiltersProps) {
  const brandDisabled = options.brands.length === 0;
  const hasActiveFilters = Boolean(
    filters.brandId ||
      filters.search ||
      filters.captureMode !== "all" ||
      filters.status !== "all" ||
      filters.productPresence !== "all",
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1.4fr)_minmax(9rem,0.75fr)_minmax(8rem,0.6fr)_minmax(9rem,0.7fr)_minmax(9rem,0.7fr)_auto]">
        <Field id="admin-classes-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-classes-search"
            placeholder="Buscar clase, codigo o alias"
            title="Buscar clase, codigo o alias"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ search: event.target.value, page: 1 })}
          />
        </Field>

        <Field id="admin-classes-brand" label="Marca">
          <select
            className={`${inputClassName} truncate`}
            disabled={brandDisabled}
            id="admin-classes-brand"
            title={brandDisabled ? "Marcas pendientes de API" : "Selecciona marca"}
            value={filters.brandId ?? ""}
            onChange={(event) => onChange({ brandId: event.target.value || null, page: 1 })}
          >
            {brandDisabled ? <option value="">Marcas pendientes de API</option> : <option value="">Todas</option>}
            {options.brands.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-classes-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-classes-status"
            value={filters.status ?? "all"}
            onChange={(event) =>
              onChange({ status: event.target.value as AdminProductClassStatus | "all", page: 1 })
            }
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-classes-capture-mode" label="Modo POS">
          <select
            className={inputClassName}
            id="admin-classes-capture-mode"
            value={filters.captureMode ?? "all"}
            onChange={(event) =>
              onChange({
                captureMode: event.target.value as AdminProductClassCaptureMode | "all",
                page: 1,
              })
            }
          >
            {captureModeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-classes-product-presence" label="Productos">
          <select
            className={inputClassName}
            id="admin-classes-product-presence"
            value={filters.productPresence ?? "all"}
            onChange={(event) =>
              onChange({
                productPresence: event.target.value as AdminProductClassProductPresence,
                page: 1,
              })
            }
          >
            {productPresenceOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <div className="flex min-w-0 items-end md:col-span-2 xl:col-span-1">
          <div className="flex min-w-0 max-w-full flex-wrap items-center gap-2 text-xs text-slate-500 xl:justify-end">
            <span className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600">
              {isBackendConnected ? "Datos conectados" : "Esperando API"}
            </span>
            {hasActiveFilters ? (
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                type="button"
                onClick={() => onChange(resetFilters)}
              >
                Limpiar
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
