import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";

import { logoutSession } from "./session-api";

import { AdminLayout } from "../admin/layout/AdminLayout";
import { ApiError, getCurrentBackofficeUser } from "../../lib/api";
import {
  backofficeAuthorizationQueryKey,
  clearAdministrativeQueries,
} from "../../lib/query-client";
import { authorizationIdentity } from "./authorization";
import { BackofficeAuthorizationContext } from "./authorization-context";
import {
  clearDisallowedAccessTokenFromCurrentUrl,
  isBackofficeUser,
  redirectToPos,
} from "./auth-surfaces";
import { useBackofficeAuthStore } from "./backoffice-auth-store";

export function ProtectedAdminRoute() {
  const isAuthenticated = useBackofficeAuthStore((state) => state.isAuthenticated);
  const clearSession = useBackofficeAuthStore((state) => state.clearSession);
  const queryClient = useQueryClient();
  const [logoutError, setLogoutError] = useState<string | null>(null);
  const [acceptedIdentity, setAcceptedIdentity] = useState<string | null>(null);
  const currentUserQuery = useQuery({
    enabled: isAuthenticated,
    queryFn: () => getCurrentBackofficeUser(),
    queryKey: backofficeAuthorizationQueryKey,
    retry: false,
    refetchInterval: 60_000,
    refetchOnWindowFocus: "always",
  });
  const identity = currentUserQuery.data ? authorizationIdentity(currentUserQuery.data) : null;

  useEffect(() => {
    if (!identity || identity === acceptedIdentity) return;
    let current = true;
    void clearAdministrativeQueries(queryClient).then(() => {
      if (current) setAcceptedIdentity(identity);
    });
    return () => {
      current = false;
    };
  }, [acceptedIdentity, identity, queryClient]);

  useEffect(() => {
    clearDisallowedAccessTokenFromCurrentUrl();
  }, []);

  useEffect(() => {
    if (currentUserQuery.error instanceof ApiError && currentUserQuery.error.statusCode === 401) {
      clearSession();
    }
  }, [clearSession, currentUserQuery.error]);

  useEffect(() => {
    if (!currentUserQuery.data || isBackofficeUser(currentUserQuery.data)) {
      return;
    }

    clearSession();
    redirectToPos();
  }, [clearSession, currentUserQuery.data]);

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (currentUserQuery.isError) {
    return (
      <main className="grid min-h-screen place-content-center gap-3 bg-slate-50 px-4 text-slate-950">
        <h1 className="text-xl font-semibold">No fue posible validar el acceso</h1>
        <p>Revisa la conexión o solicita que revisen tus permisos.</p>
        <button type="button" onClick={() => void currentUserQuery.refetch()}>
          Reintentar
        </button>
        {logoutError ? <p role="alert">{logoutError}</p> : null}
        <button type="button" onClick={() => void logoutSession().catch(() => setLogoutError("No se pudo cerrar la sesión. Reintenta."))}>
          Cerrar sesión
        </button>
      </main>
    );
  }

  if (currentUserQuery.isLoading || !currentUserQuery.data || identity !== acceptedIdentity) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-50 px-4 py-10 text-slate-950">
        <div className="rounded-[24px] border border-[var(--ui-color-border)] bg-white px-5 py-4 text-sm font-semibold shadow-[var(--ui-shadow-subtle)]">
          Validando acceso administrativo...
        </div>
      </main>
    );
  }

  if (!isBackofficeUser(currentUserQuery.data)) {
    return null;
  }

  return (
    <BackofficeAuthorizationContext.Provider value={currentUserQuery.data}>
      <AdminLayout key={identity} />
    </BackofficeAuthorizationContext.Provider>
  );
}
