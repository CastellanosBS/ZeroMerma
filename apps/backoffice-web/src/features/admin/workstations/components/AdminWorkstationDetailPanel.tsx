import type { ReactNode } from "react";

import type {
  AdminWorkstationDetail,
  AdminWorkstationListItem,
  AdminWorkstationWarning,
} from "../types";

function formatStatus(status: "active" | "inactive"): string {
  return status === "active" ? "Activa" : "Inactiva";
}

function formatReadiness(value: AdminWorkstationDetail["overview"]["readiness"] | AdminWorkstationListItem["readiness"]) {
  const labels = {
    blocked: "Bloqueada",
    ready: "Lista para POS",
    warning: "Requiere revision",
  };

  return labels[value];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin registro";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-2 text-xs">
      <span className="truncate font-semibold uppercase tracking-[0.08em] text-slate-500" title={label}>
        {label}
      </span>
      <span className="min-w-0 truncate font-medium text-slate-900" title={String(value ?? "No registrado")}>
        {value ?? "No registrado"}
      </span>
    </div>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4 className="mb-2 truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500" title={title}>
        {title}
      </h4>
      {children}
    </div>
  );
}

function WarningItem({ warning }: { warning: AdminWorkstationWarning }) {
  const toneClass =
    warning.severity === "critical"
      ? "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
      : warning.severity === "warning"
        ? "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
        : "border-[var(--ui-color-border)] bg-slate-50 text-slate-600";

  return (
    <li className={`rounded-[14px] border px-3 py-2 text-xs leading-5 ${toneClass}`} title={warning.message}>
      <span className="font-semibold">{warning.code}</span>: {warning.message}
    </li>
  );
}

interface AdminWorkstationDetailPanelProps {
  errorMessage?: string | null;
  isLoading?: boolean;
  onEdit: (workstation: AdminWorkstationDetail | AdminWorkstationListItem) => void;
  onOpenBranch: (branchId: string) => void;
  onToggleStatus: (workstation: AdminWorkstationDetail | AdminWorkstationListItem) => void;
  workstationDetail?: AdminWorkstationDetail | null;
  workstationPreview?: AdminWorkstationListItem | null;
}

