import { Navigate } from "@tanstack/react-router";

import { usePosAuthStore } from "../features/auth/auth-store";
import { useCurrentCashSessionQuery } from "../features/cash-session-open/queries";
import { resolvePosEntryRoute } from "../features/pos-bootstrap/route-state";

export function HomePage() {
  const isAuthenticated = usePosAuthStore((state) => state.isAuthenticated);
  const currentCashSessionQuery = useCurrentCashSessionQuery();

  const nextRoute = resolvePosEntryRoute({
    hasActiveCashSession: currentCashSessionQuery.data !== null,
    isAuthenticated: isAuthenticated,
  });

  return <Navigate to={nextRoute} />;
}
