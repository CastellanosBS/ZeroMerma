// @vitest-environment jsdom

import { act } from "react";
import { createRoot } from "react-dom/client";
import { afterEach, describe, expect, it } from "vitest";

import {
  CARD_PAYMENT_METHOD_CODE,
  CONTROL_STATE_PAYMENT_CAPTURE,
  MIXED_PAYMENT_METHOD_CODE,
} from "./model";
import {
  isPaymentIntentComboReady,
  SALE_FLOW_AMOUNT_CONFIRMED,
  SALE_FLOW_PAYMENT_AMOUNT_CAPTURE,
  useSaleFlowController,
} from "./sale-flow-controller";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT?: boolean })
  .IS_REACT_ACT_ENVIRONMENT = true;

type HookApi = ReturnType<typeof useSaleFlowController>;

function renderHookHarness(props: {
  cartLineCount: number;
  controlState: typeof CONTROL_STATE_PAYMENT_CAPTURE;
  hasCompletedSale: boolean;
  totalAmountCents: number;
}) {
  let api: HookApi | null = null;

  function Harness() {
    api = useSaleFlowController(props);
    return null;
  }

  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);

  act(() => {
    root.render(<Harness />);
  });

  return {
    getApi() {
      if (api === null) {
        throw new Error("Hook api not ready");
      }

      return api;
    },
    unmount() {
      act(() => {
        root.unmount();
      });
      container.remove();
    },
  };
}

let mounted: Array<() => void> = [];

afterEach(() => {
  for (const unmount of mounted) {
    unmount();
  }
  mounted = [];
  document.body.innerHTML = "";
});

describe("sale flow controller", () => {
  it("accepts the payment intent combo within the timing window", () => {
    expect(isPaymentIntentComboReady(1_000, 1_250)).toBe(true);
    expect(isPaymentIntentComboReady(1_000, 1_301)).toBe(false);
  });

  it("confirms a cash amount into the pre-close state", () => {
    const harness = renderHookHarness({
      cartLineCount: 1,
      controlState: CONTROL_STATE_PAYMENT_CAPTURE,
      hasCompletedSale: false,
      totalAmountCents: 300,
    });
    mounted.push(() => harness.unmount());

    act(() => {
      harness.getApi().updateCashReceivedText("3.00");
    });

    let result: ReturnType<HookApi["confirmAmount"]> | undefined;
    act(() => {
      result = harness.getApi().confirmAmount(300);
    });
    expect(result).toEqual({ ok: true });
    expect(harness.getApi().state.mode).toBe(SALE_FLOW_AMOUNT_CONFIRMED);
  });

  it("builds mixed legs until the full amount is covered", () => {
    const harness = renderHookHarness({
      cartLineCount: 1,
      controlState: CONTROL_STATE_PAYMENT_CAPTURE,
      hasCompletedSale: false,
      totalAmountCents: 300,
    });
    mounted.push(() => harness.unmount());

    act(() => {
      harness.getApi().switchPaymentMethod(MIXED_PAYMENT_METHOD_CODE);
      harness.getApi().updateMixedCurrentLegAmountText("1.00");
    });

    let firstResult: ReturnType<HookApi["confirmAmount"]> | undefined;
    act(() => {
      firstResult = harness.getApi().confirmAmount(300);
    });
    expect(firstResult).toEqual({ ok: true });
    expect(harness.getApi().state.mode).toBe(SALE_FLOW_PAYMENT_AMOUNT_CAPTURE);

    act(() => {
      harness.getApi().setMixedCurrentLegMethodCode(CARD_PAYMENT_METHOD_CODE);
      harness.getApi().updateMixedCurrentLegAmountText("2.00");
    });

    let secondResult: ReturnType<HookApi["confirmAmount"]> | undefined;
    act(() => {
      secondResult = harness.getApi().confirmAmount(300);
    });
    expect(secondResult).toEqual({ ok: true });
    expect(harness.getApi().state.mode).toBe(SALE_FLOW_AMOUNT_CONFIRMED);
    expect(harness.getApi().buildPaymentDraft()).toMatchObject({
      mixedConfirmedLegs: [
        { amountText: "1.00", methodCode: "CASH" },
        { amountText: "2.00", methodCode: "CARD" },
      ],
      paymentMethodCode: MIXED_PAYMENT_METHOD_CODE,
    });
  });
});
