import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminWorkstationsBackendContract,
  createAdminWorkstation,
  fetchAdminWorkstationDetail,
  fetchAdminWorkstations,
  updateAdminWorkstation,
} from "../api";
import { AdminWorkstationDetailPanel } from "../components/AdminWorkstationDetailPanel";
import { AdminWorkstationFormPanel } from "../components/AdminWorkstationFormPanel";
import { AdminWorkstationsFilters } from "../components/AdminWorkstationsFilters";
import { AdminWorkstationsTable } from "../components/AdminWorkstationsTable";
import type {
  AdminWorkstationCreatePayload,
  AdminWorkstationDetail,
  AdminWorkstationFilterOptions,
  AdminWorkstationListFilters,
  AdminWorkstationListItem,
  AdminWorkstationListResponse,
  AdminWorkstationUpdatePayload,
} from "../types";

const defaultFilters: AdminWorkstationListFilters = {
  cashSessionState: "all",
  page: 1,
  pageSize: 25,
  readiness: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminWorkstationFilterOptions = {
  branches: [],
};

const emptyWorkstationList: AdminWorkstationListResponse = {
  backendContract: adminWorkstationsBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeWorkstations: "0",
    inactiveWorkstations: "0",
    totalWorkstations: "0",
    withOpenCashSession: "0",
    withWarnings: "0",
    withoutActiveBranch: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminWorkstationListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }

  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    branchId: params.get("branchId"),
  };
}

function AdminWorkstationsMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminWorkstationListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Total",
      title: "Estaciones totales",
      value: loadingValue ?? metrics.totalWorkstations,
    },
    {
      label: "Activas",
      title: "Estaciones activas",
      value: loadingValue ?? metrics.activeWorkstations,
    },
    {
      label: "Inactivas",
      title: "Estaciones inactivas",
      value: loadingValue ?? metrics.inactiveWorkstations,
    },
    {
      label: "Caja abierta",
      title: "Estaciones con caja abierta",
      value: loadingValue ?? metrics.withOpenCashSession,
    },
    {
      label: "Sucursal inactiva",
      title: "Estaciones con sucursal inactiva",
      value: loadingValue ?? metrics.withoutActiveBranch,
    },
    {
      label: "Revisar",
      title: "Estaciones con advertencias",
      value: loadingValue ?? metrics.withWarnings,
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
          title={`${item.title}: ${item.value}`}
        >
          <span className="truncate text-slate-500">{item.label}</span>
          <span className="truncate font-semibold text-slate-950">{item.value}</span>
        </span>
      ))}
    </section>
  );
}

function toUpdatePayload(
  payload: AdminWorkstationCreatePayload | AdminWorkstationUpdatePayload,
): AdminWorkstationUpdatePayload {
  return {
    branchId: payload.branchId ?? null,
    code: payload.code ?? null,
    isActive: payload.isActive ?? null,
    name: payload.name ?? null,
  };
}

function getWorkstationId(workstation: AdminWorkstationDetail | AdminWorkstationListItem): string {
  return "overview" in workstation ? workstation.overview.id : workstation.id;
}

function getWorkstationStatus(
  workstation: AdminWorkstationDetail | AdminWorkstationListItem,
): "active" | "inactive" {
  return "overview" in workstation ? workstation.overview.status : workstation.status;
}

function getWorkstationName(
  workstation: AdminWorkstationDetail | AdminWorkstationListItem,
): string {
  return "overview" in workstation ? workstation.overview.name : workstation.name;
}

function getWorkstationWarnings(workstation: AdminWorkstationDetail | AdminWorkstationListItem) {
  return "overview" in workstation ? workstation.warnings : workstation.warnings;
}

function hasOpenCashSession(
  workstation: AdminWorkstationDetail | AdminWorkstationListItem,
): boolean {
  if ("cashSessionContext" in workstation) {
    return Boolean(workstation.cashSessionContext.activeSession);
  }

  return workstation.hasActiveCashSession;
}

