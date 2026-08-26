import { useState } from "react";

import {
  AdminActiveFilterChips,
  AdminAdvancedFiltersSheet,
  AdminDataToolbar,
  AdminFilterField,
  type AdminFilterChip,
} from "../../components/AdminFilterControls";
import { adminFilterInputClassName } from "../../components/adminFilterStyles";
import type {
  AdminProductCaptureMode,
  AdminProductFilterOptions,
  AdminProductListFilters,
  AdminProductReadinessStatus,
  AdminProductStatus,
} from "../types";

const inputClassName = adminFilterInputClassName();

const statusOptions: Array<{ label: string; value: AdminProductStatus | "all" }> = [
  { value: "all", label: "Todos los estados" },
  { value: "active", label: "Activo" },
  { value: "inactive", label: "Inactivo" },
];

const captureModeOptions: Array<{ label: string; value: AdminProductCaptureMode | "all" }> = [
  { value: "all", label: "Todos los modos" },
  { value: "PRODUCT_DIRECT", label: "Producto directo" },
  { value: "CLASS_CAPTURE", label: "Captura por clase" },
];

const readinessOptions: Array<{ label: string; value: AdminProductReadinessStatus | "all" }> = [
  { value: "all", label: "Toda preparacion" },
  { value: "ready", label: "Listo" },
  { value: "requires_attention", label: "Requiere atencion" },
  { value: "incomplete", label: "Incompleto" },
  { value: "pending_integration", label: "Pendiente de integracion" },
  { value: "unknown", label: "Sin evaluar" },
];

const resetFilters: Partial<AdminProductListFilters> = {
  brandId: null,
  branchId: null,
  captureMode: "all",
  classId: null,
  page: 1,
  readiness: "all",
  search: "",
  status: "all",
};

function optionLabel(options: Array<{ id: string; label: string }>, value: string | null | undefined) {
  return options.find((option) => option.id === value)?.label ?? value ?? "";
}

interface AdminProductsFiltersProps {
  filters: AdminProductListFilters;
  isBackendConnected: boolean;
  options: AdminProductFilterOptions;
  onChange: (patch: Partial<AdminProductListFilters>) => void;
}

