import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getPosCatalog, getPosClassProducts } from "./pos-terminal-api";

function normalizeQuery(query: string): string {
  return query.trim();
}

export function posCatalogQueryKey(workstationCode: string, query: string) {
  return ["pos-catalog", workstationCode, normalizeQuery(query)] as const;
}

export function usePosCatalogQuery(query: string) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: posCatalogQueryKey(appEnv.VITE_POS_WORKSTATION_CODE, normalizedQuery),
    queryFn: () =>
      getPosCatalog(
        accessToken!,
        appEnv.VITE_POS_WORKSTATION_CODE,
        normalizedQuery.length > 0 ? normalizedQuery : undefined,
      ),
    enabled: accessToken !== null,
  });
}

export function posClassProductsQueryKey(
  workstationCode: string,
  classId: string,
  query: string,
) {
  return ["pos-class-products", workstationCode, classId, normalizeQuery(query)] as const;
}

export function usePosClassProductsQuery(classId: string | null, query: string) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const normalizedQuery = normalizeQuery(query);

  return useQuery({
    queryKey: posClassProductsQueryKey(
      appEnv.VITE_POS_WORKSTATION_CODE,
      classId ?? "none",
      normalizedQuery,
    ),
    queryFn: () =>
      getPosClassProducts(
        accessToken!,
        appEnv.VITE_POS_WORKSTATION_CODE,
        classId!,
        normalizedQuery.length > 0 ? normalizedQuery : undefined,
      ),
    enabled: accessToken !== null && classId !== null,
  });
}
