import { describe, expect, it } from "vitest";

import type { OperationDocumentView } from "../../lib/api-contracts";
import {
  buildTransferReceiveLines,
  createTransferReceiptDraftState,
  getTransferReceiptCommitBlockedReason,
  getTransferReceiptDifferenceTotalMilli,
  getTransferDispatchUiState,
  getTransferReceiptExpectedTotalMilli,
  getTransferReceiptLineVarianceMilli,
  getTransferReceiptReceivedTotalMilli,
  getTransferReceiptUiState,
  getTransferReceiptVarianceLineCount,
  hasTransferDispatchDestination,
  hasTransferReceiptLineVariance,
  hasTransferReceiptMissingQuantities,
  hasTransferReceiptMissingVarianceReason,
  updateTransferReceiptLineQuantity,
  updateTransferReceiptLineVarianceReason,
} from "./model";

const shipment: OperationDocumentView = {
  committed_at_utc: "2026-04-09T17:00:00Z",
  created_at_utc: "2026-04-09T16:55:00Z",
  created_by_user_email: "cashier@zeromerma.local",
  created_by_user_full_name: "Main Branch Cashier",
  created_by_user_id: "11111111-1111-1111-1111-111111111111",
  folio: "ENV-AAAAAA",
  destination_branch_code: "NORTE",
  destination_branch_id: "33333333-3333-3333-3333-333333333333",
  destination_branch_name: "North Branch",
  destination_bucket_code: "BACKROOM",
  document_type: "BRANCH_TRANSFER_SHIPMENT",
  id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  lines: [
    {
      expected_quantity: "4.000",
      id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      line_number: 1,
      notes: null,
      product_class_code_snapshot: "BOLILLO",
      product_class_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
      product_class_name_snapshot: "Bolillo",
      product_code_snapshot: "BOLILLO-STD",
      product_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
      product_name_snapshot: "Standard Bolillo",
      quantity: "4.000",
      received_quantity: null,
      unit_of_measure_code: "EACH",
      variance_reason: null,
    },
    {
      expected_quantity: "2.000",
      id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
      line_number: 2,
      notes: null,
      product_class_code_snapshot: "BEBIDAS",
      product_class_id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
      product_class_name_snapshot: "Bebidas",
      product_code_snapshot: "CAFE-AMERICANO",
      product_id: "12121212-1212-1212-1212-121212121212",
      product_name_snapshot: "Cafe americano",
      quantity: "2.000",
      received_quantity: null,
      unit_of_measure_code: "EACH",
      variance_reason: null,
    },
  ],
  notes: "North branch transfer",
  reason_code: null,
  reason_name: null,
  reference_document_id: null,
  source_branch_code: "MAIN",
  source_branch_id: "22222222-2222-2222-2222-222222222222",
  source_branch_name: "Main Branch",
  source_bucket_code: "BACKROOM",
  status: "IN_TRANSIT",
  workstation_code: "POS-01",
  workstation_id: "99999999-9999-9999-9999-999999999999",
  workstation_name: "Front Register 01",
};

