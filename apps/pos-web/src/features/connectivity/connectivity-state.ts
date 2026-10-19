import { requestApiJson, type components } from "@zeromerma/api-client";
import { create } from "zustand";

import { appEnv } from "../../env";

type LocalReadinessResponse = components["schemas"]["LocalReadinessResponse"];
export type LocalConnectionStatus = "unknown" | "ready" | "unreachable" | "databaseUnavailable";

interface ConnectivityState {
  local: LocalConnectionStatus;
  checking: boolean;
  browserNetworkHint: boolean | null;
  lastVerifiedAt: number | null;
}

export const useConnectivityStore = create<ConnectivityState>(() => ({
  local: "unknown",
  checking: false,
  browserNetworkHint: typeof navigator === "undefined" ? null : navigator.onLine,
  lastVerifiedAt: null,
}));

let monitoring = 0;
let inFlight: Promise<boolean> | null = null;
let epoch = 0;

function readinessState(value: unknown): LocalConnectionStatus {
  if (typeof value !== "object" || value === null ||
    !("transactional_mode" in value) || value.transactional_mode !== "LOCAL_FIRST" ||
    !("browser_offline_mutations" in value) || value.browser_offline_mutations !== false ||
    !("internet" in value) || value.internet !== "UNKNOWN" ||
    !("status" in value) || !("database" in value)) return "unknown";
  if (value.status === "READY" && value.database === "READY") return "ready";
  if (value.status === "UNAVAILABLE" && value.database === "UNAVAILABLE") return "databaseUnavailable";
  return "unknown";
}

export class LocalBackendUnavailableError extends Error {
  readonly requestSent = false;
  constructor() {
    super("No se envió la operación: no fue posible verificar el servidor local y su base de datos. Revisa la red del local y consulta la referencia pendiente antes de reintentar.");
    this.name = "LocalBackendUnavailableError";
  }
}

export function updateBrowserNetworkHint() {
  useConnectivityStore.setState({ browserNetworkHint: navigator.onLine });
}

export function markLocalConnectionUnreachable() {
  useConnectivityStore.setState({ local: "unreachable" });
}

export function observeLocalConnectivity() {
  monitoring += 1;
  return () => {
    monitoring = Math.max(0, monitoring - 1);
    if (monitoring === 0) {
      epoch += 1;
      inFlight = null;
      useConnectivityStore.setState({ local: "unknown", checking: false, lastVerifiedAt: null });
    }
  };
}

export function checkLocalReadiness(): Promise<boolean> {
  if (inFlight) return inFlight;
  const expectedEpoch = epoch;
  useConnectivityStore.setState({ checking: true });
  const controller = new AbortController();
  const timer = globalThis.setTimeout(() => controller.abort(), 5_000);
  const probe = async () => {
    try {
      const response = await requestApiJson<LocalReadinessResponse>({
        baseUrl: appEnv.VITE_API_BASE_URL,
        surface: "POS",
        path: "/ready",
        signal: controller.signal,
      });
      const local = readinessState(response);
      const ready = local === "ready";
      if (epoch === expectedEpoch) useConnectivityStore.setState({
        local,
        lastVerifiedAt: ready ? Date.now() : null,
      });
      return ready;
    } catch (error) {
      // Only the explicit readiness response identifies PostgreSQL as unavailable.
      // A transport failure cannot distinguish LAN, DNS, TLS, proxy, or API failure.
      const unavailable = error instanceof Error && "responseBody" in error &&
        readinessState(error.responseBody) === "databaseUnavailable";
      if (epoch === expectedEpoch) useConnectivityStore.setState({
        local: unavailable ? "databaseUnavailable" : "unreachable",
        lastVerifiedAt: null,
      });
      return false;
    } finally {
      globalThis.clearTimeout(timer);
      if (epoch === expectedEpoch) {
        useConnectivityStore.setState({ checking: false });
        inFlight = null;
      }
    }
  };
  inFlight = probe();
  return inFlight;
}

export async function requireLocalBackendForCommand() {
  // Unit consumers can use the transport without mounting the application boundary.
  // Every mounted POS app enables this guard before its business content is rendered.
  if (monitoring === 0) return;
  if (!(await checkLocalReadiness())) throw new LocalBackendUnavailableError();
}
