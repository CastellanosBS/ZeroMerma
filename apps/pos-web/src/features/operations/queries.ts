import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import {
  getOperationDocument,
  getOperationHistory,
  getOperationsBootstrap,
  getOperationsCatalog,
  getOperationsClassProducts,
  type OperationHistoryFilters,
} from "./operations-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function operationsBootstrapQueryKey(workstationCode: string) {
  return ["operations-bootstrap", workstationCode] as const;
}

export function useOperationsBootstrapQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: operationsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getOperationsBootstrap(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}

export function operationsCatalogQueryKey(
  workstationCode: string,
  module: string,
  query: string,
) {
  return ["operations-catalog", workstationCode, module, normalizeQuery(query)] as const;
}

export function useOperationsCatalogQuery(module: string, query: string) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: operationsCatalogQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      module,
      normalizedQuery,
    ),
    queryFn: () =>
      getOperationsCatalog(
        appEnv.VITE_POS_WORKSTATION_CODE,
        module,
        normalizedQuery.length > 0 ? normalizedQuery : undefined,
      ),
    enabled: isAuthenticated,
  });
}

export function operationsClassProductsQueryKey(
  workstationCode: string,
  module: string,
  classId: string,
  query: string,
) {
  return [
    "operations-class-products",
    workstationCode,
    module,
    classId,
    normalizeQuery(query),
  ] as const;
}

export function useOperationsClassProductsQuery(
  module: string,
  classId: string | null,
  query: string,
) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: operationsClassProductsQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      module,
      classId ?? "none",
      normalizedQuery,
    ),
    queryFn: () =>
      getOperationsClassProducts(
        appEnv.VITE_POS_WORKSTATION_CODE,
        module,
        classId!,
        normalizedQuery.length > 0 ? normalizedQuery : undefined,
      ),
    enabled: isAuthenticated && classId !== null,
  });
}

export function operationDocumentQueryKey(workstationCode: string, documentId: string) {
  return ["operation-document", workstationCode, documentId] as const;
}

export function useOperationDocumentQuery(documentId: string | null) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: operationDocumentQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      documentId ?? "none",
    ),
    queryFn: () =>
      getOperationDocument(
        appEnv.VITE_POS_WORKSTATION_CODE,
        documentId!,
      ),
    enabled: isAuthenticated && documentId !== null,
  });
}

export function operationHistoryQueryKey(
  workstationCode: string,
  documentType: string,
  filters: OperationHistoryFilters,
) {
  return [
    "operation-history",
    workstationCode,
    documentType,
    filters.scope ?? "CURRENT_SHIFT",
    filters.createdByUserId ?? "all-users",
    filters.reasonCode ?? "all-reasons",
    filters.productId ?? "all-products",
    filters.sourceBucketCode ?? "all-sources",
    filters.destinationBucketCode ?? "all-destinations",
  ] as const;
}

export function useOperationHistoryQuery(
  documentType: string,
  filters: OperationHistoryFilters,
  enabled = true,
) {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: operationHistoryQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      documentType,
      filters,
    ),
    queryFn: () =>
      getOperationHistory(
        appEnv.VITE_POS_WORKSTATION_CODE,
        documentType,
        filters,
      ),
    enabled: isAuthenticated && enabled,
  });
}
