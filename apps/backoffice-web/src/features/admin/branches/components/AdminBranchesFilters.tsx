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
  AdminBranchActiveWorkstationFilter,
  AdminBranchFilterOptions,
  AdminBranchListFilters,
  AdminBranchStatus,
  AdminBranchWarningState,
} from "../types";

const inputClassName = adminFilterInputClassName();

const resetFilters: Partial<AdminBranchListFilters> = {
  brandId: null,
  hasActiveWorkstations: "all",
  page: 1,
  search: "",
  status: "all",
  warningState: "all",
};

const statusOptions: Array<{ label: string; value: AdminBranchStatus | "all" }> = [
  { value: "all", label: "Todas" },
  { value: "active", label: "Activas" },
  { value: "inactive", label: "Inactivas" },
];

const workstationOptions: Array<{ label: string; value: AdminBranchActiveWorkstationFilter }> = [
  { value: "all", label: "Todas" },
  { value: "yes", label: "Con estacion activa" },
  { value: "no", label: "Sin estacion activa" },
];

function optionLabel(options: Array<{ id: string; label: string }>, value: string | null | undefined) {
  return options.find((option) => option.id === value)?.label ?? value ?? "";
}

interface AdminBranchesFiltersProps {
  filters: AdminBranchListFilters;
  isBackendConnected: boolean;
  options: AdminBranchFilterOptions;
  onChange: (patch: Partial<AdminBranchListFilters>) => void;
}

export function AdminBranchesFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminBranchesFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const brandDisabled = options.brands.length === 0;
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ page: 1, search: "" }) }
      : null,
    filters.brandId
      ? {
          key: "brand",
          label: "Marca",
          value: optionLabel(options.brands, filters.brandId),
          onRemove: () => onChange({ brandId: null, page: 1 }),
        }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: statusOptions.find((option) => option.value === filters.status)?.label ?? filters.status,
          onRemove: () => onChange({ page: 1, status: "all" }),
        }
      : null,
    filters.hasActiveWorkstations !== "all"
      ? {
          key: "workstations",
          label: "Estaciones",
          value:
            workstationOptions.find((option) => option.value === filters.hasActiveWorkstations)?.label ??
            filters.hasActiveWorkstations,
          onRemove: () => onChange({ hasActiveWorkstations: "all", page: 1 }),
        }
      : null,
    filters.warningState !== "all"
      ? {
          key: "warnings",
          label: "Advertencias",
          value: filters.warningState === "with_warnings" ? "Con advertencias" : filters.warningState,
          onRemove: () => onChange({ page: 1, warningState: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-branches-search"
        searchPlaceholder="Buscar sucursal, codigo, marca o ciudad"
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
          <AdminFilterField id="admin-branches-brand" label="Marca">
            <select
              className={`${inputClassName} truncate`}
              disabled={brandDisabled}
              id="admin-branches-brand"
              title={brandDisabled ? "Marcas pendientes de API" : "Selecciona marca"}
              value={filters.brandId ?? ""}
              onChange={(event) => onChange({ brandId: event.target.value || null, page: 1 })}
            >
              {brandDisabled ? <option value="">Marcas pendientes de API</option> : <option value="">Todas</option>}
              {options.brands.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-branches-status" label="Estado">
            <select
              className={inputClassName}
              id="admin-branches-status"
              value={filters.status ?? "all"}
              onChange={(event) => onChange({ page: 1, status: event.target.value as AdminBranchStatus | "all" })}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-branches-workstations" label="Estaciones">
            <select
              className={inputClassName}
              id="admin-branches-workstations"
              value={filters.hasActiveWorkstations ?? "all"}
              onChange={(event) =>
                onChange({
                  hasActiveWorkstations: event.target.value as AdminBranchActiveWorkstationFilter,
                  page: 1,
                })
              }
            >
              {workstationOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3 text-xs">
            {[
              { label: "Activas", patch: { page: 1, status: "active" as const } },
              { label: "Inactivas", patch: { page: 1, status: "inactive" as const } },
              { label: "Sin estacion activa", patch: { hasActiveWorkstations: "no" as const, page: 1 } },
              {
                label: "Con advertencias",
                patch: { page: 1, warningState: "with_warnings" as AdminBranchWarningState },
              },
            ].map((quickFilter) => (
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 font-semibold text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                key={quickFilter.label}
                type="button"
                onClick={() => onChange(quickFilter.patch)}
              >
                {quickFilter.label}
              </button>
            ))}
          </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
