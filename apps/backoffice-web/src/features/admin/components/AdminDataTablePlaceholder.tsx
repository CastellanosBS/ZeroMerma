import { AdminEmptyState } from "./AdminEmptyState";
import type { AdminModuleRecord } from "../adminData";
import type { AdminModuleDefinition } from "../adminTypes";

export function AdminDataTablePlaceholder({
  module,
  records,
}: {
  module: AdminModuleDefinition;
  records: AdminModuleRecord[];
}) {
  const tableMinWidth = Math.max(760, module.tableColumns.length * 150);

  return (
    <div className="min-h-0 min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-4 py-3">
        <h3 className="min-w-0 truncate text-sm font-semibold text-slate-950">Tabla principal</h3>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {records.length} registros
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left text-sm" style={{ minWidth: tableMinWidth }}>
          <thead className="bg-slate-50 text-[0.68rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
            <tr>
              {module.tableColumns.map((column) => (
                <th key={column.key} className="px-4 py-3">
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td className="px-4 py-4" colSpan={module.tableColumns.length}>
                  <AdminEmptyState description={module.emptyDescription} title="Sin datos todavía" />
                </td>
              </tr>
            ) : (
              records.map((record) => (
                <tr key={record.id} className="border-t border-[var(--ui-color-border)] transition hover:bg-slate-50">
                  {module.tableColumns.map((column) => {
                    const value = record.values[column.key] ?? "--";

                    return (
                      <td key={column.key} className="max-w-[16rem] px-4 py-3">
                        <span className="block truncate" title={String(value)}>
                          {value}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
