import { QueryClient } from "@tanstack/react-query";
import { describe, expect, it } from "vitest";

import { clearAdministrativeQueries } from "./query-client";

describe("authorization cache isolation", () => {
  it("discards administrative reads and mutation results while preserving the fresh authorization response", async () => {
    const client = new QueryClient();
    client.setQueryData(["admin", "inventory", "list"], { confidential: "previous branch" });
    client.setQueryData(["backoffice-auth", "me"], { authorization_version: "revoked" });
    await client
      .getMutationCache()
      .build(client, { mutationFn: async () => "old exported data" })
      .execute(undefined);
    await clearAdministrativeQueries(client);
    expect(client.getQueryData(["admin", "inventory", "list"])).toBeUndefined();
    expect(client.getMutationCache().getAll()).toHaveLength(0);
    expect(client.getQueryData(["backoffice-auth", "me"])).toEqual({
      authorization_version: "revoked",
    });
    client.clear();
  });
});
