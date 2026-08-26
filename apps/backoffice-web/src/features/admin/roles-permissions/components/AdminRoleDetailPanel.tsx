import { useState, type ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminUserListItem } from "../../users/types";
import type { AdminRoleDetail, AdminRoleListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string): string {
  return value === "active" ? "Activo" : "Inactivo";
}

function surfaceLabel(values: string[]): string {
  if (values.includes("POS") && values.includes("BACKOFFICE")) {
    return "POS y Backoffice";
  }
  if (values.includes("BACKOFFICE")) {
    return "Backoffice";
  }
  if (values.includes("POS")) {
    return "POS";
  }
  return "Sin acceso";
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="text-sm font-semibold text-slate-950">{title}</h4>
      <div className="mt-2 min-w-0">{children}</div>
    </section>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0">
      <span className="block truncate text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
        {label}
      </span>
      <span className="mt-0.5 block min-w-0 truncate text-sm font-semibold text-slate-950">
        {value}
      </span>
    </div>
  );
}

interface AdminRoleDetailPanelProps {
  detail: AdminRoleDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onActivate: (item: AdminRoleListItem) => void;
  onAssignUser: (roleId: string, userId: string) => void;
  onCopyRole: (item: AdminRoleListItem | string) => void;
  onDeactivate: (item: AdminRoleListItem) => void;
  onEdit: (item: AdminRoleListItem) => void;
  onRemoveUser: (roleId: string, userId: string) => void;
  selectedRole: AdminRoleListItem | null;
  users: AdminUserListItem[];
}

