import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminTransferBackendContract,
  cancelAdminTransfer,
  createAdminTransfer,
  dispatchAdminTransfer,
  fetchAdminTransferDetail,
  fetchAdminTransfers,
  receiveAdminTransfer,
  updateAdminTransfer,
} from "../api";
import { AdminTransferDetailPanel } from "../components/AdminTransferDetailPanel";
import { AdminTransferWorkflowPanel } from "../components/AdminTransferWorkflowPanel";
import { AdminTransfersFilters } from "../components/AdminTransfersFilters";
import { AdminTransfersTable } from "../components/AdminTransfersTable";
import type {
  AdminTransferCreatePayload,
  AdminTransferDetail,
  AdminTransferFilterOptions,
  AdminTransferListFilters,
  AdminTransferListItem,
  AdminTransferListResponse,
  AdminTransferReceivePayload,
  AdminTransferUpdatePayload,
} from "../types";

type WorkflowMode = "cancel" | "create" | "dispatch" | "edit" | "receive";

const defaultFilters: AdminTransferListFilters = {
  discrepancyState: "all",
  page: 1,
  pageSize: 25,
  search: "",
  status: "all",
};

const emptyFilterOptions: AdminTransferFilterOptions = {
  branches: [],
  operators: [],
  products: [],
  statuses: [],
};

const emptyTransferList: AdminTransferListResponse = {
  backendContract: adminTransferBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    cancelledTransfers: "0",
    inTransitTransfers: "0",
    pendingReceiptTransfers: "0",
    receivedTransfers: "0",
    totalTransfers: "0",
    unitsInTransit: "0",
    withDiscrepancies: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function getInitialFilters(): AdminTransferListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }

  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    destinationBranchId: params.get("destinationBranchId"),
    originBranchId: params.get("originBranchId") ?? params.get("branchId"),
    productId: params.get("productId"),
  };
}

function AdminTransferMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminTransferListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Periodo",
      title: "Transferencias del periodo",
      value: loadingValue ?? metrics.totalTransfers,
    },
    {
      label: "En transito",
      title: "Transferencias en transito",
      value: loadingValue ?? metrics.inTransitTransfers,
    },
    {
      label: "Pend. recepcion",
      title: "Pendientes de recepcion",
      value: loadingValue ?? metrics.pendingReceiptTransfers,
    },
    {
      label: "Discrepancias",
      title: "Con discrepancias",
      value: loadingValue ?? metrics.withDiscrepancies,
    },
    { label: "Recibidas", title: "Recibidas", value: loadingValue ?? metrics.receivedTransfers },
    {
      label: "Unid. transito",
      title: "Unidades en transito",
      value: loadingValue ?? metrics.unitsInTransit,
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

export function AdminTransfersPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminTransferListFilters>(getInitialFilters);
  const [selectedTransferId, setSelectedTransferId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode | null>(null);
  const [workflowTransferId, setWorkflowTransferId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const transfersQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminTransfers(accessToken ?? "", filters),
    queryKey: ["admin", "transfers", "list", filters],
    retry: false,
  });

  const transferList = transfersQuery.data ?? emptyTransferList;
  const selectedTransferPreview = useMemo(
    () => transferList.items.find((item) => item.id === selectedTransferId) ?? null,
    [selectedTransferId, transferList.items],
  );

  const transferDetailQuery = useQuery({
    enabled: Boolean(accessToken && selectedTransferId),
    queryFn: () => fetchAdminTransferDetail(accessToken ?? "", selectedTransferId ?? ""),
    queryKey: ["admin", "transfers", "detail", selectedTransferId],
    retry: false,
  });

  const workflowTransferQuery = useQuery({
    enabled: Boolean(accessToken && workflowTransferId),
    queryFn: () => fetchAdminTransferDetail(accessToken ?? "", workflowTransferId ?? ""),
    queryKey: ["admin", "transfers", "workflow-detail", workflowTransferId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: async ({
      dispatchNow,
      payload,
    }: {
      dispatchNow: boolean;
      payload: AdminTransferCreatePayload;
    }) => {
      const created = await createAdminTransfer(accessToken ?? "", payload);
      if (!dispatchNow) {
        return created;
      }
      return dispatchAdminTransfer(accessToken ?? "", created.overview.id, payload.notes ?? null);
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo guardar la transferencia."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Transferencia guardada correctamente." });
      setSelectedTransferId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowTransferId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "transfers"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      payload,
      transferId,
    }: {
      payload: AdminTransferUpdatePayload;
      transferId: string;
    }) => updateAdminTransfer(accessToken ?? "", transferId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el borrador."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Borrador actualizado correctamente." });
      setSelectedTransferId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowTransferId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "transfers"] });
    },
  });

  const dispatchMutation = useMutation({
    mutationFn: ({ notes, transferId }: { notes?: string | null; transferId: string }) =>
      dispatchAdminTransfer(accessToken ?? "", transferId, notes),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo enviar la transferencia."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Transferencia enviada correctamente." });
      setSelectedTransferId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowTransferId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "transfers"] });
    },
  });

  const receiveMutation = useMutation({
    mutationFn: ({
      payload,
      transferId,
    }: {
      payload: AdminTransferReceivePayload;
      transferId: string;
    }) => receiveAdminTransfer(accessToken ?? "", transferId, payload),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo recibir la transferencia."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Recepcion registrada correctamente." });
      setSelectedTransferId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowTransferId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "transfers"] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: ({ reason, transferId }: { reason?: string | null; transferId: string }) =>
      cancelAdminTransfer(accessToken ?? "", transferId, reason),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo cancelar la transferencia."),
      });
    },
    onSuccess: (detail) => {
      setFeedback({ tone: "success", message: "Transferencia cancelada correctamente." });
      setSelectedTransferId(detail.overview.id);
      setWorkflowMode(null);
      setWorkflowTransferId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "transfers"] });
    },
  });

  const isSubmitting =
    createMutation.isPending ||
    updateMutation.isPending ||
    dispatchMutation.isPending ||
    receiveMutation.isPending ||
    cancelMutation.isPending;

  const detailTransfer = transferDetailQuery.data ?? null;
  const workflowTransfer =
    workflowTransferQuery.data ??
    (workflowTransferId === selectedTransferId ? detailTransfer : null);
  const listErrorMessage = transfersQuery.isError
    ? toBackofficeErrorMessage(
        transfersQuery.error,
        "No se pudo cargar transferencias. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = transferDetailQuery.isError
    ? toBackofficeErrorMessage(
        transferDetailQuery.error,
        "No se pudo cargar el detalle de transferencia.",
      )
    : null;
  const workflowErrorMessage =
    createMutation.isError ||
    updateMutation.isError ||
    dispatchMutation.isError ||
    receiveMutation.isError ||
    cancelMutation.isError
      ? feedback?.tone === "error"
        ? feedback.message
        : "No se pudo completar la operacion."
      : null;
  const pageStatusLabel = transfersQuery.isLoading
    ? "Validando API"
    : transferList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminTransferListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedTransferId(null);
  }

  function handleSelectTransfer(item: AdminTransferListItem) {
    setSelectedTransferId(item.id);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function openWorkflow(mode: WorkflowMode, transferId?: string | null) {
    setFeedback(null);
    setWorkflowMode(mode);
    setWorkflowTransferId(transferId ?? null);
    if (transferId) {
      setSelectedTransferId(transferId);
    }
  }

  function openWorkflowFromDetail(mode: WorkflowMode, transfer: AdminTransferDetail) {
    openWorkflow(mode, transfer.overview.id);
  }

  function openWorkflowFromList(mode: WorkflowMode, transfer: AdminTransferListItem) {
    openWorkflow(mode, transfer.id);
  }

  function closeWorkflow() {
    setWorkflowMode(null);
    setWorkflowTransferId(null);
  }

  function handleCreate(payload: AdminTransferCreatePayload, dispatchNow: boolean) {
    if (!accessToken || isSubmitting) {
      return;
    }
    setFeedback(null);
    createMutation.mutate({ dispatchNow, payload });
  }

  function handleUpdate(payload: AdminTransferUpdatePayload) {
    if (!accessToken || isSubmitting || !workflowTransferId) {
      return;
    }
    setFeedback(null);
    updateMutation.mutate({ payload, transferId: workflowTransferId });
  }

  function handleDispatch(notes?: string | null) {
    if (!accessToken || isSubmitting || !workflowTransferId) {
      return;
    }
    setFeedback(null);
    dispatchMutation.mutate({ notes, transferId: workflowTransferId });
  }

  function handleReceive(payload: AdminTransferReceivePayload) {
    if (!accessToken || isSubmitting || !workflowTransferId) {
      return;
    }
    setFeedback(null);
    receiveMutation.mutate({ payload, transferId: workflowTransferId });
  }

  function handleCancelTransfer(reason?: string | null) {
    if (!accessToken || isSubmitting || !workflowTransferId) {
      return;
    }
    setFeedback(null);
    cancelMutation.mutate({ reason, transferId: workflowTransferId });
  }

  function handleOpenBranch(branchId: string) {
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  function handleOpenInventory(productId: string, branchId: string) {
    window.location.href = `/admin/inventario?productId=${productId}&branchId=${branchId}`;
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="transfers.manage"
        actionLabel="Nueva transferencia"
        description="Gestiona movimientos de inventario entre sucursales, envios, recepciones y discrepancias."
        meta={[pageStatusLabel, "Inventario auditable"]}
        onAction={() => openWorkflow("create")}
        title="Transferencias"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminTransfersFilters
          filters={filters}
          isBackendConnected={transferList.isBackendConnected}
          options={transferList.filterOptions}
          onChange={patchFilters}
        />

        <AdminTransferMetricStrip
          isLoading={transfersQuery.isLoading}
          metrics={transferList.metrics}
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
          <AdminTransferWorkflowPanel
            branchOptions={transferList.filterOptions.branches}
            errorMessage={workflowErrorMessage}
            isSubmitting={isSubmitting}
            mode={workflowMode}
            productOptions={transferList.filterOptions.products}
            transfer={workflowTransfer}
            onCancelTransfer={handleCancelTransfer}
            onClose={closeWorkflow}
            onCreate={handleCreate}
            onDispatch={handleDispatch}
            onReceive={handleReceive}
            onUpdate={handleUpdate}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 items-stretch gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(15rem,20rem)]">
          <AdminTransfersTable
            backendContract={transferList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={transfersQuery.isLoading}
            isSubmitting={isSubmitting}
            page={transferList.page}
            pageSize={transferList.pageSize}
            selectedTransferId={selectedTransferId}
            total={transferList.total}
            transfers={transferList.items}
            onCancel={(transfer) => openWorkflowFromList("cancel", transfer)}
            onDispatch={(transfer) => openWorkflowFromList("dispatch", transfer)}
            onOpenBranch={handleOpenBranch}
            onPageChange={handlePageChange}
            onReceive={(transfer) => openWorkflowFromList("receive", transfer)}
            onSelectTransfer={handleSelectTransfer}
          />
          <AdminTransferDetailPanel
            errorMessage={detailErrorMessage}
            isLoading={transferDetailQuery.isLoading}
            isSubmitting={isSubmitting}
            transferDetail={detailTransfer}
            transferPreview={selectedTransferPreview}
            onCancel={(transfer) => openWorkflowFromDetail("cancel", transfer)}
            onDispatch={(transfer) => openWorkflowFromDetail("dispatch", transfer)}
            onEdit={(transfer) => openWorkflowFromDetail("edit", transfer)}
            onOpenBranch={handleOpenBranch}
            onOpenInventory={handleOpenInventory}
            onReceive={(transfer) => openWorkflowFromDetail("receive", transfer)}
          />
        </div>
      </div>
    </section>
  );
}
