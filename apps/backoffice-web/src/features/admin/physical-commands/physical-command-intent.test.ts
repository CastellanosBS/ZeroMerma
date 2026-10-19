import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  physicalIntentions,
  PHYSICAL_INTENTION_SCOPE,
  type PhysicalIntentionPayload,
} from "./physical-command-intent";
const mocks = vi.hoisted(() => ({ waste: vi.fn(), adjustment: vi.fn(), recover: vi.fn() }));
vi.mock("../waste/api", () => ({ createAdminWaste: mocks.waste }));
vi.mock("../inventory/api", () => ({ createAdminInventoryAdjustment: mocks.adjustment }));
vi.mock("../../../lib/api", () => ({ requestJson: mocks.recover }));
const context = (commandCode: "waste" | "adjustment") => ({
  userId: "actor",
  branchId: "branch",
  commandCode,
});
function payload(commandCode: "waste" | "adjustment"): PhysicalIntentionPayload {
  const body = {
    branchId: "branch",
    productId: "product",
    locationCode: "BACKROOM" as const,
    quantity: "2.000",
    notes: "Private notes",
  };
  return commandCode === "waste"
    ? { commandCode, body: { ...body, reasonCode: "DAMAGED" } }
    : { commandCode, body: { ...body, adjustmentType: "INCREASE", reason: "Private count" } };
}
beforeEach(() => {
  localStorage.clear();
  physicalIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  Object.values(mocks).forEach((m) =>
    m.mockReset().mockResolvedValue({ id: "result", branch_id: "branch" }),
  );
});
afterEach(() => vi.unstubAllGlobals());
it("forgets a volatile body when grants change without changing the actor or generation", async () => {
  useBackofficeAuthStore.setState({
    user: {
      id: "actor",
      email: "actor@example.invalid",
      full_name: "Actor",
      is_active: true,
      allowed_surfaces: ["BACKOFFICE"],
      default_surface: "BACKOFFICE",
      authorization_surface: "BACKOFFICE",
      effective_grants: [],
      authorization_version: "before",
      is_superadministrator: false,
      password_reset_required: false,
    },
  });
  mocks.waste.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    physicalIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  const saved = physicalIntentions.read(PHYSICAL_INTENTION_SCOPE)!;
  const generation = useBackofficeAuthStore.getState().generation;
  useBackofficeAuthStore.setState((state) => ({
    user: { ...state.user!, authorization_version: "after" },
  }));
  expect(useBackofficeAuthStore.getState().generation).toBe(generation);
  expect(physicalIntentions.hasBody(saved.key)).toBe(false);
  expect(physicalIntentions.read(PHYSICAL_INTENTION_SCOPE)).toEqual(saved);
});
it.each(["waste", "adjustment"] as const)(
  "keeps %s frozen body and key across retry and recovers after reload without POST",
  async (command) => {
    const body = payload(command);
    mocks[command].mockRejectedValueOnce(new TypeError("lost"));
    await expect(physicalIntentions.begin(context(command), body, null)).rejects.toThrow();
    const saved = physicalIntentions.read(PHYSICAL_INTENTION_SCOPE)!;
    expect(Object.keys(saved).sort()).toEqual(
      ["userId", "branchId", "commandCode", "key", "status", "payloadDigest"].sort(),
    );
    expect(JSON.stringify(saved)).not.toMatch(/Private|notes|quantity|productId/);
    body.body.quantity = "99";
    await physicalIntentions.retry(context(command));
    expect(mocks[command].mock.calls[1]).toEqual(mocks[command].mock.calls[0]);
    localStorage.setItem(
      "zeromerma-admin-physical-intention:physical-commands",
      JSON.stringify({ ...saved, status: "UNKNOWN" }),
    );
    physicalIntentions.forgetBodies();
    await physicalIntentions.recover(context(command));
    expect(mocks[command]).toHaveBeenCalledTimes(2);
    expect(mocks.recover.mock.calls[0]![0].path).toContain("branch_id=branch");
    expect(physicalIntentions.read(PHYSICAL_INTENTION_SCOPE)?.status).toBe("CONFIRMED");
  },
);
it("prevents a different actor and branch from recovering an uncertain write", async () => {
  mocks.waste.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    physicalIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  await expect(
    physicalIntentions.recover({ ...context("waste"), userId: "other" }),
  ).rejects.toThrow();
  expect(mocks.recover).not.toHaveBeenCalled();
  mocks.recover.mockResolvedValue({ id: "other", branch_id: "other" });
  await expect(physicalIntentions.recover(context("waste"))).rejects.toThrow();
  expect(physicalIntentions.read(PHYSICAL_INTENTION_SCOPE)?.status).toBe("CONFLICT");
});

it("discards only the frozen body on an authentication generation change", async () => {
  mocks.waste.mockRejectedValueOnce(new TypeError("lost"));
  await expect(
    physicalIntentions.begin(context("waste"), payload("waste"), null),
  ).rejects.toThrow();
  const saved = physicalIntentions.read("physical-commands")!;
  expect(physicalIntentions.hasBody(saved.key)).toBe(true);
  useBackofficeAuthStore.getState().clearSession();
  expect(physicalIntentions.hasBody(saved.key)).toBe(false);
  expect(physicalIntentions.read("physical-commands")).toMatchObject({
    key: saved.key,
    status: "UNKNOWN",
  });
});
