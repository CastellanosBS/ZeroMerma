import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminReconciliationBackendContract,
  createAdminReconciliation,
  fetchAdminReconciliationDetail,
  fetchAdminReconciliations,
  resolveAdminReconciliation,
} from "../api";
import { AdminReconciliationDetailPanel } from "../components/AdminReconciliationDetailPanel";
import { AdminReconciliationFilters } from "../components/AdminReconciliationFilters";
import { AdminReconciliationTable } from "../components/AdminReconciliationTable";
import { AdminReconciliationWorkflowPanel } from "../components/AdminReconciliationWorkflowPanel";
import type {
  AdminPendingDiscrepancyItem,
  AdminReconciliationCreatePayload,
  AdminReconciliationFilterOptions,
  AdminReconciliationListFilters,
  AdminReconciliationListItem,
  AdminReconciliationListResponse,
  AdminReconciliationResolvePayload,
} from "../types";

const initialFilters: AdminReconciliationListFilters = {
  amountMax: "",
  amountMin: "",
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  discrepancyType: "all",
  evidenceState: "all",
  page: 1,
  pageSize: 25,
  paymentMethod: "all",
  search: "",
  sourceType: "all",
  status: "all",
  workstationId: "all",
};

const fallbackReasonOptions = [
  { id: "COUNTING_ERROR", label: "Error de conteo" },
  { id: "CASH_MISSING", label: "Faltante de efectivo" },
  { id: "CASH_OVER", label: "Sobrante de efectivo" },
  { id: "OTHER", label: "Otro" },
];

const emptyFilterOptions: AdminReconciliationFilterOptions = {
  branches: [],
  cashiers: [],
  discrepancyTypes: [],
  evidenceStates: [],
  paymentMethods: [],
  reasonCodes: fallbackReasonOptions,
  sourceTypes: [],
  statuses: [],
  workstations: [],
};

const emptyReconciliationList: AdminReconciliationListResponse = {
  backendContract: adminReconciliationBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    cardTerminalPendingCount: "0",
    cashPendingCount: "0",
    netDifferenceAmount: "0.00",
    overageAmount: "0.00",
    pendingCount: "0",
    reconciledCount: "0",
    shortageAmount: "0.00",
    withEvidenceCount: "0",
  },
  page: 1,
  pageSize: 25,
  pendingDiscrepancies: [],
  total: 0,
};

