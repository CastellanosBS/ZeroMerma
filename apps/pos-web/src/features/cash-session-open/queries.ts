import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getCurrentCashSession } from "./cash-session-api";

export function currentCashSessionQueryKey(workstationCode: string) {
  return ["current-cash-session", workstationCode] as const;
}

export function useCurrentCashSessionQuery() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);

  return useQuery({
    queryKey: currentCashSessionQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getCurrentCashSession(appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: isAuthenticated,
  });
}
