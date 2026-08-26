import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminOrderFilterOptions, AdminOrderListFilters } from "../types";

interface AdminOrdersFiltersProps {
  filters: AdminOrderListFilters;
  isBackendConnected: boolean;
  options: AdminOrderFilterOptions;
  onChange: (patch: Partial<AdminOrderListFilters>) => void;
}

function toDateInput(value: Date) {
  return value.toISOString().slice(0, 10);
}

function quickRange(kind: "today" | "tomorrow" | "week"): Partial<AdminOrderListFilters> {
  const today = new Date();
  if (kind === "today") {
    return { dateFrom: toDateInput(today), dateTo: toDateInput(today) };
  }
  if (kind === "tomorrow") {
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    return { dateFrom: toDateInput(tomorrow), dateTo: toDateInput(tomorrow) };
  }
  const weekEnd = new Date(today);
  weekEnd.setDate(today.getDate() + 6);
  return { dateFrom: toDateInput(today), dateTo: toDateInput(weekEnd) };
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminOrdersFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminOrdersFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const disabledTitle = isBackendConnected ? undefined : "Endpoint administrativo pendiente";
  const inputClassName = adminFilterInputClassName();
  const resetFilters: Partial<AdminOrderListFilters> = {
    branchId: "all",
    cashierId: "all",
    dateFrom: null,
    dateTo: null,
    paymentState: "all",
    search: "",
    status: "all",
    workstationId: "all",
  };
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ search: "" }) }
      : null,
    filters.dateFrom
      ? { key: "from", label: "Entrega desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: null }) }
      : null,
    filters.dateTo
      ? { key: "to", label: "Entrega hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: null }) }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: optionLabel(options.statuses, filters.status ?? "all"),
          onRemove: () => onChange({ status: "all" }),
        }
      : null,
    filters.paymentState !== "all"
      ? {
          key: "payment",
          label: "Pago",
          value: optionLabel(options.paymentStates, filters.paymentState ?? "all"),
          onRemove: () => onChange({ paymentState: "all" }),
        }
      : null,
    filters.branchId !== "all"
      ? {
          key: "branch",
          label: "Sucursal",
          value: optionLabel(options.branches, filters.branchId ?? "all"),
          onRemove: () => onChange({ branchId: "all" }),
        }
      : null,
    filters.workstationId !== "all"
      ? {
          key: "workstation",
          label: "Caja",
          value: optionLabel(options.workstations, filters.workstationId ?? "all"),
          onRemove: () => onChange({ workstationId: "all" }),
        }
      : null,
    filters.cashierId !== "all"
      ? {
          key: "cashier",
          label: "Cajero",
          value: optionLabel(options.cashiers, filters.cashierId ?? "all"),
          onRemove: () => onChange({ cashierId: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-orders-search"
        searchPlaceholder="Buscar folio, cliente o telefono"
        searchValue={filters.search ?? ""}
        status={isBackendConnected ? "Datos conectados" : "Endpoint pendiente"}
        onOpenFilters={() => setIsFiltersOpen(true)}
        onSearchChange={(search) => onChange({ search })}
      >
        <AdminActiveFilterChips chips={chips} onClearAll={() => onChange(resetFilters)} />
      </AdminDataToolbar>

      <AdminAdvancedFiltersSheet
        isOpen={isFiltersOpen}
        onClear={() => onChange(resetFilters)}
        onClose={() => setIsFiltersOpen(false)}
      >
        <div className="grid min-w-0 gap-3">
        <AdminFilterField label="Entrega desde">
          <input
            className={inputClassName}
            type="date"
            value={filters.dateFrom ?? ""}
            onChange={(event) => onChange({ dateFrom: event.target.value || null })}
          />
        </AdminFilterField>

        <AdminFilterField label="Entrega hasta">
          <input
            className={inputClassName}
            type="date"
            value={filters.dateTo ?? ""}
            onChange={(event) => onChange({ dateTo: event.target.value || null })}
          />
        </AdminFilterField>

        <AdminFilterField label="Estado">
          <select
            className={inputClassName}
            title={disabledTitle ?? "Filtrar por estado"}
            value={filters.status ?? "all"}
            onChange={(event) => onChange({ status: event.target.value })}
          >
            <option value="all">Todos</option>
            {options.statuses.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminFilterField>

        <AdminFilterField label="Pago">
          <select
            className={inputClassName}
            value={filters.paymentState ?? "all"}
            onChange={(event) => onChange({ paymentState: event.target.value })}
          >
            <option value="all">Todos</option>
            {options.paymentStates.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminFilterField>

          <AdminFilterField label="Sucursal">
            <select
              className={inputClassName}
              value={filters.branchId ?? "all"}
              onChange={(event) => onChange({ branchId: event.target.value })}
            >
              <option value="all">Todas</option>
              {options.branches.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField label="Caja">
            <select
              className={inputClassName}
              value={filters.workstationId ?? "all"}
              onChange={(event) => onChange({ workstationId: event.target.value })}
            >
              <option value="all">Todas</option>
              {options.workstations.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField label="Cajero">
            <select
              className={inputClassName}
              value={filters.cashierId ?? "all"}
              onChange={(event) => onChange({ cashierId: event.target.value })}
            >
              <option value="all">Todos</option>
              {options.cashiers.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

      <div className="flex min-w-0 flex-wrap items-center gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange(quickRange("today"))}
        >
          Hoy
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange(quickRange("tomorrow"))}
        >
          Manana
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange(quickRange("week"))}
        >
          Esta semana
        </button>
        <button
          className="rounded-full border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--ui-color-warning)] transition hover:border-amber-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ status: "PENDING" })}
        >
          Pendientes
        </button>
        <button
          className="rounded-full border border-sky-200 bg-[var(--ui-color-info-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--ui-color-info)] transition hover:border-sky-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ status: "READY" })}
        >
          Listos
        </button>
        <button
          className="rounded-full border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--ui-color-danger)] transition hover:border-rose-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ paymentState: "BALANCE_PENDING" })}
        >
          Con saldo
        </button>
      </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
