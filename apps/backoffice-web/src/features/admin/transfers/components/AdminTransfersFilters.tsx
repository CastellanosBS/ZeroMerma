import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type {
  AdminTransferDiscrepancyState,
  AdminTransferFilterOptions,
  AdminTransferListFilters,
  AdminTransferStatus,
} from "../types";

const inputClassName = adminFilterInputClassName();

const resetFilters: Partial<AdminTransferListFilters> = {
  dateFrom: null,
  dateTo: null,
  destinationBranchId: null,
  discrepancyState: "all",
  operatorUserId: null,
  originBranchId: null,
  page: 1,
  productId: null,
  search: "",
  status: "all",
};

const discrepancyOptions: Array<{ label: string; value: AdminTransferDiscrepancyState | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "with_discrepancy", label: "Con discrepancia" },
  { value: "without_discrepancy", label: "Sin discrepancia" },
];

function optionLabel(options: Array<{ id: string; label: string }>, value: string | null | undefined) {
  return options.find((option) => option.id === value)?.label ?? value ?? "";
}

interface AdminTransfersFiltersProps {
  filters: AdminTransferListFilters;
  isBackendConnected: boolean;
  options: AdminTransferFilterOptions;
  onChange: (patch: Partial<AdminTransferListFilters>) => void;
}

export function AdminTransfersFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminTransfersFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const branchDisabled = options.branches.length === 0;
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ page: 1, search: "" }) }
      : null,
    filters.originBranchId
      ? {
          key: "origin",
          label: "Origen",
          value: optionLabel(options.branches, filters.originBranchId),
          onRemove: () => onChange({ originBranchId: null, page: 1 }),
        }
      : null,
    filters.destinationBranchId
      ? {
          key: "destination",
          label: "Destino",
          value: optionLabel(options.branches, filters.destinationBranchId),
          onRemove: () => onChange({ destinationBranchId: null, page: 1 }),
        }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: optionLabel(options.statuses, filters.status),
          onRemove: () => onChange({ page: 1, status: "all" }),
        }
      : null,
    filters.dateFrom
      ? { key: "from", label: "Desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: null, page: 1 }) }
      : null,
    filters.dateTo
      ? { key: "to", label: "Hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: null, page: 1 }) }
      : null,
    filters.productId
      ? {
          key: "product",
          label: "Producto",
          value: optionLabel(options.products, filters.productId),
          onRemove: () => onChange({ page: 1, productId: null }),
        }
      : null,
    filters.operatorUserId
      ? {
          key: "operator",
          label: "Operador",
          value: optionLabel(options.operators, filters.operatorUserId),
          onRemove: () => onChange({ operatorUserId: null, page: 1 }),
        }
      : null,
    filters.discrepancyState !== "all"
      ? {
          key: "discrepancy",
          label: "Discrepancia",
          value: discrepancyOptions.find((option) => option.value === filters.discrepancyState)?.label ?? filters.discrepancyState,
          onRemove: () => onChange({ discrepancyState: "all", page: 1 }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-transfers-search"
        searchPlaceholder="Folio, sucursal, producto u operador"
        searchValue={filters.search ?? ""}
        status={isBackendConnected ? "Datos conectados" : "Esperando API"}
        onOpenFilters={() => setIsFiltersOpen(true)}
        onSearchChange={(search) => onChange({ page: 1, search })}
      >
        <AdminActiveFilterChips chips={chips} onClearAll={() => onChange(resetFilters)} />
      </AdminDataToolbar>

      <AdminAdvancedFiltersSheet
        isOpen={isFiltersOpen}
        onClear={() => onChange(resetFilters)}
        onClose={() => setIsFiltersOpen(false)}
      >
        <div className="grid min-w-0 gap-3">
        <AdminFilterField id="admin-transfers-origin" label="Origen">
          <select
            className={`${inputClassName} truncate`}
            disabled={branchDisabled}
            id="admin-transfers-origin"
            title={branchDisabled ? "Sucursales pendientes de API" : "Sucursal origen"}
            value={filters.originBranchId ?? ""}
            onChange={(event) => onChange({ originBranchId: event.target.value || null, page: 1 })}
          >
            {branchDisabled ? <option value="">Sucursales pendientes de API</option> : <option value="">Todas</option>}
            {options.branches.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminFilterField>

        <AdminFilterField id="admin-transfers-destination" label="Destino">
          <select
            className={`${inputClassName} truncate`}
            disabled={branchDisabled}
            id="admin-transfers-destination"
            title={branchDisabled ? "Sucursales pendientes de API" : "Sucursal destino"}
            value={filters.destinationBranchId ?? ""}
            onChange={(event) => onChange({ destinationBranchId: event.target.value || null, page: 1 })}
          >
            {branchDisabled ? <option value="">Sucursales pendientes de API</option> : <option value="">Todas</option>}
            {options.branches.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminFilterField>

        <AdminFilterField id="admin-transfers-status" label="Estado">
          <select
            className={inputClassName}
            id="admin-transfers-status"
            value={filters.status ?? "all"}
            onChange={(event) => onChange({ page: 1, status: event.target.value as AdminTransferStatus | "all" })}
          >
            <option value="all">Todos</option>
            {options.statuses.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </AdminFilterField>

          <AdminFilterField id="admin-transfers-date-from" label="Desde">
            <input
              className={inputClassName}
              id="admin-transfers-date-from"
              type="date"
              value={filters.dateFrom ?? ""}
              onChange={(event) => onChange({ dateFrom: event.target.value || null, page: 1 })}
            />
          </AdminFilterField>

          <AdminFilterField id="admin-transfers-date-to" label="Hasta">
            <input
              className={inputClassName}
              id="admin-transfers-date-to"
              type="date"
              value={filters.dateTo ?? ""}
              onChange={(event) => onChange({ dateTo: event.target.value || null, page: 1 })}
            />
          </AdminFilterField>

          <AdminFilterField id="admin-transfers-product" label="Producto">
            <select
              className={`${inputClassName} truncate`}
              id="admin-transfers-product"
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
          </AdminFilterField>

          <AdminFilterField id="admin-transfers-operator" label="Operador">
            <select
              className={`${inputClassName} truncate`}
              id="admin-transfers-operator"
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
          </AdminFilterField>

          <AdminFilterField id="admin-transfers-discrepancy" label="Discrepancia">
            <select
              className={inputClassName}
              id="admin-transfers-discrepancy"
              value={filters.discrepancyState ?? "all"}
              onChange={(event) =>
                onChange({
                  discrepancyState: event.target.value as AdminTransferDiscrepancyState | "all",
                  page: 1,
                })
              }
            >
              {discrepancyOptions.map((option) => (
                <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>

      <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3 text-xs">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "IN_TRANSIT" })}
        >
          En transito
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
          onClick={() => onChange({ page: 1, status: "DRAFT" })}
        >
          Borradores
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onChange({ page: 1, status: "RECEIVED" })}
        >
          Recibidas
        </button>
      </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
