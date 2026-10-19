// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ORDER_POLICY_SCOPE, orderPolicyIntentions } from "./order-policy-intent";

const policy = { id: "policy", branch_id: "branch", version: 1, lead_time_minutes: 90, reason: "Explicit owner-approved planning" };
const context = { userId: "operator", branchId: "branch" };
beforeEach(() => {
  localStorage.clear(); orderPolicyIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", { configurable: true, value: {
    request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })),
  } });
});
afterEach(() => vi.unstubAllGlobals());

it("saves only an explicit policy and retries its frozen contents with the original key", async () => {
  const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError("lost response"))
    .mockResolvedValueOnce(new Response(JSON.stringify(policy)));
  vi.stubGlobal("fetch", fetchMock);
  const payload = { lead_time_minutes: 90, reason: policy.reason };
  await expect(orderPolicyIntentions.begin(context, payload, null)).rejects.toThrow("lost response");
  payload.lead_time_minutes = 1440;
  await orderPolicyIntentions.retry(context);
  const calls = fetchMock.mock.calls;
  expect(calls[0]![1].body).toBe(JSON.stringify({ lead_time_minutes: 90, reason: policy.reason }));
  expect(calls[1]![1].body).toBe(calls[0]![1].body);
  expect(calls[1]![1].headers.get("Idempotency-Key")).toBe(calls[0]![1].headers.get("Idempotency-Key"));
  expect(localStorage.getItem("zeromerma-order-policy-intention:order-policy")).not.toContain(policy.reason);
});

it("recovers the exact policy command after reload instead of trusting the latest policy", async () => {
  const fetchMock = vi.fn().mockRejectedValueOnce(new TypeError("lost response"))
    .mockResolvedValueOnce(new Response(JSON.stringify(policy)));
  vi.stubGlobal("fetch", fetchMock);
  await expect(orderPolicyIntentions.begin(context, { lead_time_minutes: 90, reason: policy.reason }, null)).rejects.toThrow();
  const metadata = orderPolicyIntentions.read(ORDER_POLICY_SCOPE)!;
  orderPolicyIntentions.forgetBodies();
  await orderPolicyIntentions.recover(context);
  expect(fetchMock.mock.calls[1]![0]).toContain(`/commitment-policies/branch/confirmations/${metadata.key}`);
  expect(fetchMock.mock.calls[1]![1].method).toBe("GET");
  expect(fetchMock.mock.calls.filter(([, options]) => options.method === "POST")).toHaveLength(1);
});

it("does not let a different branch or operator adopt the pending policy", async () => {
  const fetchMock = vi.fn().mockRejectedValue(new TypeError("lost response"));
  vi.stubGlobal("fetch", fetchMock);
  await expect(orderPolicyIntentions.begin(context, { lead_time_minutes: 90, reason: policy.reason }, null)).rejects.toThrow();
  await expect(orderPolicyIntentions.recover({ ...context, userId: "another" })).rejects.toThrow("operador");
  await expect(orderPolicyIntentions.retry({ ...context, branchId: "another" })).rejects.toThrow("operador");
  expect(fetchMock).toHaveBeenCalledTimes(1);
});
