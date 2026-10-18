import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getPaymentDetail, getPaymentsBootstrap, listPayments } from "./payments-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function paymentsBootstrapQueryKey(workstationCode: string) {
  return ["payments-bootstrap", workstationCode] as const;
}

export function usePaymentsBootstrapQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: paymentsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getPaymentsBootstrap(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}

export function paymentsListQueryKey(
  workstationCode: string,
  scope: string,
  query: string,
  category: string,
  paymentMethod: string,
  createdByUserId: string,
) {
  return [
    "payments-list",
    workstationCode,
    scope,
    normalizeQuery(query),
    category,
    paymentMethod,
    createdByUserId,
  ] as const;
}

export function usePaymentsListQuery(
  scope: string,
  query: string,
  category: string,
  paymentMethod: string,
  createdByUserId: string,
) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: paymentsListQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      scope,
      normalizedQuery,
      category,
      paymentMethod,
      createdByUserId,
    ),
    queryFn: () =>
      listPayments({
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        scope,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        category: category.length > 0 ? category : undefined,
        paymentMethod: paymentMethod.length > 0 ? paymentMethod : undefined,
        createdByUserId: createdByUserId.length > 0 ? createdByUserId : undefined,
      }),
    enabled: isAuthenticated,
  });
}

export function paymentDetailQueryKey(workstationCode: string, paymentId: string) {
  return ["payment-detail", workstationCode, paymentId] as const;
}

export function usePaymentDetailQuery(paymentId: string | null) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: paymentDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, paymentId ?? "none"),
    queryFn: () =>
      getPaymentDetail({
        paymentId: paymentId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: isAuthenticated && paymentId !== null,
  });
}
