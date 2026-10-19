import { isCommandIntentionPending } from "@zeromerma/api-client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useEffect, useMemo, useRef, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminPurchaseBackendContract,
  type PurchaseCommandResultView,
  fetchAdminPurchaseDetail,
  fetchAdminPurchases,
} from "../api";
import { AdminPurchaseDetailPanel } from "../components/AdminPurchaseDetailPanel";
import { AdminPurchasesFilters } from "../components/AdminPurchasesFilters";
import { AdminPurchasesTable } from "../components/AdminPurchasesTable";
import { AdminPurchaseWorkflowPanel } from "../components/AdminPurchaseWorkflowPanel";
import type {
  AdminDirectEntryPayload,
  AdminPurchaseCancelPayload,
  AdminPurchaseDetail,
  AdminPurchaseFilterOptions,
  AdminPurchaseListFilters,
  AdminPurchaseListItem,
  AdminPurchaseListResponse,
  AdminPurchasePayload,
  AdminPurchaseReceiptPayload,
} from "../types";

import { purchaseIntentions, type PurchaseIntentionPayload } from "../purchase-command-intent";

import { usePurchaseIntention } from "../use-purchase-intention";

const defaultFilters: AdminPurchaseListFilters = {
  discrepancyState: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const emptyFilterOptions: AdminPurchaseFilterOptions = {
  branches: [],
  operators: [],
  productKinds: [],
  products: [],
  statuses: [],
  suppliers: [],
};

const emptyPurchaseList: AdminPurchaseListResponse = {
  backendContract: adminPurchaseBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeSuppliersUsed: "0",
    confirmedEntries: "0",
    partiallyReceived: "0",
    pendingReceipt: "0",
    totalAmount: "0",
    totalDocuments: "0",
    withDiscrepancies: "0",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

type WorkflowMode = "purchase" | "direct" | "receive" | "cancel";

function getInitialFilters(): AdminPurchaseListFilters {
  if (typeof window === "undefined") {
    return defaultFilters;
  }
  const params = new URLSearchParams(window.location.search);
  return {
    ...defaultFilters,
    branchId: params.get("branchId"),
    supplierId: params.get("supplierId"),
  };
}

function AdminPurchaseMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminPurchaseListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Compras",
      title: "Compras del periodo",
      value: loadingValue ?? metrics.totalDocuments,
    },
    { label: "Monto", title: "Monto comprado", value: loadingValue ?? metrics.totalAmount },
    {
      label: "Pendientes",
      title: "Pendientes de recepcion",
      value: loadingValue ?? metrics.pendingReceipt,
    },
    {
      label: "Parciales",
      title: "Recibidas parcialmente",
      value: loadingValue ?? metrics.partiallyReceived,
    },
    {
      label: "Confirmadas",
      title: "Entradas confirmadas",
      value: loadingValue ?? metrics.confirmedEntries,
    },
    {
      label: "Discrepancias",
      title: "Con discrepancias",
      value: loadingValue ?? metrics.withDiscrepancies,
    },
    {
      label: "Proveedores",
      title: "Proveedores activos usados",
      value: loadingValue ?? metrics.activeSuppliersUsed,
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

function getPurchaseId(item: AdminPurchaseDetail | AdminPurchaseListItem): string {
  return "overview" in item ? item.overview.id : item.id;
}

export function AdminPurchasesPage() {
  const isAuthenticated = useBackofficeAuthStore((state) => state.isAuthenticated);
  const queryClient = useQueryClient();

  const user = useBackofficeAuthStore((state) => state.user);

  const intention = usePurchaseIntention();

  const observedKey = useRef<string | null | undefined>(undefined);

  const [filters, setFilters] = useState<AdminPurchaseListFilters>(getInitialFilters);
  const [selectedPurchaseId, setSelectedPurchaseId] = useState<string | null>(null);
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const purchasesQuery = useQuery({
    enabled: isAuthenticated,
    queryFn: () => fetchAdminPurchases(filters),
    queryKey: ["admin", "purchases", "list", filters],
    retry: false,
  });

  const purchaseList = purchasesQuery.data ?? emptyPurchaseList;
  const selectedPurchasePreview = useMemo(
    () => purchaseList.items.find((item) => item.id === selectedPurchaseId) ?? null,
    [purchaseList.items, selectedPurchaseId],
  );

  const purchaseDetailQuery = useQuery({
    enabled: Boolean(isAuthenticated && selectedPurchaseId),
    queryFn: () => fetchAdminPurchaseDetail(selectedPurchaseId ?? ""),
    queryKey: ["admin", "purchases", "detail", selectedPurchaseId],
    retry: false,
  });

  function confirmed(result: PurchaseCommandResultView) {
    setFeedback({ tone: "success", message: `${result.folio}: operación confirmada.` });

    setSelectedPurchaseId(result.id);

    setWorkflowMode(null);

    void queryClient.invalidateQueries({ queryKey: ["admin", "purchases"] });
  }

  function begin(
    payload: PurchaseIntentionPayload,
    branchId: string,
    purchaseId: string | null = null,
  ) {
    if (!user) throw new Error("Se requiere el operador original.");

    return purchaseIntentions.begin(
      { userId: user.id, branchId, purchaseId, commandCode: payload.commandCode },
      payload,
      observedKey.current ?? null,
    );
  }

  function branchFor(purchaseId: string) {
    const branch =
      purchaseDetailQuery.data?.overview.id === purchaseId
        ? purchaseDetailQuery.data.overview.branchId
        : purchaseList.items.find((item) => item.id === purchaseId)?.branchId;

    if (!branch) throw new Error("Actualiza el detalle de la compra antes de continuar.");

    return branch;
  }

  const mutationOptions = {
    onSuccess: confirmed,

    onError: (error: unknown) =>
      setFeedback({
        tone: "error" as const,
        message: toBackofficeErrorMessage(error, "No se pudo confirmar la operación de compra."),
      }),
  };

  const createPurchaseMutation = useMutation({
    ...mutationOptions,

    mutationFn: (payload: AdminPurchasePayload) =>
      begin({ commandCode: "create", body: payload }, payload.branchId),
  });

  const directEntryMutation = useMutation({
    ...mutationOptions,

    mutationFn: (payload: AdminDirectEntryPayload) =>
      begin({ commandCode: "direct-entry", body: payload }, payload.branchId),
  });

  const receiveMutation = useMutation({
    ...mutationOptions,

    mutationFn: ({
      payload,
      purchaseId,
    }: {
      payload: AdminPurchaseReceiptPayload;
      purchaseId: string;
    }) => begin({ commandCode: "receive", body: payload }, branchFor(purchaseId), purchaseId),
  });

  const confirmMutation = useMutation({
    ...mutationOptions,

    mutationFn: (purchaseId: string) =>
      begin({ commandCode: "confirm" }, branchFor(purchaseId), purchaseId),
  });

  const cancelMutation = useMutation({
    ...mutationOptions,

    mutationFn: ({
      payload,
      purchaseId,
    }: {
      payload: AdminPurchaseCancelPayload;
      purchaseId: string;
    }) => begin({ commandCode: "cancel", body: payload }, branchFor(purchaseId), purchaseId),
  });

  const recoveryMutation = useMutation({
    ...mutationOptions,

    mutationFn: (retry: boolean) => {
      const metadata = intention.metadata;

      if (!metadata || metadata.userId !== user?.id)
        throw new Error("Se requiere el operador original.");

      return retry ? purchaseIntentions.retry(metadata) : purchaseIntentions.recover(metadata);
    },
  });

  useEffect(() => {
    const key = intention.metadata?.key ?? null;
    if (observedKey.current === undefined) {
      observedKey.current =
        intention.metadata?.status === "CONFIRMED" || intention.metadata?.status === "REJECTED"
          ? key
          : null;
    } else if (intention.metadata?.status === "CONFIRMED") {
      if (key !== observedKey.current) {
        setWorkflowMode(null);
        void queryClient.invalidateQueries({ queryKey: ["admin", "purchases"] });
      }
      observedKey.current = key;
    } else if (intention.metadata?.status === "REJECTED") observedKey.current = key;
  }, [intention.metadata?.key, intention.metadata?.status, queryClient]);

  const purchaseDetail = purchaseDetailQuery.data ?? null;
  const listErrorMessage = purchasesQuery.isError
    ? toBackofficeErrorMessage(purchasesQuery.error, "No se pudieron cargar compras.")
    : null;
  const detailErrorMessage = purchaseDetailQuery.isError
    ? toBackofficeErrorMessage(purchaseDetailQuery.error, "No se pudo cargar el detalle de compra.")
    : null;
  const workflowErrorMessage = feedback?.tone === "error" ? feedback.message : null;
  const isSubmitting =
    Boolean(intention.error) ||
    isCommandIntentionPending(intention.metadata) ||
    recoveryMutation.isPending ||
    createPurchaseMutation.isPending ||
    directEntryMutation.isPending ||
    receiveMutation.isPending ||
    confirmMutation.isPending ||
    cancelMutation.isPending;
  const pageStatusLabel = purchasesQuery.isLoading
    ? "Validando API"
    : purchaseList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminPurchaseListFilters>) {
    setFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedPurchaseId(null);
    setWorkflowMode(null);
  }

  function handleSelectPurchase(item: AdminPurchaseListItem) {
    setSelectedPurchaseId(item.id);
    setWorkflowMode(null);
  }

  function handleOpenWorkflow(
    mode: WorkflowMode,
    purchase?: AdminPurchaseDetail | AdminPurchaseListItem | null,
  ) {
    if (isSubmitting) return;

    setFeedback(null);
    if (purchase) {
      setSelectedPurchaseId(getPurchaseId(purchase));
    }
    setWorkflowMode(mode);
  }

  function handleConfirm(purchase: AdminPurchaseDetail | AdminPurchaseListItem) {
    if (!isAuthenticated || isSubmitting) {
      return;
    }
    setFeedback(null);
    confirmMutation.mutate(getPurchaseId(purchase));
  }

  function handleSubmitReceipt(payload: AdminPurchaseReceiptPayload) {
    if (!isAuthenticated || !selectedPurchaseId || isSubmitting) {
      return;
    }
    setFeedback(null);
    receiveMutation.mutate({ payload, purchaseId: selectedPurchaseId });
  }

  function handleSubmitCancel(payload: AdminPurchaseCancelPayload) {
    if (!isAuthenticated || !selectedPurchaseId || isSubmitting) {
      return;
    }
    setFeedback(null);
    cancelMutation.mutate({ payload, purchaseId: selectedPurchaseId });
  }

  function handleOpenSupplier(supplierId: string) {
    window.location.href = `/admin/proveedores?supplierId=${supplierId}`;
  }

  function handleOpenBranch(branchId: string) {
    window.location.href = `/admin/sucursales?branchId=${branchId}`;
  }

  function handleOpenProduct(productId: string) {
    window.location.href = `/admin/productos?productId=${productId}`;
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="purchases.manage"
        actionLabel="Nueva compra"
        actionDisabled={isSubmitting}
        description="Registra compras a proveedores, entradas de mercancia, recepciones parciales e impacto en inventario."
        meta={[pageStatusLabel, "Recepcion auditable"]}
        onAction={() => handleOpenWorkflow("purchase")}
        title="Compras / entradas"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        {intention.error || isCommandIntentionPending(intention.metadata) ? (
          <section role="alert" className="rounded-xl border border-amber-400 bg-amber-50 p-3">
            <h2>Compra pendiente de confirmar</h2>

            <p>
              {intention.error ??
                "Consulta el resultado antes de iniciar otra operación de compra."}
            </p>

            {intention.metadata ? (
              <>
                <p>
                  Referencia: {intention.metadata.key} · {intention.metadata.commandCode}
                </p>

                <button
                  type="button"
                  disabled={recoveryMutation.isPending || intention.metadata.userId !== user?.id}
                  onClick={() => recoveryMutation.mutate(false)}
                >
                  Consultar resultado de compra
                </button>

                {purchaseIntentions.hasBody(intention.metadata.key) &&
                intention.metadata.status !== "CONFLICT" ? (
                  <button
                    type="button"
                    disabled={recoveryMutation.isPending || intention.metadata.userId !== user?.id}
                    onClick={() => recoveryMutation.mutate(true)}
                  >
                    Reintentar el mismo comando
                  </button>
                ) : (
                  <p>Tras recargar sólo se consulta el resultado.</p>
                )}
              </>
            ) : null}
          </section>
        ) : null}

        <div className="flex min-w-0 flex-wrap gap-2">
          <button
            className="rounded-full bg-[var(--ui-color-info)] px-3 py-1.5 text-sm font-semibold text-white transition hover:brightness-95 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => handleOpenWorkflow("purchase")}
          >
            Nueva compra
          </button>
          <button
            className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]"
            type="button"
            onClick={() => handleOpenWorkflow("direct")}
          >
            Nueva entrada directa
          </button>
        </div>

        <AdminPurchasesFilters
          filters={filters}
          isBackendConnected={purchaseList.isBackendConnected}
          options={purchaseList.filterOptions}
          onChange={patchFilters}
        />
        <AdminPurchaseMetricStrip
          isLoading={purchasesQuery.isLoading}
          metrics={purchaseList.metrics}
        />

        {feedback && workflowMode === null ? (
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

        {workflowMode === "receive" && !purchaseDetail ? (
          <aside className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-4 text-sm text-slate-600">
            Cargando lineas pendientes para recibir mercancia.
          </aside>
        ) : workflowMode ? (
          <AdminPurchaseWorkflowPanel
            errorMessage={workflowErrorMessage}
            isSubmitting={isSubmitting}
            mode={workflowMode}
            options={purchaseList.filterOptions}
            purchase={purchaseDetail}
            onClose={() => setWorkflowMode(null)}
            onSubmitCancel={handleSubmitCancel}
            onSubmitDirectEntry={(payload) => {
              if (!isAuthenticated || isSubmitting) {
                return;
              }
              setFeedback(null);
              directEntryMutation.mutate(payload);
            }}
            onSubmitPurchase={(payload) => {
              if (!isAuthenticated || isSubmitting) {
                return;
              }
              setFeedback(null);
              createPurchaseMutation.mutate(payload);
            }}
            onSubmitReceipt={handleSubmitReceipt}
          />
        ) : null}

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 overflow-hidden xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.42fr)]">
          <AdminPurchasesTable
            backendContract={purchaseList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={purchasesQuery.isLoading}
            isSubmitting={isSubmitting}
            page={purchaseList.page}
            pageSize={purchaseList.pageSize}
            purchases={purchaseList.items}
            selectedPurchaseId={selectedPurchaseId}
            total={purchaseList.total}
            onCancel={(purchase) => handleOpenWorkflow("cancel", purchase)}
            onConfirm={handleConfirm}
            onOpenBranch={handleOpenBranch}
            onOpenSupplier={handleOpenSupplier}
            onPageChange={(page) => setFilters((current) => ({ ...current, page }))}
            onReceive={(purchase) => handleOpenWorkflow("receive", purchase)}
            onSelectPurchase={handleSelectPurchase}
          />
          <AdminPurchaseDetailPanel
            errorMessage={detailErrorMessage}
            isLoading={purchaseDetailQuery.isLoading}
            purchaseDetail={purchaseDetail}
            purchasePreview={selectedPurchasePreview}
            onCancel={(purchase) => handleOpenWorkflow("cancel", purchase)}
            onConfirm={handleConfirm}
            onOpenBranch={handleOpenBranch}
            onOpenProduct={handleOpenProduct}
            onOpenSupplier={handleOpenSupplier}
            onReceive={(purchase) => handleOpenWorkflow("receive", purchase)}
          />
        </div>
      </div>
    </section>
  );
}
