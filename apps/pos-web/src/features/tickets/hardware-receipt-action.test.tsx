// @vitest-environment jsdom
import { webcrypto } from "node:crypto";
import type { components } from "@zeromerma/api-client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { usePosAuthStore } from "../auth/auth-store";
import { HardwareReceiptAction } from "./hardware-receipt-action";
import { hardwareIntentions } from "./print-command-intent";

const mocks = vi.hoisted(() => ({ request: vi.fn(), local: vi.fn() }));
vi.mock("../../lib/http", () => ({ requestJson: mocks.request }));
vi.mock("../../lib/local-hardware-transport", () => ({ requestLocalHardware: mocks.local }));
(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
const receipt = { source_kind: "SALE", source_id: "sale" } as components["schemas"]["OperationalReceiptView"];
const acknowledgement = { command_id: "job", grant: { command: { id: "job", workstation_id: "station", receipt } } };
let root: Root;
let container: HTMLDivElement;
let client: QueryClient;

beforeEach(() => {
  localStorage.clear(); hardwareIntentions.forgetBodies();
  vi.stubGlobal("crypto", webcrypto);
  Object.defineProperty(navigator, "locks", { configurable: true,
    value: { request: vi.fn(async (_name, _options, callback) => callback({ name: "lock" })) } });
  usePosAuthStore.setState({ user: { id: "actor", authorization_version: 1 } as never,
    session: { id: "session", workstation_id: "station" } as never,
    isAuthenticated: true, generation: 1 });
  mocks.request.mockReset().mockResolvedValue(acknowledgement);
  mocks.local.mockReset().mockResolvedValue({ command_id: "job", state: "UNKNOWN" });
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  client.setQueryData(["hardware", "POS-01", 1], { devices: [{ id: "printer", kind: "PRINTER", enabled: true }] });
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
});
afterEach(() => { act(() => root.unmount()); client.clear(); container.remove(); vi.unstubAllGlobals(); });
function render(value = receipt) {
  act(() => root.render(<QueryClientProvider client={client}>
    <HardwareReceiptAction receipt={value} workstationCode="POS-01" />
  </QueryClientProvider>));
}
const button = (label: string) => [...container.querySelectorAll("button")].find((item) => item.textContent === label)!;
async function click(label: string) {
  await act(async () => { button(label).click(); });
}
async function waitForText(text: string) {
  await vi.waitFor(async () => {
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 1)); });
    expect(container.textContent).toContain(text);
  });
}

it("keeps the unconfigured installation gated without calling a device", () => {
  client.setQueryData(["hardware", "POS-01", 1], { devices: [] }); render();
  expect(container.textContent).toContain("pendiente de instalación y validación");
  expect(container.querySelectorAll("button")).toHaveLength(0);
  expect(mocks.local).not.toHaveBeenCalled();
});

it("recovers a lost admission after reload by UUIDv7 without another POST or physical retry", async () => {
  mocks.request.mockRejectedValueOnce(new TypeError("response lost")); render();
  await click("Imprimir con dispositivo local");
  await waitForText("No se pudo confirmar");
  const key = mocks.request.mock.calls[0]![0].headers["Idempotency-Key"];
  expect(key).toMatch(/^[0-9a-f-]{14}7[0-9a-f-]+$/);
  expect(mocks.local).not.toHaveBeenCalled();
  hardwareIntentions.forgetBodies();
  act(() => root.unmount()); root = createRoot(container); render();
  expect(button("Solicitar otra copia local").disabled).toBe(true);
  await click("Consultar impresión"); await waitForText("Resultado de impresión incierto");
  expect(mocks.request.mock.calls.filter(([value]) => value.method === "POST")).toHaveLength(1);
  expect(mocks.request.mock.calls[1]![0].path).toContain(`/commands/by-key/${key}?`);
  expect(mocks.local).toHaveBeenCalledOnce();
  expect(mocks.local).toHaveBeenCalledWith(acknowledgement.grant, true);
  expect(button("Solicitar otra copia local").disabled).toBe(true);
  expect(container.textContent).not.toContain("Reanudar el mismo trabajo");
  expect(localStorage.getItem("zeromerma-hardware-intention:station:SALE:sale")).not.toMatch(/grant|signature|receipt|payment|amount/);
});

it("resumes only an explicitly queued command using its original identity", async () => {
  mocks.local.mockResolvedValueOnce({ command_id: "job", state: "QUEUED" }); render();
  await click("Imprimir con dispositivo local"); await waitForText("Reanudar el mismo trabajo");
  await click("Reanudar el mismo trabajo"); await waitForText("Resultado de impresión incierto");
  expect(mocks.request.mock.calls.filter(([value]) => value.method === "POST")).toHaveLength(1);
  expect(mocks.local.mock.calls.map(([grant]) => grant.command.id)).toEqual(["job", "job"]);
  expect(mocks.local.mock.calls.every(([, consult]) => consult === false)).toBe(true);
});

it("ignores a late device response when another receipt is selected", async () => {
  let finish!: (value: object) => void;
  mocks.local.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; })); render();
  await click("Imprimir con dispositivo local");
  await vi.waitFor(() => expect(mocks.local).toHaveBeenCalledOnce());
  render({ ...receipt, source_id: "other-sale" });
  await act(async () => { finish({ command_id: "job", state: "PRINTED", evidence_reference: "ok" }); });
  expect(container.textContent).not.toContain("confirmó la impresión");
  expect(container.textContent).not.toContain("Consultar impresión pendiente");
});
