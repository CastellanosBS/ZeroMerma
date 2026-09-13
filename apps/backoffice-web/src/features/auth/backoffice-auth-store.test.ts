import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { queryClient } from "../../lib/query-client";

let auth: typeof import("./backoffice-auth-store").useBackofficeAuthStore;

beforeAll(async () => {
  const storage = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
  auth = (await import("./backoffice-auth-store")).useBackofficeAuthStore;
});

afterEach(() => auth.getState().clearSession());

describe("actor session cache boundary", () => {
  it("does not retain another actor's reads or authorization after login replacement", () => {
    auth.getState().setAccessToken("first-test-actor");
    queryClient.setQueryData(["admin", "users"], { fullName: "Previous actor data" });
    queryClient.setQueryData(["backoffice-auth", "me"], { id: "previous-actor" });
    auth.getState().setAccessToken("second-test-actor");
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
  });

  it("clears cached exports and reads on logout", async () => {
    auth.getState().setAccessToken("test-actor");
    queryClient.setQueryData(["admin", "reports"], { data: "private" });
    await queryClient
      .getMutationCache()
      .build(queryClient, { mutationFn: async () => "exported data" })
      .execute(undefined);
    auth.getState().clearSession();
    expect(auth.getState().accessToken).toBeNull();
    expect(queryClient.getQueryCache().getAll()).toHaveLength(0);
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0);
  });
});
