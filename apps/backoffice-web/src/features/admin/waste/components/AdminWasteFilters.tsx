import type { AdminWasteFilterOptions, AdminWasteListFilters } from "../types";

interface AdminWasteFiltersProps {
  filters: AdminWasteListFilters;
  isBackendConnected: boolean;
  options: AdminWasteFilterOptions;
  onChange: (patch: Partial<AdminWasteListFilters>) => void;
}

function optionList(options: Array<{ id: string; label: string }>) {
  return options.map((option) => (
    <option key={option.id} value={option.id}>
      {option.label}
    </option>
  ));
}

const controlClass = "min-w-0 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm";

function todayString() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoString(days: number) {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

export function AdminWasteFilters({ filters, isBackendConnected, options, onChange }: AdminWasteFiltersProps) {
  return (
    <section className="grid gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm md:grid-cols-2 xl:grid-cols-7">
      <label className="flex min-w-0 flex-col gap-1 xl:col-span-2">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Buscar</span>
        <input
          className={`${controlClass} outline-none focus:border-[var(--ui-color-primary)]`}
          placeholder="Folio, producto, SKU, motivo, operador"
          value={filters.search ?? ""}
          onChange={(event) => onChange({ search: event.target.value })}
        />
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Sucursal</span>
        <select
          className={controlClass}
          value={filters.branchId ?? "all"}
          onChange={(event) => onChange({ branchId: event.target.value === "all" ? null : event.target.value })}
        >
          <option value="all">Todas</option>
          {optionList(options.branches)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Desde</span>
        <input
          className={controlClass}
          type="date"
          value={filters.dateFrom ?? ""}
          onChange={(event) => onChange({ dateFrom: event.target.value || null })}
        />
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Hasta</span>
        <input
          className={controlClass}
          type="date"
          value={filters.dateTo ?? ""}
          onChange={(event) => onChange({ dateTo: event.target.value || null })}
        />
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Producto</span>
        <select
          className={controlClass}
          value={filters.productId ?? "all"}
          onChange={(event) => onChange({ productId: event.target.value === "all" ? null : event.target.value })}
        >
          <option value="all">Todos</option>
          {optionList(options.products)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Tipo</span>
        <select
          className={controlClass}
          value={filters.productKind ?? "all"}
          onChange={(event) => onChange({ productKind: event.target.value })}
        >
          <option value="all">Todos</option>
          {optionList(options.productKinds)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Clase</span>
        <select
          className={controlClass}
          value={filters.classId ?? "all"}
          onChange={(event) => onChange({ classId: event.target.value === "all" ? null : event.target.value })}
        >
          <option value="all">Todas</option>
          {optionList(options.classes)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Motivo</span>
        <select
          className={controlClass}
          value={filters.reasonCode ?? "all"}
          onChange={(event) => onChange({ reasonCode: event.target.value === "all" ? "all" : event.target.value })}
        >
          <option value="all">Todos</option>
          {options.reasons.map((reason) => (
            <option key={reason.code} value={reason.code}>
              {reason.label}
            </option>
          ))}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Origen</span>
        <select
          className={controlClass}
          value={filters.locationCode ?? "all"}
          onChange={(event) => onChange({ locationCode: event.target.value as AdminWasteListFilters["locationCode"] })}
        >
          <option value="all">Todos</option>
          {optionList(options.locations)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Operador</span>
        <select
          className={controlClass}
          value={filters.operatorUserId ?? "all"}
          onChange={(event) => onChange({ operatorUserId: event.target.value === "all" ? null : event.target.value })}
        >
          <option value="all">Todos</option>
          {optionList(options.operators)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Estado</span>
        <select
          className={controlClass}
          value={filters.status ?? "all"}
          onChange={(event) => onChange({ status: event.target.value as AdminWasteListFilters["status"] })}
        >
          <option value="all">Todos</option>
          {optionList(options.statuses)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Impacto</span>
        <select
          className={controlClass}
          value={filters.impactLevel ?? "all"}
          onChange={(event) => onChange({ impactLevel: event.target.value as AdminWasteListFilters["impactLevel"] })}
        >
          <option value="all">Todos</option>
          {optionList(options.impactLevels)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Evidencia</span>
        <select
          className={controlClass}
          value={filters.evidenceState ?? "all"}
          onChange={(event) => onChange({ evidenceState: event.target.value as AdminWasteListFilters["evidenceState"] })}
        >
          <option value="all">Todas</option>
          {optionList(options.evidenceStates)}
        </select>
      </label>

      <label className="flex min-w-0 flex-col gap-1">
        <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Advertencia</span>
        <select
          className={controlClass}
          value={filters.warningState ?? "all"}
          onChange={(event) => onChange({ warningState: event.target.value as AdminWasteListFilters["warningState"] })}
        >
          <option value="all">Todas</option>
          <option value="info">Info</option>
          <option value="warning">Advertencia</option>
          <option value="critical">Critica</option>
        </select>
      </label>

      <div className="flex flex-wrap items-end gap-2 md:col-span-2 xl:col-span-7">
        {[
          { label: "Hoy", patch: { dateFrom: todayString(), dateTo: todayString() } },
          { label: "Ultimos 7 dias", patch: { dateFrom: daysAgoString(6), dateTo: todayString() } },
          { label: "Alto impacto", patch: { impactLevel: "high" as const } },
          { label: "Caducado", patch: { reasonCode: "EXPIRED" } },
          { label: "Danado", patch: { reasonCode: "DAMAGED" } },
          { label: "Contaminado", patch: { reasonCode: "CONTAMINATED" } },
          { label: "Sin evidencia", patch: { evidenceState: "without_evidence" as const } },
          { label: "Con advertencias", patch: { warningState: "warning" as const } },
        ].map((quickFilter) => (
          <button
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-[var(--ui-color-primary)]"
            key={quickFilter.label}
            type="button"
            onClick={() => onChange(quickFilter.patch)}
          >
            {quickFilter.label}
          </button>
        ))}
        <span className="ml-auto rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-slate-500">
          {isBackendConnected ? "API conectada" : "Sin conexion API"}
        </span>
      </div>
    </section>
  );
}
