import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminCashFlowBackendContract,
  fetchAdminCashFlowMovementDetail,
  fetchAdminCashFlowMovements,
} from "../api";
import { AdminCashFlowDetailPanel } from "../components/AdminCashFlowDetailPanel";
import { AdminCashFlowFilters } from "../components/AdminCashFlowFilters";
import { AdminCashFlowTable } from "../components/AdminCashFlowTable";
import type {
  AdminCashFlowFilterOptions,
  AdminCashFlowListFilters,
  AdminCashFlowListResponse,
  AdminCashFlowMovementListItem,
  AdminCashFlowTrendPoint,
} from "../types";

const initialFilters: AdminCashFlowListFilters = {
  amountMax: "",
  amountMin: "",
  branchId: "all",
  category: "all",
  dateFrom: null,
  dateTo: null,
  direction: "all",
  operatorId: "all",
  page: 1,
  pageSize: 25,
  paymentMethod: "all",
  reconciliationState: "all",
  search: "",
  sourceType: "all",
  workstationId: "all",
};

const emptyFilterOptions: AdminCashFlowFilterOptions = {
  branches: [],
  categories: [],
  directions: [],
  operators: [],
  paymentMethods: [],
  reconciliationStates: [],
  sourceTypes: [],
  workstations: [],
};

