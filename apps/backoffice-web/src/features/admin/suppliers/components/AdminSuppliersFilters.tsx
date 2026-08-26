import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminSupplierFilterOptions, AdminSupplierListFilters } from "../types";

interface AdminSuppliersFiltersProps {
  filters: AdminSupplierListFilters;
  isBackendConnected: boolean;
  options: AdminSupplierFilterOptions;
  onChange: (patch: Partial<AdminSupplierListFilters>) => void;
}

const controlClass = adminFilterInputClassName();

function optionList(options: Array<{ id: string; label: string }>) {
  return options.map((option) => (
    <option key={option.id} value={option.id}>
      {option.label}
    </option>
  ));
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string | null | undefined) {
  return options.find((option) => option.id === value)?.label ?? value ?? "";
}

export function AdminSuppliersFilters({ filters, isBackendConnected, options, onChange }: AdminSuppliersFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const resetFilters: Partial<AdminSupplierListFilters> = {
    branchId: null,
    category: "all",
    productKind: "all",
    search: "",
    status: "all",
    warningState: "all",
  };
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ search: "" }) }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: optionLabel(options.statuses, filters.status),
          onRemove: () => onChange({ status: "all" }),
        }
      : null,
    filters.category !== "all"
      ? {
          key: "category",
          label: "Categoria",
          value: optionLabel(options.categories, filters.category),
          onRemove: () => onChange({ category: "all" }),
        }
      : null,
    filters.productKind !== "all"
      ? {
          key: "kind",
          label: "Tipo surtido",
          value: optionLabel(options.productKinds, filters.productKind),
          onRemove: () => onChange({ productKind: "all" }),
        }
      : null,
    filters.branchId
      ? {
          key: "branch",
          label: "Sucursal",
          value: optionLabel(options.branches, filters.branchId),
          onRemove: () => onChange({ branchId: null }),
        }
      : null,
    filters.warningState !== "all"
      ? {
          key: "warning",
          label: "Advertencias",
          value: optionLabel(options.warningStates, filters.warningState),
          onRemove: () => onChange({ warningState: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-suppliers-search"
        searchPlaceholder="Proveedor, comercial, RFC, contacto, producto"
        searchValue={filters.search ?? ""}
        status={isBackendConnected ? "API conectada" : "Sin conexion API"}
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
      <AdminFilterField label="Estado">
        <select className={controlClass} value={filters.status ?? "all"} onChange={(event) => onChange({ status: event.target.value as AdminSupplierListFilters["status"] })}>
          <option value="all">Todos</option>
          {optionList(options.statuses)}
        </select>
      </AdminFilterField>

      <AdminFilterField label="Categoria">
        <select className={controlClass} value={filters.category ?? "all"} onChange={(event) => onChange({ category: event.target.value })}>
          <option value="all">Todas</option>
          {optionList(options.categories)}
        </select>
      </AdminFilterField>

      <AdminFilterField label="Tipo surtido">
        <select className={controlClass} value={filters.productKind ?? "all"} onChange={(event) => onChange({ productKind: event.target.value })}>
          <option value="all">Todos</option>
          {optionList(options.productKinds)}
        </select>
      </AdminFilterField>

      <AdminFilterField label="Sucursal">
        <select className={controlClass} value={filters.branchId ?? "all"} onChange={(event) => onChange({ branchId: event.target.value === "all" ? null : event.target.value })}>
          <option value="all">Todas</option>
          {optionList(options.branches)}
        </select>
      </AdminFilterField>

      <AdminFilterField label="Advertencias">
        <select className={controlClass} value={filters.warningState ?? "all"} onChange={(event) => onChange({ warningState: event.target.value as AdminSupplierListFilters["warningState"] })}>
          <option value="all">Todas</option>
          {optionList(options.warningStates)}
        </select>
      </AdminFilterField>

      <div className="flex flex-wrap items-end gap-2 border-t border-[var(--ui-color-border)] pt-3">
        {[
          { label: "Activos", patch: { status: "ACTIVE" as const } },
          { label: "Inactivos", patch: { status: "INACTIVE" as const } },
          { label: "Bloqueados", patch: { status: "BLOCKED" as const } },
          { label: "Con advertencias", patch: { warningState: "with_warnings" as const } },
          { label: "Materia prima", patch: { productKind: "RAW_MATERIAL" } },
          { label: "Consumibles", patch: { productKind: "CONSUMABLE" } },
        ].map((quickFilter) => (
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
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
