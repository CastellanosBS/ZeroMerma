import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminSanitaryFilterOptions, AdminSanitaryListFilters } from "../types";

const fieldClassName = adminFilterInputClassName();

interface AdminSanitaryVerificationsFiltersProps {
  filters: AdminSanitaryListFilters;
  isBackendConnected: boolean;
  options: AdminSanitaryFilterOptions;
  onChange: (patch: Partial<AdminSanitaryListFilters>) => void;
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

export function AdminSanitaryVerificationsFilters({
  filters,
  isBackendConnected,
  options,
  onChange,
}: AdminSanitaryVerificationsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const today = new Date().toISOString().slice(0, 10);
  const resetFilters: Partial<AdminSanitaryListFilters> = {
    areaName: "all",
    areaType: "all",
    branchId: "all",
    dateFrom: null,
    dateTo: null,
    evidenceState: "all",
    incidentState: "all",
    inspectorUserId: "all",
    processName: "all",
    processType: "all",
    result: "all",
    riskLevel: "all",
    search: "",
    status: "all",
    templateId: "all",
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
    filters.processType !== "all"
      ? {
          key: "process",
          label: "Proceso",
          value: optionLabel(options.processTypes, filters.processType),
          onRemove: () => onChange({ processType: "all" }),
        }
      : null,
    filters.inspectorUserId !== "all"
      ? {
          key: "inspector",
          label: "Inspector",
          value: optionLabel(options.inspectors, filters.inspectorUserId),
          onRemove: () => onChange({ inspectorUserId: "all" }),
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
    filters.result !== "all"
      ? {
          key: "result",
          label: "Resultado",
          value: optionLabel(options.results, filters.result),
          onRemove: () => onChange({ result: "all" }),
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
    filters.evidenceState !== "all"
      ? {
          key: "evidence",
          label: "Evidencia",
          value: optionLabel(options.evidenceStates, filters.evidenceState),
          onRemove: () => onChange({ evidenceState: "all" }),
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
        searchId="admin-sanitary-search"
        searchPlaceholder="Folio, area, inspector"
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
          <AdminFilterField label="Tipo area">
            <select className={fieldClassName} value={filters.areaType} onChange={(event) => onChange({ areaType: event.target.value })}>
              {optionNodes(options.areaTypes)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Proceso">
            <select className={fieldClassName} value={filters.processType} onChange={(event) => onChange({ processType: event.target.value })}>
              {optionNodes(options.processTypes)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Inspector">
            <select className={fieldClassName} value={filters.inspectorUserId} onChange={(event) => onChange({ inspectorUserId: event.target.value })}>
              {optionNodes(options.inspectors)}
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
          <AdminFilterField label="Estado">
            <select className={fieldClassName} value={filters.status} onChange={(event) => onChange({ status: event.target.value })}>
              {optionNodes(options.statuses)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Resultado">
            <select className={fieldClassName} value={filters.result} onChange={(event) => onChange({ result: event.target.value })}>
              {optionNodes(options.results)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Riesgo">
            <select className={fieldClassName} value={filters.riskLevel} onChange={(event) => onChange({ riskLevel: event.target.value })}>
              {optionNodes(options.riskLevels)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Evidencia">
            <select className={fieldClassName} value={filters.evidenceState} onChange={(event) => onChange({ evidenceState: event.target.value })}>
              {optionNodes(options.evidenceStates)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Incidencia">
            <select className={fieldClassName} value={filters.incidentState} onChange={(event) => onChange({ incidentState: event.target.value })}>
              {optionNodes(options.incidentStates)}
            </select>
          </AdminFilterField>
          <AdminFilterField label="Plantilla">
            <select className={fieldClassName} value={filters.templateId} onChange={(event) => onChange({ templateId: event.target.value })}>
              {optionNodes(options.templates)}
            </select>
          </AdminFilterField>

          <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3">
            {[
              { label: "Hoy", patch: { dateFrom: today, dateTo: today } },
              { label: "Pendientes", patch: { status: "PENDING" } },
              { label: "Aprobadas", patch: { result: "PASSED" } },
              { label: "Fallidas", patch: { result: "FAILED" } },
              { label: "Con incidencia", patch: { incidentState: "with_incident" } },
              { label: "Alto riesgo", patch: { riskLevel: "HIGH" } },
              { label: "Sin evidencia", patch: { evidenceState: "without_evidence" } },
              { label: "Produccion", patch: { areaType: "PRODUCTION_AREA" } },
              { label: "Equipo", patch: { processType: "EQUIPMENT" } },
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
