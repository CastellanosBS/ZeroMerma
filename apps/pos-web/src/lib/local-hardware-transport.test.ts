import type { components } from "@zeromerma/api-client";
import { afterEach, expect, it, vi } from "vitest";
import { requestLocalHardware } from "./local-hardware-transport";
const grant = { command: { id: "job", kind: "PRINT" } } as components["schemas"]["SignedDeviceCommand"];
afterEach(() => vi.unstubAllGlobals());
it("queries the existing physical job without using the execution route", async () => {
  const fetcher = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ command_id: "job", state: "UNKNOWN" }) });
  vi.stubGlobal("fetch", fetcher);
  expect((await requestLocalHardware(grant, true)).state).toBe("UNKNOWN");
  expect(fetcher.mock.calls[0]![0]).toBe("http://127.0.0.1:17651/commands/status");
  expect(fetcher.mock.calls[0]![1].credentials).toBe("omit");
});
it.each([
  { command_id: "other", state: "PRINTED", evidence_reference: "ok" },
  { command_id: "job", state: "PRINTED" },
  { command_id: "job", state: "OPENED", evidence_reference: "ok" },
  { command_id: "job", state: "SUCCESS" },
])("rejects an unproven or unrelated physical result: %j", async (body) => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => body }));
  await expect(requestLocalHardware(grant, false)).rejects.toThrow();
});
