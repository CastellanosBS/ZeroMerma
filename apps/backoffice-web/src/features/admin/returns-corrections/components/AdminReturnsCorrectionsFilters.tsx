import type {
  AdminCorrectionFilterOptions,
  AdminCorrectionListFilters,
  AdminReturnFilterOptions,
  AdminReturnListFilters,
  AdminReturnsCorrectionsTab,
} from "../types";

interface AdminReturnsCorrectionsFiltersProps {
  correctionFilters: AdminCorrectionListFilters;
  correctionOptions: AdminCorrectionFilterOptions;
  returnFilters: AdminReturnListFilters;
  returnOptions: AdminReturnFilterOptions;
  tab: AdminReturnsCorrectionsTab;
  onCorrectionChange: (patch: Partial<AdminCorrectionListFilters>) => void;
  onReturnChange: (patch: Partial<AdminReturnListFilters>) => void;
}

function toDateInput(value: Date) {
  return value.toISOString().slice(0, 10);
}

function quickRange(kind: "today" | "week" | "month") {
  const today = new Date();
  if (kind === "today") {
    return { dateFrom: toDateInput(today), dateTo: toDateInput(today) };
  }
  if (kind === "week") {
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() - 6);
    return { dateFrom: toDateInput(weekStart), dateTo: toDateInput(today) };
  }
  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
  return { dateFrom: toDateInput(monthStart), dateTo: toDateInput(today) };
}

