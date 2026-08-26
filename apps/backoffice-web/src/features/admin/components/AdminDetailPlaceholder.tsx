import type { AdminModuleDefinition } from "../adminTypes";

export function AdminDetailPlaceholder({ module }: { module: AdminModuleDefinition }) {
  return (
    <aside className="min-w-0 overflow-hidden rounded-[22px] border border-[var(--ui-color-border)] bg-[var(--ui-color-surface-muted)] p-3">
      <div className="flex min-w-0 items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Detalle</p>
          <h3 className="mt-1 truncate text-base font-semibold text-slate-950" title={module.detailTitle}>
            {module.detailTitle}
          </h3>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          Sin selección
        </span>
      </div>

      <div className="mt-3 rounded-2xl border border-dashed border-[var(--ui-color-border)] bg-white px-3 py-3">
        <p className="text-sm font-semibold text-slate-950">Selecciona un registro</p>
        <p className="mt-1 text-sm leading-5 text-slate-600">
          Aquí se mostrará el detalle operativo, historial y auditoría del registro seleccionado.
        </p>
      </div>

      <dl className="mt-3 grid min-w-0 gap-2 rounded-2xl bg-white px-3 py-3 text-sm">
        <div className="min-w-0">
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Entidad</dt>
          <dd className="mt-1 truncate font-semibold text-slate-950" title={module.auditEntityType}>
            {module.auditEntityType}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Permisos</dt>
          <dd className="mt-1 truncate text-slate-700" title={module.permissionActions.join(", ")}>
            {module.permissionActions.length} acciones previstas
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">Auditoría</dt>
          <dd className="mt-1 text-slate-700">Preparada para actor, sucursal, entidad, acción y metadata.</dd>
        </div>
      </dl>
    </aside>
  );
}
