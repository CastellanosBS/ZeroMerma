import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockSessionResponse } from "../../../e2e/helpers/session-mocks";
import { queryClient } from "../../lib/query-client";
import { requestJson } from "../../lib/http";
import { usePosAuthStore as auth } from "./auth-store";
import { logoutSession, reauthenticate, restoreSession } from "./session-api";

function errorResponse(code: string, status: number) {
  return new Response(JSON.stringify({ code, message: "Session operation rejected.", details: null, request_id: null, field_errors: null }), { status });
}
beforeEach(() => auth.getState().clearSession());
afterEach(() => { auth.getState().clearSession(); vi.unstubAllGlobals(); });

describe("POS server session lifecycle", () => {
  it("restores a locked session and its memory-only CSRF without enabling business routes", async () => {
    const response = mockSessionResponse(); response.session.status = "LOCKED";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(response))));
    await restoreSession();
    expect(auth.getState()).toMatchObject({ phase: "locked", isAuthenticated: false, csrfToken: response.csrf_token });
  });
  it("waits for server logout and preserves the session if the network fails", async () => {
    auth.getState().setSession(mockSessionResponse());
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(logoutSession()).rejects.toThrow("offline");
    expect(auth.getState().isAuthenticated).toBe(true);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    await logoutSession();
    expect(auth.getState()).toMatchObject({ phase: "signedOut", csrfToken: null });
  });
  it("clears business data on 423 and preserves unlock access after a wrong password", async () => {
    auth.getState().setSession(mockSessionResponse());
    queryClient.setQueryData(["private"], { value: "cached" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(errorResponse("SESSION_LOCKED", 423)));
    await expect(requestJson({ path: "/v1/pos/catalog" })).rejects.toMatchObject({ statusCode: 423 });
    expect(auth.getState().phase).toBe("locked");
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(errorResponse("INVALID_CREDENTIALS", 401)));
    await expect(reauthenticate({ password: "incorrect" })).rejects.toMatchObject({ statusCode: 401 });
    expect(auth.getState()).toMatchObject({ phase: "locked", csrfToken: "mock-csrf-memory-only" });
    const unlocked = mockSessionResponse(); unlocked.csrf_token = "rotated-memory-csrf";
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(unlocked))));
    await reauthenticate({ password: "correct-for-test" });
    expect(auth.getState()).toMatchObject({ phase: "ready", csrfToken: "rotated-memory-csrf" });
  });
  it("ignores an old unauthorized response after another session was established", async () => {
    auth.getState().setSession(mockSessionResponse());
    let finish!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => new Promise<Response>(resolve => { finish = resolve; })));
    const pending = requestJson({ path: "/v1/pos/catalog" });
    const next = mockSessionResponse(); next.csrf_token = "next-actor-csrf"; next.session.id = "next-session";
    auth.getState().setSession(next);
    finish(errorResponse("SESSION_REVOKED", 401));
    await expect(pending).rejects.toMatchObject({ statusCode: 401 });
    expect(auth.getState()).toMatchObject({ phase: "ready", csrfToken: "next-actor-csrf" });
  });
  it("does not unlock from an older active restore response", async () => {
    auth.getState().setSession(mockSessionResponse());
    let finish!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => new Promise<Response>(resolve => { finish = resolve; })));
    const pending = restoreSession();
    auth.getState().markLocked();
    finish(new Response(JSON.stringify(mockSessionResponse())));
    await pending;
    expect(auth.getState()).toMatchObject({ phase: "locked", isAuthenticated: false });
  });
  it("does not resurrect a completed logout from an older restore response", async () => {
    let finish!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn().mockImplementation(() => new Promise<Response>(resolve => { finish = resolve; })));
    const pending = restoreSession();
    auth.getState().clearSession();
    finish(new Response(JSON.stringify(mockSessionResponse())));
    await pending;
    expect(auth.getState()).toMatchObject({ phase: "signedOut", csrfToken: null });
  });
});