export function AdminWorkstationDetailPanel({
  errorMessage,
  isLoading = false,
  onEdit,
  onOpenBranch,
  onToggleStatus,
  workstationDetail,
  workstationPreview,
}: AdminWorkstationDetailPanelProps) {
  if (!workstationPreview && !workstationDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-3 py-2.5">
          <h3 className="truncate text-base font-semibold text-slate-950">Detalle de estacion</h3>
        </div>
        <div className="flex min-h-0 flex-1 items-center p-3">
          <div className="rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p className="font-semibold text-slate-950">Sin estacion seleccionada</p>
            <p>Selecciona una estacion para revisar su sucursal, estado operativo y sesiones de caja.</p>
          </div>
        </div>
      </aside>
    );
  }

  const overview = workstationDetail?.overview ?? workstationPreview;
  if (!overview) {
    return null;
  }

  const branch = workstationDetail?.branchRelationship ?? workstationPreview;
  const warnings = workstationDetail?.warnings ?? workstationPreview?.warnings ?? [];
  const activeSession = workstationDetail?.cashSessionContext.activeSession ?? null;
  const lastClosedSession = workstationDetail?.cashSessionContext.lastClosedSession ?? null;
  const hasActiveSession = Boolean(activeSession) || Boolean(workstationPreview?.hasActiveCashSession);

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-start justify-between gap-2 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title={overview.name}>
            {overview.name}
          </h3>
          <p className="truncate font-mono text-xs text-slate-500" title={overview.code}>
            {overview.code}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
          {formatReadiness(overview.readiness)}
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
        {isLoading ? (
          <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-600">
            Cargando detalle de estacion.
          </div>
        ) : null}
        {errorMessage ? (
          <div className="rounded-[18px] border border-rose-200 bg-[var(--ui-color-danger-soft)] p-3 text-sm text-[var(--ui-color-danger)]">
            {errorMessage}
          </div>
        ) : null}

        <Section title="Resumen">
          <div className="grid gap-1.5">
            <InfoRow label="Estado" value={formatStatus(overview.status)} />
            <InfoRow label="Sucursal" value={branch?.branchName} />
            <InfoRow label="Codigo suc." value={branch?.branchCode} />
            <InfoRow label="Actualizada" value={formatDate(overview.updatedAt)} />
          </div>
        </Section>

        {workstationDetail ? (
          <>
            <Section title="Relacion con sucursal">
              <div className="grid gap-1.5">
                <InfoRow label="Sucursal" value={workstationDetail.branchRelationship.branchName} />
                <InfoRow label="Codigo" value={workstationDetail.branchRelationship.branchCode} />
                <InfoRow label="Zona" value={workstationDetail.branchRelationship.branchTimezone} />
                <InfoRow
                  label="Estado"
                  value={workstationDetail.branchRelationship.branchIsActive ? "Activa" : "Inactiva"}
                />
                <button
                  className="mt-1 justify-self-start rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                  type="button"
                  onClick={() => onOpenBranch(workstationDetail.branchRelationship.branchId)}
                >
                  Abrir sucursal
                </button>
              </div>
            </Section>

            <Section title="Configuracion operativa">
              <div className="grid gap-1.5">
                <InfoRow label="Activa" value={workstationDetail.operationalConfig.isActive ? "Si" : "No"} />
                <InfoRow label="POS" value={workstationDetail.operationalConfig.posEnabled ? "Habilitado" : "No listo"} />
                <InfoRow label="Codigo" value={workstationDetail.overview.code} />
              </div>
            </Section>

            <Section title="Sesion de caja">
              {activeSession ? (
                <div className="grid gap-1.5">
                  <InfoRow label="Estado" value={activeSession.status} />
                  <InfoRow label="Apertura" value={formatDate(activeSession.openedAt)} />
                  <InfoRow label="Usuario" value={activeSession.openedByUserName} />
                  <InfoRow label="Monto inicial" value={activeSession.openingAmount} />
                </div>
              ) : (
                <p className="text-sm leading-6 text-slate-600">Esta estacion no tiene una caja abierta actualmente.</p>
              )}
              {lastClosedSession ? (
                <div className="mt-2 rounded-[14px] bg-slate-50 px-2.5 py-2 text-xs text-slate-600">
                  Ultimo cierre: {formatDate(lastClosedSession.closedAt)}
                </div>
              ) : null}
            </Section>

            <Section title="Acceso por sucursal">
              {workstationDetail.accessContext.users.length > 0 ? (
                <div className="grid gap-1.5">
                  <InfoRow
                    label="Usuarios"
                    value={`${workstationDetail.accessContext.activeAssignedUserCount} activos / ${workstationDetail.accessContext.assignedUserCount} total`}
                  />
                  {workstationDetail.accessContext.users.slice(0, 5).map((user) => (
                    <div className="min-w-0 rounded-[14px] bg-slate-50 px-2.5 py-2 text-xs" key={user.userId}>
                      <p className="truncate font-semibold text-slate-900" title={user.userName}>
                        {user.userName}
                      </p>
                      <p className="truncate text-slate-500" title={user.userEmail}>
                        {user.userEmail}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  La sucursal no tiene usuarios asignados para operar esta estacion.
                </p>
              )}
            </Section>
          </>
        ) : null}

        <Section title="Advertencias operativas">
          {warnings.length > 0 ? (
            <ul className="grid gap-1.5">
              {warnings.map((warning) => (
                <WarningItem key={warning.code} warning={warning} />
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-6 text-slate-600">Sin advertencias operativas detectadas.</p>
          )}
        </Section>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] p-3 text-xs">
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onEdit(workstationDetail ?? workstationPreview!)}
        >
          Editar
        </button>
        <button
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)] disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
          disabled={overview.status === "active" && hasActiveSession}
          type="button"
          onClick={() => onToggleStatus(workstationDetail ?? workstationPreview!)}
        >
          {overview.status === "active" ? "Desactivar" : "Activar"}
        </button>
      </div>
    </aside>
  );
}