describe("transfer receipt model", () => {
  it("creates a draft with expected quantities copied to received quantities", () => {
    const draft = createTransferReceiptDraftState(shipment);

    expect(draft.selectedTransferId).toBe(shipment.id);
    expect(draft.lines).toHaveLength(2);
    expect(draft.lines[0]?.expectedQuantityText).toBe("4");
    expect(draft.lines[0]?.receivedQuantityText).toBe("4");
    expect(getTransferReceiptExpectedTotalMilli(draft.lines)).toBe(6000);
    expect(getTransferReceiptReceivedTotalMilli(draft.lines)).toBe(6000);
    expect(getTransferReceiptVarianceLineCount(draft.lines)).toBe(0);
    expect(draft.lines[0]?.productClassName).toBe("Bolillo");
  });

  it("tracks quantity edits and variance reasons", () => {
    const initialDraft = createTransferReceiptDraftState(shipment);
    const linesWithQuantityChange = updateTransferReceiptLineQuantity(
      initialDraft.lines,
      "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "3",
    );
    const linesWithVarianceReason = updateTransferReceiptLineVarianceReason(
      linesWithQuantityChange,
      "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "One tray missing",
    );

    expect(getTransferReceiptReceivedTotalMilli(linesWithVarianceReason)).toBe(5000);
    expect(getTransferReceiptVarianceLineCount(linesWithVarianceReason)).toBe(1);
    expect(getTransferReceiptDifferenceTotalMilli(linesWithVarianceReason)).toBe(-1000);
    expect(linesWithVarianceReason[0]?.varianceReason).toBe("One tray missing");
    expect(hasTransferReceiptLineVariance(linesWithVarianceReason[0]!)).toBe(true);
    expect(getTransferReceiptLineVarianceMilli(linesWithVarianceReason[0]!)).toBe(-1000);
  });

  it("builds receipt payload lines with expected and received quantities", () => {
    const initialDraft = createTransferReceiptDraftState(shipment);
    const lines = updateTransferReceiptLineVarianceReason(
      updateTransferReceiptLineQuantity(
        initialDraft.lines,
        "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "3",
      ),
      "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "One tray missing",
    );

    expect(buildTransferReceiveLines(lines)).toEqual([
      {
        expected_quantity: "4",
        notes: null,
        received_quantity: "3",
        shipment_line_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        variance_reason: "One tray missing",
      },
      {
        expected_quantity: "2",
        notes: null,
        received_quantity: "2",
        shipment_line_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        variance_reason: null,
      },
    ]);
  });

  it("requires a variance reason when the received quantity differs", () => {
    const initialDraft = createTransferReceiptDraftState(shipment);
    const lines = updateTransferReceiptLineQuantity(
      initialDraft.lines,
      "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "3",
    );

    expect(() => buildTransferReceiveLines(lines)).toThrow(
      "Indica el motivo de la diferencia en Standard Bolillo.",
    );
  });

  it("detects missing received quantities and missing variance reasons", () => {
    const initialDraft = createTransferReceiptDraftState(shipment);
    const linesWithMissingQuantity = updateTransferReceiptLineQuantity(
      initialDraft.lines,
      "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "",
    );
    const linesWithVariance = updateTransferReceiptLineQuantity(
      initialDraft.lines,
      "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      "3",
    );

    expect(hasTransferReceiptMissingQuantities(linesWithMissingQuantity)).toBe(true);
    expect(hasTransferReceiptMissingVarianceReason(linesWithVariance)).toBe(true);
  });

  it("derives the transfer receipt UI state and commit guardrails", () => {
    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: false,
        hasSelectedTransfer: false,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 0,
        requiresQuantityCapture: false,
      }),
    ).toBe("NO_PENDING_SHIPMENTS");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: false,
        hasSelectedTransfer: false,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 2,
        requiresQuantityCapture: false,
      }),
    ).toBe("PENDING_LIST_READY");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: false,
        hasSelectedTransfer: true,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 2,
        requiresQuantityCapture: false,
      }),
    ).toBe("SHIPMENT_SELECTED");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: true,
        hasSelectedTransfer: true,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 2,
        requiresQuantityCapture: true,
      }),
    ).toBe("CAPTURING_RECEIVED_QUANTITIES");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: true,
        hasSelectedTransfer: true,
        hasVariance: true,
        isConfirmPending: false,
        pendingShipmentCount: 2,
        requiresQuantityCapture: false,
      }),
    ).toBe("WITH_VARIANCES");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: true,
        hasSelectedTransfer: true,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 2,
        requiresQuantityCapture: false,
      }),
    ).toBe("READY_TO_CONFIRM");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: false,
        hasLoadedLines: true,
        hasSelectedTransfer: true,
        hasVariance: false,
        isConfirmPending: true,
        pendingShipmentCount: 2,
        requiresQuantityCapture: false,
      }),
    ).toBe("CONFIRMING");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: true,
        hasError: false,
        hasLoadedLines: false,
        hasSelectedTransfer: false,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 1,
        requiresQuantityCapture: false,
      }),
    ).toBe("RECEIPT_CONFIRMED");

    expect(
      getTransferReceiptUiState({
        hasConfirmedReceipt: false,
        hasError: true,
        hasLoadedLines: true,
        hasSelectedTransfer: true,
        hasVariance: false,
        isConfirmPending: false,
        pendingShipmentCount: 1,
        requiresQuantityCapture: false,
      }),
    ).toBe("RECEIPT_ERROR");

    expect(
      getTransferReceiptCommitBlockedReason({
        hasLineMismatch: false,
        hasMissingQuantities: false,
        hasMissingVarianceReason: false,
        hasSelectedTransfer: false,
        isReceivable: false,
        pendingShipmentCount: 2,
      }),
    ).toBe("Selecciona un envio pendiente.");

    expect(
      getTransferReceiptCommitBlockedReason({
        hasLineMismatch: false,
        hasMissingQuantities: true,
        hasMissingVarianceReason: false,
        hasSelectedTransfer: true,
        isReceivable: true,
        pendingShipmentCount: 2,
      }),
    ).toBe("Captura las cantidades recibidas.");

    expect(
      getTransferReceiptCommitBlockedReason({
        hasLineMismatch: false,
        hasMissingQuantities: false,
        hasMissingVarianceReason: true,
        hasSelectedTransfer: true,
        isReceivable: true,
        pendingShipmentCount: 2,
      }),
    ).toBe("Revisa las lineas con diferencia.");

    expect(
      getTransferReceiptCommitBlockedReason({
        hasLineMismatch: false,
        hasMissingQuantities: false,
        hasMissingVarianceReason: false,
        hasSelectedTransfer: true,
        isReceivable: true,
        pendingShipmentCount: 2,
      }),
    ).toBeNull();
  });

  it("derives the transfer dispatch UI state from destination, lines, and commit progress", () => {
    expect(hasTransferDispatchDestination("")).toBe(false);
    expect(hasTransferDispatchDestination("branch-1")).toBe(true);

    expect(
      getTransferDispatchUiState({
        hasCommittedTransfer: false,
        hasDestination: false,
        isCaptureInProgress: false,
        isCommitPending: false,
        isValidationReady: false,
        lineCount: 0,
      }),
    ).toBe("NO_LINES_YET");

    expect(
      getTransferDispatchUiState({
        hasCommittedTransfer: false,
        hasDestination: true,
        isCaptureInProgress: true,
        isCommitPending: false,
        isValidationReady: false,
        lineCount: 2,
      }),
    ).toBe("DOCUMENT_BUILDING");

    expect(
      getTransferDispatchUiState({
        hasCommittedTransfer: false,
        hasDestination: true,
        isCaptureInProgress: false,
        isCommitPending: false,
        isValidationReady: true,
        lineCount: 2,
      }),
    ).toBe("READY_TO_COMMIT");

    expect(
      getTransferDispatchUiState({
        hasCommittedTransfer: false,
        hasDestination: true,
        isCaptureInProgress: false,
        isCommitPending: true,
        isValidationReady: true,
        lineCount: 2,
      }),
    ).toBe("COMMITTING");

    expect(
      getTransferDispatchUiState({
        hasCommittedTransfer: true,
        hasDestination: true,
        isCaptureInProgress: false,
        isCommitPending: false,
        isValidationReady: false,
        lineCount: 0,
      }),
    ).toBe("COMMITTED_SUCCESS");
  });
});
