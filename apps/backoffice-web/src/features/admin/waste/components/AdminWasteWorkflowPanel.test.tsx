// @vitest-environment jsdom
import {
  defaultScheduler,
  notifyManager,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { withCapabilities } from "../../../../test-support/authorization";
import { fetchAdminWasteStock } from "../api";
import { AdminWasteWorkflowPanel } from "./AdminWasteWorkflowPanel";

vi.mock("../api", () => ({ fetchAdminWasteStock: vi.fn() }));
(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let host: HTMLDivElement;
let client: QueryClient;
const create = vi.fn();

function field(label: string) {
  const result = [...host.querySelectorAll("label")]
    .find((item) => item.textContent?.trim().startsWith(label))
    ?.querySelector<HTMLInputElement | HTMLSelectElement>("input, select");
  if (!result) throw new Error(`Missing field ${label}`);
  return result;
}
function change(label: string, value: string) {
  const element = field(label);
  act(() => {
    Object.getOwnPropertyDescriptor(Object.getPrototypeOf(element), "value")!.set!.call(
      element,
      value,
    );
    element.dispatchEvent(new Event("input", { bubbles: true }));
    element.dispatchEvent(new Event("change", { bubbles: true }));
  });
}
function submit() {
  const button = [...host.querySelectorAll("button")].find(
    (item) => item.textContent?.trim() === "Confirmar merma",
  );
  if (!button) throw new Error("Missing submit button");
  act(() => button.click());
}

beforeEach(() => {
  notifyManager.setScheduler(queueMicrotask);
  notifyManager.setNotifyFunction((callback) => act(callback));
  create.mockReset();
  vi.mocked(fetchAdminWasteStock).mockImplementation(async (branch, product, location) => ({
    branch_id: branch,
    product_id: product,
    location_code: location,
    lot_tracking_enabled: true,
    lots: [
      {
        lot_id: `${location}-lot`,
        lot_code: "EXPIRED-PHYSICAL",
        expires_at: "2020-01-01T00:00:00Z",
        unidentified: false,
        location_code: location,
        quantity_on_hand: "3",
        quantity_reserved: "1",
        available_quantity: "2",
      },
    ],
  }));
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root.render(
      <QueryClientProvider client={client}>
        {withCapabilities(
          <AdminWasteWorkflowPanel
            branchOptions={[{ id: "branch", label: "Branch" }]}
            locationOptions={[
              { id: "BACKROOM", label: "Backroom" },
              { id: "COUNTER", label: "Counter" },
            ]}
            productOptions={[{ id: "product", label: "Product" }]}
            reasonOptions={[
              {
                code: "EXPIRED",
                label: "Expired",
                displayOrder: 1,
                requiresNote: false,
                requiresEvidence: false,
                highImpactDefault: false,
              },
            ]}
            isSubmitting={false}
            onClose={vi.fn()}
            onCreate={create}
          />,
          ["waste.manage", "waste.view"],
        )}
      </QueryClientProvider>,
    ),
  );
});
afterEach(() => {
  act(() => root.unmount());
  client.clear();
  notifyManager.setScheduler(defaultScheduler);
  notifyManager.setNotifyFunction((callback) => callback());
  host.remove();
  vi.clearAllMocks();
});

it("requires explicit physical lot selection and clears it when the source changes", async () => {
  change("Sucursal", "branch");
  change("Producto", "product");
  change("Motivo", "EXPIRED");
  change("Cantidad", "1");
  expect(fetchAdminWasteStock).toHaveBeenLastCalledWith("branch", "product", "BACKROOM");
  await act(async () => {
    await vi.mocked(fetchAdminWasteStock).mock.results.at(-1)!.value;
  });
  expect(host.textContent).toContain("EXPIRED-PHYSICAL");
  submit();
  expect(create).not.toHaveBeenCalled();
  expect(host.textContent).toContain("Selecciona el lote físico");
  change("Lote físico de merma", "BACKROOM-lot");
  change("Cantidad", "3");
  submit();
  expect(create).not.toHaveBeenCalled();
  expect(host.textContent).toContain("supera el saldo");
  change("Cantidad", "1");
  submit();
  expect(create).toHaveBeenCalledWith(
    expect.objectContaining({ lotId: "BACKROOM-lot", quantity: "1", locationCode: "BACKROOM" }),
  );
  create.mockClear();
  change("Origen", "COUNTER");
  expect(fetchAdminWasteStock).toHaveBeenLastCalledWith("branch", "product", "COUNTER");
  await act(async () => {
    await vi.mocked(fetchAdminWasteStock).mock.results.at(-1)!.value;
  });
  expect(field("Lote físico de merma").querySelector('option[value="COUNTER-lot"]')).not.toBeNull();
  expect(field("Lote físico de merma").value).toBe("");
  submit();
  expect(create).not.toHaveBeenCalled();
});
