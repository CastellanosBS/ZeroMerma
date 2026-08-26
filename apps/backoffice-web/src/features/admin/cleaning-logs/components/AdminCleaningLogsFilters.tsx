import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type { AdminCleaningFilterOptions, AdminCleaningListFilters } from "../types";

const fieldClassName = adminFilterInputClassName();

interface AdminCleaningLogsFiltersProps {
  filters: AdminCleaningListFilters;
  isBackendConnected: boolean;
  options: AdminCleaningFilterOptions;
  onChange: (patch: Partial<AdminCleaningListFilters>) => void;
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

export function AdminCleaningLogsFilters({
  filters,
  isBackendConnected,
  options,
  onChange,
}: AdminCleaningLogsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const resetFilters: Partial<AdminCleaningListFilters> = {
    areaName: "all",
    areaType: "all",
    branchId: "all",
    cleaningType: "all",
    dateFrom: null,
    dateTo: null,
    evidenceState: "all",
    observationState: "all",
    responsibleUserId: "all",
    riskLevel: "all",
    search: "",
    shiftCode: "all",
    status: "all",
    templateId: "all",
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
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: optionLabel(options.statuses, filters.status),
          onRemove: () => onChange({ status: "all" }),
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
    filters.dateFrom
      ? { key: "from", label: "Desde", value: filters.dateFrom, onRemove: () => onChange({ dateFrom: null }) }
      : null,
    filters.dateTo
      ? { key: "to", label: "Hasta", value: filters.dateTo, onRemove: () => onChange({ dateTo: null }) }
      : null,
    filters.evidenceState !== "all"
      ? {
          key: "evidence",
          label: "Evidencia",
          value: optionLabel(options.evidenceStates, filters.evidenceState),
          onRemove: () => onChange({ evidenceState: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-cleaning-search"
        searchPlaceholder="Folio, area, tarea"
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
          <select
            className={fieldClassName}
            value={filters.branchId}
            onChange={(event) => onChange({ branchId: event.target.value })}
          >
            {optionNodes(options.branches)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Area">
          <select
            className={fieldClassName}
            value={filters.areaName}
            onChange={(event) => onChange({ areaName: event.target.value })}
          >
            {optionNodes(options.areas)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Tipo area">
          <select
            className={fieldClassName}
            value={filters.areaType}
            onChange={(event) => onChange({ areaType: event.target.value })}
          >
            {optionNodes(options.areaTypes)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Turno">
          <select
            className={fieldClassName}
            value={filters.shiftCode}
            onChange={(event) => onChange({ shiftCode: event.target.value })}
          >
            {optionNodes(options.shifts)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Responsable">
          <select
            className={fieldClassName}
            value={filters.responsibleUserId}
            onChange={(event) => onChange({ responsibleUserId: event.target.value })}
          >
            {optionNodes(options.responsibleUsers)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Desde">
          <input
            className={fieldClassName}
            type="date"
            value={filters.dateFrom ?? ""}
            onChange={(event) => onChange({ dateFrom: event.target.value || null })}
          />
        </AdminFilterField>
        <AdminFilterField label="Hasta">
          <input
            className={fieldClassName}
            type="date"
            value={filters.dateTo ?? ""}
            onChange={(event) => onChange({ dateTo: event.target.value || null })}
          />
        </AdminFilterField>
        <AdminFilterField label="Estado">
          <select
            className={fieldClassName}
            value={filters.status}
            onChange={(event) => onChange({ status: event.target.value })}
          >
            {optionNodes(options.statuses)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Limpieza">
          <select
            className={fieldClassName}
            value={filters.cleaningType}
            onChange={(event) => onChange({ cleaningType: event.target.value })}
          >
            {optionNodes(options.cleaningTypes)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Riesgo">
          <select
            className={fieldClassName}
            value={filters.riskLevel}
            onChange={(event) => onChange({ riskLevel: event.target.value })}
          >
            {optionNodes(options.riskLevels)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Evidencia">
          <select
            className={fieldClassName}
            value={filters.evidenceState}
            onChange={(event) => onChange({ evidenceState: event.target.value })}
          >
            {optionNodes(options.evidenceStates)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Observaciones">
          <select
            className={fieldClassName}
            value={filters.observationState}
            onChange={(event) => onChange({ observationState: event.target.value })}
          >
            {optionNodes(options.observationStates)}
          </select>
        </AdminFilterField>
        <AdminFilterField label="Plantilla">
          <select
            className={fieldClassName}
            value={filters.templateId}
            onChange={(event) => onChange({ templateId: event.target.value })}
          >
            {optionNodes(options.templates)}
          </select>
        </AdminFilterField>

      <div className="flex min-w-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] pt-3">
        {[
          {
            label: "Hoy",
            patch: {
              dateFrom: new Date().toISOString().slice(0, 10),
              dateTo: new Date().toISOString().slice(0, 10),
            },
          },
          { label: "Pendientes", patch: { status: "PENDING" } },
          { label: "Vencidas", patch: { warningState: "overdue" } },
          { label: "Completadas", patch: { status: "COMPLETED" } },
          { label: "Sin evidencia", patch: { evidenceState: "without_evidence" } },
          { label: "Con observaciones", patch: { observationState: "with_observations" } },
          { label: "Alto riesgo", patch: { riskLevel: "HIGH" } },
          { label: "Produccion", patch: { areaType: "PRODUCTION_AREA" } },
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
