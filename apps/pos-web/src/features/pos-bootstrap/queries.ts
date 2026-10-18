import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getPosBootstrap } from "./pos-bootstrap-api";

export function bootstrapQueryKey(workstationCode: string) {
  return ["pos-bootstrap", workstationCode] as const;
}

export function usePosBootstrapQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: bootstrapQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getPosBootstrap(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}
