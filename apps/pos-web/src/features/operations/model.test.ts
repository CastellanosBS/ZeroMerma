import { describe, expect, it } from "vitest";

import type { OperationsCatalogClassView, OperationsCatalogProductView } from "../../lib/api-contracts";
import {
  addPendingSelectionLine,
  buildOperationCommitLines,
  CONTROL_STATE_CLASS_SELECTION,
  CONTROL_STATE_PRODUCT_SELECTION,
  CONTROL_STATE_QUANTITY_CAPTURE,
  createInitialOperationDraftState,
  getWasteDocumentBlockedReason,
  getWasteDocumentUiState,
  getOperationDocumentState,
  getOperationLineCount,
  getOperationPendingCaptureTargetKey,
  getOperationTotalUnitsMilli,
  hasOperationInvalidLineQuantity,
  goBackFromOperationalState,
  selectClassForOperation,
  selectProductForOperation,
  setPendingQuantityText,
  sortOperationalClasses,
} from "./model";

function buildClass(overrides: Partial<OperationsCatalogClassView>): OperationsCatalogClassView {
  return {
    code: "PAN-DULCE",
    display_order: 10,
    id: "class-1",
    name: "Pan dulce",
    product_count: 3,
    quick_name: "Dulce",
    ...overrides,
  };
}

function buildProduct(
  overrides: Partial<OperationsCatalogProductView>,
): OperationsCatalogProductView {
  return {
    code: "CONCHA-VAN",
    currency_code: "MXN",
    display_order: 10,
    id: "product-1",
    name: "Vanilla Concha",
    quick_name: "Concha",
    unit_price: "12.00",
    ...overrides,
  };
}

