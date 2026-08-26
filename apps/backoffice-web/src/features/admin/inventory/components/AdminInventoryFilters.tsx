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
  AdminInventoryFilterOptions,
  AdminInventoryListFilters,
  AdminInventoryLocationCode,
  AdminInventoryProductKind,
  AdminInventoryProductStatus,
  AdminInventoryStockState,
} from "../types";

const inputClassName = adminFilterInputClassName();

const resetFilters: Partial<AdminInventoryListFilters> = {
  branchId: null,
  classId: null,
  locationCode: "all",
  page: 1,
  productKind: "all",
  productStatus: "all",
  search: "",
  stockState: "all",
};

const stockStateOptions: Array<{ label: string; value: AdminInventoryStockState | "all" }> = [
  { value: "all", label: "Todos" },
  { value: "in_stock", label: "Con existencia" },
  { value: "out_of_stock", label: "Sin existencia" },
  { value: "negative_stock", label: "Stock negativo" },
  { value: "low_stock", label: "Stock bajo" },
];

const productStatusOptions: Array<{ label: string; value: AdminInventoryProductStatus | "all" }> = [
  { value: "all", label: "Todos" },
  { value: "active", label: "Producto activo" },
  { value: "inactive", label: "Producto inactivo" },
];

function optionLabel(options: Array<{ id: string; label: string }>, value: string | null | undefined) {
  return options.find((option) => option.id === value)?.label ?? value ?? "";
}

interface AdminInventoryFiltersProps {
  filters: AdminInventoryListFilters;
  isBackendConnected: boolean;
  options: AdminInventoryFilterOptions;
  onChange: (patch: Partial<AdminInventoryListFilters>) => void;
}

export function AdminInventoryFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminInventoryFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const branchDisabled = options.branches.length === 0;
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ page: 1, search: "" }) }
      : null,
    filters.branchId
      ? {
          key: "branch",
          label: "Sucursal",
          value: optionLabel(options.branches, filters.branchId),
          onRemove: () => onChange({ branchId: null, page: 1 }),
        }
      : null,
    filters.productKind !== "all"
      ? {
          key: "kind",
          label: "Tipo",
          value: optionLabel(options.productKinds, filters.productKind),
          onRemove: () => onChange({ page: 1, productKind: "all" }),
        }
      : null,
    filters.stockState !== "all"
      ? {
          key: "stock",
          label: "Estado stock",
          value: stockStateOptions.find((option) => option.value === filters.stockState)?.label ?? filters.stockState,
          onRemove: () => onChange({ page: 1, stockState: "all" }),
        }
      : null,
    filters.classId
      ? {
          key: "class",
          label: "Clase",
          value: optionLabel(options.classes, filters.classId),
          onRemove: () => onChange({ classId: null, page: 1 }),
        }
      : null,
    filters.locationCode !== "all"
      ? {
          key: "location",
          label: "Ubicacion",
          value: optionLabel(options.locations, filters.locationCode),
          onRemove: () => onChange({ locationCode: "all", page: 1 }),
        }
      : null,
    filters.productStatus !== "all"
      ? {
          key: "product-status",
          label: "Producto",
          value:
            productStatusOptions.find((option) => option.value === filters.productStatus)?.label ??
            filters.productStatus,
          onRemove: () => onChange({ page: 1, productStatus: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-inventory-search"
        searchPlaceholder="Buscar producto, codigo, clase o sucursal"
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
          <AdminFilterField id="admin-inventory-branch" label="Sucursal">
            <select
              className={`${inputClassName} truncate`}
              disabled={branchDisabled}
              id="admin-inventory-branch"
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
          </AdminFilterField>

          <AdminFilterField id="admin-inventory-kind" label="Tipo">
            <select
              className={inputClassName}
              id="admin-inventory-kind"
              value={filters.productKind ?? "all"}
              onChange={(event) =>
                onChange({ page: 1, productKind: event.target.value as AdminInventoryProductKind | "all" })
              }
            >
              <option value="all">Todos</option>
              {options.productKinds.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-inventory-stock-state" label="Estado stock">
            <select
              className={inputClassName}
              id="admin-inventory-stock-state"
              value={filters.stockState ?? "all"}
              onChange={(event) =>
                onChange({ page: 1, stockState: event.target.value as AdminInventoryStockState | "all" })
              }
            >
              {stockStateOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-inventory-class" label="Clase">
            <select
              className={`${inputClassName} truncate`}
              id="admin-inventory-class"
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
          </AdminFilterField>

          <AdminFilterField id="admin-inventory-location" label="Ubicacion">
            <select
              className={inputClassName}
              id="admin-inventory-location"
              value={filters.locationCode ?? "all"}
              onChange={(event) =>
                onChange({ locationCode: event.target.value as AdminInventoryLocationCode | "all", page: 1 })
              }
            >
              <option value="all">Todas</option>
              {options.locations.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>

          <AdminFilterField id="admin-inventory-product-status" label="Producto">
            <select
              className={inputClassName}
              id="admin-inventory-product-status"
              value={filters.productStatus ?? "all"}
              onChange={(event) =>
                onChange({ page: 1, productStatus: event.target.value as AdminInventoryProductStatus | "all" })
              }
            >
              {productStatusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>

          <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3 text-xs">
            {[
              { label: "Stock negativo", patch: { page: 1, stockState: "negative_stock" as const } },
              { label: "Sin existencia", patch: { page: 1, stockState: "out_of_stock" as const } },
              { label: "Materia prima", patch: { page: 1, productKind: "RAW_MATERIAL" as const } },
              { label: "Producto terminado", patch: { page: 1, productKind: "FINISHED_GOOD" as const } },
              { label: "Mostrador", patch: { locationCode: "COUNTER" as const, page: 1 } },
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
