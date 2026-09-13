import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminSanitaryBackendContract,
  completeAdminSanitaryVerification,
  createAdminSanitaryVerification,
  fetchAdminSanitaryTemplates,
  fetchAdminSanitaryVerificationDetail,
  fetchAdminSanitaryVerifications,
  startAdminSanitaryVerification,
} from "../api";
import { AdminSanitaryVerificationDetailPanel } from "../components/AdminSanitaryVerificationDetailPanel";
import { AdminSanitaryVerificationWorkflowPanel } from "../components/AdminSanitaryVerificationWorkflowPanel";
import { AdminSanitaryVerificationsFilters } from "../components/AdminSanitaryVerificationsFilters";
import { AdminSanitaryVerificationsTable } from "../components/AdminSanitaryVerificationsTable";
import type {
  AdminSanitaryCompletePayload,
  AdminSanitaryCreatePayload,
  AdminSanitaryFilterOptions,
  AdminSanitaryListFilters,
  AdminSanitaryVerificationListItem,
  AdminSanitaryVerificationListResponse,
} from "../types";

const initialFilters: AdminSanitaryListFilters = {
  areaName: "all",
  areaType: "all",
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  evidenceState: "all",
  incidentState: "all",
  inspectorUserId: "all",
  page: 1,
  pageSize: 25,
  processName: "all",
  processType: "all",
  result: "all",
  riskLevel: "all",
  search: "",
  status: "all",
  templateId: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminSanitaryFilterOptions = {
  areaTypes: [],
  areas: [],
  branches: [],
  evidenceStates: [],
  incidentStates: [],
  inspectors: [],
  processTypes: [],
  processes: [],
  results: [],
  riskLevels: [],
  statuses: [],
  templates: [],
};

const emptySanitaryList: AdminSanitaryVerificationListResponse = {
  backendContract: adminSanitaryBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    failedCount: "0",
    highRiskCount: "0",
    pendingCount: "0",
    passedCount: "0",
    requiresFollowUpCount: "0",
    totalCount: "0",
    withEvidenceCount: "0",
    withIncidentCount: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function SanitaryMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminSanitaryVerificationListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Verificaciones del periodo", value: loadingValue ?? metrics.totalCount },
    { label: "Aprobadas", value: loadingValue ?? metrics.passedCount },
    { label: "Fallidas", value: loadingValue ?? metrics.failedCount },
    { label: "Pendientes", value: loadingValue ?? metrics.pendingCount },
    { label: "Con incidencia", value: loadingValue ?? metrics.withIncidentCount },
    { label: "Alto riesgo", value: loadingValue ?? metrics.highRiskCount },
    { label: "Con evidencia", value: loadingValue ?? metrics.withEvidenceCount },
    { label: "Por seguimiento", value: loadingValue ?? metrics.requiresFollowUpCount },
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

export function AdminSanitaryVerificationsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminSanitaryListFilters>(initialFilters);
  const [selectedVerificationId, setSelectedVerificationId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"create" | "execute" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const sanitaryQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminSanitaryVerifications(accessToken ?? "", filters),
    queryKey: ["admin", "sanitary-verifications", "list", filters],
    retry: false,
  });

  const templatesQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminSanitaryTemplates(accessToken ?? ""),
    queryKey: ["admin", "sanitary-verifications", "templates"],
    retry: false,
  });

  const sanitaryList = sanitaryQuery.data ?? emptySanitaryList;
  const selectedVerification = useMemo(
    () => sanitaryList.items.find((item) => item.id === selectedVerificationId) ?? null,
    [sanitaryList.items, selectedVerificationId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedVerificationId),
    queryFn: () =>
      fetchAdminSanitaryVerificationDetail(accessToken ?? "", selectedVerificationId ?? ""),
    queryKey: ["admin", "sanitary-verifications", "detail", selectedVerificationId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminSanitaryCreatePayload) =>
      createAdminSanitaryVerification(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar la verificacion."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({
        tone: "success",
        message: `Verificacion ${detail.overview.folio} guardada.`,
      });
      setSelectedVerificationId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "sanitary-verifications"] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({
      payload,
      verificationId,
    }: {
      payload: AdminSanitaryCompletePayload;
      verificationId: string;
    }) => completeAdminSanitaryVerification(accessToken ?? "", verificationId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo completar la verificacion."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({
        tone: "success",
        message: `Verificacion ${detail.overview.folio} completada.`,
      });
      setSelectedVerificationId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "sanitary-verifications"] });
    },
  });

  const startMutation = useMutation({
    mutationFn: (verificationId: string) =>
      startAdminSanitaryVerification(accessToken ?? "", verificationId),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo iniciar la verificacion."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Verificacion ${detail.overview.folio} iniciada.` });
      setSelectedVerificationId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "sanitary-verifications"] });
    },
  });

  const listErrorMessage = sanitaryQuery.isError
    ? toBackofficeErrorMessage(
        sanitaryQuery.error,
        "No se pudieron cargar las verificaciones. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle sanitario.")
    : null;
  const workflowErrorMessage =
    createMutation.isError || completeMutation.isError
      ? toBackofficeErrorMessage(
          createMutation.error ?? completeMutation.error,
          "No se pudo guardar la verificacion.",
        )
      : null;
  const pageStatusLabel = sanitaryQuery.isLoading
    ? "Validando API"
    : sanitaryList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminSanitaryListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedVerificationId(null);
  }

  function handleSelectVerification(item: AdminSanitaryVerificationListItem) {
    setSelectedVerificationId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleCopyFolio(value: AdminSanitaryVerificationListItem | string) {
    const folio = typeof value === "string" ? value : value.folio;
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  function handleExecute(item: AdminSanitaryVerificationListItem) {
    setSelectedVerificationId(item.id);
    setWorkflowMode("execute");
  }

  function handleStart(item: AdminSanitaryVerificationListItem) {
    startMutation.mutate(item.id);
  }

  function handleCreate(payload: AdminSanitaryCreatePayload) {
    createMutation.mutate(payload);
  }

  function handleComplete(payload: AdminSanitaryCompletePayload) {
    const verificationId = selectedVerificationId;
    if (!verificationId) {
      setFeedback({ tone: "error", message: "Selecciona una verificacion para ejecutarla." });
      return;
    }
    completeMutation.mutate({ payload, verificationId });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="quality_hygiene.manage"
        actionLabel="Nueva verificacion"
        description="Evalua el cumplimiento sanitario por sucursal, zona, equipo, proceso, checklist, evidencia y nivel de riesgo."
        meta={[pageStatusLabel]}
        title="Verificaciones sanitarias"
        onAction={() => setWorkflowMode("create")}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminSanitaryVerificationsFilters
          filters={filters}
          isBackendConnected={sanitaryList.isBackendConnected}
          options={sanitaryList.filterOptions}
          onChange={patchFilters}
        />

        <SanitaryMetricStrip isLoading={sanitaryQuery.isLoading} metrics={sanitaryList.metrics} />

        {workflowMode ? (
          <AdminSanitaryVerificationWorkflowPanel
            detail={detailQuery.data ?? null}
            errorMessage={workflowErrorMessage}
            isSubmitting={createMutation.isPending || completeMutation.isPending}
            mode={workflowMode}
            options={sanitaryList.filterOptions}
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
          <AdminSanitaryVerificationsTable
            errorMessage={listErrorMessage}
            isLoading={sanitaryQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedVerificationId={selectedVerificationId}
            total={sanitaryList.total}
            verifications={sanitaryList.items}
            onCopyFolio={handleCopyFolio}
            onExecute={handleExecute}
            onPageChange={handlePageChange}
            onSelectVerification={handleSelectVerification}
          />

          <AdminSanitaryVerificationDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading || startMutation.isPending}
            selectedVerification={selectedVerification}
            onCopyFolio={handleCopyFolio}
            onExecute={handleExecute}
            onStart={handleStart}
          />
        </div>
      </div>
    </section>
  );
}
