import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getDiscountDetail, getDiscountsBootstrap, listDiscounts } from "./discounts-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function discountsBootstrapQueryKey(workstationCode: string) {
  return ["discounts-bootstrap", workstationCode] as const;
}

export function useDiscountsBootstrapQuery() {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: discountsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getDiscountsBootstrap(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null,
  });
}

export function discountsListQueryKey(
  workstationCode: string,
  scope: string,
  query: string,
  category: string,
  paymentMethod: string,
  createdByUserId: string,
) {
  return [
    "discounts-list",
    workstationCode,
    scope,
    normalizeQuery(query),
    category,
    paymentMethod,
    createdByUserId,
  ] as const;
}

export function useDiscountsListQuery(
  scope: string,
  query: string,
  category: string,
  paymentMethod: string,
  createdByUserId: string,
) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: discountsListQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      scope,
      normalizedQuery,
      category,
      paymentMethod,
      createdByUserId,
    ),
    queryFn: () =>
      listDiscounts({
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

export function discountDetailQueryKey(workstationCode: string, discountId: string) {
  return ["discount-detail", workstationCode, discountId] as const;
}

export function useDiscountDetailQuery(discountId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: discountDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, discountId ?? "none"),
    queryFn: () =>
      getDiscountDetail({
        accessToken: accessToken!,
        discountId: discountId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && discountId !== null,
  });
}