export function AdminReturnsCorrectionsFilters({
  correctionFilters,
  correctionOptions,
  onCorrectionChange,
  onReturnChange,
  returnFilters,
  returnOptions,
  tab,
}: AdminReturnsCorrectionsFiltersProps) {
  const isReturns = tab === "returns";
  const search = isReturns ? (returnFilters.search ?? "") : (correctionFilters.search ?? "");
  const dateFrom = isReturns ? returnFilters.dateFrom : correctionFilters.dateFrom;
  const dateTo = isReturns ? returnFilters.dateTo : correctionFilters.dateTo;
  const branchId = isReturns ? returnFilters.branchId : correctionFilters.branchId;
  const operatorId = isReturns ? returnFilters.operatorId : correctionFilters.operatorId;
  const status = isReturns ? returnFilters.status : correctionFilters.status;
  const branchOptions = isReturns ? returnOptions.branches : correctionOptions.branches;
  const operatorOptions = isReturns ? returnOptions.operators : correctionOptions.operators;
  const statusOptions = isReturns ? returnOptions.statuses : correctionOptions.statuses;

  function patchCommon(patch: Partial<AdminReturnListFilters> & Partial<AdminCorrectionListFilters>) {
    if (isReturns) {
      onReturnChange(patch);
      return;
    }
    onCorrectionChange(patch);
  }

  return (
    <section className="grid min-w-0 gap-2 rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/80 p-3">
      <div className="grid min-w-0 gap-2 xl:grid-cols-[minmax(16rem,1.45fr)_minmax(9rem,0.7fr)_minmax(9rem,0.7fr)_minmax(10rem,0.75fr)]">
        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Busqueda
          <input
            className="h-10 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition placeholder:text-slate-400 focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            placeholder={isReturns ? "Buscar DEV, ticket o producto" : "Buscar COR, documento o motivo"}
            type="search"
            value={search}
            onChange={(event) => patchCommon({ search: event.target.value })}
          />
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Desde
          <input
            className="h-10 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="date"
            value={dateFrom ?? ""}
            onChange={(event) => patchCommon({ dateFrom: event.target.value || null })}
          />
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Hasta
          <input
            className="h-10 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-medium normal-case tracking-normal text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="date"
            value={dateTo ?? ""}
            onChange={(event) => patchCommon({ dateTo: event.target.value || null })}
          />
        </label>

        <label className="grid min-w-0 gap-1 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
          Estado
          <select
            className="h-10 min-w-0 truncate rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold normal-case tracking-normal text-slate-950 outline-none transition focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            value={status ?? "all"}
            onChange={(event) => patchCommon({ status: event.target.value })}
          >
            <option value="all">Todos</option>
            {statusOptions.map((option) => (
              <option key={option.id} title={option.label} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <details className="group rounded-[16px] border border-[var(--ui-color-border)] bg-white px-3 py-2">
        <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-[0.12em] text-slate-500 outline-none transition focus:ring-4 focus:ring-[var(--ui-color-ring)]">
          Filtros avanzados
        </summary>
        <div className="mt-2 grid min-w-0 gap-2 lg:grid-cols-3">
          <label className="grid min-w-0 gap-1 text-xs font-semibold text-slate-600">
            Sucursal
            <select
              className="h-10 min-w-0 truncate rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-950 outline-none focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              value={branchId ?? "all"}
              onChange={(event) => patchCommon({ branchId: event.target.value })}
            >
              <option value="all">Todas</option>
              {branchOptions.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="grid min-w-0 gap-1 text-xs font-semibold text-slate-600">
            Operador
            <select
              className="h-10 min-w-0 truncate rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-950 outline-none focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
              value={operatorId ?? "all"}
              onChange={(event) => patchCommon({ operatorId: event.target.value })}
            >
              <option value="all">Todos</option>
              {operatorOptions.map((option) => (
                <option key={option.id} title={option.label} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          {isReturns ? (
            <label className="grid min-w-0 gap-1 text-xs font-semibold text-slate-600">
              Reembolso
              <select
                className="h-10 min-w-0 truncate rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-950 outline-none focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                value={returnFilters.refundMethod ?? "all"}
                onChange={(event) => onReturnChange({ refundMethod: event.target.value })}
              >
                <option value="all">Todos</option>
                {returnOptions.refundMethods.map((option) => (
                  <option key={option.id} title={option.label} value={option.id}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ) : (
            <>
              <label className="grid min-w-0 gap-1 text-xs font-semibold text-slate-600">
                Documento
                <select
                  className="h-10 min-w-0 truncate rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-950 outline-none focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                  value={correctionFilters.targetDocumentType ?? "all"}
                  onChange={(event) => onCorrectionChange({ targetDocumentType: event.target.value })}
                >
                  <option value="all">Todos</option>
                  {correctionOptions.targetDocumentTypes.map((option) => (
                    <option key={option.id} title={option.label} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="grid min-w-0 gap-1 text-xs font-semibold text-slate-600">
                Efecto neto
                <select
                  className="h-10 min-w-0 truncate rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-950 outline-none focus:border-[var(--ui-color-info)] focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                  value={correctionFilters.netEffect ?? "all"}
                  onChange={(event) => onCorrectionChange({ netEffect: event.target.value })}
                >
                  <option value="all">Todos</option>
                  <option value="POSITIVE">Positivo</option>
                  <option value="NEGATIVE">Negativo</option>
                  <option value="NEUTRAL">Neutral</option>
                </select>
              </label>
            </>
          )}
        </div>
      </details>

      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => patchCommon(quickRange("today"))}
        >
          Hoy
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => patchCommon(quickRange("week"))}
        >
          Ultimos 7 dias
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => patchCommon(quickRange("month"))}
        >
          Este mes
        </button>
        <button
          className="rounded-full border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--ui-color-warning)] transition hover:border-amber-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => (isReturns ? onReturnChange({ status: "COMMITTED" }) : onCorrectionChange({ status: "COMMITTED" }))}
        >
          Confirmados
        </button>
        {!isReturns ? (
          <button
            className="rounded-full border border-rose-200 bg-[var(--ui-color-danger-soft)] px-3 py-1.5 text-xs font-semibold text-[var(--ui-color-danger)] transition hover:border-rose-300 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => onCorrectionChange({ netEffect: "NEGATIVE" })}
          >
            Con incidencias
          </button>
        ) : null}
      </div>
    </section>
  );
}
