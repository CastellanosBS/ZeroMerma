import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import {
  getOrderDetail,
  getOrdersBootstrap,
  getOrdersCatalog,
  getOrdersClassProducts,
  listOrders,
} from "./orders-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function ordersBootstrapQueryKey(workstationCode: string) {
  return ["orders-bootstrap", workstationCode] as const;
}

export function useOrdersBootstrapQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: ordersBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getOrdersBootstrap(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}

export function ordersListQueryKey(
  workstationCode: string,
  status: string,
  query: string,
  dateFrom: string,
  dateTo: string,
) {
  return [
    "orders-list",
    workstationCode,
    status,
    normalizeQuery(query),
    normalizeQuery(dateFrom),
    normalizeQuery(dateTo),
  ] as const;
}

export function useOrdersListQuery(
  status: string,
  query: string,
  dateFrom: string,
  dateTo: string,
  enabled = true,
) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);
  const normalizedDateFrom = normalizeQuery(dateFrom);
  const normalizedDateTo = normalizeQuery(dateTo);

  return useQuery({
    queryKey: ordersListQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      status,
      normalizedQuery,
      normalizedDateFrom,
      normalizedDateTo,
    ),
    queryFn: () =>
      listOrders({
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        status,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        dateFrom: normalizedDateFrom.length > 0 ? normalizedDateFrom : undefined,
        dateTo: normalizedDateTo.length > 0 ? normalizedDateTo : undefined,
      }),
    enabled: isAuthenticated && enabled,
  });
}

export function orderDetailQueryKey(workstationCode: string, orderId: string) {
  return ["order-detail", workstationCode, orderId] as const;
}

export function useOrderDetailQuery(orderId: string | null) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: orderDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, orderId ?? "none"),
    queryFn: () =>
      getOrderDetail({
        orderId: orderId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: isAuthenticated && orderId !== null,
    refetchInterval: (query) => {
      const order = query.state.data;
      if (
        !order ||
        order.status !== "PENDING" ||
        order.can_mark_ready ||
        !order.production_commit_at
      )
        return false;
      // Refresh server authority at commitment; the browser never changes order state itself.
      const remaining = new Date(order.production_commit_at).getTime() - Date.now();
      return Math.max(1_000, Math.min(60_000, remaining + 250));
    },
  });
}

export function ordersCatalogQueryKey(workstationCode: string, query: string) {
  return ["orders-catalog", workstationCode, normalizeQuery(query)] as const;
}

export function useOrdersCatalogQuery(query: string, enabled = true) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: ordersCatalogQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, normalizedQuery),
    queryFn: () =>
      getOrdersCatalog({
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
      }),
    enabled: isAuthenticated && enabled,
  });
}

export function ordersClassProductsQueryKey(
  workstationCode: string,
  classId: string,
  query: string,
) {
  return ["orders-class-products", workstationCode, classId, normalizeQuery(query)] as const;
}

export function useOrdersClassProductsQuery(classId: string | null, query: string, enabled = true) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: ordersClassProductsQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      classId ?? "none",
      normalizedQuery,
    ),
    queryFn: () =>
      getOrdersClassProducts({
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        classId: classId!,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
      }),
    enabled: isAuthenticated && classId !== null && enabled,
  });
}
