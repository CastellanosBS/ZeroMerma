import type { ReactNode } from "react";

import type {
  AdminProductionFilterOptions,
  AdminProductionListFilters,
  AdminProductionStatus,
  AdminProductionVarianceState,
  AdminProductionWarningSeverity,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const resetFilters: Partial<AdminProductionListFilters> = {
  branchId: null,
  dateFrom: null,
  dateTo: null,
  operatorUserId: null,
  page: 1,
  productId: null,
  recipeId: null,
  search: "",
  status: "all",
  varianceState: "all",
  warningState: "all",
};

const varianceOptions: Array<{ label: string; value: AdminProductionVarianceState | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "with_variance", label: "Con variacion" },
  { value: "without_variance", label: "Sin variacion" },
];

const warningOptions: Array<{ label: string; value: AdminProductionWarningSeverity | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "critical", label: "Criticas" },
  { value: "warning", label: "Advertencias" },
  { value: "info", label: "Informativas" },
];

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

interface AdminProductionFiltersProps {
  filters: AdminProductionListFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminProductionListFilters>) => void;
  options: AdminProductionFilterOptions;
}

export function AdminProductionFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminProductionFiltersProps) {
  const hasActiveFilters = Boolean(
    filters.search ||
      filters.branchId ||
      filters.operatorUserId ||
      filters.productId ||
      filters.recipeId ||
      filters.dateFrom ||
      filters.dateTo ||
      filters.status !== "all" ||
      filters.varianceState !== "all" ||
      filters.warningState !== "all",
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(15rem,1.35fr)_minmax(10rem,0.9fr)_minmax(11rem,1fr)_minmax(9rem,0.7fr)_auto]">
        <Field id="admin-production-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-production-search"
            placeholder="Folio, producto, receta u operador"
            title="Buscar por folio, producto, receta u operador"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ page: 1, search: event.target.value })}
          />
        </Field>

        <Field id="admin-production-branch" label="Sucursal">
          <select
            className={`${inputClassName} truncate`}
            disabled={options.branches.length === 0}
            id="admin-production-branch"
            value={filters.branchId ?? ""}
            onChange={(event) => onChange({ branchId: event.target.value || null, page: 1 })}
          >
            {options.branches.length === 0 ? <option value="">Sucursales pendientes de API</option> : <option value="">Todas</option>}
            {options.branches.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-production-product" label="Producto terminado">
          <select
            className={`${inputClassName} truncate`}
            id="admin-production-product"
            value={filters.productId ?? ""}
            onChange={(event) => onChange({ page: 1, productId: event.target.value || null })}
          >
            <option value="">Todos</option>
            {options.products.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-production-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-production-status"
            value={filters.status ?? "all"}
            onChange={(event) => onChange({ page: 1, status: event.target.value as AdminProductionStatus | "all" })}
          >
            <option value="all">Todos</option>
            {options.statuses.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
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

      <details className="group rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3 py-2">
        <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 outline-none transition focus:ring-4 focus:ring-[var(--ui-color-ring)]">
          Filtros avanzados
        </summary>
        <div className="mt-2 grid min-w-0 gap-2 md:grid-cols-3 xl:grid-cols-6">
          <Field id="admin-production-date-from" label="Desde">
            <input
              className={inputClassName}
              id="admin-production-date-from"
              type="date"
              value={filters.dateFrom ?? ""}
              onChange={(event) => onChange({ dateFrom: event.target.value || null, page: 1 })}
            />
          </Field>

          <Field id="admin-production-date-to" label="Hasta">
            <input
              className={inputClassName}
              id="admin-production-date-to"
              type="date"
              value={filters.dateTo ?? ""}
              onChange={(event) => onChange({ dateTo: event.target.value || null, page: 1 })}
            />
          </Field>

          <Field id="admin-production-recipe" label="Receta">
            <select
              className={`${inputClassName} truncate`}
              id="admin-production-recipe"
              value={filters.recipeId ?? ""}
              onChange={(event) => onChange({ page: 1, recipeId: event.target.value || null })}
            >
              <option value="">Todas</option>
              {options.recipes.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-production-operator" label="Operador">
            <select
              className={`${inputClassName} truncate`}
              id="admin-production-operator"
              value={filters.operatorUserId ?? ""}
              onChange={(event) => onChange({ operatorUserId: event.target.value || null, page: 1 })}
            >
              <option value="">Todos</option>
              {options.operators.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-production-variance" label="Variacion">
            <select
              className={inputClassName}
              id="admin-production-variance"
              value={filters.varianceState ?? "all"}
              onChange={(event) =>
                onChange({ page: 1, varianceState: event.target.value as AdminProductionVarianceState | "all" })
              }
            >
              {varianceOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-production-warning" label="Alertas">
            <select
              className={inputClassName}
              id="admin-production-warning"
              value={filters.warningState ?? "all"}
              onChange={(event) =>
                onChange({ page: 1, warningState: event.target.value as AdminProductionWarningSeverity | "all" })
              }
            >
              {warningOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </details>

      <div className="flex min-w-0 flex-wrap gap-2 text-xs">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "DRAFT" })}
        >
          Pendientes
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "IN_PROGRESS" })}
        >
          En proceso
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, warningState: "critical" })}
        >
          Con faltantes
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, varianceState: "with_variance" })}
        >
          Con variacion
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "COMPLETED" })}
        >
          Completadas
        </button>
      </div>
    </section>
  );
}
