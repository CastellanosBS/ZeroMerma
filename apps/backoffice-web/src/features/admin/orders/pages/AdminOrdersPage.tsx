import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";
import { isCommandIntentionPending } from "@zeromerma/api-client";

import { toBackofficeErrorMessage } from "../../../../lib/api";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { AdminPageHeader } from "../../components/AdminPageHeader";
import { adminOrdersBackendContract, fetchAdminOrderDetail, fetchAdminOrders } from "../api";
import type { OrderCommandResultView } from "../api";
import {
  adminOrderIntentions,
  type AdminOrderCommandCode,
  type AdminOrderIntentionContext,
} from "../order-command-intent";
import { useAdminOrderIntention } from "../use-order-intention";
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
  return new Intl.NumberFormat("es-MX", { currency: currencyCode, style: "currency" }).format(
    numericValue,
  );
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
    {
      label: "Activos",
      title: "Pedidos activos",
      value: loadingValue ?? String(metrics.activeOrders),
    },
    {
      label: "Listos",
      title: "Listos para entrega",
      value: loadingValue ?? String(metrics.readyOrders),
    },
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
    {
      label: "Cancelados",
      title: "Cancelados",
      value: loadingValue ?? String(metrics.canceledOrders),
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

type OrderMutationKind = AdminOrderCommandCode;

export function AdminOrdersPage() {
  const isAuthenticated = useBackofficeAuthStore((state) => state.isAuthenticated);
  const user = useBackofficeAuthStore((state) => state.user);
  const intention = useAdminOrderIntention();
  const observedKey = useRef(intention.metadata?.key ?? null);
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<AdminOrderListFilters>(initialFilters);
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ tone: "success" | "error"; message: string } | null>(
    null,
  );

  const ordersQuery = useQuery({
    enabled: isAuthenticated,
    queryFn: () => fetchAdminOrders(filters),
    queryKey: ["admin", "orders", "list", filters],
    retry: false,
  });

  const orderList = ordersQuery.data ?? emptyOrderList;
  const selectedOrder = useMemo(
    () => orderList.items.find((item) => item.id === selectedOrderId) ?? null,
    [orderList.items, selectedOrderId],
  );

  const detailQuery = useQuery({
    enabled: Boolean(isAuthenticated && selectedOrderId),
    queryFn: () => fetchAdminOrderDetail(selectedOrderId ?? ""),
    queryKey: ["admin", "orders", "detail", selectedOrderId],
    retry: false,
  });

  function confirmed(result: OrderCommandResultView) {
    setSelectedOrderId(result.id);
    setFeedback({ tone: "success", message: `${result.folio}: operación confirmada.` });
    // Detail refresh is read-only and cannot turn a confirmed command into a retry.
    void queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
  }
  const actionMutation = useMutation({
    mutationFn: (context: AdminOrderIntentionContext) =>
      adminOrderIntentions.begin(context, {}, observedKey.current),
    onError: (error) => {
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo actualizar el pedido."),
      });
    },
    onSuccess: confirmed,
  });
  const recoveryMutation = useMutation({
    mutationFn: (retry: boolean) => {
      const metadata = intention.metadata;
      if (!metadata || metadata.userId !== user?.id)
        throw new Error("Se requiere el operador original.");
      return retry ? adminOrderIntentions.retry(metadata) : adminOrderIntentions.recover(metadata);
    },
    onSuccess: confirmed,
    onError: (error) =>
      setFeedback({
        tone: "error",
        message: toBackofficeErrorMessage(error, "No se pudo recuperar el resultado."),
      }),
  });
  useEffect(() => {
    const key = intention.metadata?.key ?? null;
    if (key !== observedKey.current)
      void queryClient.invalidateQueries({ queryKey: ["admin", "orders"] });
    observedKey.current = key;
  }, [intention.metadata?.key, queryClient]);

  const listErrorMessage = ordersQuery.isError
    ? toBackofficeErrorMessage(
        ordersQuery.error,
        "No se pudieron cargar los pedidos. Intenta nuevamente.",
      )
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
    if (
      !orderId ||
      !user ||
      actionMutation.isPending ||
      intention.error ||
      isCommandIntentionPending(intention.metadata)
    ) {
      return;
    }
    setFeedback(null);
    const branchId = "overview" in order ? order.overview.branchId : order.branchId;
    actionMutation.mutate({ commandCode: kind, orderId, branchId, userId: user.id });
  }

  return (
    <section className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-[28px] border border-[var(--ui-color-border)] bg-white shadow-[var(--ui-shadow-subtle)] lg:h-full">
      <AdminPageHeader
        actionCapability="orders.manage"
        actionDisabled
        actionLabel="Nuevo pedido"
        description="Gestiona pedidos de cliente, anticipos, saldos pendientes, fechas de entrega y estados operativos."
        meta={[pageStatusLabel]}
        title="Pedidos"
      />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2.5 overflow-hidden p-3">
        {intention.error || isCommandIntentionPending(intention.metadata) ? (
          <section role="alert" className="rounded-xl border border-amber-400 bg-amber-50 p-3">
            <h2>Pedido pendiente de confirmar</h2>
            <p>
              {intention.error ??
                "Consulta el resultado antes de repetir o iniciar otra acción de pedidos."}
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
                  Consultar resultado del pedido
                </button>
                {adminOrderIntentions.hasBody(intention.metadata.key) &&
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
            onMarkReady={(item) => handleAction("mark-ready", item)}
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
            onMarkReady={(item) => handleAction("mark-ready", item)}
          />
        </div>
      </div>
    </section>
  );
}
