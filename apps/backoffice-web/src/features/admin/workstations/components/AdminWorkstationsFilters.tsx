import type { ReactNode } from "react";

import type {
  AdminWorkstationCashSessionState,
  AdminWorkstationFilterOptions,
  AdminWorkstationListFilters,
  AdminWorkstationReadiness,
  AdminWorkstationStatus,
  AdminWorkstationWarningState,
} from "../types";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

const resetFilters: Partial<AdminWorkstationListFilters> = {
  branchId: null,
  cashSessionState: "all",
  page: 1,
  readiness: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const statusOptions: Array<{ label: string; value: AdminWorkstationStatus | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "active", label: "Activas" },
  { value: "inactive", label: "Inactivas" },
];

const cashSessionOptions: Array<{ label: string; value: AdminWorkstationCashSessionState }> = [
  { value: "all", label: "Todas" },
  { value: "open", label: "Caja abierta" },
  { value: "closed", label: "Caja cerrada" },
  { value: "no_recent_session", label: "Sin actividad" },
];

const readinessOptions: Array<{ label: string; value: AdminWorkstationReadiness | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "ready", label: "Listas" },
  { value: "warning", label: "Revisar" },
  { value: "blocked", label: "Bloqueadas" },
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

interface AdminWorkstationsFiltersProps {
  filters: AdminWorkstationListFilters;
  isBackendConnected: boolean;
  options: AdminWorkstationFilterOptions;
  onChange: (patch: Partial<AdminWorkstationListFilters>) => void;
}

export function AdminWorkstationsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminWorkstationsFiltersProps) {
  const branchDisabled = options.branches.length === 0;
  const hasActiveFilters = Boolean(
    filters.branchId ||
      filters.search ||
      filters.status !== "all" ||
      filters.cashSessionState !== "all" ||
      filters.readiness !== "all" ||
      filters.warningState !== "all",
  );

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-2.5">
      <div className="grid min-w-0 items-end gap-2 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1.35fr)_minmax(10rem,0.9fr)_minmax(8rem,0.6fr)_minmax(9rem,0.7fr)_minmax(8rem,0.65fr)_auto]">
        <Field id="admin-workstations-search" label="Busqueda">
          <input
            className={inputClassName}
            id="admin-workstations-search"
            placeholder="Buscar estacion, codigo o sucursal"
            title="Buscar estacion, codigo o sucursal"
            type="search"
            value={filters.search ?? ""}
            onChange={(event) => onChange({ page: 1, search: event.target.value })}
          />
        </Field>

        <Field id="admin-workstations-branch" label="Sucursal">
          <select
            className={`${inputClassName} truncate`}
            disabled={branchDisabled}
            id="admin-workstations-branch"
            title={branchDisabled ? "Sucursales pendientes de API" : "Selecciona sucursal"}
            value={filters.branchId ?? ""}
            onChange={(event) => onChange({ branchId: event.target.value || null, page: 1 })}
          >
            {branchDisabled ? <option value="">Sucursales pendientes de API</option> : <option value="">Todas</option>}
            {options.branches.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-workstations-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-workstations-status"
            value={filters.status ?? "all"}
            onChange={(event) => onChange({ page: 1, status: event.target.value as AdminWorkstationStatus | "all" })}
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-workstations-cash-session" label="Caja">
          <select
            className={inputClassName}
            id="admin-workstations-cash-session"
            value={filters.cashSessionState ?? "all"}
            onChange={(event) =>
              onChange({ cashSessionState: event.target.value as AdminWorkstationCashSessionState, page: 1 })
            }
          >
            {cashSessionOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field id="admin-workstations-readiness" label="Preparacion">
          <select
            className={inputClassName}
            id="admin-workstations-readiness"
            value={filters.readiness ?? "all"}
            onChange={(event) =>
              onChange({ page: 1, readiness: event.target.value as AdminWorkstationReadiness | "all" })
            }
          >
            {readinessOptions.map((option) => (
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

      <div className="flex min-w-0 flex-wrap gap-2 text-xs">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "active" })}
        >
          Activas
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ cashSessionState: "open", page: 1 })}
        >
          Con caja abierta
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ cashSessionState: "no_recent_session", page: 1 })}
        >
          Sin actividad
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, warningState: "with_warnings" as AdminWorkstationWarningState })}
        >
          Con advertencias
        </button>
      </div>
    </section>
  );
}
