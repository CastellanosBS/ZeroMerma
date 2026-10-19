import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import {
  getTransferDispatchHistory,
  getPendingInboundTransfers,
  getTransferDetail,
  getTransferReceiptHistory,
  type TransferDispatchHistoryFilters,
  type TransferReceiptHistoryFilters,
} from "./transfers-api";

export function pendingInboundTransfersQueryKey(workstationCode: string) {
  return ["pending-inbound-transfers", workstationCode] as const;
}

export function usePendingInboundTransfersQuery(enabled = true) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: pendingInboundTransfersQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getPendingInboundTransfers(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated && enabled,
  });
}

export function transferDetailQueryKey(workstationCode: string, transferId: string) {
  return ["transfer-detail", workstationCode, transferId] as const;
}

export function useTransferDetailQuery(transferId: string | null) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: transferDetailQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, transferId ?? "none"),
    queryFn: () => getTransferDetail(appEnv.VITE_POS_WORKSTATION_CODE, transferId!),
    enabled: isAuthenticated && transferId !== null,
  });
}

export function transferDispatchHistoryQueryKey(
  workstationCode: string,
  filters: TransferDispatchHistoryFilters,
) {
  return [
    "transfer-dispatch-history",
    workstationCode,
    filters.scope ?? "CURRENT_SHIFT",
    filters.createdByUserId ?? "all-users",
    filters.destinationBranchId ?? "all-destinations",
  ] as const;
}

export function useTransferDispatchHistoryQuery(
  filters: TransferDispatchHistoryFilters,
  enabled = true,
) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: transferDispatchHistoryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, filters),
    queryFn: () => getTransferDispatchHistory(appEnv.VITE_POS_WORKSTATION_CODE, filters),
    enabled: isAuthenticated && enabled,
  });
}

export function transferReceiptHistoryQueryKey(
  workstationCode: string,
  filters: TransferReceiptHistoryFilters,
) {
  return [
    "transfer-receipt-history",
    workstationCode,
    filters.scope ?? "CURRENT_SHIFT",
    filters.createdByUserId ?? "all-users",
    filters.sourceBranchId ?? "all-sources",
    filters.status ?? "all-statuses",
  ] as const;
}

export function useTransferReceiptHistoryQuery(
  filters: TransferReceiptHistoryFilters,
  enabled = true,
) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: transferReceiptHistoryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, filters),
    queryFn: () => getTransferReceiptHistory(appEnv.VITE_POS_WORKSTATION_CODE, filters),
    enabled: isAuthenticated && enabled,
  });
}
