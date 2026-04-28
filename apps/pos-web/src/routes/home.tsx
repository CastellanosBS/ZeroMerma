import { Navigate } from "@tanstack/react-router";

import { usePosAuthStore } from "../features/auth/auth-store";
import { useCurrentCashSessionQuery } from "../features/cash-session-open/queries";
import { resolvePosEntryRoute } from "../features/pos-bootstrap/route-state";

export function HomePage() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const currentCashSessionQuery = useCurrentCashSessionQuery();

  const nextRoute = resolvePosEntryRoute({
    hasActiveCashSession: currentCashSessionQuery.data !== null,
    hasAccessToken: accessToken !== null,
  });

  return <Navigate to={nextRoute} />;
}
