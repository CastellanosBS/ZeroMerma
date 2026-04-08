import { useQuery } from "@tanstack/react-query";

import { appEnv } from "../../env";
import { usePosAuthStore } from "../auth/auth-store";
import { getCurrentCashSession } from "./cash-session-api";

export function currentCashSessionQueryKey(workstationCode: string) {
  return ["current-cash-session", workstationCode] as const;
}

export function useCurrentCashSessionQuery() {
  const accessToken = usePosAuthStore((state) => state.accessToken);

  return useQuery({
    queryKey: currentCashSessionQueryKey(appEnv.VITE_POS_WORKSTATION_CODE),
    queryFn: () => getCurrentCashSession(accessToken!, appEnv.VITE_POS_WORKSTATION_CODE),
    enabled: accessToken !== null,
  });
}
