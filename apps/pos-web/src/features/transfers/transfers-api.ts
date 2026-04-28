import type {
  PendingInboundTransfersResponse,
  TransferDetailResponse,
  TransferDispatchCommitRequest,
  TransferDispatchHistoryResponse,
  TransferReceiptHistoryResponse,
  TransferReceiveRequest,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export interface TransferDispatchHistoryFilters {
  createdByUserId?: string;
  destinationBranchId?: string;
  scope?: string;
}

export interface TransferReceiptHistoryFilters {
  createdByUserId?: string;
  scope?: string;
  sourceBranchId?: string;
  status?: string;
}

export function commitTransferDispatch(
  accessToken: string,
  payload: TransferDispatchCommitRequest,
): Promise<TransferDetailResponse> {
  return requestJson<TransferDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/transfers/dispatch/commit",
  });
}

export function getPendingInboundTransfers(
  accessToken: string,
  workstationCode: string,
): Promise<PendingInboundTransfersResponse> {
  return requestJson<PendingInboundTransfersResponse>({
    accessToken,
    path: `/v1/transfers/inbound/pending?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getTransferDetail(
  accessToken: string,
  workstationCode: string,
  transferId: string,
): Promise<TransferDetailResponse> {
  return requestJson<TransferDetailResponse>({
    accessToken,
    path: `/v1/transfers/${encodeURIComponent(transferId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getTransferDispatchHistory(
  accessToken: string,
  workstationCode: string,
  filters: TransferDispatchHistoryFilters,
): Promise<TransferDispatchHistoryResponse> {
  const search = new URLSearchParams({
    workstation_code: workstationCode,
  });

  if (filters.scope) {
    search.set("scope", filters.scope);
  }
  if (filters.createdByUserId) {
    search.set("created_by_user_id", filters.createdByUserId);
  }
  if (filters.destinationBranchId) {
    search.set("destination_branch_id", filters.destinationBranchId);
  }

  return requestJson<TransferDispatchHistoryResponse>({
    accessToken,
    path: `/v1/transfers/outbound/history?${search.toString()}`,
  });
}

export function getTransferReceiptHistory(
  accessToken: string,
  workstationCode: string,
  filters: TransferReceiptHistoryFilters,
): Promise<TransferReceiptHistoryResponse> {
  const search = new URLSearchParams({
    workstation_code: workstationCode,
  });

  if (filters.scope) {
    search.set("scope", filters.scope);
  }
  if (filters.createdByUserId) {
    search.set("created_by_user_id", filters.createdByUserId);
  }
  if (filters.sourceBranchId) {
    search.set("source_branch_id", filters.sourceBranchId);
  }
  if (filters.status) {
    search.set("status", filters.status);
  }

  return requestJson<TransferReceiptHistoryResponse>({
    accessToken,
    path: `/v1/transfers/inbound/history?${search.toString()}`,
  });
}

export function receiveTransfer(
  accessToken: string,
  transferId: string,
  payload: TransferReceiveRequest,
): Promise<TransferDetailResponse> {
  return requestJson<TransferDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: `/v1/transfers/${encodeURIComponent(transferId)}/receive`,
  });
}
