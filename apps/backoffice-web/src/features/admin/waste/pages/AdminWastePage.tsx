import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminWasteBackendContract,
  createAdminWaste,
  fetchAdminWaste,
  fetchAdminWasteDetail,
} from "../api";
import { AdminWasteDetailPanel } from "../components/AdminWasteDetailPanel";
import { AdminWasteFilters } from "../components/AdminWasteFilters";
import { AdminWasteTable } from "../components/AdminWasteTable";
import { AdminWasteWorkflowPanel } from "../components/AdminWasteWorkflowPanel";
import type {
  AdminWasteCreatePayload,
  AdminWasteFilterOptions,
  AdminWasteListFilters,
  AdminWasteListItem,
  AdminWasteListResponse,
} from "../types";

const defaultFilters: AdminWasteListFilters = {
  evidenceState: "all",
  impactLevel: "all",
  locationCode: "all",
  page: 1,
  pageSize: 25,
  reasonCode: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminWasteFilterOptions = {
  branches: [],
  classes: [],
  evidenceStates: [],
  impactLevels: [],
  locations: [],
  operators: [],
  productKinds: [],
  products: [],
  reasons: [],
  statuses: [],
};

const emptyWasteList: AdminWasteListResponse = {
  backendContract: adminWasteBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    contaminatedOrDamaged: "0",
    evidenceRecords: "0",
    estimatedValue: "0",
    expiredRecords: "0",
    highImpactRecords: "0",
    totalQuantity: "0.000",
    totalRecords: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminWasteListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }

  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    branchId: params.get("branchId"),
    productId: params.get("productId"),
  };
}

function AdminWasteMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminWasteListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Periodo", title: "Mermas del periodo", value: loadingValue ?? metrics.totalRecords },
    { label: "Unidades", title: "Unidades dadas de baja", value: loadingValue ?? metrics.totalQuantity },
    { label: "Valor est.", title: "Valor estimado", value: loadingValue ?? metrics.estimatedValue },
    { label: "Caducidad", title: "Por caducidad", value: loadingValue ?? metrics.expiredRecords },
    { label: "Dano/cont.", title: "Por dano o contaminacion", value: loadingValue ?? metrics.contaminatedOrDamaged },
    { label: "Alto impacto", title: "Alto impacto", value: loadingValue ?? metrics.highImpactRecords },
    { label: "Evidencia", title: "Con evidencia", value: loadingValue ?? metrics.evidenceRecords },
  ];

  return (
    <section className="flex min-w-0 flex-wrap items-center gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs text-slate-600">
      <span className="shrink-0 font-semibold uppercase tracking-[0.12em] text-slate-500">Resumen</span>
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

export function AdminWastePage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminWasteListFilters>(getInitialFilters);
  const [selectedWasteId, setSelectedWasteId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const wasteQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminWaste(accessToken ?? "", filters),
    queryKey: ["admin", "waste", "list", filters],
    retry: false,
  });

  const wasteList = wasteQuery.data ?? emptyWasteList;
  const selectedWastePreview = useMemo(
    () => wasteList.items.find((item) => item.id === selectedWasteId) ?? null,
    [selectedWasteId, wasteList.items],
  );

  const wasteDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedWasteId),
    queryFn: () => fetchAdminWasteDetail(accessToken ?? "", selectedWasteId ?? ""),
    queryKey: ["admin", "waste", "detail", selectedWasteId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminWasteCreatePayload) => createAdminWaste(accessToken ?? "", payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo confirmar la merma."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Merma confirmada correctamente." });
      setSelectedWasteId(detail.overview.id);
      setIsCreateOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["admin", "waste"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "inventory"] });
    },
  });

  const listErrorMessage = wasteQuery.isError
    ? toBackofficeErrorMessage(wasteQuery.error, "No se pudo cargar merma. Intenta nuevamente.")
    : null;
  const detailErrorMessage = wasteDetailQuery.isError
    ? toBackofficeErrorMessage(wasteDetailQuery.error, "No se pudo cargar el detalle de merma.")
    : null;
  const workflowErrorMessage =
    createMutation.isError && feedback?.tone === "error" ? feedback.message : null;
  const pageStatusLabel = wasteQuery.isLoading
    ? "Validando API"
    : wasteList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminWasteListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedWasteId(null);
  }

  function handleSelectWaste(item: AdminWasteListItem) {
    setSelectedWasteId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleOpenBranch(branchId: string) {
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  function handleOpenProduct(productId: string) {
    window.location.href = `/admin/productos?productId=${productId}`;
  }

  function handleOpenInventory(productId: string, branchId: string) {
    window.location.href = `/admin/inventario?productId=${productId}&branchId=${branchId}`;
  }

  function handleOpenCorrection(wasteId: string) {
    window.location.href = `/admin/devoluciones-correcciones?sourceDocumentId=${wasteId}`;
  }

  function handleCreate(payload: AdminWasteCreatePayload) {
    if (!accessToken || createMutation.isPending) {
      return;
    }
    setFeedback(null);
    createMutation.mutate(payload);
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nueva merma"
        description="Registra, consulta y audita perdidas de inventario por sucursal, producto, motivo e impacto operativo."
        meta={[pageStatusLabel, "Movimiento auditable"]}
        onAction={() => {
          setFeedback(null);
          setIsCreateOpen(true);
        }}
        title="Merma"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminWasteFilters
          filters={filters}
          isBackendConnected={wasteList.isBackendConnected}
          options={wasteList.filterOptions}
          onChange={patchFilters}
        />

        <AdminWasteMetricStrip isLoading={wasteQuery.isLoading} metrics={wasteList.metrics} />

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

        {isCreateOpen ? (
          <AdminWasteWorkflowPanel
            branchOptions={wasteList.filterOptions.branches}
            errorMessage={workflowErrorMessage}
            isSubmitting={createMutation.isPending}
            locationOptions={wasteList.filterOptions.locations}
            productOptions={wasteList.filterOptions.products}
            reasonOptions={wasteList.filterOptions.reasons}
            onClose={() => setIsCreateOpen(false)}
            onCreate={handleCreate}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,20rem)]">
          <AdminWasteTable
            backendContract={wasteList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={wasteQuery.isLoading}
            isSubmitting={createMutation.isPending}
            page={wasteList.page}
            pageSize={wasteList.pageSize}
            selectedWasteId={selectedWasteId}
            total={wasteList.total}
            wasteRecords={wasteList.items}
            onOpenInventory={handleOpenInventory}
            onOpenProduct={handleOpenProduct}
            onPageChange={handlePageChange}
            onSelectWaste={handleSelectWaste}
          />
          <AdminWasteDetailPanel
            errorMessage={detailErrorMessage}
            isLoading={wasteDetailQuery.isLoading}
            wasteDetail={wasteDetailQuery.data ?? null}
            wastePreview={selectedWastePreview}
            onOpenBranch={handleOpenBranch}
            onOpenCorrection={handleOpenCorrection}
            onOpenInventory={handleOpenInventory}
            onOpenProduct={handleOpenProduct}
          />
        </div>
      </div>
    </section>
  );
}