describe("operations model", () => {
  it("orders classes by display order and name only", () => {
    const sorted = sortOperationalClasses([
      buildClass({ id: "3", name: "Telera", display_order: 30 }),
      buildClass({ id: "2", name: "Bebidas", display_order: 30 }),
      buildClass({ id: "1", name: "Bolillo", display_order: 20 }),
    ]);

    expect(sorted.map((item) => item.name)).toEqual(["Bolillo", "Bebidas", "Telera"]);
  });

  it("runs class to product to quantity to add-line flow and returns to class selection", () => {
    const initialState = createInitialOperationDraftState();
    const productClass = buildClass({});
    const product = buildProduct({});

    const productSelectionState = selectClassForOperation(initialState, productClass);
    expect(productSelectionState.controlState).toBe(CONTROL_STATE_PRODUCT_SELECTION);

    const quantityState = selectProductForOperation(productSelectionState, product);
    expect(quantityState.controlState).toBe(CONTROL_STATE_QUANTITY_CAPTURE);

    const capturedState = setPendingQuantityText(quantityState, "3");
    const nextState = addPendingSelectionLine(capturedState);

    expect(nextState.controlState).toBe(CONTROL_STATE_CLASS_SELECTION);
    expect(getOperationLineCount(nextState.lines)).toBe(1);
    expect(getOperationTotalUnitsMilli(nextState.lines)).toBe(3000);
    expect(buildOperationCommitLines(nextState.lines)).toEqual([
      { product_id: "product-1", quantity: "3" },
    ]);
  });

  it("merges repeated product captures into one operation line", () => {
    const productClass = buildClass({});
    const product = buildProduct({});
    const firstCaptureState = setPendingQuantityText(
      selectProductForOperation(
        selectClassForOperation(createInitialOperationDraftState(), productClass),
        product,
      ),
      "2",
    );
    const firstLineState = addPendingSelectionLine(firstCaptureState);
    const secondCaptureState = setPendingQuantityText(
      selectProductForOperation(selectClassForOperation(firstLineState, productClass), product),
      "3",
    );
    const nextState = addPendingSelectionLine(secondCaptureState);

    expect(getOperationLineCount(nextState.lines)).toBe(1);
    expect(getOperationTotalUnitsMilli(nextState.lines)).toBe(5000);
    expect(buildOperationCommitLines(nextState.lines)).toEqual([
      { product_id: "product-1", quantity: "5" },
    ]);
  });

  it("backs from quantity capture to product selection", () => {
    const productSelectionState = selectClassForOperation(
      createInitialOperationDraftState(),
      buildClass({}),
    );
    const quantityState = selectProductForOperation(productSelectionState, buildProduct({}));

    const nextState = goBackFromOperationalState(quantityState);
    expect(nextState.controlState).toBe(CONTROL_STATE_PRODUCT_SELECTION);
    expect(nextState.pendingSelection?.product).toBeNull();
  });

  it("derives the draft document state from lines, capture progress, and commit progress", () => {
    expect(
      getOperationDocumentState({
        hasCommittedDocument: false,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 0,
      }),
    ).toBe("NO_LINES_YET");

    expect(
      getOperationDocumentState({
        hasCommittedDocument: false,
        isCaptureInProgress: true,
        isCommitPending: false,
        lineCount: 2,
      }),
    ).toBe("DOCUMENT_BUILDING");

    expect(
      getOperationDocumentState({
        hasCommittedDocument: false,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 2,
      }),
    ).toBe("READY_TO_COMMIT");

    expect(
      getOperationDocumentState({
        hasCommittedDocument: false,
        isCaptureInProgress: false,
        isCommitPending: true,
        lineCount: 2,
      }),
    ).toBe("COMMITTING");

    expect(
      getOperationDocumentState({
        hasCommittedDocument: true,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 0,
      }),
    ).toBe("COMMITTED_SUCCESS");
  });

  it("keeps a stable quantity focus target while the operator edits digits", () => {
    const productClass = buildClass({ id: "class-pan" });
    const product = buildProduct({ id: "product-concha" });

    expect(
      getOperationPendingCaptureTargetKey({
        productClass,
        product: null,
        quantityText: "",
      }),
    ).toBe("class:class-pan");

    expect(
      getOperationPendingCaptureTargetKey({
        productClass,
        product,
        quantityText: "",
      }),
    ).toBe("product:product-concha");

    expect(
      getOperationPendingCaptureTargetKey({
        productClass,
        product,
        quantityText: "12",
      }),
    ).toBe("product:product-concha");
  });

  it("derives waste UI state from traceability, lines, and commit progress", () => {
    expect(
      getWasteDocumentUiState({
        hasCommittedDocument: false,
        hasCommitError: false,
        hasInvalidQuantity: false,
        hasOrigin: false,
        hasReason: false,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 0,
        totalUnitsMilli: 0,
      }),
    ).toBe("TRACEABILITY_INCOMPLETE");

    expect(
      getWasteDocumentUiState({
        hasCommittedDocument: false,
        hasCommitError: false,
        hasInvalidQuantity: false,
        hasOrigin: true,
        hasReason: false,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 0,
        totalUnitsMilli: 0,
      }),
    ).toBe("BLOCKED_MISSING_REASON");

    expect(
      getWasteDocumentUiState({
        hasCommittedDocument: false,
        hasCommitError: false,
        hasInvalidQuantity: false,
        hasOrigin: true,
        hasReason: true,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 0,
        totalUnitsMilli: 0,
      }),
    ).toBe("BLOCKED_NO_LINES");

    expect(
      getWasteDocumentUiState({
        hasCommittedDocument: false,
        hasCommitError: false,
        hasInvalidQuantity: false,
        hasOrigin: true,
        hasReason: true,
        isCaptureInProgress: true,
        isCommitPending: false,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("DOCUMENT_BUILDING");

    expect(
      getWasteDocumentUiState({
        hasCommittedDocument: false,
        hasCommitError: false,
        hasInvalidQuantity: false,
        hasOrigin: true,
        hasReason: true,
        isCaptureInProgress: false,
        isCommitPending: false,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("READY_TO_REGISTER");
  });

  it("reports waste blockers and invalid line quantities canonically", () => {
    const line = {
      key: "product-1",
      productClassCode: "PAN-DULCE",
      productClassId: "class-1",
      productClassName: "Pan dulce",
      productCode: "CONCHA-VAN",
      productId: "product-1",
      productName: "Vanilla Concha",
      quantityMilliUnits: 1000,
      quantityText: "",
    };

    expect(hasOperationInvalidLineQuantity([line])).toBe(true);
    expect(
      getWasteDocumentBlockedReason({
        hasInvalidQuantity: false,
        hasOrigin: false,
        hasReason: true,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("Selecciona un origen para continuar.");
    expect(
      getWasteDocumentBlockedReason({
        additionalBlockingMessages: ["La merma excede el saldo esperado en mostrador."],
        evidenceNoteRequired: true,
        hasEvidenceNote: false,
        hasHighImpactAcknowledgement: false,
        hasInvalidQuantity: true,
        highImpactAcknowledgementRequired: true,
        hasOrigin: true,
        hasReason: true,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("Revisa las cantidades capturadas.");

    expect(
      getWasteDocumentBlockedReason({
        evidenceNoteRequired: true,
        hasEvidenceNote: false,
        hasHighImpactAcknowledgement: true,
        hasInvalidQuantity: false,
        highImpactAcknowledgementRequired: false,
        hasOrigin: true,
        hasReason: true,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("Agrega notas operativas para documentar la evidencia.");

    expect(
      getWasteDocumentBlockedReason({
        evidenceNoteRequired: false,
        hasEvidenceNote: true,
        hasHighImpactAcknowledgement: false,
        hasInvalidQuantity: false,
        highImpactAcknowledgementRequired: true,
        hasOrigin: true,
        hasReason: true,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("Confirma la merma de alto impacto antes de registrar.");

    expect(
      getWasteDocumentBlockedReason({
        additionalBlockingMessages: ["La merma excede el saldo esperado en mostrador."],
        evidenceNoteRequired: false,
        hasEvidenceNote: true,
        hasHighImpactAcknowledgement: true,
        hasInvalidQuantity: false,
        highImpactAcknowledgementRequired: false,
        hasOrigin: true,
        hasReason: true,
        lineCount: 1,
        totalUnitsMilli: 1000,
      }),
    ).toBe("La merma excede el saldo esperado en mostrador.");
  });
});