function formatMoney(value: string) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} MXN`;
  }
  return new Intl.NumberFormat("es-MX", { currency: "MXN", style: "currency" }).format(
    numericValue,
  );
}

function ReconciliationMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminReconciliationListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Pendientes", value: loadingValue ?? metrics.pendingCount },
    { label: "Conciliadas", value: loadingValue ?? metrics.reconciledCount },
    { label: "Dif. neta", value: loadingValue ?? formatMoney(metrics.netDifferenceAmount) },
    { label: "Faltantes", value: loadingValue ?? formatMoney(metrics.shortageAmount) },
    { label: "Sobrantes", value: loadingValue ?? formatMoney(metrics.overageAmount) },
    { label: "Tarjeta", value: loadingValue ?? metrics.cardTerminalPendingCount },
    { label: "Efectivo", value: loadingValue ?? metrics.cashPendingCount },
    { label: "Evidencia", value: loadingValue ?? metrics.withEvidenceCount },
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

function PendingDiscrepanciesPanel({
  items,
  onCreate,
}: {
  items: AdminPendingDiscrepancyItem[];
  onCreate: (item: AdminPendingDiscrepancyItem) => void;
}) {
  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">
            Diferencias pendientes
          </h3>
          <p className="truncate text-xs text-slate-500">
            Cortes con diferencia aun sin documento de conciliacion.
          </p>
        </div>
        <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
          {items.length}
        </span>
      </div>
      <div className="mt-3 grid max-h-48 gap-1.5 overflow-y-auto pr-1">
        {items.length > 0 ? (
          items.map((item) => (
            <article
              className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-sm sm:grid-cols-[minmax(0,1fr)_6.5rem_6.5rem_auto]"
              key={`${item.sourceType}-${item.sourceDocumentId}-${item.paymentMethod}`}
            >
              <span className="min-w-0">
                <span className="block truncate font-semibold text-slate-950">
                  {item.sourceReference}
                </span>
                <span className="block truncate text-xs text-slate-500">
                  {item.branchName} - {item.workstationName}
                </span>
              </span>
              <span className="min-w-0 text-right">
                <span className="block truncate font-semibold text-slate-950">
                  {formatMoney(item.actualAmount)}
                </span>
                <span className="block truncate text-xs text-slate-500">Reportado</span>
              </span>
              <span className="min-w-0 text-right">
                <span className="block truncate font-semibold text-slate-950">
                  {formatMoney(item.differenceAmount)}
                </span>
                <span className="block truncate text-xs text-slate-500">Diferencia</span>
              </span>
              <button
                className="rounded-full border border-[var(--ui-color-border)] bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)]"
                type="button"
                onClick={() => onCreate(item)}
              >
                Conciliar
              </button>
            </article>
          ))
        ) : (
          <p className="rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
            No hay diferencias pendientes de conciliacion.
          </p>
        )}
      </div>
    </section>
  );
}

type WorkflowState =
  | { mode: "create"; source: AdminPendingDiscrepancyItem | null }
  | { mode: "resolve"; reconciliation: AdminReconciliationListItem };

export function AdminReconciliationPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminReconciliationListFilters>(initialFilters);
  const [selectedReconciliationId, setSelectedReconciliationId] = useState<string | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowState | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const reconciliationsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminReconciliations(accessToken ?? "", filters),
    queryKey: ["admin", "reconciliation", "list", filters],
    retry: false,
  });

  const reconciliationList = reconciliationsQuery.data ?? emptyReconciliationList;
  const selectedReconciliation = useMemo(
    () => reconciliationList.items.find((item) => item.id === selectedReconciliationId) ?? null,
    [reconciliationList.items, selectedReconciliationId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedReconciliationId),
    queryFn: () =>
      fetchAdminReconciliationDetail(accessToken ?? "", selectedReconciliationId ?? ""),
    queryKey: ["admin", "reconciliation", "detail", selectedReconciliationId],
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (payload: AdminReconciliationCreatePayload) =>
      createAdminReconciliation(accessToken ?? "", payload),
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Conciliacion ${detail.overview.folio} guardada.` });
      setSelectedReconciliationId(detail.overview.id);
      setWorkflow(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "reconciliation"] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: AdminReconciliationResolvePayload }) =>
      resolveAdminReconciliation(accessToken ?? "", id, payload),
    onSuccess: async (detail) => {
      setFeedback({ tone: "success", message: `Conciliacion ${detail.overview.folio} resuelta.` });
      setSelectedReconciliationId(detail.overview.id);
      setWorkflow(null);
      await queryClient.invalidateQueries({ queryKey: ["admin", "reconciliation"] });
    },
  });

  const listErrorMessage = reconciliationsQuery.isError
    ? toBackofficeErrorMessage(
        reconciliationsQuery.error,
        "No se pudieron cargar las conciliaciones. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(
        detailQuery.error,
        "No se pudo cargar el detalle de la conciliacion.",
      )
    : null;
  const workflowErrorMessage =
    createMutation.isError || resolveMutation.isError
      ? toBackofficeErrorMessage(
          createMutation.error ?? resolveMutation.error,
          "No se pudo guardar la conciliacion.",
        )
      : null;
  const pageStatusLabel = reconciliationsQuery.isLoading
    ? "Validando API"
    : reconciliationList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";
  const reasonOptions =
    reconciliationList.filterOptions.reasonCodes.length > 0
      ? reconciliationList.filterOptions.reasonCodes
      : fallbackReasonOptions;

  function patchFilters(patch: Partial<AdminReconciliationListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedReconciliationId(null);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSelectReconciliation(item: AdminReconciliationListItem) {
    setSelectedReconciliationId(item.id);
  }

  function handleCopyFolio(value: AdminReconciliationListItem | string) {
    const folio = typeof value === "string" ? value : value.folio;
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  function handleCreate(payload: AdminReconciliationCreatePayload) {
    createMutation.mutate(payload);
  }

  function handleResolve(payload: AdminReconciliationResolvePayload) {
    const reconciliation =
      workflow?.mode === "resolve" ? workflow.reconciliation : selectedReconciliation;
    if (!reconciliation) {
      setFeedback({
        tone: "error",
        message: "Selecciona una conciliacion para resolverla.",
      });
      return;
    }
    resolveMutation.mutate({ id: reconciliation.id, payload });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Nueva conciliacion"
        description="Revisa diferencias de caja y medios de pago, documenta causas y resuelve discrepancias con trazabilidad."
        meta={[pageStatusLabel]}
        title="Conciliacion"
        onAction={() => setWorkflow({ mode: "create", source: null })}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminReconciliationFilters
          filters={filters}
          isBackendConnected={reconciliationList.isBackendConnected}
          options={reconciliationList.filterOptions}
          onChange={patchFilters}
        />

        <ReconciliationMetricStrip
          isLoading={reconciliationsQuery.isLoading}
          metrics={reconciliationList.metrics}
        />

        <PendingDiscrepanciesPanel
          items={reconciliationList.pendingDiscrepancies}
          onCreate={(source) => setWorkflow({ mode: "create", source })}
        />

        {workflow ? (
          <AdminReconciliationWorkflowPanel
            errorMessage={workflowErrorMessage}
            isSubmitting={createMutation.isPending || resolveMutation.isPending}
            mode={workflow.mode}
            reasonOptions={reasonOptions}
            reconciliation={workflow.mode === "resolve" ? workflow.reconciliation : null}
            source={workflow.mode === "create" ? workflow.source : null}
            onCancel={() => setWorkflow(null)}
            onCreate={handleCreate}
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

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.4fr)]">
          <AdminReconciliationTable
            errorMessage={listErrorMessage}
            isLoading={reconciliationsQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            reconciliations={reconciliationList.items}
            selectedReconciliationId={selectedReconciliationId}
            total={reconciliationList.total}
            onCopyFolio={handleCopyFolio}
            onPageChange={handlePageChange}
            onResolve={(item) => {
              handleSelectReconciliation(item);
              setWorkflow({ mode: "resolve", reconciliation: item });
            }}
            onSelectReconciliation={handleSelectReconciliation}
          />

          <AdminReconciliationDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedReconciliation={selectedReconciliation}
            onCopyFolio={handleCopyFolio}
            onResolve={(item) => setWorkflow({ mode: "resolve", reconciliation: item })}
          />
        </div>
      </div>
    </section>
  );
}
