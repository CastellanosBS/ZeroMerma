// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { requestJson } from "../../lib/http";
import {
  checkLocalReadiness,
  LocalBackendUnavailableError,
  observeLocalConnectivity,
  requireLocalBackendForCommand,
  updateBrowserNetworkHint,
  useConnectivityStore,
} from "./connectivity-state";

const ready = { status: "READY", database: "READY", internet: "UNKNOWN", transactional_mode: "LOCAL_FIRST", browser_offline_mutations: false };
let stop: () => void;
beforeEach(() => { stop = observeLocalConnectivity(); });
afterEach(() => { stop(); vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe("local-first command admission", () => {
  it("admits a healthy LAN command despite an offline browser hint", async () => {
    vi.spyOn(navigator, "onLine", "get").mockReturnValue(false);
    updateBrowserNetworkHint();
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(ready)))
      .mockResolvedValueOnce(new Response(JSON.stringify({ id: "confirmed" })));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestJson({ path: "/v1/sales/confirm", method: "POST", headers: { "Idempotency-Key": "same-key" } })).resolves.toEqual({ id: "confirmed" });
    expect(fetchMock.mock.calls.map(([url, options]) => [new URL(url).pathname, options.method])).toEqual([["/ready", "GET"], ["/v1/sales/confirm", "POST"]]);
    expect(useConnectivityStore.getState()).toMatchObject({ local: "ready", browserNetworkHint: false });
  });

  it("does not send a command when the local database reports unavailable", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...ready, status: "UNAVAILABLE", database: "UNAVAILABLE" }), { status: 503 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestJson({ path: "/v1/sales/confirm", method: "POST" })).rejects.toBeInstanceOf(LocalBackendUnavailableError);
    expect(fetchMock.mock.calls.every(([, options]) => options.method === "GET")).toBe(true);
    expect(useConnectivityStore.getState().local).toBe("databaseUnavailable");
  });

  it("does not infer an Internet outage from a local transport failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(requireLocalBackendForCommand()).rejects.toMatchObject({ requestSent: false });
    expect(useConnectivityStore.getState().local).toBe("unreachable");
  });

  it.each([null, { status: "ok" }, { ...ready, database: "UNAVAILABLE" }])("keeps an unexpected readiness response unknown instead of diagnosing the database: %j", async response => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(response)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requireLocalBackendForCommand()).rejects.toMatchObject({ requestSent: false });
    expect(useConnectivityStore.getState().local).toBe("unknown");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("uses only a readiness read after a lost command response and preserves the request key", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(ready)))
      .mockRejectedValueOnce(new TypeError("Lost after commit"))
      .mockResolvedValueOnce(new Response(JSON.stringify(ready)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestJson({ path: "/v1/sales/confirm", method: "POST", headers: { "Idempotency-Key": "original-key" } })).rejects.toThrow("Consulta su referencia");
    expect(useConnectivityStore.getState().local).toBe("unreachable");
    await checkLocalReadiness();
    const posts = fetchMock.mock.calls.filter(([, options]) => options.method === "POST");
    expect(posts).toHaveLength(1);
    expect(posts[0]![1].headers.get("Idempotency-Key")).toBe("original-key");
  });

  it("bounds a stalled probe and never issues the waiting command", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
    }));
    vi.stubGlobal("fetch", fetchMock);
    const command = requestJson({ path: "/v1/sales/confirm", method: "POST" });
    const rejected = expect(command).rejects.toBeInstanceOf(LocalBackendUnavailableError);
    await vi.advanceTimersByTimeAsync(5_000);
    await rejected;
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(useConnectivityStore.getState().checking).toBe(false);
  });

  it("never trusts a cached ready result or the workstation clock for a new command", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(ready)))
      .mockRejectedValueOnce(new TypeError("LAN lost"));
    vi.stubGlobal("fetch", fetchMock);
    expect(await checkLocalReadiness()).toBe(true);
    vi.setSystemTime(new Date("2020-01-01"));
    await expect(requireLocalBackendForCommand()).rejects.toBeInstanceOf(LocalBackendUnavailableError);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
