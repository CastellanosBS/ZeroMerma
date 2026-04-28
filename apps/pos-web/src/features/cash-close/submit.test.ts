import { describe, expect, it, vi } from "vitest";

import {
  CLOSE_SECTION_CONTEXT,
  CLOSE_SECTION_FINANCIAL,
  CLOSE_SECTION_PHYSICAL,
  CLOSE_SECTION_RECONCILIATION,
  CLOSE_SECTION_REVIEW,
} from "./model";
import {
  canAttemptCashCloseSubmit,
  finalizeSuccessfulCashClose,
  getCashCloseSubmitTargetSection,
  submitCashCloseAttempt,
} from "./submit";

describe("cash close submit helpers", () => {
  it("allows attempting close without depending on preview freshness or blocker-free state", () => {
    expect(
      canAttemptCashCloseSubmit({
        accessToken: "token",
        hasOpenCashSession: true,
        isCommitPending: false,
      }),
    ).toBe(true);
  });

  it("blocks submit attempts only for hard runtime constraints", () => {
    expect(
      canAttemptCashCloseSubmit({
        accessToken: null,
        hasOpenCashSession: true,
        isCommitPending: false,
      }),
    ).toBe(false);
    expect(
      canAttemptCashCloseSubmit({
        accessToken: "token",
        hasOpenCashSession: false,
        isCommitPending: false,
      }),
    ).toBe(false);
    expect(
      canAttemptCashCloseSubmit({
        accessToken: "token",
        hasOpenCashSession: true,
        isCommitPending: true,
      }),
    ).toBe(false);
  });

  it("runs preview first and prevents commit when submit-time blockers remain", async () => {
    const payload = { counted_payment_methods: [], workstation_code: "POS-01" };
    const callOrder: string[] = [];
    const preview = vi.fn(async (receivedPayload: typeof payload) => {
      callOrder.push("preview");
      expect(receivedPayload).toBe(payload);
      return {
        blockers: [
          {
            code: "MISSING_COUNTED_PAYMENT_TOTALS",
            message: "Falta efectivo contado.",
          },
        ],
        reconciliation_status: "BLOCKED" as const,
      };
    });
    const commit = vi.fn(async () => {
      callOrder.push("commit");
      return { id: "close-1" };
    });

    const result = await submitCashCloseAttempt({
      commit,
      payload,
      preview,
    });

    expect(callOrder).toEqual(["preview"]);
    expect(commit).not.toHaveBeenCalled();
    expect(result.detail).toBeNull();
    expect(result.preview.blockers).toHaveLength(1);
  });

  it("commits with the exact same payload after a ready preview without blockers", async () => {
    const payload = {
      counted_payment_methods: [{ counted_amount: "150.00", payment_method_code: "CASH" }],
      workstation_code: "POS-01",
    };
    const previewPayloads: Array<typeof payload> = [];
    const commitPayloads: Array<typeof payload> = [];
    const preview = vi.fn(async (receivedPayload: typeof payload) => {
      previewPayloads.push(receivedPayload);
      return {
        blockers: [],
        reconciliation_status: "READY" as const,
      };
    });
    const commit = vi.fn(async (receivedPayload: typeof payload) => {
      commitPayloads.push(receivedPayload);
      return { id: "close-1" };
    });

    const result = await submitCashCloseAttempt({
      commit,
      payload,
      preview,
    });

    expect(preview).toHaveBeenCalledTimes(1);
    expect(commit).toHaveBeenCalledTimes(1);
    expect(previewPayloads[0]).toBe(payload);
    expect(commitPayloads[0]).toBe(payload);
    expect(result.detail).toEqual({ id: "close-1" });
  });

  it("maps submit-time blockers to the first actionable close section", () => {
    expect(
      getCashCloseSubmitTargetSection({
        blockers: [{ code: "MISSING_COUNTED_PAYMENT_TOTALS", message: "Falta." }],
      }),
    ).toBe(CLOSE_SECTION_FINANCIAL);

    expect(
      getCashCloseSubmitTargetSection({
        blockers: [{ code: "MISSING_COUNTED_CLOSING_STOCK", message: "Falta." }],
      }),
    ).toBe(CLOSE_SECTION_PHYSICAL);

    expect(
      getCashCloseSubmitTargetSection({
        blockers: [
          { code: "UNRESOLVED_CLASS_CAPTURE_MISMATCH", message: "Falta." },
        ],
      }),
    ).toBe(CLOSE_SECTION_RECONCILIATION);

    expect(
      getCashCloseSubmitTargetSection({
        blockers: [{ code: "INCONSISTENT_SESSION_CONTEXT", message: "Falta." }],
      }),
    ).toBe(CLOSE_SECTION_CONTEXT);

    expect(
      getCashCloseSubmitTargetSection({
        blockers: [{ code: "UNKNOWN", message: "Falta." }],
      }),
    ).toBe(CLOSE_SECTION_REVIEW);
  });

  it("clears canonical POS state and navigates to login after a successful close", async () => {
    const calls: string[] = [];

    await finalizeSuccessfulCashClose({
      clearQueryCache: () => calls.push("query-cache"),
      clearSession: () => calls.push("session"),
      navigateToLogin: async () => {
        calls.push("navigate");
      },
      resetPosTerminal: () => calls.push("terminal"),
    });

    expect(calls).toEqual(["terminal", "session", "query-cache", "navigate"]);
  });
});
