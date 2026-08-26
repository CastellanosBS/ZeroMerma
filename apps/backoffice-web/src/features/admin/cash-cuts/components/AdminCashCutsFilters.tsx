import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminCashCutFilterOptions, AdminCashCutListFilters } from "../types";

interface AdminCashCutsFiltersProps {
  filters: AdminCashCutListFilters;
  isBackendConnected: boolean;
  options: AdminCashCutFilterOptions;
  onChange: (patch: Partial<AdminCashCutListFilters>) => void;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function last7DaysIsoDate() {
  const date = new Date();
  date.setDate(date.getDate() - 6);
  return date.toISOString().slice(0, 10);
}

function monthStartIsoDate() {
  const date = new Date();
  return new Date(date.getFullYear(), date.getMonth(), 1).toISOString().slice(0, 10);
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminCashCutsFilters({
  filters,
  isBackendConnected,
  options,
  onChange,
}: AdminCashCutsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const selectClass =
    adminFilterInputClassName();
  const inputClass = adminFilterInputClassName();
  const quickButtonClass =
    "rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]";
  const resetFilters: Partial<AdminCashCutListFilters> = {
    branchId: "all",
    cashierId: "all",
    dateFrom: null,
    dateTo: null,
    differenceState: "all",
    hasOperationalPayments: "all",
    hasRefunds: "all",
    paymentMethod: "all",
    search: "",
    status: "all",
    workstationId: "all",
  };
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ search: "" }) }
      : null,
    filters.branchId !== "all"
      ? {
          key: "branch",
          label: "Sucursal",
          value: optionLabel(options.branches, filters.branchId),
          onRemove: () => onChange({ branchId: "all" }),
        }
      : null,
    filters.workstationId !== "all"
      ? {
          key: "workstation",
          label: "Caja",
          value: optionLabel(options.workstations, filters.workstationId),
          onRemove: () => onChange({ workstationId: "all" }),
        }
      : null,
    filters.cashierId !== "all"
      ? {
          key: "cashier",
          label: "Cajero",
          value: optionLabel(options.cashiers, filters.cashierId),
          onRemove: () => onChange({ cashierId: "all" }),
        }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: optionLabel(options.statuses, filters.status),
          onRemove: () => onChange({ status: "all" }),
        }
      : null,
    filters.dateFrom
      ? { key: "from", label: "Desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: null }) }
      : null,
    filters.dateTo
      ? { key: "to", label: "Hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: null }) }
      : null,
    filters.differenceState !== "all"
      ? {
          key: "difference",
          label: "Diferencia",
          value: optionLabel(options.differenceStates, filters.differenceState),
          onRemove: () => onChange({ differenceState: "all" }),
        }
      : null,
    filters.paymentMethod !== "all"
      ? {
          key: "payment",
          label: "Metodo",
          value: optionLabel(options.paymentMethods, filters.paymentMethod),
          onRemove: () => onChange({ paymentMethod: "all" }),
        }
      : null,
    filters.hasRefunds !== "all"
      ? {
          key: "refunds",
          label: "Devoluciones",
          value: filters.hasRefunds === "true" ? "Con devoluciones" : "Sin devoluciones",
          onRemove: () => onChange({ hasRefunds: "all" }),
        }
      : null,
    filters.hasOperationalPayments !== "all"
      ? {
          key: "payments",
          label: "Pagos operativos",
          value: filters.hasOperationalPayments === "true" ? "Con pagos" : "Sin pagos",
          onRemove: () => onChange({ hasOperationalPayments: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        isSearchDisabled={!isBackendConnected}
        searchId="admin-cash-cuts-search"
        searchPlaceholder="Buscar folio, cajero, sucursal o estacion"
        searchValue={filters.search}
        status={isBackendConnected ? "Datos conectados" : "Esperando API"}
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
        <div className="grid gap-3">
        <AdminFilterField label="Sucursal">
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
        </AdminFilterField>

        <AdminFilterField label="Caja">
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
        </AdminFilterField>

        <AdminFilterField label="Cajero">
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.cashierId}
          onChange={(event) => onChange({ cashierId: event.target.value })}
        >
          <option value="all">Todos los cajeros</option>
          {options.cashiers.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>

        <AdminFilterField label="Estado">
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
        </AdminFilterField>

        <AdminFilterField label="Desde">
        <input
          className={inputClass}
          disabled={!isBackendConnected}
          type="date"
          value={filters.dateFrom ?? ""}
          onChange={(event) => onChange({ dateFrom: event.target.value || null })}
        />
        </AdminFilterField>
        <AdminFilterField label="Hasta">
        <input
          className={inputClass}
          disabled={!isBackendConnected}
          type="date"
          value={filters.dateTo ?? ""}
          onChange={(event) => onChange({ dateTo: event.target.value || null })}
        />
        </AdminFilterField>
        <AdminFilterField label="Diferencia">
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.differenceState}
          onChange={(event) => onChange({ differenceState: event.target.value })}
        >
          <option value="all">Todas las diferencias</option>
          {options.differenceStates.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>
        <AdminFilterField label="Metodo de pago">
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
        </AdminFilterField>
        <AdminFilterField label="Devoluciones">
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.hasRefunds}
          onChange={(event) => onChange({ hasRefunds: event.target.value })}
        >
          <option value="all">Devoluciones: todas</option>
          <option value="true">Con devoluciones</option>
          <option value="false">Sin devoluciones</option>
        </select>
        </AdminFilterField>
        <AdminFilterField label="Pagos operativos">
        <select
          className={selectClass}
          disabled={!isBackendConnected}
          value={filters.hasOperationalPayments}
          onChange={(event) => onChange({ hasOperationalPayments: event.target.value })}
        >
          <option value="all">Pagos operativos: todos</option>
          <option value="true">Con pagos operativos</option>
          <option value="false">Sin pagos operativos</option>
        </select>
        </AdminFilterField>

      <div className="flex min-w-0 flex-wrap items-center gap-1.5 border-t border-[var(--ui-color-border)] pt-3">
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
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ dateFrom: monthStartIsoDate(), dateTo: todayIsoDate() })}
        >
          Este mes
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ differenceState: "WITH_DIFFERENCE" })}
        >
          Con diferencia
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ differenceState: "WITHOUT_DIFFERENCE" })}
        >
          Sin diferencia
        </button>
        <button
          className={quickButtonClass}
          type="button"
          onClick={() => onChange({ status: "OPEN" })}
        >
          Pendientes de cierre
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
      </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
