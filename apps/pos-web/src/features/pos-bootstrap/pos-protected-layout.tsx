import { Navigate } from "@tanstack/react-router";
import type { PropsWithChildren } from "react";
import { useEffect } from "react";

import { AppShell } from "../../components/app-shell";
import { Button } from "../../components/ui/button";
import { formatLocalDateTime } from "../../lib/formatters";
import { ApiError, toOperationalErrorMessage } from "../../lib/http";
import { queryClient } from "../../lib/query-client";
import { usePosAuthStore } from "../auth/auth-store";
import { usePosBootstrapQuery } from "./queries";

export function PosProtectedLayout({ children }: PropsWithChildren) {
  const accessToken = usePosAuthStore((state) => state.accessToken);
  const clearSession = usePosAuthStore((state) => state.clearSession);
  const bootstrapQuery = usePosBootstrapQuery();
  const isUnauthorized =
    bootstrapQuery.error instanceof ApiError && bootstrapQuery.error.statusCode === 401;

  useEffect(() => {
    if (!isUnauthorized) {
      return;
    }

    clearSession();
    queryClient.clear();
  }, [clearSession, isUnauthorized]);

  if (!accessToken) {
    return <Navigate to="/login" />;
  }

  if (isUnauthorized) {
    return <Navigate to="/login" />;
  }

  if (bootstrapQuery.isPending) {
    return (
      <div className="min-h-screen bg-slate-50 px-4 py-10">
        <section className="mx-auto max-w-3xl rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium uppercase tracking-wide text-green-800">ZeroMerma POS</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Loading workstation context</h1>
          <p className="mt-4 text-sm leading-6 text-slate-700">
            Retrieving the active branch, workstation, and operator context for this register.
          </p>
        </section>
      </div>
    );
  }

  if (bootstrapQuery.error) {
    return (
      <div className="min-h-screen bg-slate-50 px-4 py-10">
        <section className="mx-auto max-w-3xl rounded-lg border border-amber-200 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium uppercase tracking-wide text-green-800">ZeroMerma POS</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            Workstation context is unavailable
          </h1>
          <p className="mt-4 text-sm leading-6 text-slate-700">
            {toOperationalErrorMessage(
              bootstrapQuery.error,
              "Confirm the API, branch assignment, and workstation configuration.",
            )}
          </p>
          <div className="mt-6">
            <Button onClick={() => bootstrapQuery.refetch()}>Retry context load</Button>
          </div>
        </section>
      </div>
    );
  }

  const bootstrap = bootstrapQuery.data;

  return (
    <AppShell
      branchName={bootstrap.branch.name}
      localDateTime={formatLocalDateTime(bootstrap.local_timestamp, bootstrap.branch.timezone)}
      operatorName={bootstrap.user.full_name}
      onSignOut={() => {
        clearSession();
        queryClient.clear();
      }}
      workstationName={bootstrap.workstation.name}
    >
      {children}
    </AppShell>
  );
}
