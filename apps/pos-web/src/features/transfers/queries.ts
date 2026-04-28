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
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: pendingInboundTransfersQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () =>
      getPendingInboundTransfers(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null && enabled,
  });
}

export function transferDetailQueryKey(workstationCode: string, transferId: string) {
  return ["transfer-detail", workstationCode, transferId] as const;
}

export function useTransferDetailQuery(transferId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: transferDetailQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      transferId ?? "none",
    ),
    queryFn: () =>
      getTransferDetail(
        accessToken!,
        appEnv.VITE_POS_WORKSTATION_CODE,
        transferId!,
      ),
    enabled: accessToken !== null && transferId !== null,
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
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: transferDispatchHistoryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, filters),
    queryFn: () =>
      getTransferDispatchHistory(
        accessToken!,
        appEnv.VITE_POS_WORKSTATION_CODE,
        filters,
      ),
    enabled: accessToken !== null && enabled,
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
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: transferReceiptHistoryQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, filters),
    queryFn: () =>
      getTransferReceiptHistory(
        accessToken!,
        appEnv.VITE_POS_WORKSTATION_CODE,
        filters,
      ),
    enabled: accessToken !== null && enabled,
  });
}
