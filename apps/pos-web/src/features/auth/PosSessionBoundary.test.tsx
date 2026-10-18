// @vitest-environment jsdom

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockSessionResponse } from "../../../e2e/helpers/session-mocks";
import { queryClient } from "../../lib/query-client";
import { requestJson } from "../../lib/http";
import { usePosAuthStore as auth } from "./auth-store";
import { PosSessionBoundary } from "./PosSessionBoundary";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let container: HTMLDivElement;
let root: Root;
beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(new Date("2026-10-18T12:00:00Z"));
  auth.getState().clearSession();
  container = document.createElement("div"); document.body.append(container);
  root = createRoot(container);
});
afterEach(() => {
  act(() => root.unmount()); container.remove(); auth.getState().clearSession();
  vi.useRealTimers(); vi.unstubAllGlobals();
});
async function renderBoundary() {
  await act(async () => root.render(<PosSessionBoundary><p>Protected business data</p></PosSessionBoundary>));
}

describe("session verification UI", () => {
  it("hides expired business data offline and restores only through a successful status read", async () => {
    const response = mockSessionResponse();
    response.session.idle_expires_at = new Date(Date.now() + 1_000).toISOString();
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(response)))
      .mockRejectedValueOnce(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);
    await renderBoundary();
    expect(container.textContent).toContain("Protected business data");
    queryClient.setQueryData(["private"], "cached business data");
    await act(async () => { await vi.advanceTimersByTimeAsync(1_101); });
    expect(container.textContent).not.toContain("Protected business data");
    expect(container.textContent).toContain("No fue posible verificar la sesión");
    expect(auth.getState()).toMatchObject({ phase: "restoring", isAuthenticated: false });
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    const renewed = mockSessionResponse();
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(renewed)));
    await act(async () => { container.querySelector("button")!.click(); });
    expect(container.textContent).toContain("Protected business data");
    expect(fetchMock.mock.calls).toHaveLength(3);
    for (const [url, options] of fetchMock.mock.calls) {
      expect(String(url)).toMatch(/\/v1\/auth\/session$/);
      expect(options.method).toBe("GET");
    }
  });

  it("restores the cookie and CSRF rotated by another tab when the locked tab gains focus", async () => {
    const locked = mockSessionResponse(); locked.session.status = "LOCKED";
    const rotated = mockSessionResponse(); rotated.csrf_token = "csrf-rotated-in-another-tab";
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(locked)))
      .mockResolvedValueOnce(new Response(JSON.stringify(rotated)));
    vi.stubGlobal("fetch", fetchMock);
    await renderBoundary();
    expect(container.textContent).toContain("Sesión bloqueada");
    await act(async () => { window.dispatchEvent(new Event("focus")); });
    expect(container.textContent).toContain("Protected business data");
    expect(auth.getState().csrfToken).toBe(rotated.csrf_token);
    expect(fetchMock.mock.calls).toHaveLength(2);
    expect(fetchMock.mock.calls.every(([url, options]) => String(url).endsWith("/v1/auth/session") && options.method === "GET")).toBe(true);
  });

  it("recovers CSRF after rejection without repeating the rejected mutation", async () => {
    auth.getState().setSession(mockSessionResponse());
    const rotated = mockSessionResponse(); rotated.csrf_token = "new-csrf";
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ code: "CSRF_FAILED", message: "Rejected.", details: null, field_errors: null, request_id: null }), { status: 403 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(rotated)));
    vi.stubGlobal("fetch", fetchMock);
    await expect(requestJson({ path: "/v1/auth/logout", method: "POST" })).rejects.toMatchObject({ statusCode: 403 });
    expect(fetchMock.mock.calls.map(([url, options]) => [new URL(String(url)).pathname, options.method])).toEqual([
      ["/v1/auth/logout", "POST"], ["/v1/auth/session", "GET"],
    ]);
    expect(auth.getState()).toMatchObject({ phase: "ready", csrfToken: rotated.csrf_token });
  });

  it("offers a status-read retry when CSRF recovery also loses connectivity", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(mockSessionResponse())))
      .mockResolvedValueOnce(new Response(JSON.stringify({ code: "CSRF_FAILED", message: "Rejected.", details: null, field_errors: null, request_id: null }), { status: 403 }))
      .mockRejectedValueOnce(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);
    await renderBoundary();
    await act(async () => { await expect(requestJson({ path: "/v1/auth/logout", method: "POST" })).rejects.toMatchObject({ statusCode: 403 }); });
    expect(container.textContent).not.toContain("Protected business data");
    expect(container.querySelector("button")?.textContent).toBe("Reintentar");
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(mockSessionResponse())));
    await act(async () => { container.querySelector("button")!.click(); });
    expect(container.textContent).toContain("Protected business data");
    expect(fetchMock.mock.calls.filter(([, options]) => options.method === "POST")).toHaveLength(1);
  });
});
