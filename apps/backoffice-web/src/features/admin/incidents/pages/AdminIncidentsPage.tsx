import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  addAdminIncidentFollowUp,
  adminIncidentBackendContract,
  changeAdminIncidentStatus,
  createAdminIncident,
  fetchAdminIncidentDetail,
  fetchAdminIncidents,
  reopenAdminIncident,
  resolveAdminIncident,
} from "../api";
import { AdminIncidentDetailPanel } from "../components/AdminIncidentDetailPanel";
import { AdminIncidentsFilters } from "../components/AdminIncidentsFilters";
import { AdminIncidentsTable } from "../components/AdminIncidentsTable";
import { AdminIncidentWorkflowPanel } from "../components/AdminIncidentWorkflowPanel";
import type {
  AdminIncidentCreatePayload,
  AdminIncidentFilterOptions,
  AdminIncidentFollowUpPayload,
  AdminIncidentListFilters,
  AdminIncidentListItem,
  AdminIncidentListResponse,
  AdminIncidentResolvePayload,
} from "../types";

const initialFilters: AdminIncidentListFilters = {
  areaName: "all",
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  dueState: "all",
  evidenceState: "all",
  incidentType: "all",
  page: 1,
  pageSize: 25,
  relatedDocumentState: "all",
  reportedByUserId: "all",
  responsibleUserId: "all",
  search: "",
  severity: "all",
  sourceType: "all",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminIncidentFilterOptions = {
  areas: [],
  branches: [],
  dueStates: [],
  evidenceStates: [],
  incidentTypes: [],
  relatedDocumentStates: [],
  reportedByUsers: [],
  responsibleUsers: [],
  severities: [],
  sourceTypes: [],
  statuses: [],
};

const emptyIncidentList: AdminIncidentListResponse = {
  backendContract: adminIncidentBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    highRiskCount: "0",
    inProgressCount: "0",
    openCount: "0",
    overdueCount: "0",
    resolvedCount: "0",
    sanitaryGeneratedCount: "0",
    totalCount: "0",
    withEvidenceCount: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function IncidentMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminIncidentListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Incidencias del periodo", value: loadingValue ?? metrics.totalCount },
    { label: "Abiertas", value: loadingValue ?? metrics.openCount },
    { label: "En seguimiento", value: loadingValue ?? metrics.inProgressCount },
    { label: "Resueltas", value: loadingValue ?? metrics.resolvedCount },
    { label: "Alto riesgo", value: loadingValue ?? metrics.highRiskCount },
    { label: "Vencidas", value: loadingValue ?? metrics.overdueCount },
    { label: "Con evidencia", value: loadingValue ?? metrics.withEvidenceCount },
    {
      label: "Generadas por verificacion",
      value: loadingValue ?? metrics.sanitaryGeneratedCount,
    },
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

export function AdminIncidentsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminIncidentListFilters>(initialFilters);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<"create" | "followUp" | "resolve" | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const incidentsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminIncidents(accessToken ?? "", filters),
    queryKey: ["admin", "incidents", "list", filters],
    retry: false,
  });

  const incidentList = incidentsQuery.data ?? emptyIncidentList;
  const selectedIncident = useMemo(
    () => incidentList.items.find((item) => item.id === selectedIncidentId) ?? null,
    [incidentList.items, selectedIncidentId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedIncidentId),
    queryFn: () => fetchAdminIncidentDetail(accessToken ?? "", selectedIncidentId ?? ""),
    queryKey: ["admin", "incidents", "detail", selectedIncidentId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminIncidentCreatePayload) =>
      createAdminIncident(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar la incidencia."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Incidencia ${detail.overview.folio} guardada.` });
      setSelectedIncidentId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "incidents"] });
    },
  });

  const followUpMutation = useMutation({
    mutationFn: ({
      incidentId,
      payload,
    }: {
      incidentId: string;
      payload: AdminIncidentFollowUpPayload;
    }) => addAdminIncidentFollowUp(accessToken ?? "", incidentId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo agregar seguimiento."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({
        tone: "success",
        message: `Seguimiento guardado para ${detail.overview.folio}.`,
      });
      setSelectedIncidentId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "incidents"] });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({
      incidentId,
      note,
      status,
    }: {
      incidentId: string;
      note: string | null;
      status: "IN_PROGRESS";
    }) =>
      changeAdminIncidentStatus(accessToken ?? "", incidentId, {
        cancellationReason: null,
        note,
        status,
      }),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cambiar el estado."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `${detail.overview.folio} actualizado.` });
      setSelectedIncidentId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "incidents"] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({
      incidentId,
      payload,
    }: {
      incidentId: string;
      payload: AdminIncidentResolvePayload;
    }) => resolveAdminIncident(accessToken ?? "", incidentId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo resolver la incidencia."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Incidencia ${detail.overview.folio} resuelta.` });
      setSelectedIncidentId(detail.overview.id);
      setWorkflowMode(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "incidents"] });
    },
  });

  const reopenMutation = useMutation({
    mutationFn: ({ incidentId, note }: { incidentId: string; note: string }) =>
      reopenAdminIncident(accessToken ?? "", incidentId, note),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo reabrir la incidencia."),
      });
    },
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Incidencia ${detail.overview.folio} reabierta.` });
      setSelectedIncidentId(detail.overview.id);
      await queryClient.invalidateQueries({ queryKey: ["admin", "incidents"] });
    },
  });

  const listErrorMessage = incidentsQuery.isError
    ? toBackofficeErrorMessage(
        incidentsQuery.error,
        "No se pudieron cargar las incidencias. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle de la incidencia.")
    : null;
  const workflowErrorMessage =
    createMutation.isError || followUpMutation.isError || resolveMutation.isError
      ? toBackofficeErrorMessage(
          createMutation.error ?? followUpMutation.error ?? resolveMutation.error,
          "No se pudo guardar la incidencia.",
        )
      : null;
  const pageStatusLabel = incidentsQuery.isLoading
    ? "Validando API"
    : incidentList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminIncidentListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedIncidentId(null);
  }

  function handleSelectIncident(item: AdminIncidentListItem) {
    setSelectedIncidentId(item.id);
  }

  function handleCopyFolio(value: AdminIncidentListItem | string) {
    const folio = typeof value === "string" ? value : value.folio;
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  function handleWorkflow(mode: "followUp" | "resolve", item: AdminIncidentListItem) {
    setSelectedIncidentId(item.id);
    setWorkflowMode(mode);
  }

  function handleFollowUp(payload: AdminIncidentFollowUpPayload) {
    if (!selectedIncidentId) {
      setFeedback({ tone: "error", message: "Selecciona una incidencia." });
      return;
    }
    followUpMutation.mutate({ incidentId: selectedIncidentId, payload });
  }

  function handleResolve(payload: AdminIncidentResolvePayload) {
    if (!selectedIncidentId) {
      setFeedback({ tone: "error", message: "Selecciona una incidencia." });
      return;
    }
    resolveMutation.mutate({ incidentId: selectedIncidentId, payload });
  }

  function handleMarkInProgress(item: AdminIncidentListItem) {
    statusMutation.mutate({
      incidentId: item.id,
      note: "Incidencia marcada en seguimiento desde Backoffice.",
      status: "IN_PROGRESS",
    });
  }

  function handleReopen(item: AdminIncidentListItem) {
    reopenMutation.mutate({
      incidentId: item.id,
      note: "Incidencia reabierta desde Backoffice para seguimiento.",
    });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="quality_hygiene.manage"
        actionLabel="Nueva incidencia"
        description="Registra, clasifica y da seguimiento a problemas operativos, sanitarios, de limpieza, equipo, produccion o inventario."
        meta={[pageStatusLabel]}
        title="Incidencias"
        onAction={() => setWorkflowMode("create")}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminIncidentsFilters
          filters={filters}
          isBackendConnected={incidentList.isBackendConnected}
          options={incidentList.filterOptions}
          onChange={patchFilters}
        />

        <IncidentMetricStrip isLoading={incidentsQuery.isLoading} metrics={incidentList.metrics} />

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => patchFilters({ status: "OPEN" })}
          >
            Ver abiertas
          </button>
          <button
            className="rounded-2xl border border-[var(--ui-color-border)] bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)]"
            type="button"
            onClick={() => patchFilters({ severity: "HIGH" })}
          >
            Ver alto riesgo
          </button>
        </div>

        {workflowMode ? (
          <AdminIncidentWorkflowPanel
            errorMessage={workflowErrorMessage}
            incident={selectedIncident}
            isSubmitting={
              createMutation.isPending || followUpMutation.isPending || resolveMutation.isPending
            }
            mode={workflowMode}
            options={incidentList.filterOptions}
            onAddFollowUp={handleFollowUp}
            onCancel={() => setWorkflowMode(null)}
            onCreate={(payload) => createMutation.mutate(payload)}
            onResolve={handleResolve}
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
          <AdminIncidentsTable
            errorMessage={listErrorMessage}
            incidents={incidentList.items}
            isLoading={incidentsQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedIncidentId={selectedIncidentId}
            total={incidentList.total}
            onAddFollowUp={(item) => handleWorkflow("followUp", item)}
            onCopyFolio={handleCopyFolio}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onResolve={(item) => handleWorkflow("resolve", item)}
            onSelectIncident={handleSelectIncident}
          />

          <AdminIncidentDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={
              detailQuery.isLoading || statusMutation.isPending || reopenMutation.isPending
            }
            selectedIncident={selectedIncident}
            onAddFollowUp={(item) => handleWorkflow("followUp", item)}
            onCopyFolio={handleCopyFolio}
            onMarkInProgress={handleMarkInProgress}
            onReopen={handleReopen}
            onResolve={(item) => handleWorkflow("resolve", item)}
          />
        </div>
      </div>
    </section>
  );
}
