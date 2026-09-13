import { AdminActionButton } from "../../components/AdminActionButton";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminRoleListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  return value === "active" ? "Activo" : "Inactivo";
}

function accessLabel(values: string[]): string {
  if (values.includes("POS") && values.includes("BACKOFFICE")) {
    return "POS + Backoffice";
  }
  if (values.includes("BACKOFFICE")) {
    return "Backoffice";
  }
  if (values.includes("POS")) {
    return "POS";
  }
  return "Sin acceso";
}

function badgeClass(value: string): string {
  if (value === "active" || value === "ready") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (value === "blocked" || value === "high") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

interface AdminRolesPermissionsTableProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyRole: (item: AdminRoleListItem) => void;
  onEdit: (item: AdminRoleListItem) => void;
  onPageChange: (page: number) => void;
  onSelectRole: (item: AdminRoleListItem) => void;
  page: number;
  pageSize: number;
  roles: AdminRoleListItem[];
  selectedRoleId?: string | null;
  total: number;
}

export function AdminRolesPermissionsTable({
  errorMessage,
  isLoading = false,
  onCopyRole,
  onEdit,
  onPageChange,
  onSelectRole,
  page,
  pageSize,
  roles,
  selectedRoleId,
  total,
}: AdminRolesPermissionsTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Roles</h3>
          <p className="truncate text-xs text-slate-500">
            Permisos, usuarios asignados, superficie, alcance, riesgo y advertencias.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando roles y permisos persistidos en backend."
            title="Cargando roles"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar roles" />
        ) : roles.length > 0 ? (
          <div className="min-w-[82rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[12rem_16rem_8rem_10rem_8rem_10rem_11rem_8rem_10rem_10rem_9rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Rol</span>
              <span>Descripcion</span>
              <span>Estado</span>
              <span>Acceso</span>
              <span>Permisos</span>
              <span>Usuarios</span>
              <span>Alcance</span>
              <span>Riesgo</span>
              <span>Actualizado</span>
              <span>Advertencias</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {roles.map((item) => {
                const isSelected = item.id === selectedRoleId;
                return (
                  <article
                    className={[
                      "grid grid-cols-[12rem_16rem_8rem_10rem_8rem_10rem_11rem_8rem_10rem_10rem_9rem] items-center px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={`${item.name} (${item.code})`}
                      type="button"
                      onClick={() => onSelectRole(item)}
                    >
                      {item.name}
                    </button>
                    <span className="truncate text-slate-700" title={item.description ?? ""}>
                      {item.description ?? "Sin descripcion"}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.status,
                      )}`}
                    >
                      <span className="truncate">{statusLabel(item.status)}</span>
                    </span>
                    <span className="truncate font-semibold text-slate-700">
                      {accessLabel(item.surfaces)}
                    </span>
                    <span className="truncate text-slate-700">{item.permissionCount}</span>
                    <span className="truncate text-slate-700">{item.assignedUserCount}</span>
                    <span className="truncate text-slate-700" title={item.scopeSummary}>
                      {item.scopeSummary}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${
                        item.isHighPrivilege ? badgeClass("high") : badgeClass("ready")
                      }`}
                    >
                      <span className="truncate">{item.isHighPrivilege ? "Alto" : "Normal"}</span>
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.updatedAt)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.warningState,
                      )}`}
                      title={item.warnings.map((warning) => warning.message).join(" | ")}
                    >
                      <span className="truncate">
                        {item.warnings.length > 0
                          ? `${item.warnings.length} alertas`
                          : "Sin alertas"}
                      </span>
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectRole(item)}
                      >
                        Ver
                      </button>
                      <AdminActionButton
                        capability="roles.manage"
                        globalOnly
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] disabled:opacity-40"
                        disabled={item.isSystem}
                        type="button"
                        onClick={() => onEdit(item)}
                      >
                        Editar
                      </AdminActionButton>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onCopyRole(item)}
                      >
                        Copiar
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        ) : (
          <AdminEmptyState
            description="No hay roles registrados para los filtros seleccionados."
            title="Sin roles"
          />
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-[var(--ui-color-border)] px-3 py-2">
        <span className="text-xs font-semibold text-slate-500">
          Pagina {page} de {totalPages}
        </span>
        <div className="flex gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoNext}
            type="button"
            onClick={() => onPageChange(page + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
    </section>
  );
}
