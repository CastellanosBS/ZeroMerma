import type { ReactNode } from "react";

import type {
  AdminPurchaseFilterOptions,
  AdminPurchaseListFilters,
  AdminPurchaseStatus,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const resetFilters: Partial<AdminPurchaseListFilters> = {
  amountMax: null,
  amountMin: null,
  branchId: null,
  dateFrom: null,
  dateTo: null,
  discrepancyState: "all",
  operatorUserId: null,
  page: 1,
  productId: null,
  productKind: "all",
  search: "",
  status: "all",
  supplierId: null,
  warningState: "all",
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

interface AdminPurchasesFiltersProps {
  filters: AdminPurchaseListFilters;
  isBackendConnected: boolean;
  options: AdminPurchaseFilterOptions;
  onChange: (patch: Partial<AdminPurchaseListFilters>) => void;
}

export function AdminPurchasesFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminPurchasesFiltersProps) {
  const hasActiveFilters = Boolean(
    filters.amountMax ||
      filters.amountMin ||
      filters.branchId ||
      filters.dateFrom ||
      filters.dateTo ||
      filters.operatorUserId ||
      filters.productId ||
      filters.search ||
      filters.supplierId ||
      filters.discrepancyState !== "all" ||
      filters.productKind !== "all" ||
      filters.status !== "all" ||
      filters.warningState !== "all",
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1.25fr)_minmax(10rem,0.9fr)_minmax(10rem,0.9fr)_minmax(9rem,0.7fr)_auto]">
        <Field id="admin-purchases-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-purchases-search"
            placeholder="Folio, proveedor, documento externo"
            title="Buscar por folio, proveedor o documento externo"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ page: 1, search: event.target.value })}
          />
        </Field>

        <Field id="admin-purchases-supplier" label="Proveedor">
          <select
            className={`${inputClassName} truncate`}
            id="admin-purchases-supplier"
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

        <Field id="admin-purchases-branch" label="Sucursal">
          <select
            className={`${inputClassName} truncate`}
            id="admin-purchases-branch"
            value={filters.branchId ?? ""}
            onChange={(event) => onChange({ branchId: event.target.value || null, page: 1 })}
          >
            <option value="">Todas</option>
            {options.branches.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-purchases-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-purchases-status"
            value={filters.status ?? "all"}
            onChange={(event) =>
              onChange({ page: 1, status: event.target.value as AdminPurchaseStatus | "all" })
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
          <Field id="admin-purchases-product" label="Producto">
            <select
              className={`${inputClassName} truncate`}
              id="admin-purchases-product"
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

          <Field id="admin-purchases-kind" label="Tipo producto">
            <select
              className={inputClassName}
              id="admin-purchases-kind"
              value={filters.productKind ?? "all"}
              onChange={(event) => onChange({ page: 1, productKind: event.target.value })}
            >
              <option value="all">Todos</option>
              {options.productKinds.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field id="admin-purchases-discrepancy" label="Discrepancias">
            <select
              className={inputClassName}
              id="admin-purchases-discrepancy"
              value={filters.discrepancyState ?? "all"}
              onChange={(event) =>
                onChange({
                  discrepancyState: event.target.value as AdminPurchaseListFilters["discrepancyState"],
                  page: 1,
                })
              }
            >
              <option value="all">Todas</option>
              <option value="with_discrepancy">Con discrepancias</option>
              <option value="without_discrepancy">Sin discrepancias</option>
            </select>
          </Field>

          <Field id="admin-purchases-operator" label="Operador">
            <select
              className={`${inputClassName} truncate`}
              id="admin-purchases-operator"
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

          <Field id="admin-purchases-date-from" label="Desde">
            <input
              className={inputClassName}
              id="admin-purchases-date-from"
              type="date"
              value={filters.dateFrom ?? ""}
              onChange={(event) => onChange({ dateFrom: event.target.value || null, page: 1 })}
            />
          </Field>

          <Field id="admin-purchases-date-to" label="Hasta">
            <input
              className={inputClassName}
              id="admin-purchases-date-to"
              type="date"
              value={filters.dateTo ?? ""}
              onChange={(event) => onChange({ dateTo: event.target.value || null, page: 1 })}
            />
          </Field>

          <Field id="admin-purchases-amount-min" label="Monto min.">
            <input
              className={inputClassName}
              id="admin-purchases-amount-min"
              min="0"
              step="0.01"
              type="number"
              value={filters.amountMin ?? ""}
              onChange={(event) => onChange({ amountMin: event.target.value || null, page: 1 })}
            />
          </Field>

          <Field id="admin-purchases-amount-max" label="Monto max.">
            <input
              className={inputClassName}
              id="admin-purchases-amount-max"
              min="0"
              step="0.01"
              type="number"
              value={filters.amountMax ?? ""}
              onChange={(event) => onChange({ amountMax: event.target.value || null, page: 1 })}
            />
          </Field>
        </div>
      </details>

      <div className="flex min-w-0 flex-wrap gap-2 text-xs">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ dateFrom: new Date().toISOString().slice(0, 10), page: 1 })}
        >
          Hoy
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "ORDERED" })}
        >
          Pendientes
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "PARTIALLY_RECEIVED" })}
        >
          Parciales
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "RECEIVED" })}
        >
          Recibidas
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ discrepancyState: "with_discrepancy", page: 1 })}
        >
          Con discrepancias
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, productKind: "RAW_MATERIAL" })}
        >
          Materia prima
        </button>
      </div>
    </section>
  );
}
