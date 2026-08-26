import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminAuditFilterOptions, AdminAuditListFilters } from "../types";

interface AdminAuditFiltersProps {
  filters: AdminAuditListFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminAuditListFilters>) => void;
  options: AdminAuditFilterOptions;
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

function TextFilter({
  label,
  placeholder,
  value,
  onChange,
}: {
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <AdminFilterField label={label}>
      <input
        className={adminFilterInputClassName()}
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </AdminFilterField>
  );
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminAuditFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminAuditFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const quickFilters = [
    { label: "Hoy", patch: { dateFrom: new Date().toISOString().slice(0, 10), dateTo: "" } },
    { label: "Sensibles", patch: { sensitive: "yes" } },
    { label: "Fallidos", patch: { result: "failed" } },
    { label: "Usuarios", patch: { module: "users" } },
    { label: "Caja y finanzas", patch: { module: "cash" } },
    { label: "Inventario", patch: { module: "inventory" } },
    { label: "Control", patch: { module: "roles_permissions" } },
    { label: "Sistema", patch: { sourceApp: "SYSTEM" } },
  ];
  const resetFilters: Partial<AdminAuditListFilters> = {
    action: "all",
    actorEmail: "",
    actorUserId: "all",
    branchId: "all",
    dateFrom: "",
    dateTo: "",
    entityId: "",
    entityType: "all",
    module: "all",
    relatedReference: "",
    result: "all",
    search: "",
    sensitive: "all",
    severity: "all",
    sourceApp: "all",
    warningState: "all",
    workstation: "",
  };
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ search: "" }) }
      : null,
    filters.actorEmail
      ? {
          key: "actor-email",
          label: "Actor email",
          value: filters.actorEmail,
          onRemove: () => onChange({ actorEmail: "" }),
        }
      : null,
    filters.actorUserId !== "all"
      ? {
          key: "actor-user",
          label: "Usuario",
          value: optionLabel(options.users, filters.actorUserId),
          onRemove: () => onChange({ actorUserId: "all" }),
        }
      : null,
    filters.module !== "all"
      ? {
          key: "module",
          label: "Modulo",
          value: optionLabel(options.modules, filters.module),
          onRemove: () => onChange({ module: "all" }),
        }
      : null,
    filters.action !== "all"
      ? {
          key: "action",
          label: "Accion",
          value: optionLabel(options.actions, filters.action),
          onRemove: () => onChange({ action: "all" }),
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
    filters.dateFrom
      ? { key: "from", label: "Desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: "" }) }
      : null,
    filters.dateTo
      ? { key: "to", label: "Hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: "" }) }
      : null,
    filters.sensitive !== "all"
      ? {
          key: "sensitive",
          label: "Sensible",
          value: optionLabel(options.sensitivities, filters.sensitive),
          onRemove: () => onChange({ sensitive: "all" }),
        }
      : null,
    filters.result !== "all"
      ? {
          key: "result",
          label: "Resultado",
          value: optionLabel(options.results, filters.result),
          onRemove: () => onChange({ result: "all" }),
        }
      : null,
    filters.sourceApp !== "all"
      ? {
          key: "source",
          label: "Origen",
          value: optionLabel(options.sourceApps, filters.sourceApp),
          onRemove: () => onChange({ sourceApp: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-audit-search"
        searchPlaceholder="Evento, folio, entidad..."
        searchValue={filters.search}
        status={isBackendConnected ? "Eventos desde backend" : "Esperando contrato"}
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
        <TextFilter
          label="Actor email"
          placeholder="correo@dominio"
          value={filters.actorEmail}
          onChange={(actorEmail) => onChange({ actorEmail })}
        />
        <TextFilter
          label="Entidad ID"
          placeholder="UUID o referencia"
          value={filters.entityId}
          onChange={(entityId) => onChange({ entityId })}
        />
        <TextFilter
          label="Documento"
          placeholder="folio / referencia"
          value={filters.relatedReference}
          onChange={(relatedReference) => onChange({ relatedReference })}
        />
        <TextFilter
          label="Estacion"
          placeholder="caja / estacion"
          value={filters.workstation}
          onChange={(workstation) => onChange({ workstation })}
        />
        <TextFilter
          label="Desde"
          placeholder="YYYY-MM-DD"
          value={filters.dateFrom}
          onChange={(dateFrom) => onChange({ dateFrom })}
        />

        <SelectFilter
          label="Usuario"
          options={options.users}
          value={filters.actorUserId}
          onChange={(actorUserId) => onChange({ actorUserId })}
        />
        <SelectFilter
          label="Modulo"
          options={options.modules}
          value={filters.module}
          onChange={(module) => onChange({ module })}
        />
        <SelectFilter
          label="Accion"
          options={options.actions}
          value={filters.action}
          onChange={(action) => onChange({ action })}
        />
        <SelectFilter
          label="Entidad"
          options={options.entityTypes}
          value={filters.entityType}
          onChange={(entityType) => onChange({ entityType })}
        />
        <SelectFilter
          label="Sucursal"
          options={options.branches}
          value={filters.branchId}
          onChange={(branchId) => onChange({ branchId })}
        />
        <TextFilter
          label="Hasta"
          placeholder="YYYY-MM-DD"
          value={filters.dateTo}
          onChange={(dateTo) => onChange({ dateTo })}
        />

        <SelectFilter
          label="Severidad"
          options={options.severities}
          value={filters.severity}
          onChange={(severity) => onChange({ severity })}
        />
        <SelectFilter
          label="Sensible"
          options={options.sensitivities}
          value={filters.sensitive}
          onChange={(sensitive) => onChange({ sensitive })}
        />
        <SelectFilter
          label="Resultado"
          options={options.results}
          value={filters.result}
          onChange={(result) => onChange({ result })}
        />
        <SelectFilter
          label="Origen"
          options={options.sourceApps}
          value={filters.sourceApp}
          onChange={(sourceApp) => onChange({ sourceApp })}
        />
        <SelectFilter
          label="Advertencia"
          options={options.warningStates}
          value={filters.warningState}
          onChange={(warningState) => onChange({ warningState })}
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