export function AdminRoleDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onActivate,
  onAssignUser,
  onCopyRole,
  onDeactivate,
  onEdit,
  onRemoveUser,
  selectedRole,
  users,
}: AdminRoleDetailPanelProps) {
  const [userToAssign, setUserToAssign] = useState("");

  if (!selectedRole) {
    return (
      <AdminEmptyState
        description="Selecciona un rol para revisar permisos, usuarios asignados y alcance operativo."
        title="Sin rol seleccionado"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando permisos, usuarios asignados, advertencias y auditoria."
        title="Cargando rol"
      />
    );
  }

  if (errorMessage) {
    return <AdminEmptyState description={errorMessage} title="No se pudo cargar el rol" />;
  }

  if (!detail) {
    return (
      <AdminEmptyState
        description="Selecciona un rol para revisar permisos, usuarios asignados y alcance operativo."
        title="Sin rol seleccionado"
      />
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de rol
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.name}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.overview.code}</p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
              {statusLabel(detail.overview.status)}
            </span>
            {detail.overview.isSystem ? (
              <span className="rounded-full border border-slate-200 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                Sistema
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="ID" value={detail.overview.id} />
            <Fact label="Codigo" value={detail.overview.code} />
            <Fact label="Estado" value={statusLabel(detail.overview.status)} />
            <Fact label="Acceso" value={surfaceLabel(detail.overview.surfaces)} />
            <Fact label="Alto privilegio" value={detail.overview.isHighPrivilege ? "Si" : "No"} />
            <Fact label="Sistema" value={detail.overview.isSystem ? "Si" : "No"} />
            <Fact label="Creado" value={formatDateTime(detail.overview.createdAt)} />
            <Fact label="Actualizado" value={formatDateTime(detail.overview.updatedAt)} />
          </div>
        </Section>

        <Section title="Superficies de acceso">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="POS" value={detail.accessSurfaces.posEnabled ? "Habilitado" : "Sin acceso"} />
            <Fact
              label="Backoffice"
              value={detail.accessSurfaces.backofficeEnabled ? "Habilitado" : "Sin acceso"}
            />
            <Fact label="Ambos" value={detail.accessSurfaces.grantsBothSurfaces ? "Si" : "No"} />
            <Fact label="Nota" value={detail.accessSurfaces.note} />
          </div>
        </Section>

        <Section title="Matriz de permisos">
          {detail.permissionMatrix.some((group) =>
            group.permissions.some((permission) => permission.isEnabled),
          ) ? (
            <div className="grid gap-2">
              {detail.permissionMatrix.map((group) => {
                const enabledPermissions = group.permissions.filter((permission) => permission.isEnabled);
                if (enabledPermissions.length === 0) {
                  return null;
                }
                return (
                  <div
                    className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2"
                    key={group.module}
                  >
                    <p className="text-sm font-semibold text-slate-950">{group.label}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {enabledPermissions.map((permission) => (
                        <span
                          className={`rounded-full border px-2 py-1 text-xs font-semibold ${
                            permission.isSensitive
                              ? "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
                              : "border-[var(--ui-color-border)] bg-white text-slate-700"
                          }`}
                          key={permission.code}
                          title={permission.description ?? permission.code}
                        >
                          {permission.label}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este rol no tiene permisos asignados.
            </p>
          )}
        </Section>

        <Section title="Permisos sensibles">
          {detail.sensitivePermissions.length > 0 ? (
            <div className="grid gap-2">
              {detail.sensitivePermissions.map((permission) => (
                <div
                  className="rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2"
                  key={permission.code}
                >
                  <p className="truncate text-sm font-semibold text-[var(--ui-color-warning)]">
                    {permission.label}
                  </p>
                  <p className="mt-1 text-xs text-slate-600">{permission.description}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este rol no tiene permisos sensibles.
            </p>
          )}
        </Section>

        <Section title="Alcance">
          <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
            {detail.scopes.scopeSummary}{" "}
            {!detail.scopes.isSupported ? detail.scopes.missingContractNote : null}
          </p>
        </Section>

        <Section title="Usuarios asignados">
          {detail.availableActions.canAssignUsers ? (
            <div className="mb-2 flex min-w-0 flex-wrap gap-2">
              <select
                className="h-9 min-w-0 rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 text-sm font-semibold text-slate-700"
                value={userToAssign}
                onChange={(event) => setUserToAssign(event.target.value)}
              >
                <option value="">Seleccionar usuario</option>
                {users
                  .filter(
                    (user) =>
                      !detail.assignedUsers.some((assigned) => assigned.userId === user.id),
                  )
                  .map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.fullName} · {user.email}
                    </option>
                  ))}
              </select>
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
                disabled={!userToAssign}
                type="button"
                onClick={() => {
                  onAssignUser(detail.overview.id, userToAssign);
                  setUserToAssign("");
                }}
              >
                Asignar usuario
              </button>
            </div>
          ) : null}
          {detail.assignedUsers.length > 0 ? (
            <div className="grid gap-2">
              {detail.assignedUsers.map((user) => (
                <div className="rounded-[14px] bg-slate-50 px-3 py-2" key={user.userId}>
                  <div className="flex min-w-0 items-start justify-between gap-2">
                    <p className="truncate text-sm font-semibold text-slate-950">{user.fullName}</p>
                    <button
                      className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={!detail.availableActions.canRemoveUsers}
                      type="button"
                      onClick={() => onRemoveUser(detail.overview.id, user.userId)}
                    >
                      Quitar
                    </button>
                  </div>
                  <p className="truncate text-xs text-slate-500">
                    {user.email} · {user.status} · {surfaceLabel(user.surfaces)}
                  </p>
                  <p className="truncate text-xs text-slate-500">{user.branchSummary}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este rol no tiene usuarios asignados.
            </p>
          )}
        </Section>

        <Section title="Auditoria / historial">
          {detail.auditHistory.length > 0 ? (
            <div className="grid gap-2">
              {detail.auditHistory.map((event) => (
                <div className="rounded-[14px] bg-slate-50 px-3 py-2" key={event.id}>
                  <p className="truncate text-sm font-semibold text-slate-950">{event.action}</p>
                  <p className="truncate text-xs text-slate-500">
                    {formatDateTime(event.occurredAt)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              No hay eventos de auditoria disponibles para este rol.
            </p>
          )}
        </Section>

        <Section title="Acciones disponibles">
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canEdit}
              type="button"
              onClick={() => onEdit(detail.overview)}
            >
              Editar
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canDeactivate}
              type="button"
              onClick={() => onDeactivate(detail.overview)}
            >
              Desactivar
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canActivate}
              type="button"
              onClick={() => onActivate(detail.overview)}
            >
              Activar
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={() => onCopyRole(detail.overview)}
            >
              Copiar codigo
            </button>
          </div>
        </Section>
      </div>
    </aside>
  );
}
