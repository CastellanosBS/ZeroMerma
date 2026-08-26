import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import {
  adminOrdersBackendContract,
  cancelAdminOrder,
  deliverAdminOrder,
  fetchAdminOrderDetail,
  fetchAdminOrders,
  markAdminOrderReady,
} from "../api";
import { AdminOrderDetailPanel } from "../components/AdminOrderDetailPanel";
import { AdminOrdersFilters } from "../components/AdminOrdersFilters";
import { AdminOrdersTable } from "../components/AdminOrdersTable";
import type {
  AdminOrderDetail,
  AdminOrderFilterOptions,
  AdminOrderListFilters,
  AdminOrderListItem,
  AdminOrdersListResponse,
} from "../types";

const initialFilters: AdminOrderListFilters = {
  branchId: "all",
  cashierId: "all",
  dateFrom: null,
  dateTo: null,
  page: 1,
  pageSize: 25,
  paymentState: "all",
  search: "",
  status: "all",
  workstationId: "all",
};

const emptyFilterOptions: AdminOrderFilterOptions = {
  branches: [],
  cashiers: [],
  paymentStates: [],
  statuses: [],
  workstations: [],
};

const emptyOrderList: AdminOrdersListResponse = {
  backendContract: adminOrdersBackendContract,
  filterOptions: emptyFilterOptions,
  isBackendConnected: false,
  items: [],
  metrics: {
    activeOrders: 0,
    canceledOrders: 0,
    depositsReceivedAmount: "0.00",
    dueToday: 0,
    outstandingBalanceAmount: "0.00",
    readyOrders: 0,
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

function AdminOrdersMetricStrip({
  isLoading,
  metrics,
}: {
  isLoading: boolean;
  metrics: AdminOrdersListResponse["metrics"];
}) {
  const loadingValue = isLoading ? "Cargando" : null;
  const items = [
    { label: "Activos", title: "Pedidos activos", value: loadingValue ?? String(metrics.activeOrders) },
    { label: "Listos", title: "Listos para entrega", value: loadingValue ?? String(metrics.readyOrders) },
    { label: "Hoy", title: "Entregas de hoy", value: loadingValue ?? String(metrics.dueToday) },
    {
      label: "Anticipos",
      title: "Anticipos recibidos",
      value: loadingValue ?? formatMoney(metrics.depositsReceivedAmount),
    },
    {
      label: "Saldo",
      title: "Saldo pendiente",
      value: loadingValue ?? formatMoney(metrics.outstandingBalanceAmount),
    },
    { label: "Cancelados", title: "Cancelados", value: loadingValue ?? String(metrics.canceledOrders) },
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

type OrderMutationKind = "cancel" | "deliver" | "markReady";

export function AdminOrdersPage() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminOrderListFilters>(initialFilters);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(null);

  const ordersQuery = useQuery({
    enabled: Boolean(accessToken),
    queryFn: () => fetchAdminOrders(accessToken ?? "", filters),
    queryKey: ["admin", "orders", "list", filters],
    retry: false,
  });

  const orderList = ordersQuery.data ?? emptyOrderList;
  const selectedOrder = useMemo(
    () => orderList.items.find((item) => item.id === selectedOrderId) ?? null,
    [orderList.items, selectedOrderId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(accessToken && selectedOrderId),
    queryFn: () => fetchAdminOrderDetail(accessToken ?? "", selectedOrderId ?? ""),
    queryKey: ["admin", "orders", "detail", selectedOrderId],
    retry: false,
  });

  const actionMutation = useMutation({
    mutationFn: ({ kind, orderId }: { kind: OrderMutationKind; orderId: string }) => {
      if (kind === "markReady") {
        return markAdminOrderReady(accessToken ?? "", orderId);
      }
      if (kind === "deliver") {
        return deliverAdminOrder(accessToken ?? "", orderId);
      }
      return cancelAdminOrder(accessToken ?? "", orderId);
    },
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el pedido."),
      });
    },
    onSuccess: (detail) => {
      setSelectedOrderId(detail.overview.id);
      setFeedback({ tone: "success", message: `${detail.overview.folio} actualizado.` });
      void queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
    },
  });

  const listErrorMessage = ordersQuery.isError
    ? toBackofficeErrorMessage(ordersQuery.error, "No se pudieron cargar los pedidos. Intenta nuevamente.")
    : null;
  const detailErrorMessage = detailQuery.isError
    ? toBackofficeErrorMessage(detailQuery.error, "No se pudo cargar el detalle del pedido.")
    : null;
  const pageStatusLabel = ordersQuery.isLoading
    ? "Validando API"
    : orderList.isBackendConnected
      ? "Datos conectados"
      : "Integracion parcial";

  function patchFilters(patch: Partial<AdminOrderListFilters>) {
    setFilters((current) => ({
      ...current,
      ...patch,
      page: patch.page ?? 1,
    }));
    setSelectedOrderId(null);
  }

  function handlePageChange(page: number) {
    setFilters((current) => ({ ...current, page }));
  }

  function handleSelectOrder(item: AdminOrderListItem) {
    setSelectedOrderId(item.id);
  }

  function handleAction(kind: OrderMutationKind, order: AdminOrderListItem | AdminOrderDetail) {
    const orderId = "overview" in order ? order.overview.id : order.id;
    if (!orderId || actionMutation.isPending) {
      return;
    }
    setFeedback(null);
    actionMutation.mutate({ kind, orderId });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionDisabled
        actionLabel="Nuevo pedido"
        description="Gestiona pedidos de cliente, anticipos, saldos pendientes, fechas de entrega y estados operativos."
        meta={[pageStatusLabel]}
        title="Pedidos"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        <AdminOrdersFilters
          filters={filters}
          isBackendConnected={orderList.isBackendConnected}
          options={orderList.filterOptions}
          onChange={patchFilters}
        />

        <AdminOrdersMetricStrip metrics={orderList.metrics} isLoading={ordersQuery.isLoading} />

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
          <AdminOrdersTable
            errorMessage={listErrorMessage}
            isLoading={ordersQuery.isLoading}
            orders={orderList.items}
            page={filters.page}
            pageSize={filters.pageSize}
            selectedOrderId={selectedOrderId}
            total={orderList.total}
            onCancel={(item) => handleAction("cancel", item)}
            onDeliver={(item) => handleAction("deliver", item)}
            onMarkReady={(item) => handleAction("markReady", item)}
            onPageChange={handlePageChange}
            onSelectOrder={handleSelectOrder}
          />

          <AdminOrderDetailPanel
            detail={detailQuery.data ?? null}
            errorMessage={detailErrorMessage}
            isLoading={detailQuery.isLoading}
            selectedOrder={selectedOrder}
            onCancel={(item) => handleAction("cancel", item)}
            onDeliver={(item) => handleAction("deliver", item)}
            onMarkReady={(item) => handleAction("markReady", item)}
          />
        </div>
      </div>
    </section>
  );
}