export function AdminProductsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminProductsFiltersProps) {
  const [isFiltersOpen, setIsFiltersOpen] = useState(false);
  const branchDisabled = options.branches.length === 0;
  const brandDisabled = options.brands.length === 0;
  const classDisabled = options.classes.length === 0;
  const chips: AdminFilterChip[] = [
    filters.search
      ? { key: "search", label: "Busqueda", value: filters.search, onRemove: () => onChange({ page: 1, search: "" }) }
      : null,
    filters.brandId
      ? {
          key: "brand",
          label: "Marca",
          value: optionLabel(options.brands, filters.brandId),
          onRemove: () => onChange({ brandId: null, page: 1 }),
        }
      : null,
    filters.branchId
      ? {
          key: "branch",
          label: "Sucursal",
          value: optionLabel(options.branches, filters.branchId),
          onRemove: () => onChange({ branchId: null, page: 1 }),
        }
      : null,
    filters.status !== "all"
      ? {
          key: "status",
          label: "Estado",
          value: statusOptions.find((option) => option.value === filters.status)?.label ?? filters.status,
          onRemove: () => onChange({ page: 1, status: "all" }),
        }
      : null,
    filters.classId
      ? {
          key: "class",
          label: "Clase",
          value: optionLabel(options.classes, filters.classId),
          onRemove: () => onChange({ classId: null, page: 1 }),
        }
      : null,
    filters.captureMode !== "all"
      ? {
          key: "capture-mode",
          label: "Modo",
          value:
            captureModeOptions.find((option) => option.value === filters.captureMode)?.label ??
            filters.captureMode,
          onRemove: () => onChange({ captureMode: "all", page: 1 }),
        }
      : null,
    filters.readiness !== "all"
      ? {
          key: "readiness",
          label: "Preparacion",
          value: readinessOptions.find((option) => option.value === filters.readiness)?.label ?? filters.readiness,
          onRemove: () => onChange({ page: 1, readiness: "all" }),
        }
      : null,
  ].filter((chip): chip is AdminFilterChip => Boolean(chip));

  return (
    <>
      <AdminDataToolbar
        filterCount={chips.length}
        searchId="admin-products-search"
        searchPlaceholder="Buscar producto, SKU, codigo o clase"
        searchValue={filters.search ?? ""}
        status={isBackendConnected ? "Datos conectados" : "Esperando API"}
        onOpenFilters={() => setIsFiltersOpen(true)}
        onSearchChange={(search) => onChange({ page: 1, search })}
      >
        <AdminActiveFilterChips chips={chips} onClearAll={() => onChange(resetFilters)} />
      </AdminDataToolbar>

      <AdminAdvancedFiltersSheet
        isOpen={isFiltersOpen}
        onClear={() => onChange(resetFilters)}
        onClose={() => setIsFiltersOpen(false)}
      >
        <div className="grid min-w-0 gap-3">
          <AdminFilterField id="admin-products-brand" label="Marca">
            <select
              className={`${inputClassName} truncate`}
              disabled={brandDisabled}
              id="admin-products-brand"
              title={brandDisabled ? "Marcas pendientes de API" : "Selecciona marca"}
              value={filters.brandId ?? ""}
              onChange={(event) =>
                onChange({ brandId: event.target.value || null, branchId: null, classId: null, page: 1 })
              }
            >
              {brandDisabled ? (
                <option value="">Marcas pendientes de API</option>
              ) : (
                <option value="">Todas las marcas</option>
              )}
              {options.brands.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-products-branch" label="Sucursal">
            <select
              className={`${inputClassName} truncate`}
              disabled={branchDisabled}
              id="admin-products-branch"
              title={branchDisabled ? "Sucursales pendientes de API" : "Selecciona sucursal"}
              value={filters.branchId ?? ""}
              onChange={(event) =>
                onChange({ brandId: null, branchId: event.target.value || null, classId: null, page: 1 })
              }
            >
              {branchDisabled ? (
                <option value="">Sucursales pendientes de API</option>
              ) : (
                <option value="">Todas las sucursales</option>
              )}
              {options.branches.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-products-status" label="Estado">
            <select
              className={inputClassName}
              id="admin-products-status"
              value={filters.status ?? "all"}
              onChange={(event) =>
                onChange({ status: event.target.value as AdminProductStatus | "all", page: 1 })
              }
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </AdminFilterField>

          <AdminFilterField id="admin-products-class" label="Clase / categoria">
            <select
              className={`${inputClassName} truncate`}
              disabled={classDisabled}
              id="admin-products-class"
              title={classDisabled ? "Clases pendientes de API" : "Selecciona clase o categoria"}
              value={filters.classId ?? ""}
              onChange={(event) => onChange({ classId: event.target.value || null, page: 1 })}
            >
              {classDisabled ? <option value="">Clases pendientes de API</option> : <option value="">Todas las clases</option>}
              {options.classes.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>

          <AdminFilterField id="admin-products-capture-mode" label="Modo">
            <select
              className={inputClassName}
              id="admin-products-capture-mode"
              value={filters.captureMode ?? "all"}
              onChange={(event) =>
                onChange({ captureMode: event.target.value as AdminProductCaptureMode | "all", page: 1 })
              }
            >
              {captureModeOptions.map((option) => (
                <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>

          <AdminFilterField id="admin-products-readiness" label="Preparacion">
            <select
              className={inputClassName}
              id="admin-products-readiness"
              value={filters.readiness ?? "all"}
              onChange={(event) =>
                onChange({ readiness: event.target.value as AdminProductReadinessStatus | "all", page: 1 })
              }
            >
              {readinessOptions.map((option) => (
                <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          </AdminFilterField>
        </div>
      </AdminAdvancedFiltersSheet>
    </>
  );
}
