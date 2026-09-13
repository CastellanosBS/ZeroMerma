import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminCorrectionsBackendContract,
  adminReturnsBackendContract,
  fetchAdminCorrectionDetail,
  fetchAdminCorrections,
  fetchAdminReturnDetail,
  fetchAdminReturns,
} from "../api";
import { AdminReturnCorrectionDetailPanel } from "../components/AdminReturnCorrectionDetailPanel";
import { AdminReturnsCorrectionsFilters } from "../components/AdminReturnsCorrectionsFilters";
import { AdminReturnsCorrectionsTable } from "../components/AdminReturnsCorrectionsTable";
import type {
  AdminCorrectionFilterOptions,
  AdminCorrectionListFilters,
  AdminCorrectionsListResponse,
  AdminReturnFilterOptions,
  AdminReturnListFilters,
  AdminReturnsCorrectionsTab,
  AdminReturnsListResponse,
} from "../types";

const initialReturnFilters: AdminReturnListFilters = {
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  maxAmount: null,
  minAmount: null,
  operatorId: "all",
  page: 1,
  pageSize: 25,
  refundMethod: "all",
  search: "",
  status: "all",
};

const initialCorrectionFilters: AdminCorrectionListFilters = {
  branchId: "all",
  correctionType: "all",
  dateFrom: null,
  dateTo: null,
  netEffect: "all",
  operatorId: "all",
  page: 1,
  pageSize: 25,
  reasonCode: "all",
  search: "",
  status: "all",
  targetDocumentType: "all",
};

const emptyReturnOptions: AdminReturnFilterOptions = {
  branches: [],
  operators: [],
  refundMethods: [],
  statuses: [],
};

const emptyCorrectionOptions: AdminCorrectionFilterOptions = {
  branches: [],
  correctionTypes: [],
  operators: [],
  reasons: [],
  statuses: [],
  targetDocumentTypes: [],
};

const emptyReturnsList: AdminReturnsListResponse = {
  backendContract: adminReturnsBackendContract,
  filterOptions: emptyReturnOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    cashRefundedAmount: "0.00",
    pendingReviewCount: 0,
    refundedAmount: "0.00",
    returnedLineCount: 0,
    returnsCount: 0,
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

const emptyCorrectionsList: AdminCorrectionsListResponse = {
  backendContract: adminCorrectionsBackendContract,
  filterOptions: emptyCorrectionOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    correctionsCount: 0,
    negativeEffectCount: 0,
    pendingReviewCount: 0,
    positiveEffectCount: 0,
    totalUnitsAffected: "0.000",
  },
  page: 1,
  pageSize: 25,
  total: 0,
};

function formatMoney(value: string, currencyCode = "MXN") {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) {
    return `${value} ${currencyCode}`;
  }
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(
    numericValue,
  );
}