const emptyCashFlowList: AdminCashFlowListResponse = {
  backendContract: adminCashFlowBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  page: 1,
  pageSize: 25,
  summary: {
    cardTotal: "0.00",
    cashTotal: "0.00",
    differenceTotal: "0.00",
    inflowsTotal: "0.00",
    netTotal: "0.00",
    operationalPaymentsTotal: "0.00",
    outflowsTotal: "0.00",
    pendingReconciliationTotal: "0.00",
    refundsTotal: "0.00",
  },
  total: 0,
  trend: [],
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

function CashFlowMetricStrip({
  isLoading,
  summary,
}: {
  isLoading: boolean;
  summary: AdminCashFlowListResponse["summary"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Entradas", value: loadingValue ?? formatMoney(summary.inflowsTotal) },
    { label: "Salidas", value: loadingValue ?? formatMoney(summary.outflowsTotal) },
    { label: "Flujo neto", value: loadingValue ?? formatMoney(summary.netTotal) },
    { label: "Efectivo", value: loadingValue ?? formatMoney(summary.cashTotal) },
    { label: "Tarjeta", value: loadingValue ?? formatMoney(summary.cardTotal) },
    {
      label: "Pagos op.",
      value: loadingValue ?? formatMoney(summary.operationalPaymentsTotal),
    },
    { label: "Devoluciones", value: loadingValue ?? formatMoney(summary.refundsTotal) },
    {
      label: "Pendiente conciliacion",
      value: loadingValue ?? formatMoney(summary.pendingReconciliationTotal),
    },
    { label: "Diferencias caja", value: loadingValue ?? formatMoney(summary.differenceTotal) },
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

function CashFlowTrendPanel({ trend }: { trend: AdminCashFlowTrendPoint[] }) {
  const maxValue = Math.max(
    1,
    ...trend.map((point) =>
      Math.max(Math.abs(Number(point.inflows)), Math.abs(Number(point.outflows))),
    ),
  );

  return (
    <section className="rounded-[20px] border border-[var(--ui-color-border)] bg-white p-3">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-slate-950">Tendencia del periodo</h3>
          <p className="truncate text-xs text-slate-500">
            Entradas, salidas y flujo neto agrupados por dia desde documentos reales.
          </p>
        </div>
        <span className="rounded-full border border-[var(--ui-color-border)] bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600">
          {trend.length} dias
        </span>
      </div>
      {trend.length === 0 ? (
        <p className="mt-3 rounded-[14px] border border-dashed border-[var(--ui-color-border)] px-3 py-3 text-sm text-slate-600">
          No hay datos suficientes para mostrar la tendencia del periodo.
        </p>
      ) : (
        <div className="mt-3 grid max-h-44 gap-2 overflow-y-auto pr-1">
          {trend.map((point) => {
            const inflowWidth = `${Math.max(5, (Math.abs(Number(point.inflows)) / maxValue) * 100)}%`;
            const outflowWidth = `${Math.max(5, (Math.abs(Number(point.outflows)) / maxValue) * 100)}%`;
            return (
              <article
                className="grid min-w-0 gap-2 rounded-[14px] border border-[var(--ui-color-border)] bg-slate-50 px-3 py-2 text-xs sm:grid-cols-[7rem_minmax(0,1fr)_7rem]"
                key={point.date}
              >
                <span className="font-semibold text-slate-700">{point.date}</span>
                <span className="grid min-w-0 gap-1.5">
                  <span className="h-2 rounded-full bg-emerald-100">
                    <span
                      className="block h-2 rounded-full bg-[var(--ui-color-success)]"
                      style={{ width: inflowWidth }}
                    />
                  </span>
                  <span className="h-2 rounded-full bg-amber-100">
                    <span
                      className="block h-2 rounded-full bg-[var(--ui-color-warning)]"
                      style={{ width: outflowWidth }}
                    />
                  </span>
                </span>
                <span className="text-right font-semibold text-slate-950">
                  {formatMoney(point.net)}
                </span>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export function AdminCashFlowPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const [filters, setFilters] = useState<AdminCashFlowListFilters>(initialFilters);
  const [selectedMovementId, setSelectedMovementId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const cashFlowQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminCashFlowMovements(accessToken ?? "", filters),
    queryKey: ["admin", "cash-flow", "list", filters],
    retry: false,
  });

  const cashFlowList = cashFlowQuery.data ?? emptyCashFlowList;
  const selectedMovement = useMemo(
    () => cashFlowList.items.find((item) => item.id === selectedMovementId) ?? null,
    [cashFlowList.items, selectedMovementId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedMovementId),
    queryFn: () => fetchAdminCashFlowMovementDetail(accessToken ?? "", selectedMovementId ?? ""),
    queryKey: ["admin", "cash-flow", "detail", selectedMovementId],
    retry: false,
  });

  const listErrorMessage = cashFlowQuery.isError
    ? toBackofficeErrorMessage(
        cashFlowQuery.error,
        "No se pudieron cargar los movimientos de flujo de efectivo.",
      )
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del movimiento.")
    : null;
  const pageStatusLabel = cashFlowQuery.isLoading
    ? "Validando API"
    : cashFlowList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminCashFlowListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedMovementId(null);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSelectMovement(item: AdminCashFlowMovementListItem) {
    setSelectedMovementId(item.id);
  }

  function handleCopyReference(value: AdminCashFlowMovementListItem | string) {
    const reference = typeof value === "string" ? value : value.sourceReference;
    void navigator.clipboard?.writeText(reference);
    setFeedback({ tone: "success", message: `Folio ${reference} copiado.` });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Actualizar"
        description="Analiza entradas, salidas, flujo neto, metodos de pago y documentos que explican el movimiento de caja."
        meta={[pageStatusLabel]}
        title="Flujo de efectivo"
        onAction={() => void cashFlowQuery.refetch()}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminCashFlowFilters
          filters={filters}
          isBackendConnected={cashFlowList.isBackendConnected}
          options={cashFlowList.filterOptions}
          onChange={patchFilters}
        />

        <CashFlowMetricStrip isLoading={cashFlowQuery.isLoading} summary={cashFlowList.summary} />
        <CashFlowTrendPanel trend={cashFlowList.trend} />

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
          <AdminCashFlowTable
            errorMessage={listErrorMessage}
            isLoading={cashFlowQuery.isLoading}
            movements={cashFlowList.items}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedMovementId={selectedMovementId}
            total={cashFlowList.total}
            onCopyReference={handleCopyReference}
            onPageChange={handlePageChange}
            onSelectMovement={handleSelectMovement}
          />

          <AdminCashFlowDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedMovement={selectedMovement}
            onCopyReference={handleCopyReference}
          />
        </div>
      </div>
    </section>
  );
}
