import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminUserFilterOptions, AdminUserListFilters } from "../types";

interface AdminUsersFiltersProps {
  filters: AdminUserListFilters;
  isBackendConnected: boolean;
  options: AdminUserFilterOptions;
  onChange: (patch: Partial<AdminUserListFilters>) => void;
}

function selectClass() {
  return adminFilterInputClassName();
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminUsersFilters({
  filters,
  isBackendConnected,
  options,
  onChange,
}: AdminUsersFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const quickFilters = [
    { label: "Activos", patch: { status: "active" } },
    { label: "Inactivos", patch: { status: "inactive" } },
    { label: "Bloqueados", patch: { status: "locked" } },
    { label: "Sin sucursal", patch: { warningState: "with_warnings" } },
    { label: "POS", patch: { appAccess: "POS" } },
    { label: "Backoffice", patch: { appAccess: "BACKOFFICE" } },
    { label: "Con advertencias", patch: { warningState: "with_warnings" } },
  ];
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
    filters.appAccess !== "all"
      ? {
          key: "app-access",
          label: "Acceso",
          value: optionLabel(options.appAccess, filters.appAccess),
          onRemove: () => onChange({ appAccess: "all" }),
        }
      : null,
    filters.branchId !== "all"
      ? {
          key: "branch",
          label: "Sucursal",
          value: optionLabel(options.branches, filters.branchId),
          onRemove: () => onChange({ branchId: "all" }),
        }
      : null,
    filters.roleId !== "all"
      ? {
          key: "role",
          label: "Rol",
          value: optionLabel(options.roles, filters.roleId),
          onRemove: () => onChange({ roleId: "all" }),
        }
      : null,
    filters.lastLoginState !== "all"
      ? {
          key: "last-login",
          label: "Ultimo acceso",
          value: optionLabel(options.lastLoginStates, filters.lastLoginState),
          onRemove: () => onChange({ lastLoginState: "all" }),
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
  const resetFilters = {
    appAccess: "all",
    branchId: "all",
    lastLoginState: "all",
    roleId: "all",
    search: "",
    status: "all",
    warningState: "all",
  };

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-users-search"
        searchPlaceholder="Buscar por nombre o correo"
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
          <AdminFilterField id="admin-users-status" label="Estado">
            <select
              className={selectClass()}
              id="admin-users-status"
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
          <AdminFilterField id="admin-users-access" label="Acceso">
            <select
              className={selectClass()}
              id="admin-users-access"
              value={filters.appAccess}
              onChange={(event) => onChange({ appAccess: event.target.value })}
            >
              <option value="all">Todo acceso</option>
              {options.appAccess.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>
          <AdminFilterField id="admin-users-branch" label="Sucursal">
            <select
              className={selectClass()}
              id="admin-users-branch"
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
          <AdminFilterField id="admin-users-role" label="Rol">
            <select
              className={selectClass()}
              id="admin-users-role"
              value={filters.roleId}
              onChange={(event) => onChange({ roleId: event.target.value })}
            >
              <option value="all">Todos los roles</option>
              {options.roles.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>
          <AdminFilterField id="admin-users-last-login" label="Ultimo acceso">
            <select
              className={selectClass()}
              id="admin-users-last-login"
              value={filters.lastLoginState}
              onChange={(event) => onChange({ lastLoginState: event.target.value })}
            >
              <option value="all">Ultimo acceso</option>
              {options.lastLoginStates.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>
          <AdminFilterField id="admin-users-warning" label="Advertencias">
            <select
              className={selectClass()}
              id="admin-users-warning"
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
          </div>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
