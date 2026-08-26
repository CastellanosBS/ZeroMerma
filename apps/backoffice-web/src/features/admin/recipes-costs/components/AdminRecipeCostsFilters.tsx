import type { ReactNode } from "react";

import type {
  AdminRecipeCostFilterOptions,
  AdminRecipeCostListFilters,
  AdminRecipeState,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const recipeStateOptions: Array<{ label: string; value: AdminRecipeState }> = [
  { value: "all", label: "Todos" },
  { value: "no_recipe", label: "Sin receta" },
  { value: "active_recipe", label: "Con receta activa" },
  { value: "warning", label: "Con advertencias" },
];

const resetFilters: Partial<AdminRecipeCostListFilters> = {
  brandId: null,
  classId: null,
  page: 1,
  recipeState: "all",
  search: "",
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

interface AdminRecipeCostsFiltersProps {
  filters: AdminRecipeCostListFilters;
  isBackendConnected: boolean;
  options: AdminRecipeCostFilterOptions;
  onChange: (patch: Partial<AdminRecipeCostListFilters>) => void;
}

export function AdminRecipeCostsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminRecipeCostsFiltersProps) {
  const brandDisabled = options.brands.length === 0;
  const classDisabled = options.classes.length === 0;
  const hasActiveFilters = Boolean(
    filters.brandId || filters.classId || filters.search || filters.recipeState !== "all",
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1.4fr)_minmax(9rem,0.75fr)_minmax(10rem,0.8fr)_minmax(9rem,0.7fr)_auto]">
        <Field id="admin-recipes-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-recipes-search"
            placeholder="Buscar producto, SKU o clase"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ search: event.target.value, page: 1 })}
          />
        </Field>

        <Field id="admin-recipes-brand" label="Marca">
          <select
            className={`${inputClassName} truncate`}
            disabled={brandDisabled}
            id="admin-recipes-brand"
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

        <Field id="admin-recipes-class" label="Clase">
          <select
            className={`${inputClassName} truncate`}
            disabled={classDisabled}
            id="admin-recipes-class"
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

        <Field id="admin-recipes-state" label="Estado receta">
          <select
            className={inputClassName}
            id="admin-recipes-state"
            value={filters.recipeState ?? "all"}
            onChange={(event) => onChange({ recipeState: event.target.value as AdminRecipeState, page: 1 })}
          >
            {recipeStateOptions.map((option) => (
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
