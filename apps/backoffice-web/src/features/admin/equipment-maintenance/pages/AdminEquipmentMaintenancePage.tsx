import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminEquipmentBackendContract,
  completeAdminMaintenance,
  createAdminEquipment,
  createAdminMaintenance,
  fetchAdminEquipment,
  fetchAdminEquipmentDetail,
  startAdminMaintenance,
  updateAdminEquipmentStatus,
} from "../api";
import { AdminEquipmentMaintenanceDetailPanel } from "../components/AdminEquipmentMaintenanceDetailPanel";
import { AdminEquipmentMaintenanceFilters } from "../components/AdminEquipmentMaintenanceFilters";
import { AdminEquipmentMaintenanceTable } from "../components/AdminEquipmentMaintenanceTable";
import { AdminEquipmentMaintenanceWorkflowPanel } from "../components/AdminEquipmentMaintenanceWorkflowPanel";
import type {
  AdminEquipmentCreatePayload,
  AdminEquipmentFilterOptions,
  AdminEquipmentListFilters,
  AdminEquipmentListItem,
  AdminEquipmentListResponse,
  AdminMaintenanceCompletePayload,
  AdminMaintenanceCreatePayload,
  AdminMaintenanceRecordListItem,
} from "../types";

const initialFilters: AdminEquipmentListFilters = {
  areaName: "all",
  areaType: "all",
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  equipmentType: "all",
  incidentState: "all",
  maintenanceStatus: "all",
  maintenanceType: "all",
  operationalStatus: "all",
  overdueState: "all",
  page: 1,
  pageSize: 25,
  providerName: "all",
  riskLevel: "all",
  search: "",
  technicianName: "all",
};

const emptyFilterOptions: AdminEquipmentFilterOptions = {
  areaTypes: [],
  areas: [],
  branches: [],
  equipmentTypes: [],
  incidentStates: [],
  maintenanceStatuses: [],
  maintenanceTypes: [],
  operationalStatuses: [],
  providers: [],
  riskLevels: [],
  technicians: [],
};

