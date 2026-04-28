import { useQuery } from "@tanstack/react-query";

import { fetchApiHealth } from "../lib/api";
import type { HealthResponse } from "../lib/api";

const fallbackHealth: HealthResponse = {
  status: "sin revisar",
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
      <h1 className="text-2xl font-semibold">Salud de la API</h1>
      <dl className="mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <dt className="text-sm font-medium text-slate-600">Estado</dt>
          <dd className="mt-1 text-lg font-semibold">{isFetching ? "revisando" : data.status}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Servicio</dt>
          <dd className="mt-1 text-lg font-semibold">{data.service}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Entorno</dt>
          <dd className="mt-1 text-lg font-semibold">{data.environment}</dd>
        </div>
        <div>
          <dt className="text-sm font-medium text-slate-600">Version</dt>
          <dd className="mt-1 text-lg font-semibold">{data.version}</dd>
        </div>
      </dl>
      {error ? (
        <p className="mt-4 rounded-md border border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] px-3 py-2 text-sm text-[var(--ui-color-warning)]">
          La salud de la API no esta disponible desde esta sesion del navegador.
        </p>
      ) : null}
    </section>
  );
}
