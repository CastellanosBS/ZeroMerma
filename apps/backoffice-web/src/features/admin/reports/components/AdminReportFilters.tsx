import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminReportCatalogFilterOptions, AdminReportCatalogFilters } from "../types";

interface AdminReportFiltersProps {
  filters: AdminReportCatalogFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminReportCatalogFilters>) => void;
  options: AdminReportCatalogFilterOptions;
}

function SelectFilter({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: Array<{ id: string; label: string }>;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <AdminFilterField label={label}>
      <select
        className={adminFilterInputClassName()}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="all">Todos</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </AdminFilterField>
  );
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminReportFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminReportFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const quickFilters = [
    { label: "Disponibles", patch: { status: "available" } },
    { label: "Exportables", patch: { exportSupport: "yes" } },
    { label: "Ventas", patch: { category: "ventas_pedidos" } },
    { label: "Caja", patch: { category: "caja_finanzas" } },
    { label: "Inventario", patch: { sourceModule: "inventory" } },
    { label: "Compras", patch: { category: "compras_abastecimiento" } },
    { label: "Calidad", patch: { category: "calidad_higiene" } },
    { label: "Control", patch: { category: "control" } },
    { label: "Pendientes", patch: { status: "requires_backend" } },
  ];
  const resetFilters: Partial<AdminReportCatalogFilters> = {
    category: "all",
    exportSupport: "all",
    search: "",
    sensitivity: "all",
    sourceModule: "all",
    status: "all",
  };
  const exportOptions = [
    { id: "yes", label: "Exportables" },
    { id: "no", label: "Sin exportacion" },
  ];
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ search: "" }) }
      : null,
    filters.category !== "all"
      ? {
          key: "category",
          label: "Categoria",
          value: optionLabel(options.categories, filters.category),
          onRemove: () => onChange({ category: "all" }),
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
    filters.exportSupport !== "all"
      ? {
          key: "export",
          label: "Exportacion",
          value: optionLabel(exportOptions, filters.exportSupport),
          onRemove: () => onChange({ exportSupport: "all" }),
        }
      : null,
    filters.sensitivity !== "all"
      ? {
          key: "sensitivity",
          label: "Sensibilidad",
          value: optionLabel(options.sensitivities, filters.sensitivity),
          onRemove: () => onChange({ sensitivity: "all" }),
        }
      : null,
    filters.sourceModule !== "all"
      ? {
          key: "source",
          label: "Modulo",
          value: optionLabel(options.sourceModules, filters.sourceModule),
          onRemove: () => onChange({ sourceModule: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-reports-search"
        searchPlaceholder="Nombre, modulo o fuente"
        searchValue={filters.search}
        status={isBackendConnected ? "Definiciones desde backend" : "Esperando contrato"}
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
        <SelectFilter
          label="Categoria"
          options={options.categories}
          value={filters.category}
          onChange={(category) => onChange({ category })}
        />
        <SelectFilter
          label="Estado"
          options={options.statuses}
          value={filters.status}
          onChange={(status) => onChange({ status })}
        />
        <SelectFilter
          label="Exportacion"
          options={exportOptions}
          value={filters.exportSupport}
          onChange={(exportSupport) => onChange({ exportSupport })}
        />
        <SelectFilter
          label="Sensibilidad"
          options={options.sensitivities}
          value={filters.sensitivity}
          onChange={(sensitivity) => onChange({ sensitivity })}
        />

        <SelectFilter
          label="Modulo fuente"
          options={options.sourceModules}
          value={filters.sourceModule}
          onChange={(sourceModule) => onChange({ sourceModule })}
        />
          <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3">
            {quickFilters.map((item) => (
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                key={item.label}
                type="button"
                onClick={() => onChange(item.patch)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
