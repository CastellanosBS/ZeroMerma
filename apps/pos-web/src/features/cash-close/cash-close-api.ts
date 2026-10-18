import type { CashCloseCommitRequest, CashCloseCommitResultView } from "../../lib/api-contracts";
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
  workstationCode: string,
): Promise<CashCloseBootstrapResponse> {
  return requestJson<CashCloseBootstrapResponse>({
    path: `/v1/cash-close/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getCashCloseSummary(workstationCode: string): Promise<CashCloseSummaryResponse> {
  return requestJson<CashCloseSummaryResponse>({
    path: `/v1/cash-close/summary?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getCashCloseReconciliation(
  workstationCode: string,
): Promise<CashCloseReconciliationResponse> {
  return requestJson<CashCloseReconciliationResponse>({
    path: `/v1/cash-close/reconciliation?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function previewCashClose(
  payload: CashClosePreviewRequest,
): Promise<CashClosePreviewResponse> {
  return requestJson<CashClosePreviewResponse>({
    body: payload,
    method: "POST",
    path: "/v1/cash-close/preview",
  });
}

export function commitCashClose(
  payload: CashCloseCommitRequest,
  idempotencyKey: string,
): Promise<CashCloseCommitResultView> {
  return requestJson<CashCloseCommitResultView>({
    headers: { "Idempotency-Key": idempotencyKey },
    body: payload,
    method: "POST",
    path: "/v1/cash-close/commit",
  });
}

export function getCashCloseDetail(closeId: string): Promise<CashCloseDetailResponse> {
  return requestJson<CashCloseDetailResponse>({
    path: `/v1/cash-close/${encodeURIComponent(closeId)}`,
  });
}
