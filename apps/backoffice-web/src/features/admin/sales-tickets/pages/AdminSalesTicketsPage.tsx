import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminSalesTicketsBackendContract,
  fetchAdminSalesTicketDetail,
  fetchAdminSalesTickets,
} from "../api";
import { AdminSalesTicketDetailPanel } from "../components/AdminSalesTicketDetailPanel";
import { AdminSalesTicketsFilters } from "../components/AdminSalesTicketsFilters";
import { AdminSalesTicketsTable } from "../components/AdminSalesTicketsTable";
import type {
  AdminSalesTicketFilterOptions,
  AdminSalesTicketListFilters,
  AdminSalesTicketListItem,
  AdminSalesTicketListResponse,
} from "../types";

const initialFilters: AdminSalesTicketListFilters = {
  page: 1,
  pageSize: 25,
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  maxAmount: null,
  minAmount: null,
  paymentMethod: "all",
  search: "",
  status: "all",
  workstationId: "all",
};

const emptyFilterOptions: AdminSalesTicketFilterOptions = {
  branches: [],
  cashiers: [],
  paymentMethods: [],
  statuses: [],
  workstations: [],
};

const emptyTicketList: AdminSalesTicketListResponse = {
  backendContract: adminSalesTicketsBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    averageTicketAmount: "0.00",
    cardAmount: "0.00",
    cashAmount: "0.00",
    ticketCount: "0",
    ticketsWithReturns: "0",
    totalSalesAmount: "0.00",
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
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(numericValue);
}

function AdminSalesTicketsMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminSalesTicketListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    {
      label: "Ventas",
      title: "Ventas del periodo",
      value: loadingValue ?? formatMoney(metrics.totalSalesAmount),
    },
    { label: "Tickets", title: "Tickets emitidos", value: loadingValue ?? metrics.ticketCount },
    {
      label: "Promedio",
      title: "Ticket promedio",
      value: loadingValue ?? formatMoney(metrics.averageTicketAmount),
    },
    { label: "Efectivo", title: "Cobro en efectivo", value: loadingValue ?? formatMoney(metrics.cashAmount) },
    { label: "Tarjeta", title: "Cobro con tarjeta", value: loadingValue ?? formatMoney(metrics.cardAmount) },
    { label: "Devoluciones", title: "Tickets con devoluciones", value: loadingValue ?? metrics.ticketsWithReturns },
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

export function AdminSalesTicketsPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const [filters, setFilters] = useState<AdminSalesTicketListFilters>(initialFilters);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const ticketsQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminSalesTickets(accessToken ?? "", filters),
    queryKey: ["admin", "sales-tickets", "list", filters],
    retry: false,
  });

  const ticketList = ticketsQuery.data ?? emptyTicketList;
  const selectedTicket = useMemo(
    () => ticketList.items.find((item) => item.id === selectedTicketId) ?? null,
    [selectedTicketId, ticketList.items],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedTicketId),
    queryFn: () => fetchAdminSalesTicketDetail(accessToken ?? "", selectedTicketId ?? ""),
    queryKey: ["admin", "sales-tickets", "detail", selectedTicketId],
    retry: false,
  });

  const listErrorMessage = ticketsQuery.isError
    ? toBackofficeErrorMessage(ticketsQuery.error, "No se pudieron cargar las ventas. Intenta nuevamente.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del ticket.")
    : null;
  const pageStatusLabel = ticketsQuery.isLoading
    ? "Validando API"
    : ticketList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminSalesTicketListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedTicketId(null);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSelectTicket(item: AdminSalesTicketListItem) {
    setSelectedTicketId(item.id);
  }

  function handleCopyFolio(value: AdminSalesTicketListItem | string) {
    const folio = typeof value === "string" ? value : value.folio;
    void navigator.clipboard?.writeText(folio);
    setFeedback({ tone: "success", message: `Folio ${folio} copiado.` });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionLabel="Actualizar"
        description="Consulta ventas confirmadas, pagos, tickets emitidos y contexto operativo de caja."
        meta={[pageStatusLabel]}
        title="Ventas / tickets"
        onAction={() => void ticketsQuery.refetch()}
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminSalesTicketsFilters
          filters={filters}
          isBackendConnected={ticketList.isBackendConnected}
          options={ticketList.filterOptions}
          onChange={patchFilters}
        />

        <AdminSalesTicketsMetricStrip metrics={ticketList.metrics} isLoading={ticketsQuery.isLoading} />

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
          <AdminSalesTicketsTable
            backendContract={ticketList.backendContract}
            errorMessage={listErrorMessage}
            isLoading={ticketsQuery.isLoading}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedTicketId={selectedTicketId}
            tickets={ticketList.items}
            total={ticketList.total}
            onCopyFolio={handleCopyFolio}
            onPageChange={handlePageChange}
            onSelectTicket={handleSelectTicket}
          />

          <AdminSalesTicketDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedTicket={selectedTicket}
            onCopyFolio={handleCopyFolio}
          />
        </div>
      </div>
    </section>
  );
}
