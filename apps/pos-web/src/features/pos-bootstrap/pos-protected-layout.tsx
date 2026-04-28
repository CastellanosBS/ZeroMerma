import { Navigate, useRouterState } from "@tanstack/react-router";
import type { PropsWithChildren } from "react";
import { useEffect } from "react";

import { AppShell } from "../../components/app-shell";
import { OperationalStatus } from "../../components/operational-status";
import { Button } from "../../components/ui/button";
import { ApiError, toOperationalErrorMessage } from "../../lib/http";
import { queryClient } from "../../lib/query-client";
import { useCurrentCashSessionQuery } from "../cash-session-open/queries";
import { usePosAuthStore } from "../auth/auth-store";
import { usePosShellStore } from "../pos-shell/shell-store";
import { usePosTerminalStore } from "../pos-terminal/store";
import { usePosBootstrapQuery } from "./queries";
import { resolvePosEntryRoute } from "./route-state";

export function PosProtectedLayout({ children }: PropsWithChildren) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const clearSession = usePosAuthStore((state) => state.clearSession);
  const resetPosTerminal = usePosTerminalStore((state) => state.reset);
  const lastOperationalPath = usePosShellStore((state) => state.lastOperationalPath);
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  });
  const bootstrapQuery = usePosBootstrapQuery();
  const currentCashSessionQuery = useCurrentCashSessionQuery();
  const isUnauthorized =
    (bootstrapQuery.error instanceof ApiError && bootstrapQuery.error.statusCode === 401) ||
    (currentCashSessionQuery.error instanceof ApiError && currentCashSessionQuery.error.statusCode === 401);

  useEffect(() => {
    if (!isUnauthorized) {
      return;
    }

    clearSession();
    resetPosTerminal();
    queryClient.clear();
  }, [clearSession, isUnauthorized, resetPosTerminal]);

  if (!accessToken) {
    return <Navigate to="/login" />;
  }

  if (isUnauthorized) {
    return <Navigate to="/login" />;
  }

  if (bootstrapQuery.isPending || currentCashSessionQuery.isPending) {
    return (
      <div className="min-h-screen bg-[var(--pos-shell-bg)] px-4 py-4">
        <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-3xl items-center">
          <OperationalStatus
            description="Consultando la sucursal, la estacion y el cajero de este punto de venta."
            title="Cargando contexto"
          />
        </div>
      </div>
    );
  }

  if (bootstrapQuery.error) {
    return (
      <div className="min-h-screen bg-[var(--pos-shell-bg)] px-4 py-4">
        <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-3xl items-center">
          <OperationalStatus
            action={<Button onClick={() => bootstrapQuery.refetch()}>Reintentar</Button>}
            description={toOperationalErrorMessage(
              bootstrapQuery.error,
              "Confirma la API, la asignacion de sucursal y la configuracion de la estacion.",
            )}
            title="No fue posible cargar el contexto"
          />
        </div>
      </div>
    );
  }

  if (currentCashSessionQuery.error) {
    return (
      <div className="min-h-screen bg-[var(--pos-shell-bg)] px-4 py-4">
        <div className="mx-auto flex min-h-[calc(100vh-2rem)] max-w-3xl items-center">
          <OperationalStatus
            action={<Button onClick={() => currentCashSessionQuery.refetch()}>Reintentar</Button>}
            description={toOperationalErrorMessage(
              currentCashSessionQuery.error,
              "Confirma la conexion con la API y el estado actual de la caja para esta estacion.",
            )}
            title="No fue posible consultar la caja"
          />
        </div>
      </div>
    );
  }

  const hasActiveCashSession = currentCashSessionQuery.data !== null;
  const resumePath =
    hasActiveCashSession &&
    lastOperationalPath &&
    lastOperationalPath !== "/" &&
    lastOperationalPath !== "/cash-session/open"
      ? lastOperationalPath
      : "/pos";

  if (pathname === "/") {
    const nextRoute = resolvePosEntryRoute({
      hasActiveCashSession,
      hasAccessToken: true,
    });

    return <Navigate to={nextRoute === "/pos" ? resumePath : nextRoute} />;
  }

  const bootstrap = bootstrapQuery.data;

  return (
    <AppShell
      bootstrap={bootstrap}
      cashSession={currentCashSessionQuery.data}
      onSignOut={() => {
        clearSession();
        resetPosTerminal();
        queryClient.clear();
      }}
    >
      {children}
    </AppShell>
  );
}
