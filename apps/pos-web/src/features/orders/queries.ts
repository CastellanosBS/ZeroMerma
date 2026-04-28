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
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: ordersBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getOrdersBootstrap(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null,
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
  const accessToken = usePosAuthStore((state) => state.accessToken);
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
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        status,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        dateFrom: normalizedDateFrom.length > 0 ? normalizedDateFrom : undefined,
        dateTo: normalizedDateTo.length > 0 ? normalizedDateTo : undefined,
      }),
    enabled: accessToken !== null && enabled,
  });
}

export function orderDetailQueryKey(workstationCode: string, orderId: string) {
  return ["order-detail", workstationCode, orderId] as const;
}

export function useOrderDetailQuery(orderId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: orderDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, orderId ?? "none"),
    queryFn: () =>
      getOrderDetail({
        accessToken: accessToken!,
        orderId: orderId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && orderId !== null,
  });
}

export function ordersCatalogQueryKey(workstationCode: string, query: string) {
  return ["orders-catalog", workstationCode, normalizeQuery(query)] as const;
}

export function useOrdersCatalogQuery(query: string, enabled = true) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: ordersCatalogQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, normalizedQuery),
    queryFn: () =>
      getOrdersCatalog({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
      }),
    enabled: accessToken !== null && enabled,
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
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: ordersClassProductsQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      classId ?? "none",
      normalizedQuery,
    ),
    queryFn: () =>
      getOrdersClassProducts({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        classId: classId!,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
      }),
    enabled: accessToken !== null && classId !== null && enabled,
  });
}
