import type {
  OperationCommitLineRequest,
  OperationsCatalogClassView,
  OperationsCatalogProductView,
} from "../../lib/api-contracts";
import {
  formatQuantityFromMilliUnits,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";

export const CONTROL_STATE_CLASS_SELECTION = "CLASS_SELECTION";
export const CONTROL_STATE_PRODUCT_SELECTION = "PRODUCT_SELECTION";
export const CONTROL_STATE_QUANTITY_CAPTURE = "QUANTITY_CAPTURE";

export type OperationControlState =
  | typeof CONTROL_STATE_CLASS_SELECTION
  | typeof CONTROL_STATE_PRODUCT_SELECTION
  | typeof CONTROL_STATE_QUANTITY_CAPTURE;

export type OperationDocumentState =
  | "NO_LINES_YET"
  | "DOCUMENT_BUILDING"
  | "READY_TO_COMMIT"
  | "COMMITTING"
  | "COMMITTED_SUCCESS";

export type WasteDocumentUiState =
  | "TRACEABILITY_INCOMPLETE"
  | "READY_TO_CAPTURE"
  | "DOCUMENT_BUILDING"
  | "BLOCKED_NO_LINES"
  | "BLOCKED_MISSING_ORIGIN"
  | "BLOCKED_MISSING_REASON"
  | "READY_TO_REGISTER"
  | "REGISTERING"
  | "REGISTERED_SUCCESS"
  | "ERROR";

export interface OperationPendingSelection {
  productClass: OperationsCatalogClassView;
  product: OperationsCatalogProductView | null;
  quantityText: string;
}

export interface OperationLine {
  key: string;
  productClassCode: string;
  productClassId: string;
  productClassName: string;
  productCode: string;
  productId: string;
  productName: string;
  quantityMilliUnits: number;
  quantityText: string;
}

export interface OperationDraftState {
  controlState: OperationControlState;
  lines: OperationLine[];
  pendingSelection: OperationPendingSelection | null;
  searchText: string;
}

export function createInitialOperationDraftState(): OperationDraftState {
  return {
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lines: [],
    pendingSelection: null,
    searchText: "",
  };
}

export function sortOperationalClasses(
  classes: OperationsCatalogClassView[],
): OperationsCatalogClassView[] {
  return [...classes].sort((left, right) => {
    const displayOrderDifference = left.display_order - right.display_order;
    if (displayOrderDifference !== 0) {
      return displayOrderDifference;
    }

    return left.name.localeCompare(right.name);
  });
}

export function sortOperationalProducts(
  products: OperationsCatalogProductView[],
): OperationsCatalogProductView[] {
  return [...products].sort((left, right) => {
    const displayOrderDifference = left.display_order - right.display_order;
    if (displayOrderDifference !== 0) {
      return displayOrderDifference;
    }

    return left.name.localeCompare(right.name);
  });
}

export function selectClassForOperation(
  state: OperationDraftState,
  productClass: OperationsCatalogClassView,
): OperationDraftState {
  return {
    ...state,
    controlState: CONTROL_STATE_PRODUCT_SELECTION,
    pendingSelection: {
      productClass,
      product: null,
      quantityText: "",
    },
    searchText: "",
  };
}

export function selectProductForOperation(
  state: OperationDraftState,
  product: OperationsCatalogProductView,
): OperationDraftState {
  if (state.pendingSelection === null) {
    throw new Error("Selecciona una clase antes de elegir un producto.");
  }

  return {
    ...state,
    controlState: CONTROL_STATE_QUANTITY_CAPTURE,
    pendingSelection: {
      ...state.pendingSelection,
      product,
      quantityText: "",
    },
    searchText: "",
  };
}

export function goBackFromOperationalState(state: OperationDraftState): OperationDraftState {
  if (state.controlState === CONTROL_STATE_PRODUCT_SELECTION) {
    return {
      ...state,
      controlState: CONTROL_STATE_CLASS_SELECTION,
      pendingSelection: null,
      searchText: "",
    };
  }

  if (state.controlState === CONTROL_STATE_QUANTITY_CAPTURE) {
    return {
      ...state,
      controlState: CONTROL_STATE_PRODUCT_SELECTION,
      pendingSelection:
        state.pendingSelection === null
          ? null
          : {
              ...state.pendingSelection,
              product: null,
              quantityText: "",
            },
      searchText: "",
    };
  }

  return state;
}

export function setPendingQuantityText(
  state: OperationDraftState,
  quantityText: string,
): OperationDraftState {
  if (state.pendingSelection === null) {
    return state;
  }

  return {
    ...state,
    pendingSelection: {
      ...state.pendingSelection,
      quantityText: sanitizeQuantityInput(quantityText),
    },
  };
}

export function incrementPendingOperationQuantity(
  state: OperationDraftState,
): OperationDraftState {
  if (state.pendingSelection === null) {
    return state;
  }

  const currentQuantity = parseQuantityToMilliUnits(state.pendingSelection.quantityText) ?? 0;
  return setPendingQuantityText(
    state,
    formatQuantityFromMilliUnits(currentQuantity + 1000),
  );
}

export function decrementPendingOperationQuantity(
  state: OperationDraftState,
): OperationDraftState {
  if (state.pendingSelection === null) {
    return state;
  }

  const currentQuantity = parseQuantityToMilliUnits(state.pendingSelection.quantityText) ?? 0;
  if (currentQuantity <= 1000) {
    return setPendingQuantityText(state, "");
  }

  return setPendingQuantityText(
    state,
    formatQuantityFromMilliUnits(currentQuantity - 1000),
  );
}

export function addPendingSelectionLine(state: OperationDraftState): OperationDraftState {
  if (state.pendingSelection === null || state.pendingSelection.product === null) {
    throw new Error("Selecciona el producto exacto antes de agregar la linea.");
  }

  const quantityMilliUnits = parseQuantityToMilliUnits(state.pendingSelection.quantityText);
  if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
    throw new Error("Captura una cantidad mayor que cero.");
  }

  const nextLine = buildOperationLine(state.pendingSelection, quantityMilliUnits);
  const existingLine = state.lines.find((line) => line.key === nextLine.key);
  const nextLines = existingLine
    ? state.lines.map((line) =>
        line.key === nextLine.key
          ? updateOperationLineQuantity(
              line,
              line.quantityMilliUnits + nextLine.quantityMilliUnits,
            )
          : line,
      )
    : [...state.lines, nextLine];

  return {
    ...state,
    controlState: CONTROL_STATE_CLASS_SELECTION,
    lines: nextLines,
    pendingSelection: null,
    searchText: "",
  };
}

