// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import type { components } from "@zeromerma/api-client";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { usePosAuthStore } from "../auth/auth-store";
import { browserPrintIntentions } from "./print-command-intent";
import { ReceiptPrintButton } from "./receipt-print-button";

const mocks = vi.hoisted(() => ({ request: vi.fn(), open: vi.fn(), write: vi.fn(), close: vi.fn() }));
vi.mock("../../lib/http", () => ({ requestJson: mocks.request }));
vi.mock("../../lib/browser-print", () => ({ openBrowserPrintWindow: mocks.open, writePrintableDocument: mocks.write }));
vi.mock("./hardware-receipt-action", () => ({ HardwareReceiptAction: () => null }));
vi.mock("./print", () => ({ buildOperationalReceiptPrintDocument: () => "frozen document" }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const receipt = { source_kind: "SALE", source_id: "sale" } as components["schemas"]["OperationalReceiptView"];
let container: HTMLDivElement;
let root: Root;
beforeEach(() => {
  localStorage.clear(); browserPrintIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", { configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) } });
  usePosAuthStore.setState({ user: { id: "actor" } as never, session: { id: "session", workstation_id: "station" } as never,
    isAuthenticated: true, generation: 1 });
  mocks.request.mockReset().mockResolvedValue({ receipt, print_command_id: "command", physical_outcome: "NOT_CONFIRMED" });
  mocks.write.mockReset(); mocks.close.mockReset(); mocks.open.mockReset().mockReturnValue({ close: mocks.close });
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); container.remove(); vi.unstubAllGlobals(); });
function render(value = receipt) { act(() => root.render(<ReceiptPrintButton receipt={value} workstationCode="POS-01" />)); }
async function click() { await act(async () => { container.querySelector("button")!.click(); }); }

it("recovers a lost print acknowledgement with the same UUIDv7 before opening the document", async () => {
  mocks.request.mockRejectedValueOnce(new TypeError("lost")); render(); await click();
  await vi.waitFor(async () => { await act(async () => {}); expect(mocks.close).toHaveBeenCalledOnce(); });
  const key = mocks.request.mock.calls[0]![0].headers["Idempotency-Key"];
  expect(key.split("-")[2][0]).toBe("7");
  browserPrintIntentions.forgetBodies(); await click();
  await vi.waitFor(async () => { await act(async () => {}); expect(mocks.write).toHaveBeenCalledOnce(); });
  expect(mocks.request.mock.calls[1]![0].path).toContain(`/print-requests/${key}?`);
  expect(mocks.request.mock.calls.filter(([request]) => request.method === "POST")).toHaveLength(1);
  expect(container.textContent).toContain("verifica la salida");
});

it("closes a pending popup without printing after changing the selected receipt", async () => {
  let resolve!: (value: object) => void;
  mocks.request.mockImplementationOnce(() => new Promise((finish) => { resolve = finish; }));
  render(); await click(); await vi.waitFor(() => expect(mocks.request).toHaveBeenCalledOnce());
  render({ ...receipt, source_id: "other" });
  await act(async () => { resolve({ receipt, print_command_id: "command" }); });
  expect(mocks.close).toHaveBeenCalledOnce(); expect(mocks.write).not.toHaveBeenCalled();
});
