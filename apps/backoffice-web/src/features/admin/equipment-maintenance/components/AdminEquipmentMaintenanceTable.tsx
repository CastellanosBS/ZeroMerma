import { AdminActionButton } from "../../components/AdminActionButton";
import { formatEquipmentMoney } from "../api";
import { AdminEmptyState } from "../../components/AdminEmptyState";
import type { AdminEquipmentListItem } from "../types";

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "Pendiente";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function equipmentTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    DISPLAY_CASE: "Vitrina",
    MIXER: "Batidora",
    OTHER: "Otro",
    OVEN: "Horno",
    PACKAGING: "Empaque",
    REFRIGERATION: "Refrigeracion",
    SANITATION: "Sanidad",
    SCALE: "Bascula",
  };
  return labels[value] ?? value;
}

function statusLabel(value: string): string {
  const labels: Record<string, string> = {
    CANCELLED: "Cancelado",
    COMPLETED: "Completado",
    INACTIVE: "Inactivo",
    IN_PROGRESS: "En proceso",
    NO_HISTORY: "Sin historial",
    OK: "Al dia",
    OPERATIONAL: "Operativo",
    OUT_OF_SERVICE: "Fuera de servicio",
    OVERDUE: "Vencido",
    PENDING: "Pendiente",
    RETIRED: "Retirado",
    SCHEDULED: "Programado",
    UNDER_MAINTENANCE: "En mantenimiento",
  };
  return labels[value] ?? value;
}

function badgeClass(value: string): string {
  if (value === "OPERATIONAL" || value === "OK" || value === "COMPLETED") {
    return "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }
  if (
    value === "OUT_OF_SERVICE" ||
    value === "OVERDUE" ||
    value === "CRITICAL" ||
    value === "FAILED"
  ) {
    return "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }
  if (value === "UNDER_MAINTENANCE" || value === "HIGH" || value === "IN_PROGRESS") {
    return "border-amber-200 bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }
  return "border-slate-200 bg-slate-50 text-slate-600";
}

interface AdminEquipmentMaintenanceTableProps {
  equipment: AdminEquipmentListItem[];
  errorMessage?: string | null;
  isLoading?: boolean;
  onCopyCode: (item: AdminEquipmentListItem) => void;
  onCreateMaintenance: (item: AdminEquipmentListItem) => void;
  onPageChange: (page: number) => void;
  onSelectEquipment: (item: AdminEquipmentListItem) => void;
  page: number;
  pageSize: number;
  selectedEquipmentId?: string | null;
  total: number;
}

export function AdminEquipmentMaintenanceTable({
  equipment,
  errorMessage,
  isLoading = false,
  onCopyCode,
  onCreateMaintenance,
  onPageChange,
  onSelectEquipment,
  page,
  pageSize,
  selectedEquipmentId,
  total,
}: AdminEquipmentMaintenanceTableProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[20px] border border-[var(--ui-color-border)] bg-white">
      <div className="flex min-w-0 shrink-0 items-center justify-between gap-3 border-b border-[var(--ui-color-border)] px-3 py-2.5">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Equipos registrados</h3>
          <p className="truncate text-xs text-slate-500">
            Codigo, sucursal, zona, estado operativo, mantenimiento, riesgo e incidencias.
          </p>
        </div>
        <span className="shrink-0 rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1 text-xs font-semibold text-slate-600">
          {total} registros
        </span>
      </div>

      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2.5">
        {isLoading ? (
          <AdminEmptyState
            description="Consultando equipos y mantenimientos persistidos en backend."
            title="Cargando equipos"
          />
        ) : errorMessage ? (
          <AdminEmptyState description={errorMessage} title="No se pudieron cargar los equipos" />
        ) : equipment.length > 0 ? (
          <div className="min-w-[86rem] overflow-hidden rounded-[16px] border border-[var(--ui-color-border)]">
            <div className="grid grid-cols-[8rem_12rem_8rem_10rem_9rem_9rem_9rem_9rem_9rem_7rem_7rem_8rem_9rem] border-b border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">
              <span>Codigo / activo</span>
              <span>Equipo</span>
              <span>Tipo</span>
              <span>Sucursal</span>
              <span>Zona / area</span>
              <span>Estado operativo</span>
              <span>Ultimo mantto.</span>
              <span>Proximo mantto.</span>
              <span>Mantto. estado</span>
              <span>Riesgo</span>
              <span>Incid.</span>
              <span>Costo periodo</span>
              <span className="text-right">Acciones</span>
            </div>
            <div className="divide-y divide-[var(--ui-color-border)]">
              {equipment.map((item) => {
                const isSelected = item.id === selectedEquipmentId;
                return (
                  <article
                    className={[
                      "grid grid-cols-[8rem_12rem_8rem_10rem_9rem_9rem_9rem_9rem_9rem_7rem_7rem_8rem_9rem] items-center gap-0 px-3 py-2 text-sm transition",
                      isSelected ? "bg-[var(--ui-color-info-soft)]" : "bg-white hover:bg-slate-50",
                    ].join(" ")}
                    key={item.id}
                  >
                    <button
                      className="truncate text-left font-semibold text-slate-950 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
                      title={item.code}
                      type="button"
                      onClick={() => onSelectEquipment(item)}
                    >
                      {item.code}
                    </button>
                    <span className="truncate font-medium text-slate-950" title={item.name}>
                      {item.name}
                    </span>
                    <span className="truncate text-slate-700">
                      {equipmentTypeLabel(item.equipmentType)}
                    </span>
                    <span className="truncate text-slate-700" title={item.branchName}>
                      {item.branchName}
                    </span>
                    <span className="truncate text-slate-700" title={item.areaName ?? "N/A"}>
                      {item.areaName ?? "N/A"}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.operationalStatus,
                      )}`}
                    >
                      <span className="truncate">{statusLabel(item.operationalStatus)}</span>
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.lastMaintenanceAt)}
                    </span>
                    <span className="truncate text-xs text-slate-600">
                      {formatDateTime(item.nextMaintenanceAt)}
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.maintenanceStatus,
                      )}`}
                    >
                      <span className="truncate">{statusLabel(item.maintenanceStatus)}</span>
                    </span>
                    <span
                      className={`mr-1 inline-flex min-w-0 rounded-full border px-2 py-1 text-xs font-semibold ${badgeClass(
                        item.riskLevel,
                      )}`}
                    >
                      {item.riskLevel}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {item.openIncidentCount}
                    </span>
                    <span className="truncate text-xs font-semibold text-slate-700">
                      {formatEquipmentMoney(item.periodCost)}
                    </span>
                    <div className="flex min-w-0 items-center justify-end gap-1">
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onSelectEquipment(item)}
                      >
                        Ver
                      </button>
                      <AdminActionButton
                        capability="quality_hygiene.manage"
                        branchIds={[item.branchId]}
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onCreateMaintenance(item)}
                      >
                        Mantto.
                      </AdminActionButton>
                      <button
                        className="rounded-full border border-[var(--ui-color-border)] bg-white px-2 py-1 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
                        type="button"
                        onClick={() => onCopyCode(item)}
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
            description="No hay equipos registrados para los filtros seleccionados."
            title="Sin equipos"
          />
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between gap-3 border-t border-[var(--ui-color-border)] px-3 py-2 text-xs text-slate-500">
        <span>
          Pagina {page} de {totalPages}
        </span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={!canGoPrevious}
            type="button"
            onClick={() => onPageChange(page - 1)}
          >
            Anterior
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 font-semibold text-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
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
