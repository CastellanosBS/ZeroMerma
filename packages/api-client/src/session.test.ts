import { afterEach, describe, expect, it, vi } from "vitest";
import { observeOperatorActivity, removeLegacyAuthStorage } from "./session";
import { requestApiJson } from "./transport";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
describe("cookie session transport", () => {
  it("includes the selected audience but never sends CSRF on a read", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}")); vi.stubGlobal("fetch", fetchMock);
    await requestApiJson({ surface: "BACKOFFICE", baseUrl: "https://api.test", path: "/v1/auth/session", csrfToken: "memory-only", headers: { "X-CSRF-Token": "caller-value" } });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(init.credentials).toBe("include");
    expect((init.headers as Headers).get("X-ZeroMerma-Surface")).toBe("BACKOFFICE");
    expect((init.headers as Headers).has("X-CSRF-Token")).toBe(false);
  });
  it("rejects a bearer header before sending any request", async () => {
    const fetchMock = vi.fn(); vi.stubGlobal("fetch", fetchMock);
    await expect(requestApiJson({ surface: "POS", baseUrl: "https://api.test", path: "/resource", headers: { Authorization: "Bearer obsolete" } })).rejects.toThrow("Bearer authentication is not supported");
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("sends CSRF for a mutation and supports the empty logout response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 })); vi.stubGlobal("fetch", fetchMock);
    await expect(requestApiJson({ surface: "POS", baseUrl: "https://api.test", path: "/v1/auth/logout", method: "POST", csrfToken: "in-memory" })).resolves.toBeUndefined();
    expect((fetchMock.mock.calls[0][1].headers as Headers).get("X-CSRF-Token")).toBe("in-memory");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
describe("operator activity", () => {
  it("only emits trusted keyboard/pointer/touch activity, throttles it and never polls", () => {
    vi.useFakeTimers();
    const handlers = new Map<string, EventListener>();
    const target = { addEventListener: (name: string, listener: EventListenerOrEventListenerObject) => handlers.set(name, listener as EventListener), removeEventListener: (name: string) => handlers.delete(name) };
    const activity = vi.fn();
    const stop = observeOperatorActivity(target, activity);
    vi.advanceTimersByTime(60_000); expect(activity).not.toHaveBeenCalled();
    handlers.get("keydown")!({ isTrusted: false } as Event); expect(activity).not.toHaveBeenCalled();
    handlers.get("pointerdown")!({ isTrusted: true } as Event);
    handlers.get("touchstart")!({ isTrusted: true } as Event); expect(activity).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(30_001); expect(activity).toHaveBeenCalledTimes(1);
    handlers.get("keydown")!({ isTrusted: true } as Event); expect(activity).toHaveBeenCalledTimes(2);
    stop(); expect(handlers.size).toBe(0);
  });
  it("deletes both old auth keys even if no session is available", () => {
    const removeItem = vi.fn(); removeLegacyAuthStorage({ removeItem });
    expect(removeItem.mock.calls).toEqual([["zeromerma-pos-auth"], ["zeromerma-backoffice-auth"]]);
    expect(() => removeLegacyAuthStorage({ removeItem: () => { throw new Error("disabled storage"); } })).not.toThrow();
  });
});
