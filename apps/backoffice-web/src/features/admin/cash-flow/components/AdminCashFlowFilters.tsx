import type { AdminCashFlowFilterOptions, AdminCashFlowListFilters } from "../types";

interface AdminCashFlowFiltersProps {
  filters: AdminCashFlowListFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminCashFlowListFilters>) => void;
  options: AdminCashFlowFilterOptions;
}

function optionNodes(options: Array<{ id: string; label: string }>) {
  return options.map((option) => (
    <option key={option.id} value={option.id}>
      {option.label}
    </option>
  ));
}

export function AdminCashFlowFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminCashFlowFiltersProps) {
  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3">
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <input
          className="h-10 min-w-[14rem] flex-1 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-800"
          placeholder="Buscar folio, documento, categoria u operador"
          value={filters.search}
          onChange={(event) => onChange({ search: event.target.value })}
        />
        <input
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          type="date"
          value={filters.dateFrom ?? ""}
          onChange={(event) => onChange({ dateFrom: event.target.value || null })}
        />
        <input
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          type="date"
          value={filters.dateTo ?? ""}
          onChange={(event) => onChange({ dateTo: event.target.value || null })}
        />
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            isBackendConnected
              ? "bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
              : "bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
          }`}
        >
          {isBackendConnected ? "API conectada" : "Integracion parcial"}
        </span>
      </div>

      <div className="mt-3 grid gap-2 md:grid-cols-4 xl:grid-cols-8">
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.branchId}
          onChange={(event) => onChange({ branchId: event.target.value })}
        >
          <option value="all">Todas las sucursales</option>
          {optionNodes(options.branches)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.workstationId}
          onChange={(event) => onChange({ workstationId: event.target.value })}
        >
          <option value="all">Todas las cajas</option>
          {optionNodes(options.workstations)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.direction}
          onChange={(event) => onChange({ direction: event.target.value })}
        >
          <option value="all">Todas las direcciones</option>
          {optionNodes(options.directions)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.sourceType}
          onChange={(event) => onChange({ sourceType: event.target.value })}
        >
          <option value="all">Todos los origenes</option>
          {optionNodes(options.sourceTypes)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.paymentMethod}
          onChange={(event) => onChange({ paymentMethod: event.target.value })}
        >
          <option value="all">Todos los metodos</option>
          {optionNodes(options.paymentMethods)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.reconciliationState}
          onChange={(event) => onChange({ reconciliationState: event.target.value })}
        >
          <option value="all">Toda conciliacion</option>
          {optionNodes(options.reconciliationStates)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.category}
          onChange={(event) => onChange({ category: event.target.value })}
        >
          <option value="all">Todas las categorias</option>
          {optionNodes(options.categories)}
        </select>
        <select
          className="h-10 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-700"
          value={filters.operatorId}
          onChange={(event) => onChange({ operatorId: event.target.value })}
        >
          <option value="all">Todos los operadores</option>
          {optionNodes(options.operators)}
        </select>
      </div>

      <div className="mt-3 flex min-w-0 flex-wrap gap-2">
        {[
          {
            label: "Hoy",
            patch: {
              dateFrom: new Date().toISOString().slice(0, 10),
              dateTo: new Date().toISOString().slice(0, 10),
            },
          },
          { label: "Entradas", patch: { direction: "INFLOW" } },
          { label: "Salidas", patch: { direction: "OUTFLOW" } },
          { label: "Efectivo", patch: { paymentMethod: "CASH" } },
          { label: "Tarjeta", patch: { paymentMethod: "CARD" } },
          { label: "Pendiente de conciliacion", patch: { reconciliationState: "PENDING" } },
          { label: "Con diferencia", patch: { sourceType: "CASH_CUT_DIFFERENCE" } },
        ].map((quick) => (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)]"
            key={quick.label}
            type="button"
            onClick={() => onChange(quick.patch)}
          >
            {quick.label}
          </button>
        ))}
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-600"
          type="button"
          onClick={() =>
            onChange({
              amountMax: "",
              amountMin: "",
              branchId: "all",
              category: "all",
              dateFrom: null,
              dateTo: null,
              direction: "all",
              operatorId: "all",
              paymentMethod: "all",
              reconciliationState: "all",
              search: "",
              sourceType: "all",
              workstationId: "all",
            })
          }
        >
          Limpiar filtros
        </button>
      </div>
    </section>
  );
}
