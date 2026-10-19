// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import { ApiError } from "@zeromerma/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { authorizationUser, withCapabilities } from "../../../../test-support/authorization";
import { useBackofficeAuthStore } from "../../../auth/backoffice-auth-store";
import { purchaseIntentions } from "../purchase-command-intent";
import { AdminPurchasesPage } from "./AdminPurchasesPage";

const mocks = vi.hoisted(() => ({
  send: vi.fn(),
  list: vi.fn(),
  detail: vi.fn(),
  recover: vi.fn(),
}));
vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  createAdminPurchase: mocks.send,
  fetchAdminPurchases: mocks.list,
  fetchAdminPurchaseDetail: mocks.detail,
  recoverAdminPurchaseCommand: mocks.recover,
}));
(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
const actor = authorizationUser();
const confirmed = { id: "purchase-1", branch_id: "branch-1", folio: "CMP-001", status: "DRAFT" };
let root: Root;
let host: HTMLDivElement;
let queryClient: QueryClient;

function button(text: string) {
  const element = [...host.querySelectorAll("button")].find(
    (item) => item.textContent?.trim() === text,
  );
  if (!element) throw new Error(`Missing button: ${text}`);
  return element;
}
function field(label: string) {
  const panel = host.querySelector('h3[title="Nueva compra"]')?.closest("aside");
  const element = [...(panel?.querySelectorAll("label") ?? [])]
    .find((item) => item.textContent?.trim().startsWith(label))
    ?.querySelector<
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    >("input,select,textarea");
  if (!element) throw new Error(`Missing field: ${label}`);
  return element;
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
async function prepareDraft() {
  await act(async () => {
    await vi.waitFor(() => expect(mocks.list).toHaveBeenCalled());
  });
  act(() => button("Nueva compra").click());
  change("Proveedor", "supplier-1");
  change("Sucursal receptora", "branch-1");
  change("Producto", "product-1");
  change("Cantidad", "3.000");
  change("Notas", "Preserve this draft");
}
beforeEach(() => {
  localStorage.clear();
  purchaseIntentions.forgetBodies();
  useBackofficeAuthStore.setState({ user: actor, isAuthenticated: true, phase: "ready" });
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", {
    configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) },
  });
  mocks.send.mockReset().mockResolvedValue(confirmed);
  mocks.recover.mockReset().mockResolvedValue(confirmed);
  mocks.detail.mockReset().mockResolvedValue(null);
  mocks.list.mockReset().mockResolvedValue({
    backendContract: { createAvailable: true },
    filterOptions: {
      branches: [{ id: "branch-1", label: "Main" }],
      suppliers: [{ id: "supplier-1", label: "Supplier" }],
      products: [{ id: "product-1", label: "Flour" }],
      operators: [],
      productKinds: [],
      statuses: [],
    },
    isBackendConnected: true,
    items: [],
    page: 1,
    pageSize: 25,
    total: 0,
    metrics: {
      activeSuppliersUsed: "0",
      confirmedEntries: "0",
      partiallyReceived: "0",
      pendingReceipt: "0",
      totalAmount: "0",
      totalDocuments: "0",
      withDiscrepancies: "0",
    },
  });
  queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  host = document.createElement("div");
  document.body.append(host);
  root = createRoot(host);
  act(() =>
    root.render(
      <QueryClientProvider client={queryClient}>
        {withCapabilities(<AdminPurchasesPage />, ["purchases.manage"])}
      </QueryClientProvider>,
    ),
  );
});
afterEach(() => {
  act(() => root.unmount());
  queryClient.clear();
  host.remove();
  purchaseIntentions.forgetBodies();
  vi.unstubAllGlobals();
});

it("preserves rejected form fields, allows correction, and clears the draft only once after confirmation", async () => {
  mocks.send.mockRejectedValueOnce(
    new ApiError(409, "Quantity rejected", {
      code: "PURCHASE_COMMAND_REJECTED",
      message: "Quantity rejected",
      details: null,
      field_errors: null,
      request_id: null,
    }),
  );
  await prepareDraft();
  expect(button("Guardar borrador").disabled).toBe(false);
  act(() => button("Guardar borrador").click());
  await act(async () => {
    await vi.waitFor(() =>
      expect(queryClient.getMutationCache().getAll().at(-1)?.state.status).toBe("error"),
    );
  });
  expect(host.textContent).toContain("Quantity rejected");
  expect(field("Cantidad").value).toBe("3.000");
  expect(field("Notas").value).toBe("Preserve this draft");
  const rejected = purchaseIntentions.read("purchases")!;
  expect(rejected.status).toBe("REJECTED");
  change("Cantidad", "2.000");
  act(() => button("Guardar borrador").click());
  await act(async () => {
    await vi.waitFor(() =>
      expect(queryClient.getMutationCache().getAll().at(-1)?.state.status).toBe("success"),
    );
  });
  expect(host.textContent).toContain("CMP-001: operación confirmada.");
  expect(host.querySelector("textarea")).toBeNull();
  expect(mocks.send).toHaveBeenCalledTimes(2);
  expect(mocks.send.mock.calls[0]![1]).toBe(rejected.key);
  expect(mocks.send.mock.calls[1]![1]).not.toBe(rejected.key);
  act(() => button("Nueva compra").click());
  change("Notas", "A new draft");
  act(() =>
    window.dispatchEvent(
      new StorageEvent("storage", { key: "zeromerma-admin-purchase-intention:purchases" }),
    ),
  );
  expect(field("Notas").value).toBe("A new draft");
});

it("blocks the current draft while another tab is uncertain, then clears it when that original result is recovered", async () => {
  await prepareDraft();
  mocks.send.mockRejectedValueOnce(new TypeError("Lost response"));
  await act(async () => {
    await purchaseIntentions
      .begin(
        { userId: actor.id, branchId: "branch-1", purchaseId: null, commandCode: "create" },
        {
          commandCode: "create",
          body: {
            branchId: "branch-1",
            supplierId: "supplier-1",
            lines: [{ productId: "product-1", orderedQuantity: "3", unitCost: "0" }],
          },
        },
        null,
      )
      .catch(() => undefined);
  });
  expect(field("Notas").value).toBe("Preserve this draft");
  expect(button("Guardando").disabled).toBe(true);
  act(() => button("Guardando").click());
  expect(mocks.send).toHaveBeenCalledTimes(1);
  act(() => button("Consultar resultado de compra").click());
  await act(async () => {
    await vi.waitFor(() => expect(purchaseIntentions.read("purchases")?.status).toBe("CONFIRMED"));
  });
  expect(host.querySelector("textarea")).toBeNull();
  expect(mocks.send).toHaveBeenCalledTimes(1);
});
