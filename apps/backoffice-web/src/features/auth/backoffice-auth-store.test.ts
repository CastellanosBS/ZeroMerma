import type { SessionResponse } from "@zeromerma/api-client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "../../lib/query-client";
import { useBackofficeAuthStore as auth } from "./backoffice-auth-store";

function response(id = "actor-1", version = "v1"): SessionResponse {
  return {
    csrf_token: `memory-csrf-${id}`,
    session: { id, audience: "BACKOFFICE", status: "ACTIVE", created_at: "2026-10-18T00:00:00Z", last_activity_at: "2026-10-18T00:00:00Z", idle_expires_at: "2026-10-18T00:30:00Z", absolute_expires_at: "2026-10-18T08:00:00Z", workstation_id: null, cash_session_id: null, revoked_at: null, revocation_reason: null },
    user: { id, email: "operator@example.invalid", full_name: "Operator", is_active: true, default_surface: "BACKOFFICE", allowed_surfaces: ["BACKOFFICE"], authorization_surface: "BACKOFFICE", authorization_version: version, is_superadministrator: false, effective_grants: [], password_reset_required: false },
  };
}
beforeEach(() => {
  vi.stubGlobal("localStorage", { removeItem: vi.fn(), setItem: vi.fn() });
  auth.getState().clearSession();
});
afterEach(() => { auth.getState().clearSession(); vi.unstubAllGlobals(); });

describe("server session cache boundary", () => {
  it("clears reads and authorization when the actor or authorization version changes", () => {
    auth.getState().setSession(response());
    queryClient.setQueryData(["admin", "users"], { private: "previous actor" });
    auth.getState().setSession(response("actor-2"));
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    queryClient.setQueryData(["admin", "users"], { private: "old grants" });
    auth.getState().setSession(response("actor-2", "v2"));
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });
  it("never persists credentials or CSRF and removes obsolete auth storage", () => {
    auth.getState().setSession(response());
    expect(auth.getState().csrfToken).toBe("memory-csrf-actor-1");
    expect(localStorage.setItem).not.toHaveBeenCalled();
    expect(localStorage.removeItem).toHaveBeenCalledWith("zeromerma-pos-auth");
    expect(localStorage.removeItem).toHaveBeenCalledWith("zeromerma-backoffice-auth");
  });
  it("clears queries, mutations and credentials when signed out", async () => {
    auth.getState().setSession(response());
    queryClient.setQueryData(["admin", "reports"], { private: true });
    await queryClient.getMutationCache().build(queryClient, { mutationFn: async () => "private export" }).execute(undefined);
    auth.getState().clearSession();
    expect(auth.getState()).toMatchObject({ isAuthenticated: false, csrfToken: null, session: null, phase: "signedOut" });
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0);
  });
  it("blocks business UI and purges reads on lock or forced password change", () => {
    auth.getState().setSession(response());
    queryClient.setQueryData(["private"], "sensitive");
    auth.getState().markLocked();
    expect(auth.getState()).toMatchObject({ phase: "locked", isAuthenticated: false });
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    const restricted = response(); restricted.user.password_reset_required = true;
    auth.getState().setSession(restricted);
    expect(auth.getState()).toMatchObject({ phase: "passwordChange", isAuthenticated: false });
  });
});
