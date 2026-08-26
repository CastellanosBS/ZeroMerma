import type { ReactNode } from "react";
import { useState } from "react";

import type {
  AdminPriceCaptureMode,
  AdminPriceEntityType,
  AdminPriceFilterOptions,
  AdminPriceHealth,
  AdminPriceListFilters,
  AdminPriceStatus,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const entityTypeOptions: Array<{ label: string; value: AdminPriceEntityType | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "product", label: "Producto" },
  { value: "class", label: "Clase" },
];

const captureModeOptions: Array<{ label: string; value: AdminPriceCaptureMode | "all" }> = [
  { value: "all", label: "Todos" },
  { value: "PRODUCT_DIRECT", label: "Producto directo" },
  { value: "CLASS_CAPTURE", label: "Captura por clase" },
];

const statusOptions: Array<{ label: string; value: AdminPriceStatus | "all" }> = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Activo" },
  { value: "inactive", label: "Inactivo" },
];

const healthOptions: Array<{ label: string; value: AdminPriceHealth | "all" }> = [
  { value: "all", label: "Toda salud" },
  { value: "healthy", label: "Saludable" },
  { value: "missing_price", label: "Sin precio" },
  { value: "warning", label: "Revisar" },
  { value: "low_margin", label: "Margen bajo" },
  { value: "negative_margin", label: "Margen negativo" },
];

const resetFilters: Partial<AdminPriceListFilters> = {
  brandId: null,
  captureMode: "all",
  classId: null,
  entityType: "all",
  page: 1,
  priceHealth: "all",
  search: "",
  status: "all",
  updatedFrom: null,
  updatedTo: null,
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

interface AdminPricesFiltersProps {
  filters: AdminPriceListFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminPriceListFilters>) => void;
  options: AdminPriceFilterOptions;
}

export function AdminPricesFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminPricesFiltersProps) {
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const brandDisabled = options.brands.length === 0;
  const classDisabled = options.classes.length === 0;
  const activeAdvancedFilters = [
    filters.classId,
    filters.captureMode !== "all" ? filters.captureMode : null,
    filters.updatedFrom,
    filters.updatedTo,
  ].filter(Boolean).length;
  const hasActiveFilters = Boolean(
    filters.brandId ||
      filters.classId ||
      filters.search ||
      filters.captureMode !== "all" ||
      filters.entityType !== "all" ||
      filters.priceHealth !== "all" ||
      filters.status !== "all" ||
      filters.updatedFrom ||
      filters.updatedTo,
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(15rem,1.4fr)_minmax(9rem,0.7fr)_minmax(9rem,0.7fr)_minmax(9rem,0.7fr)_auto]">
        <Field id="admin-prices-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-prices-search"
            placeholder="Buscar entidad, codigo o clase"
            title="Buscar entidad, codigo o clase"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ search: event.target.value, page: 1 })}
          />
        </Field>

        <Field id="admin-prices-brand" label="Marca">
          <select
            className={`${inputClassName} truncate`}
            disabled={brandDisabled}
            id="admin-prices-brand"
            value={filters.brandId ?? ""}
            onChange={(event) => onChange({ brandId: event.target.value || null, classId: null, page: 1 })}
          >
            {brandDisabled ? <option value="">Marcas pendientes</option> : <option value="">Todas</option>}
            {options.brands.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-prices-entity-type" label="Entidad">
          <select
            className={inputClassName}
            id="admin-prices-entity-type"
            value={filters.entityType ?? "all"}
            onChange={(event) =>
              onChange({ entityType: event.target.value as AdminPriceEntityType | "all", page: 1 })
            }
          >
            {entityTypeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-prices-health" label="Salud">
          <select
            className={inputClassName}
            id="admin-prices-health"
            value={filters.priceHealth ?? "all"}
            onChange={(event) =>
              onChange({ priceHealth: event.target.value as AdminPriceHealth | "all", page: 1 })
            }
          >
            {healthOptions.map((option) => (
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
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              type="button"
              onClick={() => setShowAdvancedFilters((current) => !current)}
            >
              Filtros avanzados{activeAdvancedFilters > 0 ? ` (${activeAdvancedFilters})` : ""}
            </button>
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

      {showAdvancedFilters ? (
        <div className="grid min-w-0 gap-2 border-t border-[var(--ui-color-border)] pt-2 md:grid-cols-3 xl:grid-cols-5">
          <Field id="admin-prices-class" label="Clase">
            <select
              className={`${inputClassName} truncate`}
              disabled={classDisabled}
              id="admin-prices-class"
              value={filters.classId ?? ""}
              onChange={(event) => onChange({ classId: event.target.value || null, page: 1 })}
            >
              {classDisabled ? <option value="">Clases pendientes</option> : <option value="">Todas</option>}
              {options.classes.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-prices-capture" label="Modo">
            <select
              className={inputClassName}
              id="admin-prices-capture"
              value={filters.captureMode ?? "all"}
              onChange={(event) =>
                onChange({ captureMode: event.target.value as AdminPriceCaptureMode | "all", page: 1 })
              }
            >
              {captureModeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-prices-status" label="Estado">
            <select
              className={inputClassName}
              id="admin-prices-status"
              value={filters.status ?? "all"}
              onChange={(event) => onChange({ status: event.target.value as AdminPriceStatus | "all", page: 1 })}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-prices-updated-from" label="Desde">
            <input
              className={inputClassName}
              id="admin-prices-updated-from"
              type="date"
              value={filters.updatedFrom ?? ""}
              onChange={(event) => onChange({ updatedFrom: event.target.value || null, page: 1 })}
            />
          </Field>

          <Field id="admin-prices-updated-to" label="Hasta">
            <input
              className={inputClassName}
              id="admin-prices-updated-to"
              type="date"
              value={filters.updatedTo ?? ""}
              onChange={(event) => onChange({ updatedTo: event.target.value || null, page: 1 })}
            />
          </Field>
        </div>
      ) : null}
    </section>
  );
}
