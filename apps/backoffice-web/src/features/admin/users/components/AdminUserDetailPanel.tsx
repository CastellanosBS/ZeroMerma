import { AdminActionButton } from "../../components/AdminActionButton";
import type { ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminUserDetail, AdminUserListItem } from "../types";

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
  const labels: Record<string, string> = {
    active: "Activo",
    inactive: "Inactivo",
    locked: "Bloqueado",
  };
  return labels[value] ?? value;
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

interface AdminUserDetailPanelProps {
  detail: AdminUserDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onActivate: (item: AdminUserListItem) => void;
  onCopyEmail: (item: AdminUserListItem | string) => void;
  onDeactivate: (item: AdminUserListItem) => void;
  onEdit: (item: AdminUserListItem) => void;
  onLock: (item: AdminUserListItem) => void;
  onUnlock: (item: AdminUserListItem) => void;
  selectedUser: AdminUserListItem | null;
}

export function AdminUserDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onActivate,
  onCopyEmail,
  onDeactivate,
  onEdit,
  onLock,
  onUnlock,
  selectedUser,
}: AdminUserDetailPanelProps) {
  if (!selectedUser) {
    return (
      <AdminEmptyState
        description="Selecciona un usuario para revisar acceso, sucursales, roles y estado de cuenta."
        title="Sin usuario seleccionado"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando acceso, sucursales, seguridad, actividad y auditoria."
        title="Cargando usuario"
      />
    );
  }

  if (errorMessage) {
    return <AdminEmptyState description={errorMessage} title="No se pudo cargar el usuario" />;
  }

  if (!detail) {
    return (
      <AdminEmptyState
        description="Selecciona un usuario para revisar acceso, sucursales, roles y estado de cuenta."
        title="Sin usuario seleccionado"
      />
    );
  }

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de usuario
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.fullName}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.overview.email}</p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
            {statusLabel(detail.overview.status)}
          </span>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="ID" value={detail.overview.id} />
            <Fact label="Estado" value={statusLabel(detail.overview.status)} />
            <Fact label="Acceso" value={surfaceLabel(detail.overview.allowedSurfaces)} />
            <Fact label="Inicio predeterminado" value={detail.overview.defaultSurface} />
            <Fact label="Creado" value={formatDateTime(detail.overview.createdAt)} />
            <Fact label="Actualizado" value={formatDateTime(detail.overview.updatedAt)} />
            <Fact label="Ultimo acceso" value={formatDateTime(detail.overview.lastLoginAt)} />
            <Fact label="Advertencias" value={detail.warnings.length} />
          </div>
        </Section>

        <Section title="Identidad / perfil">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Nombre" value={detail.profile.fullName} />
            <Fact label="Correo" value={detail.profile.email} />
            <Fact label="Telefono" value={detail.profile.phone ?? "No registrado"} />
            <Fact label="Nombre visible" value={detail.profile.displayName ?? "No soportado"} />
            <Fact label="Codigo empleado" value={detail.profile.employeeCode ?? "No soportado"} />
            <Fact label="Notas" value={detail.profile.notes ?? "Sin notas"} />
          </div>
        </Section>

        <Section title="Estado de cuenta">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Activo" value={detail.accountStatus.isActive ? "Si" : "No"} />
            <Fact label="Bloqueado" value={detail.accountStatus.isLocked ? "Si" : "No"} />
            <Fact label="Motivo bloqueo" value={detail.accountStatus.lockReason ?? "Sin motivo"} />
            <Fact
              label="Restablecer contrasena"
              value={detail.accountStatus.passwordResetRequired ? "Requerido" : "No requerido"}
            />
            <Fact
              label="Intentos fallidos"
              value={detail.accountStatus.failedLoginCount ?? "No soportado"}
            />
            <Fact
              label="Sesiones activas"
              value={
                detail.accountStatus.activeSessionsSupported
                  ? (detail.accountStatus.activeSessionsCount ?? 0)
                  : "Este usuario no tiene sesiones activas registradas."
              }
            />
          </div>
        </Section>

        <Section title="Acceso a aplicaciones">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="POS" value={detail.appAccess.posEnabled ? "Habilitado" : "Sin acceso"} />
            <Fact
              label="Backoffice"
              value={detail.appAccess.backofficeEnabled ? "Habilitado" : "Sin acceso"}
            />
            <Fact label="Ambos" value={detail.appAccess.hasBothSurfaces ? "Si" : "No"} />
            <Fact label="Inicio predeterminado" value={detail.appAccess.defaultSurface} />
          </div>
        </Section>

        <Section title="Sucursales asignadas">
          {detail.branchAssignments.length > 0 ? (
            <div className="grid gap-2">
              {detail.branchAssignments.map((assignment) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2"
                  key={assignment.assignmentId}
                >
                  <div className="flex min-w-0 items-center justify-between gap-2">
                    <span className="truncate text-sm font-semibold text-slate-950">
                      {assignment.branchName} ({assignment.branchCode})
                    </span>
                    <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-600">
                      {assignment.isDefault
                        ? "Predeterminada"
                        : assignment.isActive
                          ? "Activa"
                          : "Inactiva"}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-xs text-slate-500">
                    Asignada {formatDateTime(assignment.assignedAt)}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este usuario no tiene sucursales asignadas.
            </p>
          )}
        </Section>

        <Section title="Roles asignados">
          {detail.roleAssignments.items.length > 0 ? (
            <div className="grid gap-2">
              {detail.roleAssignments.items.map((role) => (
                <Fact
                  key={role.roleId}
                  label={role.roleName}
                  value={
                    role.scopeType === "GLOBAL"
                      ? "Global explícito"
                      : `${role.branchIds.length} sucursales`
                  }
                />
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este usuario no tiene roles asignados. {detail.roleAssignments.missingContractNote}
            </p>
          )}
        </Section>

        <Section title="Acciones de seguridad">
          <div className="flex flex-wrap gap-2">
            <AdminActionButton
              capability="users.manage"
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.securityActions.canLock}
              type="button"
              onClick={() => onLock(detail.overview)}
            >
              Bloquear
            </AdminActionButton>
            <AdminActionButton
              capability="users.manage"
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.securityActions.canUnlock}
              type="button"
              onClick={() => onUnlock(detail.overview)}
            >
              Desbloquear
            </AdminActionButton>
            <AdminActionButton
              capability="users.manage"
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.securityActions.canDeactivate}
              type="button"
              onClick={() => onDeactivate(detail.overview)}
            >
              Desactivar
            </AdminActionButton>
            <AdminActionButton
              capability="users.manage"
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.securityActions.canActivate}
              type="button"
              onClick={() => onActivate(detail.overview)}
            >
              Activar
            </AdminActionButton>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Restablecimiento, invitaciones y revocacion de sesiones no estan soportados por el
            contrato actual.
          </p>
        </Section>

        <Section title="Contexto operativo">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Cajas abiertas" value={detail.operationalContext.openCashSessionsCount} />
            <Fact label="Actividad POS" value={detail.operationalContext.recentPosActivityCount} />
            <Fact
              label="Actividad Backoffice"
              value={detail.operationalContext.recentBackofficeActivityCount}
            />
            <Fact
              label="Ultima estacion"
              value={detail.operationalContext.lastWorkstationUsed ?? "No disponible"}
            />
            <Fact
              label="Sucursales recientes"
              value={
                detail.operationalContext.recentlyOperatedBranches.length > 0
                  ? detail.operationalContext.recentlyOperatedBranches.join(", ")
                  : "Sin actividad registrada"
              }
            />
          </div>
        </Section>

        <Section title="Auditoria / timeline">
          {detail.auditTimeline.length > 0 ? (
            <div className="grid gap-2">
              {detail.auditTimeline.map((event) => (
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
              No hay eventos de auditoria disponibles para este usuario.
            </p>
          )}
        </Section>

        <Section title="Acciones disponibles">
          <div className="flex flex-wrap gap-2">
            <AdminActionButton
              capability="users.manage"
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              disabled={!detail.availableActions.canEditProfile}
              onClick={() => onEdit(detail.overview)}
            >
              Editar
            </AdminActionButton>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={() => onCopyEmail(detail.overview)}
            >
              Copiar correo
            </button>
          </div>
        </Section>
      </div>
    </aside>
  );
}