function AdminReturnsCorrectionsMetricStrip({
  activeTab,
  corrections,
  isLoading,
  returns,
}: {
  activeTab: AdminReturnsCorrectionsTab;
  corrections: AdminCorrectionsListResponse["metrics"];
  isLoading: boolean;
  returns: AdminReturnsListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Devoluciones",
      title: "Devoluciones del periodo",
      value: loadingValue ?? String(returns.returnsCount),
    },
    {
      label: "Reembolsado",
      title: "Monto reembolsado",
      value: loadingValue ?? formatMoney(returns.refundedAmount),
    },
    {
      label: "Lineas dev.",
      title: "Articulos devueltos",
      value: loadingValue ?? String(returns.returnedLineCount),
    },
    {
      label: "Correcciones",
      title: "Correcciones registradas",
      value: loadingValue ?? String(corrections.correctionsCount),
    },
    {
      label: "Unid. afectadas",
      title: "Unidades afectadas por correcciones",
      value: loadingValue ?? corrections.totalUnitsAffected,
    },
    {
      label: "Revision",
      title: "Pendientes de revision",
      value: loadingValue ?? String(returns.pendingReviewCount + corrections.pendingReviewCount),
    },
  ];

  return (
    <section className="flex min-w-0 flex-wrap items-center gap-2 rounded-[18px] border border-[var(--ui-color-border)] bg-white px-3 py-2 text-xs text-slate-600">
      <span className="shrink-0 font-semibold uppercase tracking-[0.12em] text-slate-500">
        {activeTab === "returns" ? "Resumen devoluciones" : "Resumen correcciones"}
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

export function AdminReturnsCorrectionsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const [activeTab, setActiveTab] = useState<AdminReturnsCorrectionsTab>("returns");
  const [returnFilters, setReturnFilters] = useState<AdminReturnListFilters>(initialReturnFilters);
  const [correctionFilters, setCorrectionFilters] =
    useState<AdminCorrectionListFilters>(initialCorrectionFilters);
  const [selectedReturnId, setSelectedReturnId] = useState<string | null>(null);
  const [selectedCorrectionId, setSelectedCorrectionId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const returnsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminReturns(accessToken ?? "", returnFilters),
    queryKey: ["admin", "returns-corrections", "returns", returnFilters],
    retry: false,
  });

  const correctionsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminCorrections(accessToken ?? "", correctionFilters),
    queryKey: ["admin", "returns-corrections", "corrections", correctionFilters],
    retry: false,
  });

  const returnsList = returnsQuery.data ?? emptyReturnsList;
  const correctionsList = correctionsQuery.data ?? emptyCorrectionsList;
  const activeList = activeTab === "returns" ? returnsList : correctionsList;
  const isActiveLoading =
    activeTab === "returns" ? returnsQuery.isLoading : correctionsQuery.isLoading;

  const selectedReturn = useMemo(
    () => returnsList.items.find((item) => item.id === selectedReturnId) ?? null,
    [returnsList.items, selectedReturnId],
  );
  const selectedCorrection = useMemo(
    () => correctionsList.items.find((item) => item.id === selectedCorrectionId) ?? null,
    [correctionsList.items, selectedCorrectionId],
  );

  const returnDetailQuery = useQuery({
    enabled: Boolean(accessToken && activeTab === "returns" && selectedReturnId),
    queryFn: () => fetchAdminReturnDetail(accessToken ?? "", selectedReturnId ?? ""),
    queryKey: ["admin", "returns-corrections", "returns", "detail", selectedReturnId],
    retry: false,
  });

  const correctionDetailQuery = useQuery({
    enabled: Boolean(accessToken && activeTab === "corrections" && selectedCorrectionId),
    queryFn: () => fetchAdminCorrectionDetail(accessToken ?? "", selectedCorrectionId ?? ""),
    queryKey: ["admin", "returns-corrections", "corrections", "detail", selectedCorrectionId],
    retry: false,
  });

  const listErrorMessage =
    activeTab === "returns" && returnsQuery.isError
      ? toBackofficeErrorMessage(returnsQuery.error, "No se pudieron cargar las devoluciones.")
      : activeTab === "corrections" && correctionsQuery.isError
        ? toBackofficeErrorMessage(
            correctionsQuery.error,
            "No se pudieron cargar las correcciones.",
          )
        : null;
  const detailErrorMessage =
    activeTab === "returns" && returnDetailQuery.isError
      ? toBackofficeErrorMessage(
          returnDetailQuery.error,
          "No se pudo cargar el detalle de la devolucion.",
        )
      : activeTab === "corrections" && correctionDetailQuery.isError
        ? toBackofficeErrorMessage(
            correctionDetailQuery.error,
            "No se pudo cargar el detalle de la correccion.",
          )
        : null;
  const pageStatusLabel =
    returnsQuery.isLoading || correctionsQuery.isLoading
      ? "Validando API"
      : returnsList.isBackendConnected && correctionsList.isBackendConnected
        ? "Datos conectados"
        : "Integracion parcial";

  function patchReturnFilters(patch: Partial<AdminReturnListFilters>) {
    setReturnFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedReturnId(null);
  }

  function patchCorrectionFilters(patch: Partial<AdminCorrectionListFilters>) {
    setCorrectionFilters((current) => ({ ...current, ...patch, page: patch.page ?? 1 }));
    setSelectedCorrectionId(null);
  }

  function handlePageChange(tab: AdminReturnsCorrectionsTab, page: number) {
    if (tab === "returns") {
      setReturnFilters((current) => ({ ...current, page }));
      return;
    }
    setCorrectionFilters((current) => ({ ...current, page }));
  }

  function handleCopyFolio(folio: string) {
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  function handleRefresh() {
    setFeedback(null);
    void returnsQuery.refetch();
    void correctionsQuery.refetch();
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="returns_corrections.view"
        actionLabel="Actualizar"
        description="Consulta devoluciones, reembolsos y ajustes auditados vinculados a ventas, tickets y documentos operativos."
        meta={[pageStatusLabel]}
        title="Devoluciones / correcciones"
        onAction={handleRefresh}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          {(["returns", "corrections"] as const).map((tab) => {
            const isSelected = activeTab === tab;
            const label = tab === "returns" ? "Devoluciones" : "Correcciones";
            const count = tab === "returns" ? returnsList.total : correctionsList.total;
            return (
              <button
                className={[
                  "inline-flex min-w-0 items-center gap-2 rounded-full border px-3 py-1.5 text-sm font-semibold transition focus:outline-none focus:ring-4 focus:ring-[var(--ui-color-ring)]",
                  isSelected
                    ? "border-[var(--ui-color-primary)] bg-[var(--ui-color-primary)] text-white"
                    : "border-[var(--ui-color-border)] bg-white text-slate-700 hover:border-[var(--ui-color-info)] hover:text-[var(--ui-color-info)]",
                ].join(" ")}
                key={tab}
                type="button"
                onClick={() => {
                  setActiveTab(tab);
                  setFeedback(null);
                }}
              >
                <span className="truncate">{label}</span>
                <span
                  className={[
                    "rounded-full px-2 py-0.5 text-xs",
                    isSelected ? "bg-white/20 text-white" : "bg-slate-100 text-slate-600",
                  ].join(" ")}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        <AdminReturnsCorrectionsFilters
          correctionFilters={correctionFilters}
          correctionOptions={correctionsList.filterOptions}
          returnFilters={returnFilters}
          returnOptions={returnsList.filterOptions}
          tab={activeTab}
          onCorrectionChange={patchCorrectionFilters}
          onReturnChange={patchReturnFilters}
        />

        <AdminReturnsCorrectionsMetricStrip
          activeTab={activeTab}
          corrections={correctionsList.metrics}
          isLoading={returnsQuery.isLoading || correctionsQuery.isLoading}
          returns={returnsList.metrics}
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

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1fr)_minmax(21rem,0.38fr)]">
          <AdminReturnsCorrectionsTable
            activeTab={activeTab}
            corrections={correctionsList.items}
            errorMessage={listErrorMessage}
            isLoading={isActiveLoading}
            page={activeTab === "returns" ? returnFilters.page : correctionFilters.page}
            pageSize={activeTab === "returns" ? returnFilters.pageSize : correctionFilters.pageSize}
            returns={returnsList.items}
            selectedCorrectionId={selectedCorrectionId}
            selectedReturnId={selectedReturnId}
            total={activeList.total}
            onCopyFolio={handleCopyFolio}
            onPageChange={handlePageChange}
            onSelectCorrection={(item) => {
              setSelectedCorrectionId(item.id);
              setSelectedReturnId(null);
            }}
            onSelectReturn={(item) => {
              setSelectedReturnId(item.id);
              setSelectedCorrectionId(null);
            }}
          />

          <AdminReturnCorrectionDetailPanel
            activeTab={activeTab}
            correctionDetail={correctionDetailQuery.data ?? null}
            detailErrorMessage={detailErrorMessage}
            isLoading={
              activeTab === "returns"
                ? returnDetailQuery.isLoading
                : correctionDetailQuery.isLoading
            }
            returnDetail={returnDetailQuery.data ?? null}
            selectedCorrection={selectedCorrection}
            selectedReturn={selectedReturn}
          />
        </div>
      </div>
    </section>
  );
}
