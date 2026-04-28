import type {
  CashCloseBootstrapResponse,
  CashCloseDetailResponse,
  CashClosePreviewRequest,
  CashClosePreviewResponse,
  CashCloseReconciliationResponse,
  CashCloseSummaryResponse,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export function getCashCloseBootstrap(
  accessToken: string,
  workstationCode: string,
): Promise<CashCloseBootstrapResponse> {
  return requestJson<CashCloseBootstrapResponse>({
    accessToken,
    path: `/v1/cash-close/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getCashCloseSummary(
  accessToken: string,
  workstationCode: string,
): Promise<CashCloseSummaryResponse> {
  return requestJson<CashCloseSummaryResponse>({
    accessToken,
    path: `/v1/cash-close/summary?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getCashCloseReconciliation(
  accessToken: string,
  workstationCode: string,
): Promise<CashCloseReconciliationResponse> {
  return requestJson<CashCloseReconciliationResponse>({
    accessToken,
    path: `/v1/cash-close/reconciliation?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function previewCashClose(
  accessToken: string,
  payload: CashClosePreviewRequest,
): Promise<CashClosePreviewResponse> {
  return requestJson<CashClosePreviewResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/cash-close/preview",
  });
}

export function commitCashClose(
  accessToken: string,
  payload: CashClosePreviewRequest,
): Promise<CashCloseDetailResponse> {
  return requestJson<CashCloseDetailResponse>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/cash-close/commit",
  });
}

export function getCashCloseDetail(
  accessToken: string,
  closeId: string,
): Promise<CashCloseDetailResponse> {
  return requestJson<CashCloseDetailResponse>({
    accessToken,
    path: `/v1/cash-close/${encodeURIComponent(closeId)}`,
  });
}
