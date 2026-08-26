import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminEquipmentFilterOptions, AdminEquipmentListFilters } from "../types";

const fieldClassName = adminFilterInputClassName();

interface AdminEquipmentMaintenanceFiltersProps {
  filters: AdminEquipmentListFilters;
  isBackendConnected: boolean;
  options: AdminEquipmentFilterOptions;
  onChange: (patch: Partial<AdminEquipmentListFilters>) => void;
}

function optionNodes(options: { id: string; label: string }[], allLabel = "Todos") {
  return (
    <>
      <option value="all">{allLabel}</option>
      {options.map((option) => (
        <option key={option.id} value={option.id}>
          {option.label}
        </option>
      ))}
    </>
  );
}

function optionLabel(options: Array<{ id: string; label: string }>, value: string) {
  return options.find((option) => option.id === value)?.label ?? value;
}

export function AdminEquipmentMaintenanceFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminEquipmentMaintenanceFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const resetFilters: Partial<AdminEquipmentListFilters> = {
    areaName: "all",
    areaType: "all",
    branchId: "all",
    dateFrom: null,
    dateTo: null,
    equipmentType: "all",
    incidentState: "all",
    maintenanceStatus: "all",
    maintenanceType: "all",
    operationalStatus: "all",
    overdueState: "all",
    providerName: "all",
    riskLevel: "all",
    search: "",
    technicianName: "all",
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
    filters.areaName !== "all"
      ? {
          key: "area",
          label: "Area",
          value: optionLabel(options.areas, filters.areaName),
          onRemove: () => onChange({ areaName: "all" }),
        }
      : null,
    filters.equipmentType !== "all"
      ? {
          key: "equipment",
          label: "Tipo",
          value: optionLabel(options.equipmentTypes, filters.equipmentType),
          onRemove: () => onChange({ equipmentType: "all" }),
        }
      : null,
    filters.operationalStatus !== "all"
      ? {
          key: "operational",
          label: "Estado operativo",
          value: optionLabel(options.operationalStatuses, filters.operationalStatus),
          onRemove: () => onChange({ operationalStatus: "all" }),
        }
      : null,
    filters.maintenanceStatus !== "all"
      ? {
          key: "maintenance",
          label: "Mantenimiento",
          value: optionLabel(options.maintenanceStatuses, filters.maintenanceStatus),
          onRemove: () => onChange({ maintenanceStatus: "all" }),
        }
      : null,
    filters.riskLevel !== "all"
      ? {
          key: "risk",
          label: "Riesgo",
          value: optionLabel(options.riskLevels, filters.riskLevel),
          onRemove: () => onChange({ riskLevel: "all" }),
        }
      : null,
    filters.overdueState !== "all"
      ? {
          key: "overdue",
          label: "Vencido",
          value: filters.overdueState === "overdue" ? "Vencidos" : "No vencidos",
          onRemove: () => onChange({ overdueState: "all" }),
        }
      : null,
    filters.incidentState !== "all"
      ? {
          key: "incident",
          label: "Incidencia",
          value: optionLabel(options.incidentStates, filters.incidentState),
          onRemove: () => onChange({ incidentState: "all" }),
        }
      : null,
    filters.dateFrom
      ? { key: "from", label: "Desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: null }) }
      : null,
    filters.dateTo
      ? { key: "to", label: "Hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: null }) }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-equipment-search"
        searchPlaceholder="Equipo, codigo, tecnico"
        searchValue={filters.search}
        status={isBackendConnected ? "API conectada" : "Integracion parcial"}
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
        <div className="grid min-w-0 gap-3">
          <AdminFilterField label="Sucursal">
            <select className={fieldClassName} value={filters.branchId} onChange={(event) => onChange({ branchId: event.target.value })}>
              {optionNodes(options.branches)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Area">
            <select className={fieldClassName} value={filters.areaName} onChange={(event) => onChange({ areaName: event.target.value })}>
              {optionNodes(options.areas)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Tipo equipo">
            <select className={fieldClassName} value={filters.equipmentType} onChange={(event) => onChange({ equipmentType: event.target.value })}>
              {optionNodes(options.equipmentTypes)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Estado operativo">
            <select className={fieldClassName} value={filters.operationalStatus} onChange={(event) => onChange({ operationalStatus: event.target.value })}>
              {optionNodes(options.operationalStatuses)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Mantenimiento">
            <select className={fieldClassName} value={filters.maintenanceStatus} onChange={(event) => onChange({ maintenanceStatus: event.target.value })}>
              {optionNodes(options.maintenanceStatuses)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Tipo mantto.">
            <select className={fieldClassName} value={filters.maintenanceType} onChange={(event) => onChange({ maintenanceType: event.target.value })}>
              {optionNodes(options.maintenanceTypes)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Riesgo">
            <select className={fieldClassName} value={filters.riskLevel} onChange={(event) => onChange({ riskLevel: event.target.value })}>
              {optionNodes(options.riskLevels)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Proveedor">
            <select className={fieldClassName} value={filters.providerName} onChange={(event) => onChange({ providerName: event.target.value })}>
              {optionNodes(options.providers)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Tecnico">
            <select className={fieldClassName} value={filters.technicianName} onChange={(event) => onChange({ technicianName: event.target.value })}>
              {optionNodes(options.technicians)}
            </select>
          </AdminFilterField>
          <div className="grid min-w-0 gap-3 sm:grid-cols-2">
            <AdminFilterField label="Desde">
              <input className={fieldClassName} type="date" value={filters.dateFrom ?? ""} onChange={(event) => onChange({ dateFrom: event.target.value || null })} />
            </AdminFilterField>
            <AdminFilterField label="Hasta">
              <input className={fieldClassName} type="date" value={filters.dateTo ?? ""} onChange={(event) => onChange({ dateTo: event.target.value || null })} />
            </AdminFilterField>
          </div>
          <AdminFilterField label="Vencido">
            <select className={fieldClassName} value={filters.overdueState} onChange={(event) => onChange({ overdueState: event.target.value })}>
              <option value="all">Todos</option>
              <option value="overdue">Vencidos</option>
              <option value="not_overdue">No vencidos</option>
            </select>
          </AdminFilterField>
          <AdminFilterField label="Incidencia">
            <select className={fieldClassName} value={filters.incidentState} onChange={(event) => onChange({ incidentState: event.target.value })}>
              {optionNodes(options.incidentStates)}
            </select>
          </AdminFilterField>

          <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3">
            {[
              { label: "Operativos", patch: { operationalStatus: "OPERATIONAL" } },
              { label: "Fuera de servicio", patch: { operationalStatus: "OUT_OF_SERVICE" } },
              { label: "Pendientes", patch: { maintenanceStatus: "PENDING" } },
              { label: "Vencidos", patch: { overdueState: "overdue" } },
              { label: "Correctivos abiertos", patch: { maintenanceType: "CORRECTIVE" } },
              { label: "Preventivos", patch: { maintenanceType: "PREVENTIVE" } },
              { label: "Alto riesgo", patch: { riskLevel: "HIGH" } },
              { label: "Con incidencia", patch: { incidentState: "with_incident" } },
              { label: "Hoy", patch: { dateFrom: today, dateTo: today } },
            ].map((quickFilter) => (
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
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
