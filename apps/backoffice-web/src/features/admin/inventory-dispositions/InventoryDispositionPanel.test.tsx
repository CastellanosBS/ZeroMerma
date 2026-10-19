// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { authorizationUser } from "../../../test-support/authorization";
import { useBackofficeAuthStore } from "../../auth/backoffice-auth-store";
import { dispositionIntentions } from "./disposition-command-intent";
import { InventoryDispositionPanel } from "./InventoryDispositionPanel";

const request = vi.hoisted(() => vi.fn());
vi.mock("../../../lib/api", () => ({ requestJson: request }));
(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement;
let root: Root;
let queries: QueryClient;
beforeEach(() => {
  localStorage.clear();
  dispositionIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  useBackofficeAuthStore.setState({
    user: authorizationUser(
      (["inventory.adjust", "returns_corrections.manage"] as const).map((capability) => ({
        capability,
        scope_type: "GLOBAL",
        branch_ids: [],
      })),
    ),
  });
  request
    .mockReset()
    .mockResolvedValue({ operation_id: "operation", quantity: "1", destination: "BACKROOM" });
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  queries = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
});
afterEach(() => {
  act(() => root.unmount());
  queries.clear();
  host.remove();
  vi.unstubAllGlobals();
});
function change(label: string, value: string) {
  const element = [...host.querySelectorAll("label")]
    .find((item) => item.textContent?.trim().startsWith(label))!
    .querySelector<HTMLInputElement | HTMLSelectElement>("input,select")!;
  act(() => {
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value")!.set!.call(
      element,
      value,
    );
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}
async function submit() {
  act(() => host.querySelector<HTMLButtonElement>("button")!.click());
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 20));
  });
}
it("requires inspection and an explicit quarantine lot before admitting a release", async () => {
  act(() =>
    root.render(
      <QueryClientProvider client={queries}>
        <InventoryDispositionPanel
          branchId="branch"
          productId="product"
          kind="QUARANTINE_RELEASE"
          availableQuantity="2"
          lots={[
            {
              id: "lot",
              lot_code: "LOT-1",
              expires_at: "2026-12-01T00:00:00Z",
              unidentified: false,
              quantity_on_hand: "2",
              quantity_reserved: "0",
              available_quantity: "2",
            },
          ]}
        />
      </QueryClientProvider>,
    ),
  );
  change("Cantidad a disponer", "1");
  change("Motivo de disposicion", "Inspected package");
  await submit();
  expect(request).not.toHaveBeenCalled();
  expect(host.textContent).toContain("Confirma la inspeccion");
  act(() => host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
  await submit();
  expect(request).not.toHaveBeenCalled();
  expect(host.textContent).toContain("Selecciona el lote");
  change("Lote fisico", "lot");
  act(() => host.querySelector<HTMLInputElement>('input[type="checkbox"]')!.click());
  await submit();
  expect(request).toHaveBeenCalledWith(
    expect.objectContaining({
      method: "POST",
      body: expect.objectContaining({
        lot_id: "lot",
        inspection_passed: true,
        quantity: "1",
        destination: "BACKROOM",
      }),
    }),
  );
});
it("offers only safe correction destinations and preserves the original allocation cause", async () => {
  act(() =>
    root.render(
      <QueryClientProvider client={queries}>
        <InventoryDispositionPanel
          branchId="branch"
          productId="product"
          kind="RETURN_CORRECTION"
          returnAllocationId="allocation"
          availableQuantity="2"
        />
      </QueryClientProvider>,
    ),
  );
  expect([...host.querySelectorAll("option")].map((item) => item.value)).toEqual([
    "QUARANTINE",
    "WASTE",
  ]);
  change("Cantidad a disponer", "1");
  change("Motivo de disposicion", "Wrong original storage");
  await submit();
  expect(request).toHaveBeenCalledWith(
    expect.objectContaining({
      body: expect.objectContaining({
        return_allocation_id: "allocation",
        lot_id: null,
        kind: "RETURN_CORRECTION",
        destination: "QUARANTINE",
        inspection_passed: false,
      }),
    }),
  );
});
it("does not offer a no-op quarantine correction for an already quarantined return", async () => {
  act(() =>
    root.render(
      <QueryClientProvider client={queries}>
        <InventoryDispositionPanel
          branchId="branch"
          productId="product"
          kind="RETURN_CORRECTION"
          returnAllocationId="allocation"
          availableQuantity="2"
          originalDisposition="QUARANTINE"
        />
      </QueryClientProvider>,
    ),
  );
  expect([...host.querySelectorAll("option")].map((item) => item.value)).toEqual(["WASTE"]);
  change("Cantidad a disponer", "1");
  change("Motivo de disposicion", "Quarantined product discarded");
  await submit();
  expect(request).toHaveBeenCalledWith(
    expect.objectContaining({ body: expect.objectContaining({ destination: "WASTE" }) }),
  );
});
