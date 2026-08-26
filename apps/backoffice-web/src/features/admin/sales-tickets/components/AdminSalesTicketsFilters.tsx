import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminSalesTicketFilterOptions, AdminSalesTicketListFilters } from "../types";

interface AdminSalesTicketsFiltersProps {
  filters: AdminSalesTicketListFilters;
  isBackendConnected: boolean;
  options: AdminSalesTicketFilterOptions;
  onChange: (patch: Partial<AdminSalesTicketListFilters>) => void;
}

function quickDateRange(kind: "today" | "sevenDays" | "month"): Pick<AdminSalesTicketListFilters, "dateFrom" | "dateTo"> {
  const today = new Date();
  const toDateInput = (value: Date) => value.toISOString().slice(0, 10);
  if (kind === "today") {
    return { dateFrom: toDateInput(today), dateTo: toDateInput(today) };
  }
  if (kind === "sevenDays") {
    const start = new Date(today);
    start.setDate(today.getDate() - 6);
    return { dateFrom: toDateInput(start), dateTo: toDateInput(today) };
  }
  return {
    dateFrom: `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-01`,
    dateTo: toDateInput(today),
  };
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminSalesTicketsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminSalesTicketsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const disabledTitle = isBackendConnected ? undefined : "Endpoint administrativo pendiente";
  const inputClassName = adminFilterInputClassName();
  const resetFilters: Partial<AdminSalesTicketListFilters> = {
    branchId: "all",
    cashierId: "all",
    dateFrom: null,
    dateTo: null,
    maxAmount: null,
    minAmount: null,
    paymentMethod: "all",
    search: "",
    status: "all",
    workstationId: "all",
  };
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ search: "" }) }
      : null,
    filters.dateFrom
      ? { key: "date-from", label: "Desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: null }) }
      : null,
    filters.dateTo
      ? { key: "date-to", label: "Hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: null }) }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: optionLabel(options.statuses, filters.status ?? "all"),
          onRemove: () => onChange({ status: "all" }),
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
    filters.paymentMethod !== "all"
      ? {
          key: "payment",
          label: "Pago",
          value: optionLabel(options.paymentMethods, filters.paymentMethod ?? "all"),
          onRemove: () => onChange({ paymentMethod: "all" }),
        }
      : null,
    filters.minAmount
      ? { key: "min", label: "Minimo", value: filters.minAmount, onRemove: () => onChange({ minAmount: null }) }
      : null,
    filters.maxAmount
      ? { key: "max", label: "Maximo", value: filters.maxAmount, onRemove: () => onChange({ maxAmount: null }) }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-sales-tickets-search"
        searchPlaceholder="Buscar folio, cajero, producto o sucursal"
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
        <AdminFilterField label="Desde">
          <input
            className={inputClassName}
            type="date"
            value={filters.dateFrom ?? ""}
            onChange={(event) => onChange({ dateFrom: event.target.value || null })}
          />
        </AdminFilterField>

        <AdminFilterField label="Hasta">
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
            <option value="all">Todos los estados</option>
            {options.statuses.map((option) => (
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

          <AdminFilterField label="Pago">
            <select
              className={inputClassName}
              value={filters.paymentMethod ?? "all"}
              onChange={(event) => onChange({ paymentMethod: event.target.value })}
            >
              <option value="all">Todos</option>
              {options.paymentMethods.map((option) => (
                <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>

          <AdminFilterField label="Minimo">
            <input
              className={inputClassName}
              min="0"
              placeholder="0.00"
              type="number"
              value={filters.minAmount ?? ""}
              onChange={(event) => onChange({ minAmount: event.target.value || null })}
            />
          </AdminFilterField>

          <AdminFilterField label="Maximo">
            <input
              className={inputClassName}
              min="0"
              placeholder="0.00"
              type="number"
              value={filters.maxAmount ?? ""}
              onChange={(event) => onChange({ maxAmount: event.target.value || null })}
            />
          </AdminFilterField>

      <div className="flex min-w-0 flex-wrap items-center gap-2 border-t border-[var(--ui-color-border)] pt-3">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange(quickDateRange("today"))}
        >
          Hoy
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange(quickDateRange("sevenDays"))}
        >
          Ultimos 7 dias
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange(quickDateRange("month"))}
        >
          Este mes
        </button>
      </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
