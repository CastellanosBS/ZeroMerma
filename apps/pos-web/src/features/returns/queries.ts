import { useQueries, useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import {
  getReturnSaleDetail,
  getSaleReturnDetail,
  getReturnsHistory,
  getReturnsBootstrap,
  getReturnsClassProducts,
  searchReturnSales,
} from "./returns-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

function normalizeDate(value: string): string {
  return value.trim();
}

export function returnsBootstrapQueryKey(workstationCode: string) {
  return ["returns", "bootstrap", workstationCode] as const;
}

export function useReturnsBootstrapQuery() {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: returnsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getReturnsBootstrap(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null,
  });
}

export function returnSalesQueryKey(
  workstationCode: string,
  scope: string,
  query: string,
  dateFrom: string,
  dateTo: string,
) {
  return [
    "returns",
    "sales",
    workstationCode,
    scope,
    normalizeQuery(query),
    normalizeDate(dateFrom),
    normalizeDate(dateTo),
  ] as const;
}

export function useReturnSalesQuery(
  scope: string,
  query: string,
  dateFrom: string,
  dateTo: string,
) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);
  const normalizedDateFrom = normalizeDate(dateFrom);
  const normalizedDateTo = normalizeDate(dateTo);

  return useQuery({
    queryKey: returnSalesQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      scope,
      normalizedQuery,
      normalizedDateFrom,
      normalizedDateTo,
    ),
    queryFn: () =>
      searchReturnSales({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        scope,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        dateFrom: normalizedDateFrom.length > 0 ? normalizedDateFrom : undefined,
        dateTo: normalizedDateTo.length > 0 ? normalizedDateTo : undefined,
      }),
    enabled: accessToken !== null,
  });
}

export function returnSaleDetailQueryKey(workstationCode: string, saleId: string) {
  return ["returns", "sale-detail", workstationCode, saleId] as const;
}

export function useReturnSaleDetailQuery(saleId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: returnSaleDetailQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      saleId ?? "none",
    ),
    queryFn: () =>
      getReturnSaleDetail({
        accessToken: accessToken!,
        saleId: saleId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && saleId !== null,
  });
}

export function saleReturnDetailQueryKey(workstationCode: string, returnId: string) {
  return ["returns", "return-detail", workstationCode, returnId] as const;
}

export function useSaleReturnDetailQuery(returnId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: saleReturnDetailQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      returnId ?? "none",
    ),
    queryFn: () =>
      getSaleReturnDetail({
        accessToken: accessToken!,
        returnId: returnId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && returnId !== null,
  });
}

export function returnsHistoryQueryKey(
  workstationCode: string,
  scope: string,
  query: string,
  dateFrom: string,
  dateTo: string,
  createdByUserId: string,
  reasonCode: string,
) {
  return [
    "returns",
    "history",
    workstationCode,
    scope,
    normalizeQuery(query),
    normalizeDate(dateFrom),
    normalizeDate(dateTo),
    createdByUserId.trim(),
    reasonCode.trim(),
  ] as const;
}

export function useReturnsHistoryQuery(
  scope: string,
  query: string,
  dateFrom: string,
  dateTo: string,
  createdByUserId: string,
  reasonCode: string,
) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);
  const normalizedDateFrom = normalizeDate(dateFrom);
  const normalizedDateTo = normalizeDate(dateTo);
  const normalizedCreatedByUserId = createdByUserId.trim();
  const normalizedReasonCode = reasonCode.trim();

  return useQuery({
    queryKey: returnsHistoryQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      scope,
      normalizedQuery,
      normalizedDateFrom,
      normalizedDateTo,
      normalizedCreatedByUserId,
      normalizedReasonCode,
    ),
    queryFn: () =>
      getReturnsHistory({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        scope,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        dateFrom: normalizedDateFrom.length > 0 ? normalizedDateFrom : undefined,
        dateTo: normalizedDateTo.length > 0 ? normalizedDateTo : undefined,
        createdByUserId:
          normalizedCreatedByUserId.length > 0 ? normalizedCreatedByUserId : undefined,
        reasonCode: normalizedReasonCode.length > 0 ? normalizedReasonCode : undefined,
      }),
    enabled: accessToken !== null,
  });
}

export function returnClassProductsQueryKey(workstationCode: string, classId: string) {
  return ["returns", "class-products", workstationCode, classId] as const;
}

export function useReturnClassProductsQueries(classIds: string[]) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQueries({
    queries: classIds.map((classId) => ({
      queryKey: returnClassProductsQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, classId),
      queryFn: () =>
        getReturnsClassProducts({
          accessToken: accessToken!,
          classId,
          workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        }),
      enabled: accessToken !== null && classId.length > 0,
    })),
  });
}
