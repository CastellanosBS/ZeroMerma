import { AdminEmptyState } from "../../components/AdminEmptyState";
import { AdminRowActionsMenu } from "../../components/AdminRowActionsMenu";
import type { AdminUserListItem } from "../types";

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
  const labels: Record<string, string> = {
    active: "Activo",
    inactive: "Inactivo",
    locked: "Bloqueado",
  };
  return labels[value] ?? value;
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
  if (value === "locked" || value === "blocked") {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
}

interface AdminUsersTableProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyEmail: (item: AdminUserListItem) => void;
  onEdit: (item: AdminUserListItem) => void;
  onPageChange: (page: number) => void;
  onSelectUser: (item: AdminUserListItem) => void;
  page: number;
  pageSize: number;
  selectedUserId?: string | null;
  total: number;
  users: AdminUserListItem[];
}

export function AdminUsersTable({
  errorMessage,
  isLoading = false,
  onCopyEmail,
  onEdit,
  onPageChange,
  onSelectUser,
  page,
  pageSize,
  selectedUserId,
  total,
  users,
}: AdminUsersTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Usuarios</h3>
          <p className="truncate text-xs text-slate-500">
            Acceso, sucursales, roles, ultimo acceso, advertencias y acciones seguras.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando usuarios persistidos en backend."
            title="Cargando usuarios"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar usuarios" />
        ) : users.length > 0 ? (
          <div className="min-w-[84rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[12rem_15rem_8rem_10rem_13rem_10rem_10rem_9rem_10rem_10rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Nombre</span>
              <span>Correo</span>
              <span>Estado</span>
              <span>Acceso</span>
              <span>Sucursales</span>
              <span>Roles</span>
              <span>Ultimo acceso</span>
              <span>Creado</span>
              <span>Advertencias</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {users.map((item) => {
                const isSelected = item.id === selectedUserId;
                return (
                  <article
                    className={[
                      "grid grid-cols-[12rem_15rem_8rem_10rem_13rem_10rem_10rem_9rem_10rem_10rem] items-center px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={item.fullName}
                      type="button"
                      onClick={() => onSelectUser(item)}
                    >
                      {item.fullName}
                    </button>
                    <span className="truncate text-slate-700" title={item.email}>
                      {item.email}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.status,
                      )}`}
                    >
                      <span className="truncate">{statusLabel(item.status)}</span>
                    </span>
                    <span className="truncate font-semibold text-slate-700">
                      {accessLabel(item.allowedSurfaces)}
                    </span>
                    <span
                      className="truncate text-slate-700"
                      title={item.branchNames.join(", ") || "Sin sucursal"}
                    >
                      {item.branchNames.length > 0 ? item.branchNames.join(", ") : "Sin sucursal"}
                    </span>
                    <span
                      className="truncate text-slate-700"
                      title={item.roleNames.join(", ") || "Sin roles"}
                    >
                      {item.roleCount > 0 ? item.roleNames.join(", ") : "Sin roles"}
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.lastLoginAt)}
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.createdAt)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.warningState,
                      )}`}
                      title={item.warnings.map((warning) => warning.message).join(" | ")}
                    >
                      <span className="truncate">
                        {item.warnings.length > 0 ? `${item.warnings.length} alertas` : "Sin alertas"}
                      </span>
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectUser(item)}
                      >
                        Ver
                      </button>
                      <AdminRowActionsMenu
                        actions={[
                          { label: "Editar", onSelect: () => onEdit(item) },
                          { label: "Copiar correo", onSelect: () => onCopyEmail(item) },
                        ]}
                        label={`Acciones para ${item.email}`}
                      />
                    </div>
                  </article>
                );
              })}
            </div>
          </div>
        ) : (
          <AdminEmptyState
            description="No hay usuarios registrados para los filtros seleccionados."
            title="Sin usuarios"
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