export function updateOperationLineQuantity(
  line: OperationLine,
  quantityMilliUnits: number,
): OperationLine {
  return {
    ...line,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
  };
}

export function removeOperationLine(
  lines: OperationLine[],
  lineKey: string,
): OperationLine[] {
  return lines.filter((line) => line.key !== lineKey);
}

export function getOperationLineCount(lines: OperationLine[]): number {
  return lines.length;
}

export function getOperationTotalUnitsMilli(lines: OperationLine[]): number {
  return lines.reduce((sum, line) => sum + line.quantityMilliUnits, 0);
}

export function getOperationDocumentState({
  hasCommittedDocument,
  isCaptureInProgress,
  isCommitPending,
  lineCount,
}: {
  hasCommittedDocument: boolean;
  isCaptureInProgress: boolean;
  isCommitPending: boolean;
  lineCount: number;
}): OperationDocumentState {
  if (isCommitPending) {
    return "COMMITTING";
  }

  if (hasCommittedDocument && lineCount === 0) {
    return "COMMITTED_SUCCESS";
  }

  if (lineCount === 0) {
    return "NO_LINES_YET";
  }

  if (isCaptureInProgress) {
    return "DOCUMENT_BUILDING";
  }

  return "READY_TO_COMMIT";
}

export function getOperationPendingCaptureTargetKey(
  pendingSelection: OperationPendingSelection | null,
): string | null {
  if (pendingSelection === null) {
    return null;
  }

  if (pendingSelection.product !== null) {
    return `product:${pendingSelection.product.id}`;
  }

  return `class:${pendingSelection.productClass.id}`;
}

export function hasOperationInvalidLineQuantity(lines: OperationLine[]): boolean {
  return lines.some((line) => {
    const quantityMilliUnits = parseQuantityToMilliUnits(line.quantityText);
    return quantityMilliUnits === null || quantityMilliUnits <= 0;
  });
}

