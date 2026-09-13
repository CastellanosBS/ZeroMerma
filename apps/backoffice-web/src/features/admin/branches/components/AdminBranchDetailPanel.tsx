import { AdminActionButton } from "../../components/AdminActionButton";
import type { ReactNode } from "react";

import type { AdminBranchDetail, AdminBranchListItem, AdminBranchWarning } from "../types";

function formatStatus(status: "active" | "inactive"): string {
  return status === "active" ? "Activa" : "Inactiva";
}

function formatReadiness(
  value: AdminBranchDetail["overview"]["readiness"] | AdminBranchListItem["readiness"],
) {
  const labels = {
    inactive: "Inactiva",
    ready: "Lista para operar",
    warning: "Requiere revision",
  };

  return labels[value];
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Sin fecha";
  }

  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="grid min-w-0 grid-cols-[7rem_minmax(0,1fr)] gap-2 text-xs">
      <span
        className="truncate font-semibold uppercase tracking-[0.08em] text-slate-500"
        title={label}
      >
        {label}
      </span>
      <span
        className="min-w-0 truncate font-medium text-slate-900"
        title={String(value ?? "No registrado")}
      >
        {value ?? "No registrado"}
      </span>
    </div>
  );
}

function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-white p-3">
      <h4
        className="mb-2 truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500"
        title={title}
      >
        {title}
      </h4>
      {children}
    </div>
  );
}

function WarningItem({ warning }: { warning: AdminBranchWarning }) {
  const toneClass =
    warning.severity === "critical"
      ? "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
      : warning.severity === "warning"
        ? "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]"
        : "border-[var(--ui-color-border)] bg-slate-50 text-slate-600";

  return (
    <li
      className={`rounded-[14px] border px-3 py-2 text-xs leading-5 ${toneClass}`}
      title={warning.message}
    >
      <span className="font-semibold">{warning.code}</span>: {warning.message}
    </li>
  );
}

interface AdminBranchDetailPanelProps {
  branchDetail?: AdminBranchDetail | null;
  branchPreview?: AdminBranchListItem | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onEdit: (branch: AdminBranchDetail | AdminBranchListItem) => void;
  onToggleStatus: (branch: AdminBranchDetail | AdminBranchListItem) => void;
}

