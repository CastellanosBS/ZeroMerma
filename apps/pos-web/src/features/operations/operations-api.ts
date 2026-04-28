import type {
  CounterTransferCommitRequest,
  OperationDocumentView,
  OperationHistoryResponse,
  OperationsBootstrapResponse,
  OperationsCatalogResponse,
  OperationsClassProductsResponse,
  WasteCommitRequest,
} from "../../lib/api-contracts";
import { requestJson } from "../../lib/http";

export interface OperationHistoryFilters {
  createdByUserId?: string;
  destinationBucketCode?: string;
  productId?: string;
  reasonCode?: string;
  scope?: string;
  sourceBucketCode?: string;
}

export function getOperationsBootstrap(
  accessToken: string,
  workstationCode: string,
): Promise<OperationsBootstrapResponse> {
  return requestJson<OperationsBootstrapResponse>({
    accessToken,
    path: `/v1/operations/bootstrap?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getOperationsCatalog(
  accessToken: string,
  workstationCode: string,
  module: string,
  query?: string,
): Promise<OperationsCatalogResponse> {
  const search = new URLSearchParams({
    workstation_code: workstationCode,
    module,
  });

  if (query) {
    search.set("query", query);
  }

  return requestJson<OperationsCatalogResponse>({
    accessToken,
    path: `/v1/operations/catalog?${search.toString()}`,
  });
}

export function getOperationsClassProducts(
  accessToken: string,
  workstationCode: string,
  module: string,
  classId: string,
  query?: string,
): Promise<OperationsClassProductsResponse> {
  const search = new URLSearchParams({
    workstation_code: workstationCode,
    module,
  });

  if (query) {
    search.set("query", query);
  }

  return requestJson<OperationsClassProductsResponse>({
    accessToken,
    path: `/v1/operations/classes/${encodeURIComponent(classId)}/products?${search.toString()}`,
  });
}

export function commitCounterTransfer(
  accessToken: string,
  payload: CounterTransferCommitRequest,
): Promise<OperationDocumentView> {
  return requestJson<OperationDocumentView>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/operations/counter-transfer/commit",
  });
}

export function commitWasteRecord(
  accessToken: string,
  payload: WasteCommitRequest,
): Promise<OperationDocumentView> {
  return requestJson<OperationDocumentView>({
    accessToken,
    body: payload,
    method: "POST",
    path: "/v1/operations/waste/commit",
  });
}

export function getOperationDocument(
  accessToken: string,
  workstationCode: string,
  documentId: string,
): Promise<OperationDocumentView> {
  return requestJson<OperationDocumentView>({
    accessToken,
    path: `/v1/operations/${encodeURIComponent(documentId)}?workstation_code=${encodeURIComponent(workstationCode)}`,
  });
}

export function getOperationHistory(
  accessToken: string,
  workstationCode: string,
  documentType: string,
  filters: OperationHistoryFilters,
): Promise<OperationHistoryResponse> {
  const search = new URLSearchParams({
    document_type: documentType,
    workstation_code: workstationCode,
  });

  if (filters.scope) {
    search.set("scope", filters.scope);
  }
  if (filters.createdByUserId) {
    search.set("created_by_user_id", filters.createdByUserId);
  }
  if (filters.reasonCode) {
    search.set("reason_code", filters.reasonCode);
  }
  if (filters.productId) {
    search.set("product_id", filters.productId);
  }
  if (filters.sourceBucketCode) {
    search.set("source_bucket_code", filters.sourceBucketCode);
  }
  if (filters.destinationBucketCode) {
    search.set("destination_bucket_code", filters.destinationBucketCode);
  }

  return requestJson<OperationHistoryResponse>({
    accessToken,
    path: `/v1/operations/history?${search.toString()}`,
  });
}
