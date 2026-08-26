import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminSettingFilterOptions, AdminSettingsFilters } from "../types";

interface AdminSettingsFiltersProps {
  filters: AdminSettingsFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminSettingsFilters>) => void;
  options: AdminSettingFilterOptions;
}

function renderOptions(options: { id: string; label: string }[]) {
  return options.map((option) => (
    <option key={option.id} value={option.id}>
      {option.label}
    </option>
  ));
}

function optionLabel(options: { id: string; label: string }[], value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminSettingsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminSettingsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const resetFilters: Partial<AdminSettingsFilters> = {
    affectedModule: "all",
    category: "all",
    readonly: "all",
    search: "",
    sensitivity: "all",
    status: "all",
  };
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
    filters.sensitivity !== "all"
      ? {
          key: "sensitivity",
          label: "Sensibilidad",
          value: optionLabel(options.sensitivities, filters.sensitivity),
          onRemove: () => onChange({ sensitivity: "all" }),
        }
      : null,
    filters.readonly !== "all"
      ? {
          key: "readonly",
          label: "Edicion",
          value: optionLabel(options.readonlyStates, filters.readonly),
          onRemove: () => onChange({ readonly: "all" }),
        }
      : null,
    filters.affectedModule !== "all"
      ? {
          key: "module",
          label: "Modulo",
          value: optionLabel(options.modules, filters.affectedModule),
          onRemove: () => onChange({ affectedModule: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-settings-search"
        searchPlaceholder="Clave, modulo o descripcion"
        searchValue={filters.search}
        status={isBackendConnected ? "Backend conectado" : "Contrato no disponible"}
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
        <AdminFilterField label="Categoria">
          <select
            className={adminFilterInputClassName()}
            value={filters.category}
            onChange={(event) => onChange({ category: event.target.value })}
          >
            <option value="all">Todas</option>
            {renderOptions(options.categories)}
          </select>
        </AdminFilterField>

        <AdminFilterField label="Estado">
          <select
            className={adminFilterInputClassName()}
            value={filters.status}
            onChange={(event) => onChange({ status: event.target.value })}
          >
            <option value="all">Todos</option>
            {renderOptions(options.statuses)}
          </select>
        </AdminFilterField>

        <AdminFilterField label="Sensibilidad">
          <select
            className={adminFilterInputClassName()}
            value={filters.sensitivity}
            onChange={(event) => onChange({ sensitivity: event.target.value })}
          >
            <option value="all">Todas</option>
            {renderOptions(options.sensitivities)}
          </select>
        </AdminFilterField>

        <AdminFilterField label="Edicion">
          <select
            className={adminFilterInputClassName()}
            value={filters.readonly}
            onChange={(event) => onChange({ readonly: event.target.value })}
          >
            <option value="all">Todas</option>
            {renderOptions(options.readonlyStates)}
          </select>
        </AdminFilterField>

        <AdminFilterField label="Modulo">
          <select
            className={adminFilterInputClassName()}
            value={filters.affectedModule}
            onChange={(event) => onChange({ affectedModule: event.target.value })}
          >
            <option value="all">Todos</option>
            {renderOptions(options.modules)}
          </select>
        </AdminFilterField>

      <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3 text-xs font-semibold">
        {[
          ["warning", "Con advertencias"],
          ["sensitive", "Sensibles"],
          ["editable", "Editables"],
          ["readonly", "Solo lectura"],
        ].map(([value, label]) => (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1.5 text-slate-600 transition hover:border-[var(--ui-color-info)]"
            key={value}
            type="button"
            onClick={() => {
              if (value === "warning") {
                onChange({ status: "warning" });
              } else if (value === "sensitive") {
                onChange({ sensitivity: "sensitive" });
              } else {
                onChange({ readonly: value });
              }
            }}
          >
            {label}
          </button>
        ))}
      </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
