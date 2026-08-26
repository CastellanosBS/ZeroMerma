import type { ReactNode } from "react";

import type { AdminScopeFilterKind } from "../adminTypes";

const inputClassName =
  "h-9 w-full min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]";

function FilterField({
  children,
  className = "",
  id,
  label,
}: {
  children: ReactNode;
  className?: string;
  id: string;
  label: string;
}) {
  return (
    <label
      className={`grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500 ${className}`}
      htmlFor={id}
      title={label}
    >
      <span className="truncate">{label}</span>
      {children}
    </label>
  );
}

function SelectFilter({
  id,
  label,
  options,
}: {
  id: string;
  label: string;
  options: string[];
}) {
  return (
    <FilterField id={id} label={label}>
      <select className={`${inputClassName} truncate`} id={id} title={options[0]}>
        {options.map((option) => (
          <option key={option}>{option}</option>
        ))}
      </select>
    </FilterField>
  );
}

export function AdminScopeFilters({ filters }: { filters: AdminScopeFilterKind[] }) {
  const showBranch = filters.includes("branch");
  const showBrand = filters.includes("brand");
  const showDateRange = filters.includes("dateRange");
  const showStatus = filters.includes("status");
  const showShift = filters.includes("shift");
  const showUser = filters.includes("user");
  const showSearch = filters.includes("search");

  return (
    <section className="min-w-0 rounded-[22px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-3">
      <div className="grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {showSearch ? (
          <FilterField className="md:col-span-2" id="admin-scope-search" label="Búsqueda">
            <input
              className={inputClassName}
              id="admin-scope-search"
              placeholder="Buscar por folio, nombre, usuario o entidad"
              title="Buscar por folio, nombre, usuario o entidad"
              type="search"
            />
          </FilterField>
        ) : null}

        {showBranch ? (
          <SelectFilter id="admin-scope-branch" label="Sucursal" options={["Todas las sucursales"]} />
        ) : null}

        {showBrand ? (
          <SelectFilter id="admin-scope-brand" label="Marca" options={["Todas las marcas", "El Mejor Pan", "Merenna"]} />
        ) : null}

        {showDateRange ? (
          <>
            <FilterField id="admin-scope-date-from" label="Desde">
              <input className={inputClassName} id="admin-scope-date-from" type="date" />
            </FilterField>
            <FilterField id="admin-scope-date-to" label="Hasta">
              <input className={inputClassName} id="admin-scope-date-to" type="date" />
            </FilterField>
          </>
        ) : null}

        {showStatus ? (
          <SelectFilter
            id="admin-scope-status"
            label="Estado"
            options={["Todos los estados", "Activo", "Pendiente", "Completado", "Cancelado", "Requiere revisión"]}
          />
        ) : null}

        {showShift ? (
          <SelectFilter id="admin-scope-shift" label="Turno" options={["Todos los turnos", "Mañana", "Tarde", "Noche"]} />
        ) : null}

        {showUser ? (
          <SelectFilter id="admin-scope-user" label="Usuario" options={["Todos los usuarios"]} />
        ) : null}
      </div>
    </section>
  );
}
