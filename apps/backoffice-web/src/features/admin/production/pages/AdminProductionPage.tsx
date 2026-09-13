import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminProductionBackendContract,
  cancelAdminProduction,
  completeAdminProduction,
  createAdminProduction,
  fetchAdminProduction,
  fetchAdminProductionDetail,
  startAdminProduction,
  updateAdminProduction,
} from "../api";
import { AdminProductionDetailPanel } from "../components/AdminProductionDetailPanel";
import { AdminProductionFilters } from "../components/AdminProductionFilters";
import { AdminProductionTable } from "../components/AdminProductionTable";
import { AdminProductionWorkflowPanel } from "../components/AdminProductionWorkflowPanel";
import type {
  AdminProductionCompletePayload,
  AdminProductionCreatePayload,
  AdminProductionDetail,
  AdminProductionFilterOptions,
  AdminProductionListFilters,
  AdminProductionListItem,
  AdminProductionListResponse,
  AdminProductionUpdatePayload,
} from "../types";

type WorkflowMode = "cancel" | "complete" | "create" | "edit" | "start";

const defaultFilters: AdminProductionListFilters = {
  page: 1,
  pageSize: 25,
  search: "",
  status: "all",
  varianceState: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminProductionFilterOptions = {
  branches: [],
  operators: [],
  products: [],
  recipes: [],
  statuses: [],
};

const emptyProductionList: AdminProductionListResponse = {
  backendContract: adminProductionBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    completedBatches: "0",
    inProgressBatches: "0",
    pendingBatches: "0",
    producedUnits: "0.000",
    totalBatches: "0",
    withShortages: "0",
    withVariance: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminProductionListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }

  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    branchId: params.get("branchId"),
    productId: params.get("productId"),
    recipeId: params.get("recipeId"),
  };
}

function AdminProductionMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminProductionListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Periodo",
      title: "Producciones del periodo",
      value: loadingValue ?? metrics.totalBatches,
    },
    {
      label: "En proceso",
      title: "Lotes en proceso",
      value: loadingValue ?? metrics.inProgressBatches,
    },
    {
      label: "Pendientes",
      title: "Lotes pendientes",
      value: loadingValue ?? metrics.pendingBatches,
    },
    {
      label: "Completadas",
      title: "Lotes completados",
      value: loadingValue ?? metrics.completedBatches,
    },
    {
      label: "Faltantes",
      title: "Con faltantes de insumos",
      value: loadingValue ?? metrics.withShortages,
    },
    {
      label: "Variacion",
      title: "Con variacion de rendimiento",
      value: loadingValue ?? metrics.withVariance,
    },
    {
      label: "Unid. prod.",
      title: "Unidades producidas",
      value: loadingValue ?? metrics.producedUnits,
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

export function AdminProductionPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminProductionListFilters>(getInitialFilters);
  const [selectedProductionId, setSelectedProductionId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode | null>(null);
  const [workflowProductionId, setWorkflowProductionId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const productionQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminProduction(accessToken ?? "", filters),
    queryKey: ["admin", "production", "list", filters],
    retry: false,
  });

  const productionList = productionQuery.data ?? emptyProductionList;
  const selectedProductionPreview = useMemo(
    () => productionList.items.find((item) => item.id === selectedProductionId) ?? null,
    [productionList.items, selectedProductionId],
  );

  const productionDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedProductionId),
    queryFn: () => fetchAdminProductionDetail(accessToken ?? "", selectedProductionId ?? ""),
    queryKey: ["admin", "production", "detail", selectedProductionId],
    retry: false,
  });

  const workflowProductionQuery = useQuery({
    enabled: Boolean(accessToken && workflowProductionId),
    queryFn: () => fetchAdminProductionDetail(accessToken ?? "", workflowProductionId ?? ""),
    queryKey: ["admin", "production", "workflow-detail", workflowProductionId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: async ({
      payload,
      startNow,
    }: {
      payload: AdminProductionCreatePayload;
      startNow: boolean;
    }) => {
      const created = await createAdminProduction(accessToken ?? "", payload);
      if (!startNow) {
        return created;
      }
      return startAdminProduction(accessToken ?? "", created.overview.id, payload.notes ?? null);
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar la produccion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Produccion guardada correctamente." });
      setSelectedProductionId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowProductionId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "production"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      payload,
      productionId,
    }: {
      payload: AdminProductionUpdatePayload;
      productionId: string;
    }) => updateAdminProduction(accessToken ?? "", productionId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el borrador."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Borrador actualizado correctamente." });
      setSelectedProductionId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowProductionId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "production"] });
    },
  });

  const startMutation = useMutation({
    mutationFn: ({ notes, productionId }: { notes?: string | null; productionId: string }) =>
      startAdminProduction(accessToken ?? "", productionId, notes),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo iniciar la produccion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Produccion iniciada correctamente." });
      setSelectedProductionId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowProductionId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "production"] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({
      payload,
      productionId,
    }: {
      payload: AdminProductionCompletePayload;
      productionId: string;
    }) => completeAdminProduction(accessToken ?? "", productionId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo completar la produccion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Produccion completada correctamente." });
      setSelectedProductionId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowProductionId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "production"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: ({ productionId, reason }: { productionId: string; reason?: string | null }) =>
      cancelAdminProduction(accessToken ?? "", productionId, reason),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cancelar la produccion."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Produccion cancelada correctamente." });
      setSelectedProductionId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowProductionId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "production"] });
    },
  });

  const isSubmitting =
    createMutation.isPending ||
    updateMutation.isPending ||
    startMutation.isPending ||
    completeMutation.isPending ||
    cancelMutation.isPending;

  const detailProduction = productionDetailQuery.data ?? null;
  const workflowProduction =
    workflowProductionQuery.data ??
    (workflowProductionId === selectedProductionId ? detailProduction : null);
  const listErrorMessage = productionQuery.isError
    ? toBackofficeErrorMessage(
        productionQuery.error,
        "No se pudo cargar produccion. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = productionDetailQuery.isError
    ? toBackofficeErrorMessage(
        productionDetailQuery.error,
        "No se pudo cargar el detalle de produccion.",
      )
    : null;
  const workflowErrorMessage =
    createMutation.isError ||
    updateMutation.isError ||
    startMutation.isError ||
    completeMutation.isError ||
    cancelMutation.isError
      ? feedback?.tone === "error"
        ? feedback.message
        : "No se pudo completar la operacion."
      : null;
  const pageStatusLabel = productionQuery.isLoading
    ? "Validando API"
    : productionList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminProductionListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedProductionId(null);
  }

  function handleSelectProduction(item: AdminProductionListItem) {
    setSelectedProductionId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function openWorkflow(mode: WorkflowMode, productionId?: string | null) {
    setFeedback(null);
    setWorkflowMode(mode);
    setWorkflowProductionId(productionId ?? null);
    if (productionId) {
      setSelectedProductionId(productionId);
    }
  }

  function openWorkflowFromDetail(mode: WorkflowMode, production: AdminProductionDetail) {
    openWorkflow(mode, production.overview.id);
  }

  function openWorkflowFromList(mode: WorkflowMode, production: AdminProductionListItem) {
    openWorkflow(mode, production.id);
  }

  function closeWorkflow() {
    setWorkflowMode(null);
    setWorkflowProductionId(null);
  }

  function handleCreate(payload: AdminProductionCreatePayload, startNow: boolean) {
    if (!accessToken || isSubmitting) {
      return;
    }
    setFeedback(null);
    createMutation.mutate({ payload, startNow });
  }

  function handleUpdate(payload: AdminProductionUpdatePayload) {
    if (!accessToken || isSubmitting || !workflowProductionId) {
      return;
    }
    setFeedback(null);
    updateMutation.mutate({ payload, productionId: workflowProductionId });
  }

  function handleStart(notes?: string | null) {
    if (!accessToken || isSubmitting || !workflowProductionId) {
      return;
    }
    setFeedback(null);
    startMutation.mutate({ notes, productionId: workflowProductionId });
  }

  function handleComplete(payload: AdminProductionCompletePayload) {
    if (!accessToken || isSubmitting || !workflowProductionId) {
      return;
    }
    setFeedback(null);
    completeMutation.mutate({ payload, productionId: workflowProductionId });
  }

  function handleCancelProduction(reason?: string | null) {
    if (!accessToken || isSubmitting || !workflowProductionId) {
      return;
    }
    setFeedback(null);
    cancelMutation.mutate({ productionId: workflowProductionId, reason });
  }

  function handleOpenBranch(branchId: string) {
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  function handleOpenProduct(productId: string) {
    window.location.href = `/admin/productos?productId=${productId}`;
  }

  function handleOpenRecipe(productId: string) {
    window.location.href = `/admin/recetas-costos?productId=${productId}`;
  }

  function handleOpenInventory(productId: string, branchId: string) {
    window.location.href = `/admin/inventario?productId=${productId}&branchId=${branchId}`;
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="production.manage"
        actionLabel="Nueva produccion"
        description="Planea, ejecuta y cierra lotes de produccion; valida insumos, registra salida terminada y variaciones."
        meta={[pageStatusLabel, "Inventario auditable"]}
        onAction={() => openWorkflow("create")}
        title="Produccion"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminProductionFilters
          filters={filters}
          isBackendConnected={productionList.isBackendConnected}
          options={productionList.filterOptions}
          onChange={patchFilters}
        />

        <AdminProductionMetricStrip
          isLoading={productionQuery.isLoading}
          metrics={productionList.metrics}
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

        {workflowMode ? (
          <AdminProductionWorkflowPanel
            branchOptions={productionList.filterOptions.branches}
            errorMessage={workflowErrorMessage}
            isSubmitting={isSubmitting}
            mode={workflowMode}
            productOptions={productionList.filterOptions.products}
            production={workflowProduction}
            recipeOptions={productionList.filterOptions.recipes}
            onCancelProduction={handleCancelProduction}
            onClose={closeWorkflow}
            onComplete={handleComplete}
            onCreate={handleCreate}
            onStart={handleStart}
            onUpdate={handleUpdate}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,20rem)]">
          <AdminProductionTable
            backendContract={productionList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={productionQuery.isLoading}
            isSubmitting={isSubmitting}
            page={productionList.page}
            pageSize={productionList.pageSize}
            productions={productionList.items}
            selectedProductionId={selectedProductionId}
            total={productionList.total}
            onCancel={(production) => openWorkflowFromList("cancel", production)}
            onComplete={(production) => openWorkflowFromList("complete", production)}
            onOpenProduct={handleOpenProduct}
            onOpenRecipe={handleOpenRecipe}
            onPageChange={handlePageChange}
            onSelectProduction={handleSelectProduction}
            onStart={(production) => openWorkflowFromList("start", production)}
          />
          <AdminProductionDetailPanel
            errorMessage={detailErrorMessage}
            isLoading={productionDetailQuery.isLoading}
            isSubmitting={isSubmitting}
            productionDetail={detailProduction}
            productionPreview={selectedProductionPreview}
            onCancel={(production) => openWorkflowFromDetail("cancel", production)}
            onComplete={(production) => openWorkflowFromDetail("complete", production)}
            onEdit={(production) => openWorkflowFromDetail("edit", production)}
            onOpenBranch={handleOpenBranch}
            onOpenInventory={handleOpenInventory}
            onOpenProduct={handleOpenProduct}
            onOpenRecipe={handleOpenRecipe}
            onStart={(production) => openWorkflowFromDetail("start", production)}
          />
        </div>
      </div>
    </section>
  );
}