export function AdminWorkstationsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminWorkstationListFilters>(getInitialFilters);
  const [formMode, setFormMode] = useState<
    "create" | { type: "edit"; detail: AdminWorkstationDetail } | null
  >(null);
  const [pendingEditWorkstationId, setPendingEditWorkstationId] = useState<string | null>(null);
  const [selectedWorkstationId, setSelectedWorkstationId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const workstationsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminWorkstations(accessToken ?? "", filters),
    queryKey: ["admin", "workstations", "list", filters],
    retry: false,
  });

  const workstationList = workstationsQuery.data ?? emptyWorkstationList;
  const selectedWorkstationPreview = useMemo(
    () => workstationList.items.find((item) => item.id === selectedWorkstationId) ?? null,
    [workstationList.items, selectedWorkstationId],
  );

  const workstationDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedWorkstationId),
    queryFn: () => fetchAdminWorkstationDetail(accessToken ?? "", selectedWorkstationId ?? ""),
    queryKey: ["admin", "workstations", "detail", selectedWorkstationId],
    retry: false,
  });

  const createWorkstationMutation = useMutation({
    mutationFn: (payload: AdminWorkstationCreatePayload) =>
      createAdminWorkstation(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo crear la estacion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Estacion creada correctamente." });
      setFormMode(null);
      setSelectedWorkstationId(detail.overview.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "workstations"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "branches"] });
    },
  });

  const updateWorkstationMutation = useMutation({
    mutationFn: ({
      payload,
      workstationId,
    }: {
      payload: AdminWorkstationUpdatePayload;
      workstationId: string;
    }) => updateAdminWorkstation(accessToken ?? "", workstationId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar la estacion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Estacion actualizada correctamente." });
      setFormMode(null);
      setPendingEditWorkstationId(null);
      setSelectedWorkstationId(detail.overview.id);
      void queryClient.invalidateQueries({ queryKey: ["admin", "workstations"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "branches"] });
    },
  });

  useEffect(() => {
    if (
      pendingEditWorkstationId &&
      workstationDetailQuery.data?.overview.id === pendingEditWorkstationId
    ) {
      setFormMode({ type: "edit", detail: workstationDetailQuery.data });
      setPendingEditWorkstationId(null);
    }
  }, [pendingEditWorkstationId, workstationDetailQuery.data]);

  const detailWorkstation = workstationDetailQuery.data ?? null;
  const listErrorMessage = workstationsQuery.isError
    ? toBackofficeErrorMessage(
        workstationsQuery.error,
        "No se pudieron cargar las estaciones. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = workstationDetailQuery.isError
    ? toBackofficeErrorMessage(
        workstationDetailQuery.error,
        "No se pudo cargar el detalle de la estacion.",
      )
    : null;
  const formErrorMessage =
    createWorkstationMutation.isError || updateWorkstationMutation.isError
      ? toBackofficeErrorMessage(
          createWorkstationMutation.error ?? updateWorkstationMutation.error,
          "No se pudo guardar.",
        )
      : null;
  const pageStatusLabel = workstationsQuery.isLoading
    ? "Validando API"
    : workstationList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";
  const isSaving = createWorkstationMutation.isPending || updateWorkstationMutation.isPending;

  function patchFilters(patch: Partial<AdminWorkstationListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedWorkstationId(null);
  }

  function handleSelectWorkstation(item: AdminWorkstationListItem) {
    setSelectedWorkstationId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleEditWorkstation(workstation: AdminWorkstationDetail | AdminWorkstationListItem) {
    const workstationId = getWorkstationId(workstation);
    setFeedback(null);
    setSelectedWorkstationId(workstationId);
    if ("overview" in workstation) {
      setFormMode({ type: "edit", detail: workstation });
      return;
    }
    if (detailWorkstation?.overview.id === workstationId) {
      setFormMode({ type: "edit", detail: detailWorkstation });
      return;
    }
    setPendingEditWorkstationId(workstationId);
  }

  function handleSubmitWorkstation(
    payload: AdminWorkstationCreatePayload | AdminWorkstationUpdatePayload,
  ) {
    if (!accessToken || isSaving) {
      return;
    }

    setFeedback(null);
    if (formMode && formMode !== "create") {
      updateWorkstationMutation.mutate({
        payload: toUpdatePayload(payload),
        workstationId: formMode.detail.overview.id,
      });
      return;
    }

    createWorkstationMutation.mutate(payload as AdminWorkstationCreatePayload);
  }

  function handleToggleStatus(workstation: AdminWorkstationDetail | AdminWorkstationListItem) {
    if (!accessToken || updateWorkstationMutation.isPending) {
      return;
    }

    const workstationId = getWorkstationId(workstation);
    const currentStatus = getWorkstationStatus(workstation);
    const nextStatus = currentStatus === "active" ? "inactive" : "active";
    const warnings = getWorkstationWarnings(workstation);

    if (currentStatus === "active" && hasOpenCashSession(workstation)) {
      setFeedback({
        tone: "error",
        message: "Esta estacion tiene una caja abierta. Cierra la caja antes de desactivarla.",
      });
      return;
    }

    const warningText =
      currentStatus === "active" && warnings.length > 0
        ? `\n\nAdvertencias actuales: ${warnings.map((warning) => warning.message).join(" ")}`
        : "";

    if (
      !window.confirm(
        `${nextStatus === "active" ? "Activar" : "Desactivar"} ${getWorkstationName(workstation)}?${warningText}`,
      )
    ) {
      return;
    }

    setFeedback(null);
    updateWorkstationMutation.mutate({
      payload: { isActive: nextStatus === "active" },
      workstationId,
    });
  }

  function handleCopyCode(item: AdminWorkstationListItem) {
    void navigator.clipboard?.writeText(item.code);
    setFeedback({ tone: "success", message: `Codigo copiado: ${item.code}` });
  }

  function handleOpenBranch(branchIdOrItem: string | AdminWorkstationListItem) {
    const branchId = typeof branchIdOrItem === "string" ? branchIdOrItem : branchIdOrItem.branchId;
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="workstations.manage"
        actionLabel="Nueva estacion"
        description="Administra las estaciones de operacion del POS, su sucursal, estado y preparacion para abrir caja."
        meta={[pageStatusLabel]}
        onAction={() => {
          setFeedback(null);
          setFormMode("create");
        }}
        title="Cajas / estaciones"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminWorkstationsFilters
          filters={filters}
          isBackendConnected={workstationList.isBackendConnected}
          options={workstationList.filterOptions}
          onChange={patchFilters}
        />

        <AdminWorkstationsMetricStrip
          metrics={workstationList.metrics}
          isLoading={workstationsQuery.isLoading}
        />

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

        {pendingEditWorkstationId && workstationDetailQuery.isLoading ? (
          <p className="rounded-[18px] border border-[var(--ui-color-border)] bg-slate-50 px-4 py-3 text-sm font-semibold text-slate-600">
            Cargando detalle para editar.
          </p>
        ) : null}

        {formMode ? (
          <AdminWorkstationFormPanel
            branchOptions={workstationList.filterOptions.branches}
            errorMessage={formErrorMessage}
            isSubmitting={isSaving}
            key={formMode === "create" ? "create" : formMode.detail.overview.id}
            workstationDetail={formMode === "create" ? null : formMode.detail}
            onClose={() => {
              setFormMode(null);
              setPendingEditWorkstationId(null);
            }}
            onSubmit={handleSubmitWorkstation}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,19rem)]">
          <AdminWorkstationsTable
            backendContract={workstationList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={workstationsQuery.isLoading}
            isUpdating={updateWorkstationMutation.isPending}
            page={workstationList.page}
            pageSize={workstationList.pageSize}
            selectedWorkstationId={selectedWorkstationId}
            total={workstationList.total}
            workstations={workstationList.items}
            onCopyCode={handleCopyCode}
            onEditWorkstation={handleEditWorkstation}
            onOpenBranch={handleOpenBranch}
            onPageChange={handlePageChange}
            onSelectWorkstation={handleSelectWorkstation}
            onToggleStatus={handleToggleStatus}
          />
          <AdminWorkstationDetailPanel
            errorMessage={detailErrorMessage}
            isLoading={workstationDetailQuery.isLoading}
            workstationDetail={detailWorkstation}
            workstationPreview={selectedWorkstationPreview}
            onEdit={handleEditWorkstation}
            onOpenBranch={handleOpenBranch}
            onToggleStatus={handleToggleStatus}
          />
        </div>
      </div>
    </section>
  );
}
