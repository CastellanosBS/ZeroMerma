// @vitest-environment jsdom
import { act, useCallback, useState, type MutableRefObject } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, expect, it, vi } from "vitest";
import type { TransferIntentionMetadata } from "./transfer-command-intent";
import { useTransferDraftIdentity } from "./use-transfer-intention";

(
  globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean }
).IS_REACT_ACT_ENVIRONMENT = true;
const confirmed = vi.fn();
let anchor: MutableRefObject<string | null | undefined>;
let root: Root | undefined;
let host: HTMLDivElement;
const metadata = (
  status: TransferIntentionMetadata["status"],
  key = "intention-a",
): TransferIntentionMetadata => ({
  userId: "actor",
  branchId: "branch",
  workstationId: "station",
  workstationCode: "POS-01",
  cashSessionId: "cash",
  transferId: "shipment",
  commandCode: "receive",
  key,
  payloadDigest: "digest",
  status,
});
function Draft({ intention }: { intention: TransferIntentionMetadata | null }) {
  const [draft, setDraft] = useState("");
  anchor = useTransferDraftIdentity(
    intention,
    true,
    useCallback(() => {
      setDraft("");
      confirmed();
    }, []),
  );
  return (
    <>
      <input aria-label="Quantity, reason and receipt draft" readOnly value={draft} />
      <button onClick={() => setDraft("Quantity 0.333, reason WRONG_ITEM, shipment remainder")}>
        Edit draft
      </button>
    </>
  );
}
async function render(intention: TransferIntentionMetadata | null) {
  if (!root) {
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
  }
  await act(async () => root!.render(<Draft intention={intention} />));
}
async function edit() {
  await act(async () => host.querySelector("button")!.click());
}
const value = () => host.querySelector("input")!.value;
afterEach(async () => {
  if (root) await act(async () => root!.unmount());
  root = undefined;
  host?.remove();
  confirmed.mockClear();
});

it("preserves entered quantity, reason and receipt reason after its own deterministic first-send rejection", async () => {
  await render(null);
  await edit();
  const original = value();
  await render(metadata("PENDING"));
  expect(value()).toBe(original);
  expect(anchor.current).toBeNull();
  await render(metadata("REJECTED"));
  expect(value()).toBe(original);
  expect(anchor.current).toBe("intention-a");
  expect(confirmed).not.toHaveBeenCalled();
});
it("keeps an uncertain draft anchored until confirmation invalidates the stale form", async () => {
  await render(null);
  await edit();
  const original = value();
  for (const state of ["PENDING", "UNKNOWN", "CONFLICT"] as const) {
    await render(metadata(state));
    expect(value()).toBe(original);
    expect(anchor.current).toBeNull();
  }
  await render(metadata("CONFIRMED"));
  expect(value()).toBe("");
  expect(anchor.current).toBe("intention-a");
  expect(confirmed).toHaveBeenCalledTimes(1);
});
it("does not discard a new draft for the already observed result but clears a foreign completed intention", async () => {
  await render(metadata("CONFIRMED"));
  await edit();
  const original = value();
  await render(metadata("CONFIRMED"));
  expect(value()).toBe(original);
  expect(confirmed).not.toHaveBeenCalled();
  await render(metadata("CONFIRMED", "foreign-intention"));
  expect(value()).toBe("");
  expect(confirmed).toHaveBeenCalledTimes(1);
});

it.each(["PENDING", "UNKNOWN", "CONFLICT"] as const)(
  "invalidates a draft prepared after mounting an existing %s intention when it confirms",
  async (status) => {
    await render(metadata(status));
    await edit();
    expect(value()).not.toBe("");
    expect(anchor.current).toBeNull();
    await render(metadata("CONFIRMED"));
    expect(value()).toBe("");
    expect(anchor.current).toBe("intention-a");
    expect(confirmed).toHaveBeenCalledTimes(1);
  },
);
