import type { AdminReconciliationFilterOptions, AdminReconciliationListFilters } from "../types";

interface AdminReconciliationFiltersProps {
  filters: AdminReconciliationListFilters;
  isBackendConnected: boolean;
  options: AdminReconciliationFilterOptions;
  onChange: (patch: Partial<AdminReconciliationListFilters>) => void;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function last7DaysIsoDate() {
  const date = new Date();
  date.setDate(date.getDate() - 6);
  return date.toISOString().slice(0, 10);
}

export function AdminReconciliationFilters({
  filters,
  isBackendConnected,
  options,
  onChange,
}: AdminReconciliationFiltersProps) {
  const selectClass =
    "h-9 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-700 focus:border-[var(--ui-color-primary)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";
  const inputClass =
    "h-9 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm text-slate-800 placeholder:text-slate-400 focus:border-[var(--ui-color-primary)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";
  const quickButtonClass =
    "rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";

  return (
    <section className="grid shrink-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3">
      <div className="grid gap-2 lg:grid-cols-[minmax(12rem,1.2fr)_repeat(4,minmax(8.5rem,0.8fr))]">
        <input
          className={inputClass}
          disabled={!isBackendConnected}
          placeholder="Buscar folio, corte, sucursal, caja o responsable"
          type="search"
          value={filters.search}
          onChange={(event) => onChange({ search: event.target.value })}
        />

        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.branchId}
          onChange={(event) => onChange({ branchId: event.target.value })}
        >
          <option value="all">Todas las sucursales</option>
          {options.branches.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.workstationId}
          onChange={(event) => onChange({ workstationId: event.target.value })}
        >
          <option value="all">Todas las cajas</option>
          {options.workstations.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.cashierId}
          onChange={(event) => onChange({ cashierId: event.target.value })}
        >
          <option value="all">Todos los responsables</option>
          {options.cashiers.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.status}
          onChange={(event) => onChange({ status: event.target.value })}
        >
          <option value="all">Todos los estados</option>
          {options.statuses.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-2 lg:grid-cols-[repeat(7,minmax(7.5rem,1fr))]">
        <input
          className={inputClass}
          disabled={!isBackendConnected}
          type="date"
          value={filters.dateFrom ?? ""}
          onChange={(event) => onChange({ dateFrom: event.target.value || null })}
        />
        <input
          className={inputClass}
          disabled={!isBackendConnected}
          type="date"
          value={filters.dateTo ?? ""}
          onChange={(event) => onChange({ dateTo: event.target.value || null })}
        />
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.discrepancyType}
          onChange={(event) => onChange({ discrepancyType: event.target.value })}
        >
          <option value="all">Todas las diferencias</option>
          {options.discrepancyTypes.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.paymentMethod}
          onChange={(event) => onChange({ paymentMethod: event.target.value })}
        >
          <option value="all">Todos los metodos</option>
          {options.paymentMethods.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.sourceType}
          onChange={(event) => onChange({ sourceType: event.target.value })}
        >
          <option value="all">Todos los origenes</option>
          {options.sourceTypes.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.evidenceState}
          onChange={(event) => onChange({ evidenceState: event.target.value })}
        >
          <option value="all">Evidencia: todas</option>
          {options.evidenceStates.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>
        <div className="grid grid-cols-2 gap-2">
          <input
            className={inputClass}
            disabled={!isBackendConnected}
            min="0"
            placeholder="Min"
            type="number"
            value={filters.amountMin}
            onChange={(event) => onChange({ amountMin: event.target.value })}
          />
          <input
            className={inputClass}
            disabled={!isBackendConnected}
            min="0"
            placeholder="Max"
            type="number"
            value={filters.amountMax}
            onChange={(event) => onChange({ amountMax: event.target.value })}
          />
        </div>
      </div>

      <div className="flex min-w-0 flex-wrap items-center gap-1.5">
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ status: "PENDING" })}
        >
          Pendientes
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ status: "RECONCILED" })}
        >
          Conciliadas
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ discrepancyType: "SHORTAGE" })}
        >
          Faltantes
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ discrepancyType: "OVERAGE" })}
        >
          Sobrantes
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ paymentMethod: "CASH" })}
        >
          Efectivo
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ paymentMethod: "CARD" })}
        >
          Tarjeta
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ dateFrom: todayIsoDate(), dateTo: todayIsoDate() })}
        >
          Hoy
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ dateFrom: last7DaysIsoDate(), dateTo: todayIsoDate() })}
        >
          Ultimos 7 dias
        </button>
      </div>
    </section>
  );
}
