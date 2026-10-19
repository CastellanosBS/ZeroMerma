// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { usePosAuthStore } from "../auth/auth-store";
import {
  attributionIntentions,
  type AttributionContext,
  type AttributionRequest,
} from "./attribution-command-intent";
const request = vi.hoisted(() => vi.fn());
vi.mock("../../lib/http", () => ({ requestJson: request }));
const context: AttributionContext = {
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "cash",
  saleId: "sale",
};
const body = (): AttributionRequest => ({
  workstation_code: "POS-01",
  cash_session_id: "cash",
  lines: [{ sale_line_id: "line", product_id: "product", lot_id: "lot", quantity: "1" }],
});
const result = {
  sale_id: "sale",
  operation_id: "operation",
  lines: [
    {
      attribution_id: "attribution",
      sale_line_id: "line",
      product_id: "product",
      quantity: "1.000",
      remaining_quantity: "2.000",
      inventory_movement_id: "movement",
    },
  ],
};
beforeEach(() => {
  localStorage.clear();
  attributionIntentions.forgetBodies();
  request.mockReset().mockResolvedValue(result);
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
});
afterEach(() => vi.unstubAllGlobals());
it("freezes the selected physical quantity and retries the same key", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  const payload = body();
  await expect(attributionIntentions.begin(context, payload, null)).rejects.toThrow();
  payload.lines[0]!.quantity = "9";
  await attributionIntentions.retry(context);
  expect(request.mock.calls[1]![0].body.lines[0].quantity).toBe("1");
  expect(request.mock.calls[1]![0].headers["Idempotency-Key"]).toBe(
    request.mock.calls[0]![0].headers["Idempotency-Key"],
  );
  expect(localStorage.getItem("zeromerma-attribution-intention:station")).not.toMatch(
    /quantity|product_id|lot_id|lines/,
  );
});
it("reload recovery GET keeps partial attribution from producing another stock movement", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(attributionIntentions.begin(context, body(), null)).rejects.toThrow();
  const metadata = attributionIntentions.read("station")!;
  attributionIntentions.forgetBodies();
  expect(attributionIntentions.hasBody(metadata.key)).toBe(false);
  expect(await attributionIntentions.recover(metadata)).toEqual(result);
  expect(request.mock.calls[1]![0]).toEqual({
    path: `/v1/sales/sale/inventory-attributions/${metadata.key}?workstation_code=POS-01&cash_session_id=cash`,
  });
  expect(request.mock.calls.filter(([argument]) => argument.method === "POST")).toHaveLength(1);
});
it("keeps a conflict reference when recovery returns a different sale", async () => {
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(attributionIntentions.begin(context, body(), null)).rejects.toThrow();
  request.mockResolvedValueOnce({ ...result, sale_id: "other" });
  await expect(attributionIntentions.recover(context)).rejects.toThrow(/otra venta/);
  expect(attributionIntentions.read("station")?.status).toBe("CONFLICT");
});
it("rejects a changed cash session before HTTP and clears volatile content on logout", async () => {
  await expect(
    attributionIntentions.begin(context, { ...body(), cash_session_id: "other" }, null),
  ).rejects.toThrow(/turno/);
  expect(request).not.toHaveBeenCalled();
  localStorage.clear();
  request.mockRejectedValueOnce(new TypeError("lost response"));
  await expect(attributionIntentions.begin(context, body(), null)).rejects.toThrow();
  const metadata = attributionIntentions.read("station")!;
  usePosAuthStore.getState().clearSession();
  expect(attributionIntentions.hasBody(metadata.key)).toBe(false);
  expect(attributionIntentions.read("station")).toEqual(metadata);
});
