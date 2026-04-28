import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import {
  getCorrectionDocumentDetail,
  getCorrectionTargetDetail,
  getCorrectionsHistory,
  getCorrectionsBootstrap,
  searchCorrectionProducts,
  searchCorrectionTargets,
} from "./corrections-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function correctionsBootstrapQueryKey(workstationCode: string) {
  return ["corrections", "bootstrap", workstationCode] as const;
}

export function useCorrectionsBootstrapQuery() {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: correctionsBootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getCorrectionsBootstrap(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null,
  });
}

export function correctionTargetsQueryKey(
  workstationCode: string,
  documentType: string,
  query: string,
) {
  return ["corrections", "search", workstationCode, documentType, normalizeQuery(query)] as const;
}

export function useCorrectionTargetsQuery(documentType: string, query: string) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: correctionTargetsQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      documentType,
      normalizedQuery,
    ),
    queryFn: () =>
      searchCorrectionTargets({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        documentType: documentType.length > 0 ? documentType : undefined,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
      }),
    enabled: accessToken !== null,
  });
}

export function correctionTargetDetailQueryKey(workstationCode: string, targetDocumentId: string) {
  return ["corrections", "detail", workstationCode, targetDocumentId] as const;
}

export function useCorrectionTargetDetailQuery(targetDocumentId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: correctionTargetDetailQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      targetDocumentId ?? "none",
    ),
    queryFn: () =>
      getCorrectionTargetDetail({
        accessToken: accessToken!,
        targetDocumentId: targetDocumentId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && targetDocumentId !== null,
  });
}

export function correctionProductsQueryKey(workstationCode: string, query: string) {
  return ["corrections", "products", workstationCode, normalizeQuery(query)] as const;
}

export function useCorrectionProductsQuery(query: string) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: correctionProductsQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, normalizedQuery),
    queryFn: () =>
      searchCorrectionProducts({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        query: normalizedQuery,
      }),
    enabled: accessToken !== null && normalizedQuery.length > 0,
  });
}

export function correctionsHistoryQueryKey(
  workstationCode: string,
  scope: string,
  query: string,
  createdByUserId: string,
  targetDocumentType: string,
  reasonCode: string,
) {
  return [
    "corrections",
    "history",
    workstationCode,
    scope,
    normalizeQuery(query),
    createdByUserId.trim(),
    targetDocumentType.trim(),
    reasonCode.trim(),
  ] as const;
}

export function useCorrectionsHistoryQuery(
  scope: string,
  query: string,
  createdByUserId: string,
  targetDocumentType: string,
  reasonCode: string,
) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);
  const normalizedCreatedByUserId = createdByUserId.trim();
  const normalizedTargetDocumentType = targetDocumentType.trim();
  const normalizedReasonCode = reasonCode.trim();

  return useQuery({
    queryKey: correctionsHistoryQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      scope,
      normalizedQuery,
      normalizedCreatedByUserId,
      normalizedTargetDocumentType,
      normalizedReasonCode,
    ),
    queryFn: () =>
      getCorrectionsHistory({
        accessToken: accessToken!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
        scope,
        query: normalizedQuery.length > 0 ? normalizedQuery : undefined,
        createdByUserId:
          normalizedCreatedByUserId.length > 0 ? normalizedCreatedByUserId : undefined,
        targetDocumentType:
          normalizedTargetDocumentType.length > 0 ? normalizedTargetDocumentType : undefined,
        reasonCode: normalizedReasonCode.length > 0 ? normalizedReasonCode : undefined,
      }),
    enabled: accessToken !== null,
  });
}

export function correctionDocumentDetailQueryKey(
  workstationCode: string,
  correctionId: string,
) {
  return ["corrections", "history-detail", workstationCode, correctionId] as const;
}

export function useCorrectionDocumentDetailQuery(correctionId: string | null) {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: correctionDocumentDetailQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      correctionId ?? "none",
    ),
    queryFn: () =>
      getCorrectionDocumentDetail({
        accessToken: accessToken!,
        correctionId: correctionId!,
        workstationCode: appEnv.VITE_POS_WORKSTATION_CODE,
      }),
    enabled: accessToken !== null && correctionId !== null,
  });
}
