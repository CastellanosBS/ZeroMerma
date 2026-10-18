import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import {
  getCashCloseBootstrap,
  getCashCloseDetail,
  getCashCloseReconciliation,
  getCashCloseSummary,
} from "./cash-close-api";

export function cashCloseBootstrapQueryKey(workstationCode: string) {
  return ["cash-close-bootstrap", workstationCode] as const;
}

export function useCashCloseBootstrapQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: cashCloseBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getCashCloseBootstrap(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}

export function cashCloseSummaryQueryKey(workstationCode: string) {
  return ["cash-close-summary", workstationCode] as const;
}

export function useCashCloseSummaryQuery(enabled: boolean) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: cashCloseSummaryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getCashCloseSummary(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated && enabled,
  });
}

export function cashCloseReconciliationQueryKey(workstationCode: string) {
  return ["cash-close-reconciliation", workstationCode] as const;
}

export function useCashCloseReconciliationQuery(enabled: boolean) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: cashCloseReconciliationQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () =>
      getCashCloseReconciliation(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated && enabled,
  });
}

export function cashCloseDetailQueryKey(closeId: string) {
  return ["cash-close-detail", closeId] as const;
}

export function useCashCloseDetailQuery(closeId: string | null) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: cashCloseDetailQueryKey(closeId ?? "none"),
    queryFn: () =>
      getCashCloseDetail(
        closeId!,
      ),
    enabled: isAuthenticated && closeId !== null,
  });
}