const emptyEquipmentList: AdminEquipmentListResponse = {
  backendContract: adminEquipmentBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    correctiveOpenCount: "0",
    highRiskCount: "0",
    operationalCount: "0",
    outOfServiceCount: "0",
    overdueCount: "0",
    pendingMaintenanceCount: "0",
    periodCost: "$0.00",
    totalEquipmentCount: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function EquipmentMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminEquipmentListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Equipos registrados", value: loadingValue ?? metrics.totalEquipmentCount },
    { label: "Operativos", value: loadingValue ?? metrics.operationalCount },
    { label: "Fuera de servicio", value: loadingValue ?? metrics.outOfServiceCount },
    { label: "Mantenimientos pendientes", value: loadingValue ?? metrics.pendingMaintenanceCount },
    { label: "Vencidos", value: loadingValue ?? metrics.overdueCount },
    { label: "Correctivos abiertos", value: loadingValue ?? metrics.correctiveOpenCount },
    { label: "Alto riesgo", value: loadingValue ?? metrics.highRiskCount },
    { label: "Costo del periodo", value: loadingValue ?? metrics.periodCost },
  ];

  return (
    <section className="flex min-w-0 flex-wrap items-center gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs text-slate-600">
      <span className="shrink-0 font-semibold uppercase tracking-[0.12em] text-slate-500">
        Resumen
      </span>
      {items.map((item) => (
        <span
          className="inline-flex min-w-0 max-w-full items-center gap-1.5 rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-2.5 py-1"
          key={item.label}
          title={`${item.label}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

export function AdminEquipmentMaintenancePage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminEquipmentListFilters>(initialFilters);
  const [selectedEquipmentId, setSelectedEquipmentId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"equipment" | "maintenance" | "complete" | null>(
    null,
  );
  const [selectedMaintenance, setSelectedMaintenance] =
    useState<AdminMaintenanceRecordListItem | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const equipmentQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminEquipment(accessToken ?? "", filters),
    queryKey: ["admin", "equipment-maintenance", "list", filters],
    retry: false,
  });

  const equipmentList = equipmentQuery.data ?? emptyEquipmentList;
  const selectedEquipment = useMemo(
    () => equipmentList.items.find((item) => item.id === selectedEquipmentId) ?? null,
    [equipmentList.items, selectedEquipmentId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedEquipmentId),
    queryFn: () => fetchAdminEquipmentDetail(accessToken ?? "", selectedEquipmentId ?? ""),
    queryKey: ["admin", "equipment-maintenance", "detail", selectedEquipmentId],
    retry: false,
  });

  const createEquipmentMutation = useMutation({
    mutationFn: (payload: AdminEquipmentCreatePayload) =>
      createAdminEquipment(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar el equipo."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Equipo ${detail.overview.code} guardado.` });
      setSelectedEquipmentId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "equipment-maintenance"] });
    },
  });

  const createMaintenanceMutation = useMutation({
    mutationFn: (payload: AdminMaintenanceCreatePayload) =>
      createAdminMaintenance(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear el mantenimiento."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({
        tone: "success",
        message: `Mantenimiento guardado para ${detail.overview.code}.`,
      });
      setSelectedEquipmentId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "equipment-maintenance"] });
    },
  });

  const completeMaintenanceMutation = useMutation({
    mutationFn: ({
      maintenanceId,
      payload,
    }: {
      maintenanceId: string;
      payload: AdminMaintenanceCompletePayload;
    }) => completeAdminMaintenance(accessToken ?? "", maintenanceId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo completar el mantenimiento."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Mantenimiento de ${detail.overview.code} cerrado.` });
      setSelectedEquipmentId(detail.overview.id);
      setWorkflowMode(null);
      setSelectedMaintenance(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "equipment-maintenance"] });
    },
  });

  const startMaintenanceMutation = useMutation({
    mutationFn: (maintenanceId: string) => startAdminMaintenance(accessToken ?? "", maintenanceId),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo iniciar el mantenimiento."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Mantenimiento de ${detail.overview.code} iniciado.` });
      setSelectedEquipmentId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "equipment-maintenance"] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({
      equipmentId,
      reason,
      status,
    }: {
      equipmentId: string;
      reason: string | null;
      status: "OPERATIONAL" | "OUT_OF_SERVICE";
    }) =>
      updateAdminEquipmentStatus(accessToken ?? "", equipmentId, {
        operationalStatus: status,
        reason,
      }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cambiar el estado del equipo."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Estado de ${detail.overview.code} actualizado.` });
      setSelectedEquipmentId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "equipment-maintenance"] });
    },
  });

  const listErrorMessage = equipmentQuery.isError
    ? toBackofficeErrorMessage(
        equipmentQuery.error,
        "No se pudieron cargar los equipos. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del equipo.")
    : null;
  const workflowErrorMessage =
    createEquipmentMutation.isError ||
    createMaintenanceMutation.isError ||
    completeMaintenanceMutation.isError
      ? toBackofficeErrorMessage(
          createEquipmentMutation.error ??
            createMaintenanceMutation.error ??
            completeMaintenanceMutation.error,
          "No se pudo guardar la informacion de mantenimiento.",
        )
      : null;
  const pageStatusLabel = equipmentQuery.isLoading
    ? "Validando API"
    : equipmentList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminEquipmentListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedEquipmentId(null);
  }

  function handleSelectEquipment(item: AdminEquipmentListItem) {
    setSelectedEquipmentId(item.id);
  }

  function handleCopyCode(value: AdminEquipmentListItem | string) {
    const code = typeof value === "string" ? value : value.code;
    void navigator.clipboard?.writeText(code);
    setFeedback({ tone: "success", message: `Codigo ${code} copiado.` });
  }

  function handleCreateMaintenance(item: AdminEquipmentListItem) {
    setSelectedEquipmentId(item.id);
    setSelectedMaintenance(null);
    setWorkflowMode("maintenance");
  }

  function handleCompleteMaintenance(record: AdminMaintenanceRecordListItem) {
    setSelectedMaintenance(record);
    setWorkflowMode("complete");
  }

  function handleMarkOutOfService(item: AdminEquipmentListItem) {
    statusMutation.mutate({
      equipmentId: item.id,
      reason: "Marcado fuera de servicio desde Backoffice por mantenimiento.",
      status: "OUT_OF_SERVICE",
    });
  }

  function handleMarkOperational(item: AdminEquipmentListItem) {
    statusMutation.mutate({
      equipmentId: item.id,
      reason: null,
      status: "OPERATIONAL",
    });
  }

  function handleComplete(payload: AdminMaintenanceCompletePayload) {
    if (!selectedMaintenance) {
      setFeedback({ tone: "error", message: "Selecciona un mantenimiento abierto." });
      return;
    }
    completeMaintenanceMutation.mutate({ maintenanceId: selectedMaintenance.id, payload });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nuevo equipo"
        description="Administra equipos, servicios preventivos, fallas, reparaciones, evidencias, costos y estado operativo por sucursal."
        meta={[pageStatusLabel]}
        title="Mantenimiento de equipos"
        onAction={() => {
          setSelectedMaintenance(null);
          setWorkflowMode("equipment");
        }}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminEquipmentMaintenanceFilters
          filters={filters}
          isBackendConnected={equipmentList.isBackendConnected}
          options={equipmentList.filterOptions}
          onChange={patchFilters}
        />

        <EquipmentMetricStrip isLoading={equipmentQuery.isLoading} metrics={equipmentList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => setWorkflowMode("maintenance")}
          >
            Nuevo mantenimiento
          </button>
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => patchFilters({ overdueState: "overdue" })}
          >
            Ver vencidos
          </button>
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => patchFilters({ operationalStatus: "OUT_OF_SERVICE" })}
          >
            Ver fuera de servicio
          </button>
        </div>

        {workflowMode ? (
          <AdminEquipmentMaintenanceWorkflowPanel
            equipment={equipmentList.items}
            errorMessage={workflowErrorMessage}
            isSubmitting={
              createEquipmentMutation.isPending ||
              createMaintenanceMutation.isPending ||
              completeMaintenanceMutation.isPending
            }
            maintenanceRecord={selectedMaintenance}
            mode={workflowMode}
            options={equipmentList.filterOptions}
            selectedEquipment={selectedEquipment}
            onCancel={() => setWorkflowMode(null)}
            onCompleteMaintenance={handleComplete}
            onCreateEquipment={(payload) => createEquipmentMutation.mutate(payload)}
            onCreateMaintenance={(payload) => createMaintenanceMutation.mutate(payload)}
          />
        ) : null}

        {feedback ? (
          <p
            className={`rounded-[18px] border px-4 py-3 text-sm font-semibold ${
              feedback.tone === "success"
                ? "border-emerald-200 bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]"
                : "border-rose-200 bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]"
            }`}
          >
            {feedback.message}
          </p>
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1fr)_minmax(23rem,0.42fr)]">
          <AdminEquipmentMaintenanceTable
            equipment={equipmentList.items}
            errorMessage={listErrorMessage}
            isLoading={equipmentQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedEquipmentId={selectedEquipmentId}
            total={equipmentList.total}
            onCopyCode={handleCopyCode}
            onCreateMaintenance={handleCreateMaintenance}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onSelectEquipment={handleSelectEquipment}
          />

          <AdminEquipmentMaintenanceDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={
              detailQuery.isLoading || startMaintenanceMutation.isPending || statusMutation.isPending
            }
            selectedEquipment={selectedEquipment}
            onCompleteMaintenance={handleCompleteMaintenance}
            onCopyCode={handleCopyCode}
            onCreateMaintenance={handleCreateMaintenance}
            onMarkOperational={handleMarkOperational}
            onMarkOutOfService={handleMarkOutOfService}
            onStartMaintenance={(record) => startMaintenanceMutation.mutate(record.id)}
          />
        </div>
      </div>
    </section>
  );
}
