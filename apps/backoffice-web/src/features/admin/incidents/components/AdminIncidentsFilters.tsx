import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminIncidentFilterOptions, AdminIncidentListFilters } from "../types";

const fieldClassName = adminFilterInputClassName();

interface AdminIncidentsFiltersProps {
  filters: AdminIncidentListFilters;
  isBackendConnected: boolean;
  options: AdminIncidentFilterOptions;
  onChange: (patch: Partial<AdminIncidentListFilters>) => void;
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

export function AdminIncidentsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminIncidentsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const resetFilters: Partial<AdminIncidentListFilters> = {
    areaName: "all",
    branchId: "all",
    dateFrom: null,
    dateTo: null,
    dueState: "all",
    evidenceState: "all",
    incidentType: "all",
    relatedDocumentState: "all",
    reportedByUserId: "all",
    responsibleUserId: "all",
    search: "",
    severity: "all",
    sourceType: "all",
    status: "all",
    warningState: "all",
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
    filters.sourceType !== "all"
      ? {
          key: "source",
          label: "Origen",
          value: optionLabel(options.sourceTypes, filters.sourceType),
          onRemove: () => onChange({ sourceType: "all" }),
        }
      : null,
    filters.incidentType !== "all"
      ? {
          key: "type",
          label: "Tipo",
          value: optionLabel(options.incidentTypes, filters.incidentType),
          onRemove: () => onChange({ incidentType: "all" }),
        }
      : null,
    filters.severity !== "all"
      ? {
          key: "severity",
          label: "Severidad",
          value: optionLabel(options.severities, filters.severity),
          onRemove: () => onChange({ severity: "all" }),
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
    filters.responsibleUserId !== "all"
      ? {
          key: "responsible",
          label: "Responsable",
          value: optionLabel(options.responsibleUsers, filters.responsibleUserId),
          onRemove: () => onChange({ responsibleUserId: "all" }),
        }
      : null,
    filters.dueState !== "all"
      ? {
          key: "due",
          label: "Vencimiento",
          value: optionLabel(options.dueStates, filters.dueState),
          onRemove: () => onChange({ dueState: "all" }),
        }
      : null,
    filters.evidenceState !== "all"
      ? {
          key: "evidence",
          label: "Evidencia",
          value: optionLabel(options.evidenceStates, filters.evidenceState),
          onRemove: () => onChange({ evidenceState: "all" }),
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
        searchId="admin-incidents-search"
        searchPlaceholder="Folio, titulo, descripcion"
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
          <AdminFilterField label="Origen">
            <select className={fieldClassName} value={filters.sourceType} onChange={(event) => onChange({ sourceType: event.target.value })}>
              {optionNodes(options.sourceTypes)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Tipo">
            <select className={fieldClassName} value={filters.incidentType} onChange={(event) => onChange({ incidentType: event.target.value })}>
              {optionNodes(options.incidentTypes)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Severidad">
            <select className={fieldClassName} value={filters.severity} onChange={(event) => onChange({ severity: event.target.value })}>
              {optionNodes(options.severities)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Estado">
            <select className={fieldClassName} value={filters.status} onChange={(event) => onChange({ status: event.target.value })}>
              {optionNodes(options.statuses)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Responsable">
            <select className={fieldClassName} value={filters.responsibleUserId} onChange={(event) => onChange({ responsibleUserId: event.target.value })}>
              {optionNodes(options.responsibleUsers)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Reportada por">
            <select className={fieldClassName} value={filters.reportedByUserId} onChange={(event) => onChange({ reportedByUserId: event.target.value })}>
              {optionNodes(options.reportedByUsers)}
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
          <AdminFilterField label="Vencimiento">
            <select className={fieldClassName} value={filters.dueState} onChange={(event) => onChange({ dueState: event.target.value })}>
              {optionNodes(options.dueStates)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Evidencia">
            <select className={fieldClassName} value={filters.evidenceState} onChange={(event) => onChange({ evidenceState: event.target.value })}>
              {optionNodes(options.evidenceStates)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Documentos">
            <select className={fieldClassName} value={filters.relatedDocumentState} onChange={(event) => onChange({ relatedDocumentState: event.target.value })}>
              {optionNodes(options.relatedDocumentStates)}
            </select>
          </AdminFilterField>

          <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3">
            {[
              { label: "Hoy", patch: { dateFrom: today, dateTo: today } },
              { label: "Abiertas", patch: { status: "OPEN" } },
              { label: "En seguimiento", patch: { status: "IN_PROGRESS" } },
              { label: "Vencidas", patch: { dueState: "overdue" } },
              { label: "Alto riesgo", patch: { severity: "HIGH" } },
              { label: "Sin responsable", patch: { responsibleUserId: "unassigned" } },
              { label: "Sin evidencia", patch: { evidenceState: "without_evidence" } },
              { label: "Sanitarias", patch: { incidentType: "SANITATION_ISSUE" } },
              { label: "Equipos", patch: { incidentType: "EQUIPMENT_FAILURE" } },
              { label: "Produccion", patch: { incidentType: "PRODUCTION_ISSUE" } },
              { label: "Inventario", patch: { incidentType: "INVENTORY_ISSUE" } },
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
