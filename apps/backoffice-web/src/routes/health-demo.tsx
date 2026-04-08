import { useQuery } from "@tanstack/react-query";

import { fetchApiHealth } from "../lib/api";
import type { HealthResponse } from "../lib/api";

const fallbackHealth: HealthResponse = {
  status: "not checked",
  service: "zeromerma-api",
  environment: "local",
  version: "0.1.0",
};

export function HealthDemoPage() {
  const {
    data = fallbackHealth,
    error,
    isFetching,
  } = useQuery({
    queryKey: ["api-health"],
    queryFn: fetchApiHealth,
    retry: false,
  });

  return (
    <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-semibold">API health</h1>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-slate-600">Status</dt>
          <dd className="mt-1 text-lg font-semibold">{isFetching ? "checking" : data.status}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Service</dt>
          <dd className="mt-1 text-lg font-semibold">{data.service}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Environment</dt>
          <dd className="mt-1 text-lg font-semibold">{data.environment}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Version</dt>
          <dd className="mt-1 text-lg font-semibold">{data.version}</dd>
        </div>
      </dl>
      {error ? (
        <p className="mt-4 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          API health is unavailable from this browser session.
        </p>
      ) : null}
    </section>
  );
}
