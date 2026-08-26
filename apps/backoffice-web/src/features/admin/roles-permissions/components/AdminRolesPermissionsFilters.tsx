import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminRoleFilterOptions, AdminRoleListFilters } from "../types";

interface AdminRolesPermissionsFiltersProps {
  filters: AdminRoleListFilters;
  isBackendConnected: boolean;
  options: AdminRoleFilterOptions;
  onChange: (patch: Partial<AdminRoleListFilters>) => void;
}

function selectClass() {
  return adminFilterInputClassName();
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminRolesPermissionsFilters({
  filters,
  isBackendConnected,
  options,
  onChange,
}: AdminRolesPermissionsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const quickFilters = [
    { label: "Activos", patch: { status: "active" } },
    { label: "Inactivos", patch: { status: "inactive" } },
    { label: "Alto privilegio", patch: { highPrivilege: "yes" } },
    { label: "Sin usuarios", patch: { hasUsers: "no" } },
    { label: "POS", patch: { appSurface: "POS" } },
    { label: "Backoffice", patch: { appSurface: "BACKOFFICE" } },
    { label: "Con advertencias", patch: { warningState: "with_warnings" } },
    { label: "Sistema", patch: { systemState: "system" } },
  ];
  const resetFilters: Partial<AdminRoleListFilters> = {
    appSurface: "all",
    hasUsers: "all",
    highPrivilege: "all",
    permissionModule: "all",
    search: "",
    status: "all",
    systemState: "all",
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
    filters.appSurface !== "all"
      ? {
          key: "surface",
          label: "Superficie",
          value: optionLabel(options.appSurfaces, filters.appSurface),
          onRemove: () => onChange({ appSurface: "all" }),
        }
      : null,
    filters.highPrivilege !== "all"
      ? {
          key: "high-privilege",
          label: "Privilegio",
          value: optionLabel(options.highPrivilege, filters.highPrivilege),
          onRemove: () => onChange({ highPrivilege: "all" }),
        }
      : null,
    filters.hasUsers !== "all"
      ? {
          key: "users",
          label: "Usuarios",
          value: optionLabel(options.hasUsers, filters.hasUsers),
          onRemove: () => onChange({ hasUsers: "all" }),
        }
      : null,
    filters.permissionModule !== "all"
      ? {
          key: "module",
          label: "Modulo",
          value: optionLabel(options.permissionModules, filters.permissionModule),
          onRemove: () => onChange({ permissionModule: "all" }),
        }
      : null,
    filters.systemState !== "all"
      ? {
          key: "system",
          label: "Sistema",
          value: optionLabel(options.systemStates, filters.systemState),
          onRemove: () => onChange({ systemState: "all" }),
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
        searchId="admin-roles-search"
        searchPlaceholder="Buscar por rol o descripcion"
        searchValue={filters.search}
        status={isBackendConnected ? "Backend conectado" : "Integracion parcial"}
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
        <select
          className={selectClass()}
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
        <AdminFilterField label="Superficie">
        <select
          className={selectClass()}
          value={filters.appSurface}
          onChange={(event) => onChange({ appSurface: event.target.value })}
        >
          <option value="all">Toda superficie</option>
          {options.appSurfaces.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>
        <AdminFilterField label="Privilegio">
        <select
          className={selectClass()}
          value={filters.highPrivilege}
          onChange={(event) => onChange({ highPrivilege: event.target.value })}
        >
          <option value="all">Todo riesgo</option>
          {options.highPrivilege.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>
        <AdminFilterField label="Usuarios">
        <select
          className={selectClass()}
          value={filters.hasUsers}
          onChange={(event) => onChange({ hasUsers: event.target.value })}
        >
          <option value="all">Usuarios</option>
          {options.hasUsers.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>
        <AdminFilterField label="Modulo permiso">
        <select
          className={selectClass()}
          value={filters.permissionModule}
          onChange={(event) => onChange({ permissionModule: event.target.value })}
        >
          <option value="all">Todos los modulos</option>
          {options.permissionModules.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>
        <AdminFilterField label="Sistema">
        <select
          className={selectClass()}
          value={filters.systemState}
          onChange={(event) => onChange({ systemState: event.target.value })}
        >
          <option value="all">Sistema / personalizados</option>
          {options.systemStates.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>
        <AdminFilterField label="Advertencias">
        <select
          className={selectClass()}
          value={filters.warningState}
          onChange={(event) => onChange({ warningState: event.target.value })}
        >
          <option value="all">Todas las advertencias</option>
          {options.warningStates.map((option) => (
            <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
        </AdminFilterField>

      <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3">
        {quickFilters.map((item) => (
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            key={item.label}
            type="button"
            onClick={() => onChange(item.patch)}
          >
            {item.label}
          </button>
        ))}
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
          type="button"
          onClick={() => onChange(resetFilters)}
        >
          Limpiar
        </button>
      </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
