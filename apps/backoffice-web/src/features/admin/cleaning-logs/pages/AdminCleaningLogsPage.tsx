import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminCleaningBackendContract,
  completeAdminCleaningLog,
  createAdminCleaningLog,
  fetchAdminCleaningLogDetail,
  fetchAdminCleaningLogs,
  fetchAdminCleaningTemplates,
} from "../api";
import { AdminCleaningLogDetailPanel } from "../components/AdminCleaningLogDetailPanel";
import { AdminCleaningLogWorkflowPanel } from "../components/AdminCleaningLogWorkflowPanel";
import { AdminCleaningLogsFilters } from "../components/AdminCleaningLogsFilters";
import { AdminCleaningLogsTable } from "../components/AdminCleaningLogsTable";
import type {
  AdminCleaningCompletePayload,
  AdminCleaningCreatePayload,
  AdminCleaningFilterOptions,
  AdminCleaningListFilters,
  AdminCleaningLogListItem,
  AdminCleaningLogListResponse,
} from "../types";

const initialFilters: AdminCleaningListFilters = {
  areaName: "all",
  areaType: "all",
  branchId: "all",
  cleaningType: "all",
  dateFrom: null,
  dateTo: null,
  evidenceState: "all",
  observationState: "all",
  page: 1,
  pageSize: 25,
  responsibleUserId: "all",
  riskLevel: "all",
  search: "",
  shiftCode: "all",
  status: "all",
  templateId: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminCleaningFilterOptions = {
  areaTypes: [],
  areas: [],
  branches: [],
  cleaningTypes: [],
  evidenceStates: [],
  observationStates: [],
  responsibleUsers: [],
  riskLevels: [],
  shifts: [],
  statuses: [],
  templates: [],
};

const emptyCleaningList: AdminCleaningLogListResponse = {
  backendContract: adminCleaningBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    completedCount: "0",
    highRiskCount: "0",
    overdueCount: "0",
    pendingCount: "0",
    requiresReviewCount: "0",
    totalCount: "0",
    withEvidenceCount: "0",
    withObservationsCount: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function CleaningMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminCleaningLogListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Bitacoras del periodo", value: loadingValue ?? metrics.totalCount },
    { label: "Completadas", value: loadingValue ?? metrics.completedCount },
    { label: "Pendientes", value: loadingValue ?? metrics.pendingCount },
    { label: "Vencidas", value: loadingValue ?? metrics.overdueCount },
    { label: "Con evidencia", value: loadingValue ?? metrics.withEvidenceCount },
    { label: "Con observaciones", value: loadingValue ?? metrics.withObservationsCount },
    { label: "Alto riesgo", value: loadingValue ?? metrics.highRiskCount },
    { label: "Por revisar", value: loadingValue ?? metrics.requiresReviewCount },
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

export function AdminCleaningLogsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminCleaningListFilters>(initialFilters);
  const [selectedCleaningLogId, setSelectedCleaningLogId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"create" | "complete" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const cleaningLogsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminCleaningLogs(accessToken ?? "", filters),
    queryKey: ["admin", "cleaning-logs", "list", filters],
    retry: false,
  });

  const templatesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminCleaningTemplates(accessToken ?? ""),
    queryKey: ["admin", "cleaning-logs", "templates"],
    retry: false,
  });

  const cleaningList = cleaningLogsQuery.data ?? emptyCleaningList;
  const selectedCleaningLog = useMemo(
    () => cleaningList.items.find((item) => item.id === selectedCleaningLogId) ?? null,
    [cleaningList.items, selectedCleaningLogId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedCleaningLogId),
    queryFn: () => fetchAdminCleaningLogDetail(accessToken ?? "", selectedCleaningLogId ?? ""),
    queryKey: ["admin", "cleaning-logs", "detail", selectedCleaningLogId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminCleaningCreatePayload) =>
      createAdminCleaningLog(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar la bitacora."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Bitacora ${detail.overview.folio} guardada.` });
      setSelectedCleaningLogId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "cleaning-logs"] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({
      cleaningLogId,
      payload,
    }: {
      cleaningLogId: string;
      payload: AdminCleaningCompletePayload;
    }) => completeAdminCleaningLog(accessToken ?? "", cleaningLogId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo completar la bitacora."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Bitacora ${detail.overview.folio} completada.` });
      setSelectedCleaningLogId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "cleaning-logs"] });
    },
  });

  const listErrorMessage = cleaningLogsQuery.isError
    ? toBackofficeErrorMessage(
        cleaningLogsQuery.error,
        "No se pudieron cargar las bitacoras. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle de la bitacora.")
    : null;
  const workflowErrorMessage =
    createMutation.isError || completeMutation.isError
      ? toBackofficeErrorMessage(
          createMutation.error ?? completeMutation.error,
          "No se pudo guardar la bitacora.",
        )
      : null;
  const pageStatusLabel = cleaningLogsQuery.isLoading
    ? "Validando API"
    : cleaningList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminCleaningListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedCleaningLogId(null);
  }

  function handleSelectCleaningLog(item: AdminCleaningLogListItem) {
    setSelectedCleaningLogId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleCopyFolio(value: AdminCleaningLogListItem | string) {
    const folio = typeof value === "string" ? value : value.folio;
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  function handleRegisterCompletion(item: AdminCleaningLogListItem) {
    setSelectedCleaningLogId(item.id);
    setWorkflowMode("complete");
  }

  function handleCreate(payload: AdminCleaningCreatePayload) {
    createMutation.mutate(payload);
  }

  function handleComplete(payload: AdminCleaningCompletePayload) {
    const cleaningLogId = selectedCleaningLogId;
    if (!cleaningLogId) {
      setFeedback({ tone: "error", message: "Selecciona una bitacora para completarla." });
      return;
    }
    completeMutation.mutate({ cleaningLogId, payload });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="quality_hygiene.manage"
        actionLabel="Nueva bitacora"
        description="Registra y consulta actividades de limpieza por sucursal, zona, turno, responsable, checklist y evidencia."
        meta={[pageStatusLabel]}
        title="Bitacoras de limpieza"
        onAction={() => setWorkflowMode("create")}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminCleaningLogsFilters
          filters={filters}
          isBackendConnected={cleaningList.isBackendConnected}
          options={cleaningList.filterOptions}
          onChange={patchFilters}
        />

        <CleaningMetricStrip
          isLoading={cleaningLogsQuery.isLoading}
          metrics={cleaningList.metrics}
        />

        {workflowMode ? (
          <AdminCleaningLogWorkflowPanel
            detail={detailQuery.data ?? null}
            errorMessage={workflowErrorMessage}
            isSubmitting={createMutation.isPending || completeMutation.isPending}
            mode={workflowMode}
            options={cleaningList.filterOptions}
            templates={templatesQuery.data ?? []}
            onCancel={() => setWorkflowMode(null)}
            onComplete={handleComplete}
            onCreate={handleCreate}
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
          <AdminCleaningLogsTable
            cleaningLogs={cleaningList.items}
            errorMessage={listErrorMessage}
            isLoading={cleaningLogsQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedCleaningLogId={selectedCleaningLogId}
            total={cleaningList.total}
            onCopyFolio={handleCopyFolio}
            onPageChange={handlePageChange}
            onRegisterCompletion={handleRegisterCompletion}
            onSelectCleaningLog={handleSelectCleaningLog}
          />

          <AdminCleaningLogDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedCleaningLog={selectedCleaningLog}
            onCopyFolio={handleCopyFolio}
            onRegisterCompletion={handleRegisterCompletion}
          />
        </div>
      </div>
    </section>
  );
}
