import { Navigate } from "@tanstack/react-router";

import { OperationalStatus } from "../components/operational-status";
import { Button } from "../components/ui/button";
import { CashSessionActiveState } from "../features/cash-session-open/cash-session-active-state";
import { useCurrentCashSessionQuery } from "../features/cash-session-open/queries";
import { usePosAuthStore } from "../features/auth/auth-store";
import { usePosBootstrapQuery } from "../features/pos-bootstrap/queries";
import { resolvePosEntryRoute } from "../features/pos-bootstrap/route-state";
import { toOperationalErrorMessage } from "../lib/http";

export function HomePage() {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const bootstrapQuery = usePosBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();

  if (bootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <OperationalStatus
        description="Retrieving the current register state for this workstation."
        title="Loading register"
      />
    );
  }

  if (bootstrapQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => bootstrapQuery.refetch()}>Retry context load</Button>}
        description={toOperationalErrorMessage(
          bootstrapQuery.error,
          "Confirm the API connection and workstation setup.",
        )}
        title="Register context is unavailable"
      />
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <OperationalStatus
        action={<Button onClick={() => currentCashSessionQuery.refetch()}>Retry session check</Button>}
        description={toOperationalErrorMessage(
          currentCashSessionQuery.error,
          "Confirm the API connection and retry the active-session check.",
        )}
        title="Register state is unavailable"
      />
    );
  }

  const nextRoute = resolvePosEntryRoute({
    hasAccessToken: accessToken !== null,
    hasActiveCashSession: currentCashSessionQuery.data !== null,
  });

  if (nextRoute === "/login") {
    return <Navigate to="/login" />;
  }

  if (nextRoute === "/cash-session/open") {
    return <Navigate to="/cash-session/open" />;
  }

  return (
    <CashSessionActiveState
      bootstrap={bootstrapQuery.data}
      cashSession={currentCashSessionQuery.data!}
    />
  );
}