export function getWasteDocumentUiState({
  hasCommittedDocument,
  hasCommitError,
  hasInvalidQuantity,
  hasOrigin,
  hasReason,
  isCaptureInProgress,
  isCommitPending,
  lineCount,
  totalUnitsMilli,
}: {
  hasCommittedDocument: boolean;
  hasCommitError: boolean;
  hasInvalidQuantity: boolean;
  hasOrigin: boolean;
  hasReason: boolean;
  isCaptureInProgress: boolean;
  isCommitPending: boolean;
  lineCount: number;
  totalUnitsMilli: number;
}): WasteDocumentUiState {
  if (hasCommitError) {
    return "ERROR";
  }

  if (isCommitPending) {
    return "REGISTERING";
  }

  if (hasCommittedDocument && lineCount === 0) {
    return "REGISTERED_SUCCESS";
  }

  if (!hasOrigin && !hasReason) {
    return "TRACEABILITY_INCOMPLETE";
  }

  if (!hasOrigin) {
    return "BLOCKED_MISSING_ORIGIN";
  }

  if (!hasReason) {
    return "BLOCKED_MISSING_REASON";
  }

  if (lineCount === 0 || totalUnitsMilli <= 0) {
    return isCaptureInProgress ? "READY_TO_CAPTURE" : "BLOCKED_NO_LINES";
  }

  if (hasInvalidQuantity) {
    return "DOCUMENT_BUILDING";
  }

  if (isCaptureInProgress) {
    return "DOCUMENT_BUILDING";
  }

  return "READY_TO_REGISTER";
}

export function getWasteDocumentBlockingMessages({
  additionalBlockingMessages = [],
  evidenceNoteRequired = false,
  hasEvidenceNote = false,
  hasHighImpactAcknowledgement = false,
  hasInvalidQuantity,
  highImpactAcknowledgementRequired = false,
  hasOrigin,
  hasReason,
  lineCount,
  totalUnitsMilli,
}: {
  additionalBlockingMessages?: string[];
  evidenceNoteRequired?: boolean;
  hasEvidenceNote?: boolean;
  hasHighImpactAcknowledgement?: boolean;
  hasInvalidQuantity: boolean;
  highImpactAcknowledgementRequired?: boolean;
  hasOrigin: boolean;
  hasReason: boolean;
  lineCount: number;
  totalUnitsMilli: number;
}): string[] {
  const messages: string[] = [];

  if (!hasOrigin) {
    messages.push("Selecciona un origen para continuar.");
  }

  if (!hasReason) {
    messages.push("Selecciona un motivo para continuar.");
  }

  if (lineCount === 0 || totalUnitsMilli <= 0) {
    messages.push("Agrega al menos una linea.");
  }

  if (hasInvalidQuantity) {
    messages.push("Revisa las cantidades capturadas.");
  }

  if (evidenceNoteRequired && !hasEvidenceNote) {
    messages.push("Agrega notas operativas para documentar la evidencia.");
  }

  if (highImpactAcknowledgementRequired && !hasHighImpactAcknowledgement) {
    messages.push("Confirma la merma de alto impacto antes de registrar.");
  }

  messages.push(...additionalBlockingMessages);

  return messages;
}

export function getWasteDocumentBlockedReason(args: {
  additionalBlockingMessages?: string[];
  evidenceNoteRequired?: boolean;
  hasEvidenceNote?: boolean;
  hasHighImpactAcknowledgement?: boolean;
  hasInvalidQuantity: boolean;
  highImpactAcknowledgementRequired?: boolean;
  hasOrigin: boolean;
  hasReason: boolean;
  lineCount: number;
  totalUnitsMilli: number;
}): string | null {
  return getWasteDocumentBlockingMessages(args)[0] ?? null;
}

export function buildOperationCommitLines(
  lines: OperationLine[],
): OperationCommitLineRequest[] {
  if (lines.length === 0) {
    throw new Error("Agrega al menos una linea antes de registrar el documento.");
  }

  return lines.map((line) => ({
    product_id: line.productId,
    quantity: formatQuantityFromMilliUnits(line.quantityMilliUnits),
  }));
}

function buildOperationLine(
  pendingSelection: OperationPendingSelection,
  quantityMilliUnits: number,
): OperationLine {
  if (pendingSelection.product === null) {
    throw new Error("Selecciona el producto exacto antes de agregar la linea.");
  }

  return {
    key: pendingSelection.product.id,
    productClassCode: pendingSelection.productClass.code,
    productClassId: pendingSelection.productClass.id,
    productClassName: pendingSelection.productClass.name,
    productCode: pendingSelection.product.code,
    productId: pendingSelection.product.id,
    productName: pendingSelection.product.name,
    quantityMilliUnits,
    quantityText: formatQuantityFromMilliUnits(quantityMilliUnits),
  };
}
