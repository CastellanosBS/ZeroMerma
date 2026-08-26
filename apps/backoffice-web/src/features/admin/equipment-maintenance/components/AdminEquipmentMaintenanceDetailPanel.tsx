import type { ReactNode } from "react";

import { AdminEmptyState } from "../../components/AdminEmptyState";
import { formatEquipmentMoney } from "../api";
import type {
  AdminEquipmentDetail,
  AdminEquipmentListItem,
  AdminMaintenanceRecordListItem,
} from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusLabel(value: string | null | undefined): string {
  const labels: Record<string, string> = {
    CANCELLED: "Cancelado",
    COMPLETED: "Completado",
    COMPLETED_SUCCESSFULLY: "Completado",
    COMPLETED_WITH_OBSERVATIONS: "Con observaciones",
    FAILED: "Fallido",
    INACTIVE: "Inactivo",
    IN_PROGRESS: "En proceso",
    NO_HISTORY: "Sin historial",
    NOT_COMPLETED: "Sin completar",
    OK: "Al dia",
    OPERATIONAL: "Operativo",
    OUT_OF_SERVICE: "Fuera de servicio",
    OVERDUE: "Vencido",
    PENDING: "Pendiente",
    REQUIRES_FOLLOW_UP: "Requiere seguimiento",
    RETIRED: "Retirado",
    SCHEDULED: "Programado",
    UNDER_MAINTENANCE: "En mantenimiento",
  };
  return value ? labels[value] ?? value : "No disponible";
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

function MaintenanceRow({ record }: { record: AdminMaintenanceRecordListItem }) {
  return (
    <article className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 sm:grid-cols-[7rem_7rem_minmax(0,1fr)_7rem_7rem]">
      <span className="truncate font-semibold text-slate-950">{record.folio}</span>
      <span className="truncate text-slate-700">{record.maintenanceType}</span>
      <span className="truncate text-slate-700">
        {record.providerName ?? record.technicianName ?? "Sin tecnico/proveedor"}
      </span>
      <span className="truncate text-slate-700">{formatEquipmentMoney(record.cost)}</span>
      <span className="truncate text-slate-700">{statusLabel(record.result)}</span>
      {record.notes ? (
        <p className="sm:col-span-5 rounded-[12px] bg-white px-2 py-1 text-xs text-slate-600">
          {record.notes}
        </p>
      ) : null}
    </article>
  );
}

interface AdminEquipmentMaintenanceDetailPanelProps {
  detail: AdminEquipmentDetail | null;
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyCode: (item: AdminEquipmentListItem | string) => void;
  onCreateMaintenance: (item: AdminEquipmentListItem) => void;
  onMarkOperational: (item: AdminEquipmentListItem) => void;
  onMarkOutOfService: (item: AdminEquipmentListItem) => void;
  onStartMaintenance: (record: AdminMaintenanceRecordListItem) => void;
  onCompleteMaintenance: (record: AdminMaintenanceRecordListItem) => void;
  selectedEquipment: AdminEquipmentListItem | null;
}

export function AdminEquipmentMaintenanceDetailPanel({
  detail,
  errorMessage,
  isLoading = false,
  onCompleteMaintenance,
  onCopyCode,
  onCreateMaintenance,
  onMarkOperational,
  onMarkOutOfService,
  onStartMaintenance,
  selectedEquipment,
}: AdminEquipmentMaintenanceDetailPanelProps) {
  if (!selectedEquipment) {
    return (
      <AdminEmptyState
        description="Selecciona un equipo para revisar mantenimiento, incidencias, estado operativo y documentos relacionados."
        title="Sin equipo seleccionado"
      />
    );
  }

  if (isLoading) {
    return (
      <AdminEmptyState
        description="Consultando detalle, historial, evidencia, costos y acciones permitidas."
        title="Cargando detalle"
      />
    );
  }

  if (errorMessage) {
    return <AdminEmptyState description={errorMessage} title="No se pudo cargar el detalle" />;
  }

  if (!detail) {
    return (
      <AdminEmptyState
        description="Selecciona un equipo para revisar mantenimiento, incidencias, estado operativo y documentos relacionados."
        title="Sin equipo seleccionado"
      />
    );
  }

  const openRecord = detail.currentMaintenanceStatus.currentOpenMaintenance;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-slate-50/70">
      <div className="shrink-0 border-b border-[var(--ui-color-border)] bg-white px-3 py-3">
        <div className="flex min-w-0 items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold uppercase tracking-[0.12em] text-slate-500">
              Detalle de equipo
            </p>
            <h3 className="mt-1 truncate text-lg font-semibold text-slate-950">
              {detail.overview.name}
            </h3>
            <p className="mt-1 truncate text-sm text-slate-600">{detail.overview.code}</p>
          </div>
          <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-700">
            {statusLabel(detail.overview.operationalStatus)}
          </span>
        </div>
      </div>

      <div className="grid min-h-0 gap-2 overflow-y-auto p-2.5">
        <Section title="Resumen del equipo">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Codigo" value={detail.overview.code} />
            <Fact label="Equipo" value={detail.overview.name} />
            <Fact label="Tipo" value={detail.overview.equipmentType} />
            <Fact label="Sucursal" value={detail.overview.branchName} />
            <Fact label="Estado" value={statusLabel(detail.overview.operationalStatus)} />
            <Fact label="Riesgo" value={detail.overview.riskLevel} />
            <Fact label="Creado" value={formatDateTime(detail.overview.createdAt)} />
            <Fact label="Actualizado" value={formatDateTime(detail.overview.updatedAt)} />
          </div>
        </Section>

        <Section title="Ubicacion / contexto operativo">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact
              label="Sucursal"
              value={`${detail.locationContext.branchName} (${detail.locationContext.branchCode})`}
            />
            <Fact label="Area" value={detail.locationContext.areaName ?? "Sin area"} />
            <Fact label="Tipo area" value={detail.locationContext.areaType} />
            <Fact label="Critico operacion" value={detail.locationContext.isCritical ? "Si" : "No"} />
            <Fact
              label="Inocuidad"
              value={detail.locationContext.foodSafetyCritical ? "Critico" : "No critico"}
            />
          </div>
        </Section>

        <Section title="Metadatos del equipo">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact label="Marca" value={detail.metadata.brand ?? "N/A"} />
            <Fact label="Modelo" value={detail.metadata.model ?? "N/A"} />
            <Fact label="Serie" value={detail.metadata.serialNumber ?? "N/A"} />
            <Fact label="Proveedor" value={detail.metadata.providerName ?? "N/A"} />
            <Fact label="Compra" value={detail.metadata.purchaseDate ?? "N/A"} />
            <Fact label="Garantia" value={detail.metadata.warrantyExpiresAt ?? "N/A"} />
            <Fact
              label="Frecuencia"
              value={
                detail.metadata.maintenanceFrequencyDays
                  ? `${detail.metadata.maintenanceFrequencyDays} dias`
                  : "No configurada"
              }
            />
          </div>
          {detail.metadata.notes ? (
            <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {detail.metadata.notes}
            </p>
          ) : null}
        </Section>

        <Section title="Estado de mantenimiento actual">
          <div className="grid gap-2 sm:grid-cols-2">
            <Fact
              label="Ultimo mantenimiento"
              value={formatDateTime(detail.currentMaintenanceStatus.lastMaintenanceAt)}
            />
            <Fact
              label="Resultado ultimo"
              value={statusLabel(detail.currentMaintenanceStatus.lastMaintenanceResult)}
            />
            <Fact
              label="Proximo mantenimiento"
              value={formatDateTime(detail.currentMaintenanceStatus.nextScheduledMaintenanceAt)}
            />
            <Fact
              label="Vencido"
              value={detail.currentMaintenanceStatus.overdue ? "Si" : "No"}
            />
            <Fact
              label="Incidencia actual"
              value={detail.currentMaintenanceStatus.currentLinkedIncident ?? "N/A"}
            />
            <Fact label="Downtime" value={detail.currentMaintenanceStatus.downtimeState} />
          </div>
          {openRecord ? (
            <div className="mt-2">
              <MaintenanceRow record={openRecord} />
            </div>
          ) : null}
        </Section>

        <Section title="Historial de mantenimiento">
          {detail.maintenanceHistory.length > 0 ? (
            <div className="grid max-h-72 gap-1.5 overflow-y-auto">
              {detail.maintenanceHistory.map((record) => (
                <MaintenanceRow key={record.id} record={record} />
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este equipo no tiene mantenimientos registrados.
            </p>
          )}
        </Section>

        <Section title="Incidencias / problemas relacionados">
          {detail.incidentsRelated.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.incidentsRelated.map((incident) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={incident.folio}
                >
                  <span className="font-semibold text-slate-950">{incident.folio}</span>
                  <span className="ml-2 text-slate-500">{incident.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este equipo no tiene incidencias relacionadas.
            </p>
          )}
        </Section>

        <Section title="Evidencia">
          {detail.evidence.hasEvidence ? (
            <p className="rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-700">
              {detail.evidence.latestEvidenceNote}
            </p>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este mantenimiento no tiene evidencia adjunta.
            </p>
          )}
        </Section>

        <Section title="Costos">
          <div className="grid gap-2 sm:grid-cols-3">
            <Fact label="Periodo" value={formatEquipmentMoney(detail.costContext.periodCost)} />
            <Fact
              label="Ultimo servicio"
              value={formatEquipmentMoney(detail.costContext.lastServiceCost)}
            />
            <Fact
              label="Historico"
              value={formatEquipmentMoney(detail.costContext.totalLifetimeCost)}
            />
          </div>
          {detail.costContext.warrantyNote ? (
            <p className="mt-2 rounded-[14px] bg-slate-50 px-3 py-2 text-sm text-slate-600">
              {detail.costContext.warrantyNote}
            </p>
          ) : null}
        </Section>

        <Section title="Documentos relacionados">
          {detail.relatedDocuments.length > 0 ? (
            <div className="grid gap-1.5">
              {detail.relatedDocuments.map((document) => (
                <div
                  className="rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm"
                  key={`${document.documentType}-${document.documentId}`}
                >
                  <span className="font-semibold text-slate-950">{document.folio}</span>
                  <span className="ml-2 text-slate-500">{document.documentType}</span>
                  <span className="ml-2 text-slate-500">{document.status}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
              Este equipo no tiene documentos relacionados.
            </p>
          )}
        </Section>

        <Section title="Acciones disponibles">
          <div className="flex flex-wrap gap-2">
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700"
              type="button"
              onClick={() => onCopyCode(detail.overview.code)}
            >
              Copiar codigo
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canCreatePreventive}
              type="button"
              onClick={() => onCreateMaintenance(detail.overview)}
            >
              Crear mantenimiento
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!openRecord || !detail.availableActions.canStartMaintenance}
              type="button"
              onClick={() => openRecord && onStartMaintenance(openRecord)}
            >
              Iniciar mantenimiento
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!openRecord || !detail.availableActions.canCompleteMaintenance}
              type="button"
              onClick={() => openRecord && onCompleteMaintenance(openRecord)}
            >
              Completar mantenimiento
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canMarkOutOfService}
              type="button"
              onClick={() => onMarkOutOfService(detail.overview)}
            >
              Fuera de servicio
            </button>
            <button
              className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!detail.availableActions.canMarkOperational}
              type="button"
              onClick={() => onMarkOperational(detail.overview)}
            >
              Marcar operativo
            </button>
          </div>
          {detail.availableActions.note ? (
            <p className="mt-2 text-xs text-slate-500">{detail.availableActions.note}</p>
          ) : null}
          {detail.warnings.map((warning) => (
            <p
              className="mt-2 rounded-[14px] border border-amber-200 bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm font-semibold text-[var(--ui-color-warning)]"
              key={`${warning.code}-${warning.message}`}
            >
              {warning.message}
            </p>
          ))}
        </Section>
      </div>
    </aside>
  );
}
