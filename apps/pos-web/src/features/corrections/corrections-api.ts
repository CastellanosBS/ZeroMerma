import type {
  CorrectionBootstrapResponse,
  CorrectionCommitRequest,
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
  accessToken: string,
  workstationCode: string,
): Promise<CorrectionBootstrapResponse> {
  return requestJson<CorrectionBootstrapResponse>({
    accessToken,
    path: `/v1/corrections/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function searchCorrectionTargets({
  accessToken,
  documentType,
  query,
  workstationCode,
}: {
  accessToken: string;
  documentType?: string;
  query?: string;
  workstationCode: string;
}): Promise<CorrectionSearchResponse> {
  return requestJson<CorrectionSearchResponse>({
    accessToken,
    path: `/v1/corrections/search${buildQueryString({
      workstation_code: workstationCode,
      document_type: documentType,
      query,
    })}`,
  });
}

export function getCorrectionTargetDetail({
  accessToken,
  targetDocumentId,
  workstationCode,
}: {
  accessToken: string;
  targetDocumentId: string;
  workstationCode: string;
}): Promise<CorrectionTargetDetailResponse> {
  return requestJson<CorrectionTargetDetailResponse>({
    accessToken,
    path: `/v1/corrections/${encodeURIComponent(targetDocumentId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getCorrectionsHistory({
  accessToken,
  createdByUserId,
  query,
  reasonCode,
  scope,
  targetDocumentType,
  workstationCode,
}: {
  accessToken: string;
  createdByUserId?: string;
  query?: string;
  reasonCode?: string;
  scope?: string;
  targetDocumentType?: string;
  workstationCode: string;
}): Promise<CorrectionsHistoryResponse> {
  return requestJson<CorrectionsHistoryResponse>({
    accessToken,
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
  accessToken,
  correctionId,
  workstationCode,
}: {
  accessToken: string;
  correctionId: string;
  workstationCode: string;
}): Promise<CorrectionDocumentView> {
  return requestJson<CorrectionDocumentView>({
    accessToken,
    path: `/v1/corrections/history/${encodeURIComponent(correctionId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function searchCorrectionProducts({
  accessToken,
  query,
  workstationCode,
}: {
  accessToken: string;
  query?: string;
  workstationCode: string;
}): Promise<CorrectionsProductsResponse> {
  return requestJson<CorrectionsProductsResponse>({
    accessToken,
    path: `/v1/corrections/products${buildQueryString({
      workstation_code: workstationCode,
      query,
    })}`,
  });
}

export function commitCorrection({
  accessToken,
  payload,
  requestId,
}: {
  accessToken: string;
  payload: CorrectionCommitRequest;
  requestId: string;
}): Promise<CorrectionDocumentView> {
  return requestJson<CorrectionDocumentView>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/corrections/commit",
    headers: {
      "X-Request-ID": requestId,
    },
  });
}
