import { useQuery } from "@tanstack/react-query";
import { Navigate } from "@tanstack/react-router";
import { useEffect, useMemo } from "react";

import { AdminLayout } from "../admin/layout/AdminLayout";
import { getCurrentBackofficeUser } from "../../lib/api";
import {
  clearAccessTokenFromCurrentUrl,
  isBackofficeUser,
  readAccessTokenFromUrl,
  redirectToPos,
} from "./auth-surfaces";
import { useBackofficeAuthStore } from "./backoffice-auth-store";

export function ProtectedAdminRoute() {
  const accessToken = useBackofficeAuthStore((state) => state.accessToken);
  const setAccessToken = useBackofficeAuthStore((state) => state.setAccessToken);
  const clearSession = useBackofficeAuthStore((state) => state.clearSession);
  const urlAccessToken = useMemo(() => readAccessTokenFromUrl(new URL(window.location.href)), []);
  const effectiveAccessToken = accessToken ?? urlAccessToken;
  const currentUserQuery = useQuery({
    enabled: Boolean(effectiveAccessToken),
    queryFn: () => getCurrentBackofficeUser(effectiveAccessToken ?? ""),
    queryKey: ["backoffice-auth", "surface", effectiveAccessToken],
    retry: false,
  });

  useEffect(() => {
    if (!urlAccessToken) {
      return;
    }

    setAccessToken(urlAccessToken);
    clearAccessTokenFromCurrentUrl();
  }, [setAccessToken, urlAccessToken]);

  useEffect(() => {
    if (currentUserQuery.isError) {
      clearSession();
    }
  }, [clearSession, currentUserQuery.isError]);

  useEffect(() => {
    if (!currentUserQuery.data || isBackofficeUser(currentUserQuery.data)) {
      return;
    }

    clearSession();
    redirectToPos();
  }, [clearSession, currentUserQuery.data]);

  if (!effectiveAccessToken) {
    return <Navigate to="/login" />;
  }

  if (currentUserQuery.isLoading || !currentUserQuery.data) {
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

  return <AdminLayout />;
}
