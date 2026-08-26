import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import { adminCashCutsBackendContract, fetchAdminCashCutDetail, fetchAdminCashCuts } from "../api";
import { AdminCashCutDetailPanel } from "../components/AdminCashCutDetailPanel";
import { AdminCashCutsFilters } from "../components/AdminCashCutsFilters";
import { AdminCashCutsTable } from "../components/AdminCashCutsTable";
import type {
  AdminCashCutFilterOptions,
  AdminCashCutListFilters,
  AdminCashCutListItem,
  AdminCashCutsListResponse,
} from "../types";

const initialFilters: AdminCashCutListFilters = {
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  differenceState: "all",
  hasOperationalPayments: "all",
  hasRefunds: "all",
  page: 1,
  pageSize: 25,
  paymentMethod: "all",
  search: "",
  status: "all",
  workstationId: "all",
};

const emptyFilterOptions: AdminCashCutFilterOptions = {
  branches: [],
  cashiers: [],
  differenceStates: [],
  paymentMethods: [],
  statuses: [],
  workstations: [],
};

const emptyCashCutsList: AdminCashCutsListResponse = {
  backendContract: adminCashCutsBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    closedCutsCount: "0",
    countedCashAmount: "0.00",
    cutsWithDifferenceCount: "0",
    expectedCashAmount: "0.00",
    netDifferenceAmount: "0.00",
    netSalesAmount: "0.00",
    operationalPaymentsAmount: "0.00",
    pendingCloseCount: "0",
  },
  page: 1,
  pageSize: 25,
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

function AdminCashCutsMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminCashCutsListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Cortes",
      title: "Cortes del periodo",
      value: loadingValue ?? metrics.closedCutsCount,
    },
    {
      label: "Ventas netas",
      title: "Ventas netas",
      value: loadingValue ?? formatMoney(metrics.netSalesAmount),
    },
    {
      label: "Efectivo esperado",
      title: "Efectivo esperado",
      value: loadingValue ?? formatMoney(metrics.expectedCashAmount),
    },
    {
      label: "Efectivo contado",
      title: "Efectivo contado",
      value: loadingValue ?? formatMoney(metrics.countedCashAmount),
    },
    {
      label: "Diferencia",
      title: "Diferencia neta",
      value: loadingValue ?? formatMoney(metrics.netDifferenceAmount),
    },
    {
      label: "Con diferencia",
      title: "Cortes con diferencia",
      value: loadingValue ?? metrics.cutsWithDifferenceCount,
    },
    {
      label: "Pendientes",
      title: "Pendientes de cierre",
      value: loadingValue ?? metrics.pendingCloseCount,
    },
    {
      label: "Pagos op.",
      title: "Pagos operativos",
      value: loadingValue ?? formatMoney(metrics.operationalPaymentsAmount),
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

export function AdminCashCutsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const [filters, setFilters] = useState<AdminCashCutListFilters>(initialFilters);
  const [selectedCashSessionId, setSelectedCashSessionId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const cashCutsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminCashCuts(accessToken ?? "", filters),
    queryKey: ["admin", "cash-cuts", "list", filters],
    retry: false,
  });

  const cashCutsList = cashCutsQuery.data ?? emptyCashCutsList;
  const selectedCashCut = useMemo(
    () => cashCutsList.items.find((item) => item.cashSessionId === selectedCashSessionId) ?? null,
    [cashCutsList.items, selectedCashSessionId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedCashSessionId),
    queryFn: () => fetchAdminCashCutDetail(accessToken ?? "", selectedCashSessionId ?? ""),
    queryKey: ["admin", "cash-cuts", "detail", selectedCashSessionId],
    retry: false,
  });

  const listErrorMessage = cashCutsQuery.isError
    ? toBackofficeErrorMessage(
        cashCutsQuery.error,
        "No se pudieron cargar los cortes. Intenta nuevamente.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del corte.")
    : null;
  const pageStatusLabel = cashCutsQuery.isLoading
    ? "Validando API"
    : cashCutsList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminCashCutListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedCashSessionId(null);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSelectCashCut(item: AdminCashCutListItem) {
    setSelectedCashSessionId(item.cashSessionId);
  }

  function handleCopyFolio(value: AdminCashCutListItem | string) {
    const folio = typeof value === "string" ? value : value.folio;
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Actualizar"
        description="Consulta cierres de caja, diferencias, ventas incluidas, pagos, devoluciones y contexto operativo por sucursal y estacion."
        meta={[pageStatusLabel]}
        title="Cortes de caja"
        onAction={() => void cashCutsQuery.refetch()}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminCashCutsFilters
          filters={filters}
          isBackendConnected={cashCutsList.isBackendConnected}
          options={cashCutsList.filterOptions}
          onChange={patchFilters}
        />

        <AdminCashCutsMetricStrip
          metrics={cashCutsList.metrics}
          isLoading={cashCutsQuery.isLoading}
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

        <div className="grid min-h-0 min-w-0 flex-1 gap-2.5 xl:grid-cols-[minmax(0,1fr)_minmax(22rem,0.4fr)]">
          <AdminCashCutsTable
            cashCuts={cashCutsList.items}
            errorMessage={listErrorMessage}
            isLoading={cashCutsQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedCashSessionId={selectedCashSessionId}
            total={cashCutsList.total}
            onCopyFolio={handleCopyFolio}
            onPageChange={handlePageChange}
            onSelectCashCut={handleSelectCashCut}
          />

          <AdminCashCutDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedCashCut={selectedCashCut}
            onCopyFolio={handleCopyFolio}
          />
        </div>
      </div>
    </section>
  );
}