export function AdminBranchDetailPanel({
  branchDetail,
  branchPreview,
  errorMessage,
  isLoading = false,
  onEdit,
  onToggleStatus,
}: AdminBranchDetailPanelProps) {
  if (!branchPreview && !branchDetail) {
    return (
      <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
        <div className="border-b border-[var(--ui-color-border)] px-3 py-2.5">
          <h3 className="truncate text-base font-semibold text-slate-950">Detalle de sucursal</h3>
        </div>
        <div className="flex min-h-0 flex-1 items-center p-3">
          <div className="rounded-[18px] border border-dashed border-[var(--ui-color-border)] bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            <p className="font-semibold text-slate-950">Sin sucursal seleccionada</p>
            <p>
              Selecciona una sucursal para revisar su configuracion, estaciones asociadas y estado
              operativo.
            </p>
          </div>
        </div>
      </aside>
    );
  }

  const overview = branchDetail?.overview ?? branchPreview;
  if (!overview) {
    return null;
  }

  const warnings = branchDetail?.warnings ?? branchPreview?.warnings ?? [];

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-start justify-between gap-2 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950" title={overview.name}>
            {overview.name}
          </h3>
          <p
            className="truncate text-xs text-slate-500"
            title={`${overview.code} - ${overview.brandName}`}
          >
            {overview.code} - {overview.brandName}
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-2.5 py-1 text-xs font-semibold text-slate-600">
          {formatReadiness(overview.readiness)}
        </span>
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
        {isLoading ? (
          <div className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 p-3 text-sm text-slate-600">
            Cargando detalle de sucursal.
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
            <InfoRow label="Marca" value={overview.brandName} />
            <InfoRow label="Zona horaria" value={overview.timezone} />
            <InfoRow label="Actualizada" value={formatDate(overview.updatedAt)} />
          </div>
        </Section>

        {branchDetail ? (
          <>
            <Section title="Ubicacion y contacto">
              <div className="grid gap-1.5">
                <InfoRow label="Direccion" value={branchDetail.locationContact.addressLine} />
                <InfoRow label="Ciudad" value={branchDetail.locationContact.city} />
                <InfoRow label="Estado" value={branchDetail.locationContact.state} />
                <InfoRow label="Pais" value={branchDetail.locationContact.country} />
                <InfoRow label="Telefono" value={branchDetail.locationContact.phone} />
                <InfoRow label="Correo" value={branchDetail.locationContact.contactEmail} />
              </div>
            </Section>

            <Section title="Configuracion operativa">
              <div className="grid gap-1.5">
                <InfoRow
                  label="POS"
                  value={branchDetail.operationalConfig.posReady ? "Listo" : "No listo"}
                />
                <InfoRow
                  label="Inventario"
                  value={
                    branchDetail.operationalConfig.inventoryScopeReady ? "Preparado" : "No listo"
                  }
                />
                <InfoRow
                  label="Produccion"
                  value={
                    branchDetail.operationalConfig.productionScopeReady ? "Preparado" : "No listo"
                  }
                />
                <InfoRow
                  label="Cajas abiertas"
                  value={branchDetail.relatedOperationsSummary.openCashSessions}
                />
              </div>
            </Section>

            <Section title="Cajas / estaciones">
              {branchDetail.workstationsSummary.items.length > 0 ? (
                <div className="grid gap-1.5">
                  <InfoRow
                    label="Resumen"
                    value={`${branchDetail.workstationsSummary.active} activas / ${branchDetail.workstationsSummary.total} total`}
                  />
                  <div className="grid gap-1">
                    {branchDetail.workstationsSummary.items.slice(0, 5).map((workstation) => (
                      <div
                        className="flex min-w-0 items-center justify-between gap-2 rounded-[14px] bg-slate-50 px-2.5 py-2 text-xs"
                        key={workstation.id}
                      >
                        <span
                          className="min-w-0 truncate font-semibold text-slate-900"
                          title={workstation.name}
                        >
                          {workstation.name}
                        </span>
                        <span className="shrink-0 text-slate-500">
                          {workstation.isActive ? "Activa" : "Inactiva"}
                        </span>
                      </div>
                    ))}
                  </div>
                  <a
                    className="text-xs font-semibold text-[var(--ui-color-info)] underline-offset-2 hover:underline"
                    href={`/admin/cajas-estaciones?branchId=${branchDetail.overview.id}`}
                  >
                    Ver cajas / estaciones
                  </a>
                </div>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  Esta sucursal no tiene cajas o estaciones registradas.
                </p>
              )}
            </Section>

            <Section title="Usuarios asignados">
              {branchDetail.userAssignmentsSummary.items.length > 0 ? (
                <div className="grid gap-1.5">
                  <InfoRow
                    label="Resumen"
                    value={`${branchDetail.userAssignmentsSummary.active} activos / ${branchDetail.userAssignmentsSummary.total} total`}
                  />
                  {branchDetail.userAssignmentsSummary.items.slice(0, 5).map((assignment) => (
                    <div
                      className="min-w-0 rounded-[14px] bg-slate-50 px-2.5 py-2 text-xs"
                      key={assignment.assignmentId}
                    >
                      <p
                        className="truncate font-semibold text-slate-900"
                        title={assignment.userName}
                      >
                        {assignment.userName}
                      </p>
                      <p className="truncate text-slate-500" title={assignment.userEmail}>
                        {assignment.userEmail}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm leading-6 text-slate-600">
                  Esta sucursal no tiene usuarios asignados.
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
            <p className="text-sm leading-6 text-slate-600">
              Sin advertencias operativas detectadas.
            </p>
          )}
        </Section>
      </div>

      <div className="flex shrink-0 flex-wrap gap-2 border-t border-[var(--ui-color-border)] p-3 text-xs">
        <AdminActionButton
          capability="branches.manage"
          branchIds={[overview.id]}
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onEdit(branchDetail ?? branchPreview!)}
        >
          Editar
        </AdminActionButton>
        <AdminActionButton
          capability="branches.manage"
          branchIds={[overview.id]}
          className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-[var(--ui-color-info)] transition hover:bg-[var(--ui-color-surface-tint)] focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
          type="button"
          onClick={() => onToggleStatus(branchDetail ?? branchPreview!)}
        >
          {overview.status === "active" ? "Desactivar" : "Activar"}
        </AdminActionButton>
      </div>
    </aside>
  );
}
