import type { AdminDiscountFilterOptions, AdminDiscountListFilters } from "../types";

const controlClassName =
  "h-10 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-500";

interface AdminDiscountsFiltersProps {
  filters: AdminDiscountListFilters;
  isBackendConnected: boolean;
  onChange: (patch: Partial<AdminDiscountListFilters>) => void;
  options: AdminDiscountFilterOptions;
}

export function AdminDiscountsFilters({
  filters,
  isBackendConnected,
  onChange,
  options,
}: AdminDiscountsFiltersProps) {
  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3">
      <div className="grid min-w-0 gap-2 lg:grid-cols-[minmax(13rem,1.2fr)_minmax(9rem,0.7fr)_minmax(9rem,0.7fr)_minmax(9rem,0.7fr)]">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
          <span className="truncate">Busqueda</span>
          <input
            className={controlClassName}
            placeholder="Buscar descuento, codigo o objetivo"
            value={filters.search}
            onChange={(event) => onChange({ search: event.target.value })}
          />
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
          <span className="truncate">Marca</span>
          <select
            className={controlClassName}
            disabled={!isBackendConnected}
            value={filters.brandId ?? "all"}
            onChange={(event) => onChange({ brandId: event.target.value === "all" ? null : event.target.value })}
          >
            <option value="all">Todas</option>
            {options.brands.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
          <span className="truncate">Estado</span>
          <select
            className={controlClassName}
            value={filters.status}
            onChange={(event) => onChange({ status: event.target.value as AdminDiscountListFilters["status"] })}
          >
            <option value="all">Todos</option>
            <option value="ACTIVE">Activos</option>
            <option value="INACTIVE">Inactivos</option>
            <option value="ARCHIVED">Archivados</option>
          </select>
        </label>
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
          <span className="truncate">Salud</span>
          <select
            className={controlClassName}
            value={filters.warningState}
            onChange={(event) =>
              onChange({ warningState: event.target.value as AdminDiscountListFilters["warningState"] })
            }
          >
            <option value="all">Todos</option>
            <option value="with_warnings">Con advertencias</option>
            <option value="without_warnings">Sin advertencias</option>
          </select>
        </label>
      </div>

      <details className="mt-2 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
          Filtros avanzados
        </summary>
        <div className="mt-3 grid min-w-0 gap-2 lg:grid-cols-4">
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            <span className="truncate">Tipo</span>
            <select
              className={controlClassName}
              value={filters.discountType}
              onChange={(event) =>
                onChange({ discountType: event.target.value as AdminDiscountListFilters["discountType"] })
              }
            >
              <option value="all">Todos</option>
              <option value="PERCENTAGE">Porcentaje</option>
              <option value="FIXED_AMOUNT">Monto fijo</option>
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            <span className="truncate">Alcance</span>
            <select
              className={controlClassName}
              value={filters.targetScope}
              onChange={(event) =>
                onChange({ targetScope: event.target.value as AdminDiscountListFilters["targetScope"] })
              }
            >
              <option value="all">Todos</option>
              <option value="PRODUCT">Producto</option>
              <option value="CLASS">Clase</option>
              <option value="GLOBAL">Global</option>
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            <span className="truncate">Clase</span>
            <select
              className={controlClassName}
              value={filters.classId ?? "all"}
              onChange={(event) => onChange({ classId: event.target.value === "all" ? null : event.target.value })}
            >
              <option value="all">Todas</option>
              {options.classes.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
            <span className="truncate">Vigencia</span>
            <select
              className={controlClassName}
              value={filters.validity}
              onChange={(event) =>
                onChange({ validity: event.target.value as AdminDiscountListFilters["validity"] })
              }
            >
              <option value="all">Todas</option>
              <option value="current">Vigente</option>
              <option value="upcoming">Proxima</option>
              <option value="expired">Expirada</option>
              <option value="not_scheduled">Sin calendario</option>
            </select>
          </label>
        </div>
      </details>
    </section>
  );
}
