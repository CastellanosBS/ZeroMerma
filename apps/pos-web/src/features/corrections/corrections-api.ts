import type {
  CorrectionBootstrapResponse,
  CorrectionCommitRequest,
  CorrectionCommitResultView,
  CorrectionDocumentView,
  CorrectionsHistoryResponse,
  CorrectionSearchResponse,
  CorrectionTargetDetailResponse,
  CorrectionsProductsResponse,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

function buildQueryString(params: Record<string, string | undefined>): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }

    searchParams.set(key, value);
  }

  const serialized = searchParams.toString();
  return serialized.length > 0 ? `?${serialized}` : "";
}

export function getCorrectionsBootstrap(
  workstationCode: string,
): Promise<CorrectionBootstrapResponse> {
  return requestJson<CorrectionBootstrapResponse>({
    path: `/v1/corrections/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function searchCorrectionTargets({
  documentType,
  query,
  workstationCode,
}: {
  documentType?: string;
  query?: string;
  workstationCode: string;
}): Promise<CorrectionSearchResponse> {
  return requestJson<CorrectionSearchResponse>({
    path: `/v1/corrections/search${buildQueryString({
      workstation_code: workstationCode,
      document_type: documentType,
      query,
    })}`,
  });
}

export function getCorrectionTargetDetail({
  targetDocumentId,
  workstationCode,
}: {
  targetDocumentId: string;
  workstationCode: string;
}): Promise<CorrectionTargetDetailResponse> {
  return requestJson<CorrectionTargetDetailResponse>({
    path: `/v1/corrections/${encodeURIComponent(targetDocumentId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getCorrectionsHistory({
  createdByUserId,
  query,
  reasonCode,
  scope,
  targetDocumentType,
  workstationCode,
}: {
  createdByUserId?: string;
  query?: string;
  reasonCode?: string;
  scope?: string;
  targetDocumentType?: string;
  workstationCode: string;
}): Promise<CorrectionsHistoryResponse> {
  return requestJson<CorrectionsHistoryResponse>({
    path: `/v1/corrections/history${buildQueryString({
      workstation_code: workstationCode,
      scope,
      query,
      created_by_user_id: createdByUserId,
      target_document_type: targetDocumentType,
      reason_code: reasonCode,
    })}`,
  });
}

export function getCorrectionDocumentDetail({
  correctionId,
  workstationCode,
}: {
  correctionId: string;
  workstationCode: string;
}): Promise<CorrectionDocumentView> {
  return requestJson<CorrectionDocumentView>({
    path: `/v1/corrections/history/${encodeURIComponent(correctionId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function searchCorrectionProducts({
  query,
  workstationCode,
}: {
  query?: string;
  workstationCode: string;
}): Promise<CorrectionsProductsResponse> {
  return requestJson<CorrectionsProductsResponse>({
    path: `/v1/corrections/products${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function commitCorrection({
  payload,
  requestId,
  idempotencyKey,
}: {
  payload: CorrectionCommitRequest;
  requestId: string;
  idempotencyKey: string;
}): Promise<CorrectionCommitResultView> {
  return requestJson<CorrectionCommitResultView>({
    body: payload,
    method: "POST",
    path: "/v1/corrections/commit",
    headers: {
      "X-Request-ID": requestId,
      "Idempotency-Key": idempotencyKey,
    },
  });
}
