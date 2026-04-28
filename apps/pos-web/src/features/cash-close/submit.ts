import type { CashClosePreviewResponse } from "../../lib/api-contracts";
import {
  CLOSE_SECTION_CONTEXT,
  CLOSE_SECTION_FINANCIAL,
  CLOSE_SECTION_PHYSICAL,
  CLOSE_SECTION_RECONCILIATION,
  CLOSE_SECTION_REVIEW,
  type CashCloseSection,
} from "./model";

export function canAttemptCashCloseSubmit({
  accessToken,
  hasOpenCashSession,
  isCommitPending,
}: {
  accessToken: string | null;
  hasOpenCashSession: boolean;
  isCommitPending: boolean;
}): boolean {
  return accessToken !== null && hasOpenCashSession && !isCommitPending;
}

export function getCashCloseSubmitTargetSection(
  preview: Pick<CashClosePreviewResponse, "blockers">,
): CashCloseSection {
  const firstBlockerCode = preview.blockers[0]?.code ?? null;

  switch (firstBlockerCode) {
    case "NO_ACTIVE_OPEN_CASH_SESSION":
    case "SESSION_ALREADY_CLOSED":
    case "INCONSISTENT_SESSION_CONTEXT":
      return CLOSE_SECTION_CONTEXT;
    case "MISSING_COUNTED_PAYMENT_TOTALS":
      return CLOSE_SECTION_FINANCIAL;
    case "MISSING_COUNTED_CLOSING_STOCK":
      return CLOSE_SECTION_PHYSICAL;
    case "UNRESOLVED_CLASS_CAPTURE_MISMATCH":
    case "INVALID_MANUAL_RECONCILIATION_OVERRIDE":
    case "INVALID_DISCREPANCY_RESOLUTION":
    case "INTERNAL_INTEGRITY_MISMATCH":
      return CLOSE_SECTION_RECONCILIATION;
    default:
      return CLOSE_SECTION_REVIEW;
  }
}

export function shouldCommitCashClosePreview(
  preview: Pick<CashClosePreviewResponse, "blockers" | "reconciliation_status">,
): boolean {
  return preview.blockers.length === 0 && preview.reconciliation_status === "READY";
}

export async function submitCashCloseAttempt<
  TPayload,
  TPreview extends Pick<CashClosePreviewResponse, "blockers" | "reconciliation_status">,
  TDetail,
>({
  commit,
  payload,
  preview,
}: {
  commit: (payload: TPayload) => Promise<TDetail>;
  payload: TPayload;
  preview: (payload: TPayload) => Promise<TPreview>;
}): Promise<{
  detail: TDetail | null;
  preview: TPreview;
}> {
  const previewResult = await preview(payload);

  if (!shouldCommitCashClosePreview(previewResult)) {
    return {
      detail: null,
      preview: previewResult,
    };
  }

  const detail = await commit(payload);
  return {
    detail,
    preview: previewResult,
  };
}

export async function finalizeSuccessfulCashClose({
  clearQueryCache,
  clearSession,
  navigateToLogin,
  resetPosTerminal,
}: {
  clearQueryCache: () => void;
  clearSession: () => void;
  navigateToLogin: () => Promise<void> | void;
  resetPosTerminal: () => void;
}): Promise<void> {
  resetPosTerminal();
  clearSession();
  clearQueryCache();
  await navigateToLogin();
}
