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
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: paymentsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getPaymentsBootstrap(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null,
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
  const accessToken = usePosAuthStore((state) => state.accessToken);
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
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        scope,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        category: category.length > 0 ? category : undefined,
        paymentMethod: paymentMethod.length > 0 ? paymentMethod : undefined,
        createdByUserId: createdByUserId.length > 0 ? createdByUserId : undefined,
      }),
    enabled: accessToken !== null,
  });
}

export function paymentDetailQueryKey(workstationCode: string, paymentId: string) {
  return ["payment-detail", workstationCode, paymentId] as const;
}

export function usePaymentDetailQuery(paymentId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: paymentDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, paymentId ?? "none"),
    queryFn: () =>
      getPaymentDetail({
        accessToken: accessToken!,
        paymentId: paymentId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && paymentId !== null,
  });
}
