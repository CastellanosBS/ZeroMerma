import type { ReactNode } from "react";

import type {
  AdminInputSupplyKind,
  AdminInputSupplyFilterOptions,
  AdminInputSupplyListFilters,
  AdminInputSupplyStatus,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const resetFilters: Partial<AdminInputSupplyListFilters> = {
  classId: null,
  costState: "all",
  inventoryTracked: "all",
  page: 1,
  productKind: "all",
  purchasable: "all",
  recipeUsage: "all",
  search: "",
  status: "all",
  stockState: "all",
  supplierId: null,
  usageType: null,
  warningState: "all",
  withoutSupplier: "all",
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

interface AdminInputSuppliesFiltersProps {
  filters: AdminInputSupplyListFilters;
  isBackendConnected: boolean;
  options: AdminInputSupplyFilterOptions;
  onChange: (patch: Partial<AdminInputSupplyListFilters>) => void;
}

export function AdminInputSuppliesFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminInputSuppliesFiltersProps) {
  const hasActiveFilters = Boolean(
    filters.classId ||
    filters.supplierId ||
    filters.usageType ||
    filters.search ||
    filters.costState !== "all" ||
    filters.inventoryTracked !== "all" ||
    filters.productKind !== "all" ||
    filters.purchasable !== "all" ||
    filters.recipeUsage !== "all" ||
    filters.status !== "all" ||
    filters.stockState !== "all" ||
    filters.warningState !== "all" ||
    filters.withoutSupplier !== "all",
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1.25fr)_minmax(10rem,0.85fr)_minmax(10rem,0.85fr)_minmax(9rem,0.75fr)_auto]">
        <Field id="admin-inputs-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-inputs-search"
            placeholder="Nombre, codigo, proveedor"
            title="Buscar por nombre, codigo o proveedor"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ page: 1, search: event.target.value })}
          />
        </Field>

        <Field id="admin-inputs-kind" label="Tipo">
          <select
            className={inputClassName}
            id="admin-inputs-kind"
            value={filters.productKind ?? "all"}
            onChange={(event) =>
              onChange({ page: 1, productKind: event.target.value as AdminInputSupplyKind | "all" })
            }
          >
            <option value="all">Todos</option>
            {options.productKinds.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-inputs-supplier" label="Proveedor">
          <select
            className={`${inputClassName} truncate`}
            id="admin-inputs-supplier"
            value={filters.supplierId ?? ""}
            onChange={(event) => onChange({ page: 1, supplierId: event.target.value || null })}
          >
            <option value="">Todos</option>
            {options.suppliers.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-inputs-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-inputs-status"
            value={filters.status ?? "all"}
            onChange={(event) =>
              onChange({ page: 1, status: event.target.value as AdminInputSupplyStatus | "all" })
            }
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
        <div className="mt-2 grid min-w-0 gap-2 md:grid-cols-4">
          <Field id="admin-inputs-class" label="Categoria">
            <select
              className={`${inputClassName} truncate`}
              id="admin-inputs-class"
              value={filters.classId ?? ""}
              onChange={(event) => onChange({ classId: event.target.value || null, page: 1 })}
            >
              <option value="">Todas</option>
              {options.classes.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-inputs-stock" label="Stock">
            <select
              className={inputClassName}
              id="admin-inputs-stock"
              value={filters.stockState ?? "all"}
              onChange={(event) =>
                onChange({
                  page: 1,
                  stockState: event.target.value as AdminInputSupplyListFilters["stockState"],
                })
              }
            >
              <option value="all">Todos</option>
              {options.stockStates.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-inputs-cost" label="Costo">
            <select
              className={inputClassName}
              id="admin-inputs-cost"
              value={filters.costState ?? "all"}
              onChange={(event) =>
                onChange({
                  costState: event.target.value as AdminInputSupplyListFilters["costState"],
                  page: 1,
                })
              }
            >
              <option value="all">Todos</option>
              {options.costStates.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-inputs-recipe" label="Recetas">
            <select
              className={inputClassName}
              id="admin-inputs-recipe"
              value={filters.recipeUsage ?? "all"}
              onChange={(event) =>
                onChange({
                  page: 1,
                  recipeUsage: event.target.value as AdminInputSupplyListFilters["recipeUsage"],
                })
              }
            >
              <option value="all">Todos</option>
              {options.recipeUsageStates.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-inputs-usage" label="Uso">
            <select
              className={inputClassName}
              id="admin-inputs-usage"
              value={filters.usageType ?? ""}
              onChange={(event) => onChange({ page: 1, usageType: event.target.value || null })}
            >
              <option value="">Todos</option>
              {options.usageTypes.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-inputs-inventory-tracked" label="Inventariable">
            <select
              className={inputClassName}
              id="admin-inputs-inventory-tracked"
              value={filters.inventoryTracked ?? "all"}
              onChange={(event) =>
                onChange({
                  inventoryTracked: event.target
                    .value as AdminInputSupplyListFilters["inventoryTracked"],
                  page: 1,
                })
              }
            >
              <option value="all">Todos</option>
              <option value="true">Si</option>
              <option value="false">No</option>
            </select>
          </Field>

          <Field id="admin-inputs-purchasable" label="Comprable">
            <select
              className={inputClassName}
              id="admin-inputs-purchasable"
              value={filters.purchasable ?? "all"}
              onChange={(event) =>
                onChange({
                  page: 1,
                  purchasable: event.target.value as AdminInputSupplyListFilters["purchasable"],
                })
              }
            >
              <option value="all">Todos</option>
              <option value="true">Si</option>
              <option value="false">No</option>
            </select>
          </Field>

          <Field id="admin-inputs-warning" label="Advertencias">
            <select
              className={inputClassName}
              id="admin-inputs-warning"
              value={filters.warningState ?? "all"}
              onChange={(event) =>
                onChange({
                  page: 1,
                  warningState: event.target.value as AdminInputSupplyListFilters["warningState"],
                })
              }
            >
              <option value="all">Todas</option>
              {options.warningStates.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </details>

      <div className="flex min-w-0 flex-wrap gap-2 text-xs">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ page: 1, productKind: "RAW_MATERIAL" })}
        >
          Materia prima
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ page: 1, productKind: "CONSUMABLE" })}
        >
          Consumibles
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ page: 1, productKind: "DISPOSABLE" })}
        >
          Desechables
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ page: 1, supplierId: null, withoutSupplier: "true" })}
        >
          Sin proveedor
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ costState: "missing_cost", page: 1 })}
        >
          Sin costo
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ page: 1, stockState: "low_stock" })}
        >
          Stock bajo
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600"
          type="button"
          onClick={() => onChange({ page: 1, recipeUsage: "used" })}
        >
          Usados en recetas
        </button>
      </div>
    </section>
  );
}
