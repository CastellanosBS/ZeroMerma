import type {
  OperationDocumentLineView,
  OperationDocumentView,
  TransferReceiveRequest,
} from "../../lib/api-contracts";
import {
  formatQuantityFromMilliUnits,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";

export type TransferDispatchUiState =
  | "NO_LINES_YET"
  | "DOCUMENT_BUILDING"
  | "READY_TO_COMMIT"
  | "COMMITTING"
  | "COMMITTED_SUCCESS";

export function hasTransferDispatchDestination(
  destinationBranchId: string | null | undefined,
): boolean {
  return typeof destinationBranchId === "string" && destinationBranchId.trim().length > 0;
}

export function getTransferDispatchUiState({
  hasCommittedTransfer,
  hasDestination,
  isCaptureInProgress,
  isCommitPending,
  isValidationReady,
  lineCount,
}: {
  hasCommittedTransfer: boolean;
  hasDestination: boolean;
  isCaptureInProgress: boolean;
  isCommitPending: boolean;
  isValidationReady: boolean;
  lineCount: number;
}): TransferDispatchUiState {
  if (isCommitPending) {
    return "COMMITTING";
  }

  if (hasCommittedTransfer && lineCount === 0) {
    return "COMMITTED_SUCCESS";
  }

  if (lineCount === 0) {
    return "NO_LINES_YET";
  }

  if (hasDestination && isValidationReady) {
    return "READY_TO_COMMIT";
  }

  void isCaptureInProgress;
  return "DOCUMENT_BUILDING";
}

export const TRANSFER_RECEIPT_STATE_SHIPMENT_SELECTION = "SHIPMENT_SELECTION";
export const TRANSFER_RECEIPT_STATE_DETAIL = "SHIPMENT_DETAIL";

export type TransferReceiptControlState =
  | typeof TRANSFER_RECEIPT_STATE_SHIPMENT_SELECTION
  | typeof TRANSFER_RECEIPT_STATE_DETAIL;

export type TransferReceiptUiState =
  | "NO_PENDING_SHIPMENTS"
  | "PENDING_LIST_READY"
  | "SHIPMENT_SELECTED"
  | "CAPTURING_RECEIVED_QUANTITIES"
  | "WITH_VARIANCES"
  | "READY_TO_CONFIRM"
  | "CONFIRMING"
  | "RECEIPT_CONFIRMED"
  | "RECEIPT_ERROR";

export interface TransferReceiptLineDraft {
  expectedQuantityText: string;
  lineNumber: number;
  productCode: string;
  productClassName: string;
  productName: string;
  shipmentLineId: string;
  varianceReason: string;
  receivedQuantityText: string;
}

export interface TransferReceiptDraftState {
  controlState: TransferReceiptControlState;
  selectedTransferId: string | null;
  lines: TransferReceiptLineDraft[];
  notes: string;
}

export function createInitialTransferReceiptDraftState(): TransferReceiptDraftState {
  return {
    controlState: TRANSFER_RECEIPT_STATE_SHIPMENT_SELECTION,
    selectedTransferId: null,
    lines: [],
    notes: "",
  };
}

export function createTransferReceiptDraftState(
  shipment: OperationDocumentView,
): TransferReceiptDraftState {
  return {
    controlState: TRANSFER_RECEIPT_STATE_DETAIL,
    selectedTransferId: shipment.id,
    lines: shipment.lines.map(createTransferReceiptLineDraft),
    notes: "",
  };
}

export function updateTransferReceiptLineQuantity(
  lines: TransferReceiptLineDraft[],
  shipmentLineId: string,
  receivedQuantityText: string,
): TransferReceiptLineDraft[] {
  return lines.map((line) =>
    line.shipmentLineId === shipmentLineId
      ? {
          ...line,
          receivedQuantityText: sanitizeQuantityInput(receivedQuantityText),
        }
      : line,
  );
}

export function updateTransferReceiptLineVarianceReason(
  lines: TransferReceiptLineDraft[],
  shipmentLineId: string,
  varianceReason: string,
): TransferReceiptLineDraft[] {
  return lines.map((line) =>
    line.shipmentLineId === shipmentLineId
      ? {
          ...line,
          varianceReason,
        }
      : line,
  );
}

export function getTransferReceiptExpectedTotalMilli(
  lines: TransferReceiptLineDraft[],
): number {
  return lines.reduce(
    (sum, line) => sum + (parseQuantityToMilliUnits(line.expectedQuantityText) ?? 0),
    0,
  );
}

export function getTransferReceiptReceivedTotalMilli(
  lines: TransferReceiptLineDraft[],
): number {
  return lines.reduce(
    (sum, line) => sum + (parseQuantityToMilliUnits(line.receivedQuantityText) ?? 0),
    0,
  );
}

export function getTransferReceiptVarianceLineCount(
  lines: TransferReceiptLineDraft[],
): number {
  return lines.filter((line) => hasTransferReceiptLineVariance(line)).length;
}

export function hasTransferReceiptMissingQuantities(
  lines: TransferReceiptLineDraft[],
): boolean {
  return lines.some(
    (line) => parseQuantityToMilliUnits(line.receivedQuantityText) === null,
  );
}

export function hasTransferReceiptMissingVarianceReason(
  lines: TransferReceiptLineDraft[],
): boolean {
  return lines.some(
    (line) =>
      hasTransferReceiptLineVariance(line) &&
      line.varianceReason.trim().length === 0,
  );
}

export function hasTransferReceiptLineVariance(
  line: TransferReceiptLineDraft,
): boolean {
  return line.receivedQuantityText.trim() !== line.expectedQuantityText.trim();
}

export function getTransferReceiptLineVarianceMilli(
  line: TransferReceiptLineDraft,
): number {
  const expectedMilli = parseQuantityToMilliUnits(line.expectedQuantityText) ?? 0;
  const receivedMilli = parseQuantityToMilliUnits(line.receivedQuantityText) ?? 0;
  return receivedMilli - expectedMilli;
}

export function getTransferReceiptDifferenceTotalMilli(
  lines: TransferReceiptLineDraft[],
): number {
  return (
    getTransferReceiptReceivedTotalMilli(lines) -
    getTransferReceiptExpectedTotalMilli(lines)
  );
}

export function getTransferReceiptUiState({
  hasConfirmedReceipt,
  hasError,
  hasLoadedLines,
  hasSelectedTransfer,
  hasVariance,
  isConfirmPending,
  pendingShipmentCount,
  requiresQuantityCapture,
}: {
  hasConfirmedReceipt: boolean;
  hasError: boolean;
  hasLoadedLines: boolean;
  hasSelectedTransfer: boolean;
  hasVariance: boolean;
  isConfirmPending: boolean;
  pendingShipmentCount: number;
  requiresQuantityCapture: boolean;
}): TransferReceiptUiState {
  if (isConfirmPending) {
    return "CONFIRMING";
  }

  if (hasConfirmedReceipt && !hasSelectedTransfer) {
    return "RECEIPT_CONFIRMED";
  }

  if (hasError) {
    return "RECEIPT_ERROR";
  }

  if (pendingShipmentCount === 0) {
    return "NO_PENDING_SHIPMENTS";
  }

  if (!hasSelectedTransfer) {
    return "PENDING_LIST_READY";
  }

  if (!hasLoadedLines) {
    return "SHIPMENT_SELECTED";
  }

  if (requiresQuantityCapture) {
    return "CAPTURING_RECEIVED_QUANTITIES";
  }

  if (hasVariance) {
    return "WITH_VARIANCES";
  }

  return "READY_TO_CONFIRM";
}

export function getTransferReceiptCommitBlockedReason({
  hasLineMismatch,
  hasMissingQuantities,
  hasMissingVarianceReason,
  hasSelectedTransfer,
  isReceivable,
  pendingShipmentCount,
}: {
  hasLineMismatch: boolean;
  hasMissingQuantities: boolean;
  hasMissingVarianceReason: boolean;
  hasSelectedTransfer: boolean;
  isReceivable: boolean;
  pendingShipmentCount: number;
}): string | null {
  if (pendingShipmentCount === 0) {
    return "No hay envios pendientes para esta sucursal.";
  }

  if (!hasSelectedTransfer) {
    return "Selecciona un envio pendiente.";
  }

  if (!isReceivable) {
    return "Este envio ya no esta pendiente de recepcion.";
  }

  if (hasLineMismatch) {
    return "Revisa las lineas del envio.";
  }

  if (hasMissingQuantities) {
    return "Captura las cantidades recibidas.";
  }

  if (hasMissingVarianceReason) {
    return "Revisa las lineas con diferencia.";
  }

  return null;
}

export function buildTransferReceiveLines(
  lines: TransferReceiptLineDraft[],
): TransferReceiveRequest["lines"] {
  if (lines.length === 0) {
    throw new Error("Selecciona un envio pendiente antes de confirmar la recepcion.");
  }

  return lines.map((line) => {
    const expectedMilli = parseQuantityToMilliUnits(line.expectedQuantityText);
    const receivedMilli = parseQuantityToMilliUnits(line.receivedQuantityText);

    if (expectedMilli === null || expectedMilli <= 0) {
      throw new Error("Las cantidades esperadas deben ser mayores que cero.");
    }

    if (receivedMilli === null || receivedMilli < 0) {
      throw new Error("Las cantidades recibidas deben ser cero o mayores.");
    }

    if (
      receivedMilli !== expectedMilli &&
      line.varianceReason.trim().length === 0
    ) {
      throw new Error(
        `Indica el motivo de la diferencia en ${line.productName}.`,
      );
    }

    return {
      shipment_line_id: line.shipmentLineId,
      expected_quantity: formatQuantityFromMilliUnits(expectedMilli),
      received_quantity: formatQuantityFromMilliUnits(receivedMilli),
      variance_reason:
        receivedMilli !== expectedMilli && line.varianceReason.trim().length > 0
          ? line.varianceReason.trim()
          : null,
      notes: null,
    };
  });
}

function createTransferReceiptLineDraft(
  line: OperationDocumentLineView,
): TransferReceiptLineDraft {
  const expectedQuantityText = formatLineQuantity(
    line.expected_quantity ?? line.quantity,
    "La cantidad esperada del envio es obligatoria.",
  );

  return {
    expectedQuantityText,
    lineNumber: line.line_number,
    productCode: line.product_code_snapshot,
    productClassName: line.product_class_name_snapshot,
    productName: line.product_name_snapshot,
    shipmentLineId: line.id,
    varianceReason: "",
    receivedQuantityText: expectedQuantityText,
  };
}

function formatLineQuantity(
  value: string | number | null,
  errorMessage: string,
): string {
  if (value === null) {
    throw new Error(errorMessage);
  }

  const normalizedValue = typeof value === "string" ? value : String(value);
  const milliUnits = parseQuantityToMilliUnits(normalizedValue);
  if (milliUnits === null) {
    throw new Error(errorMessage);
  }

  return formatQuantityFromMilliUnits(milliUnits);
}
