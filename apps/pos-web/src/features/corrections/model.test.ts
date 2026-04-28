import { describe, expect, it } from "vitest";

import {
  addProductDraft,
  addTargetLineDraft,
  buildCorrectionCommitLines,
  getCorrectionDraftBlockedReason,
  getCorrectionDraftLineDirection,
  getCorrectionDraftLineMagnitudeText,
  getCorrectionDraftNetQuantityMilliUnits,
  getCorrectionDraftTotalAdjustedQuantityMilliUnits,
  parseSignedQuantityToMilliUnits,
  sanitizeSignedQuantityInput,
  setCorrectionDraftLineDirection,
  setCorrectionDraftLineMagnitudeText,
  type CorrectionDraftLine,
} from "./model";

describe("corrections model", () => {
  it("sanitizes and parses signed quantities", () => {
    expect(sanitizeSignedQuantityInput(" -1a.2349 ")).toBe("-1.234");
    expect(parseSignedQuantityToMilliUnits("-1.25")).toBe(-1250);
    expect(parseSignedQuantityToMilliUnits("+2")).toBe(2000);
    expect(parseSignedQuantityToMilliUnits("0")).toBeNull();
  });

  it("maps direction and magnitude safely for the draft row UI", () => {
    const targetLines = addTargetLineDraft([], {
      id: "line-1",
      line_number: 1,
      product_id: "product-1",
      product_code_snapshot: "BOLILLO-STD",
      product_name_snapshot: "Bolillo estandar",
      product_class_id: "class-1",
      product_class_code_snapshot: "BOLILLO",
      product_class_name_snapshot: "Bolillo",
      quantity: "3.000",
      expected_quantity: null,
      received_quantity: null,
      unit_of_measure_code: "EACH",
      variance_reason: null,
      notes: null,
    });

    expect(getCorrectionDraftLineDirection(targetLines[0])).toBe("DECREASE");
    expect(getCorrectionDraftLineMagnitudeText(targetLines[0])).toBe("1");

    const increased = setCorrectionDraftLineDirection(targetLines, targetLines[0].key, "INCREASE");
    expect(increased[0].deltaQuantityText).toBe("1");

    const edited = setCorrectionDraftLineMagnitudeText(increased, increased[0].key, "2.5");
    expect(edited[0].deltaQuantityText).toBe("2.5");
    expect(getCorrectionDraftLineDirection(edited[0])).toBe("INCREASE");
    expect(getCorrectionDraftLineMagnitudeText(edited[0])).toBe("2.5");
  });

  it("returns the first visible blocker reason for the draft", () => {
    expect(
      getCorrectionDraftBlockedReason({
        correctedDestinationBranchId: null,
        hasSelectedTarget: false,
        isCorrectable: false,
        lines: [],
        reasonAllowsDestinationCorrection: false,
        reasonCode: "",
      }),
    ).toBe("Selecciona un documento original.");

    expect(
      getCorrectionDraftBlockedReason({
        correctedDestinationBranchId: null,
        hasSelectedTarget: true,
        isCorrectable: false,
        lines: [],
        reasonAllowsDestinationCorrection: false,
        reasonCode: "",
      }),
    ).toBe("Este documento ya no admite correcciones.");

    const lines: CorrectionDraftLine[] = [
      {
        key: "target:line-1",
        lineNumber: 1,
        notes: "",
        productClassCode: "BOLILLO",
        productClassId: "class-1",
        productClassName: "Bolillo",
        productCode: "BOLILLO-STD",
        productId: "product-1",
        productName: "Bolillo estandar",
        sourceKind: "TARGET_LINE",
        targetLineId: "line-1",
        deltaQuantityText: "0",
      },
    ];

    expect(
      getCorrectionDraftBlockedReason({
        correctedDestinationBranchId: null,
        hasSelectedTarget: true,
        isCorrectable: true,
        lines,
        reasonAllowsDestinationCorrection: false,
        reasonCode: "",
      }),
    ).toBe("Revisa cantidades y direccion del ajuste.");

    expect(
      getCorrectionDraftBlockedReason({
        hasHighImpactAcknowledgement: false,
        correctedDestinationBranchId: null,
        hasSelectedTarget: true,
        highImpactAcknowledgementRequired: true,
        isCorrectable: true,
        lines: [{ ...lines[0], deltaQuantityText: "-1" }],
        reasonAllowsDestinationCorrection: false,
        reasonCode: "",
      }),
    ).toBe("Selecciona un motivo para continuar.");

    expect(
      getCorrectionDraftBlockedReason({
        correctedDestinationBranchId: null,
        hasHighImpactAcknowledgement: false,
        hasSelectedTarget: true,
        highImpactAcknowledgementRequired: true,
        isCorrectable: true,
        lines: [{ ...lines[0], deltaQuantityText: "-1" }],
        reasonAllowsDestinationCorrection: false,
        reasonCode: "WRONG_QUANTITY",
      }),
    ).toBe("Confirma el ajuste de alto impacto antes de registrarlo.");
  });

  it("builds commit payload with target and added-product lines", () => {
    const targetLines = addTargetLineDraft([], {
      id: "line-1",
      line_number: 1,
      product_id: "product-1",
      product_code_snapshot: "BOLILLO-STD",
      product_name_snapshot: "Bolillo estandar",
      product_class_id: "class-1",
      product_class_code_snapshot: "BOLILLO",
      product_class_name_snapshot: "Bolillo",
      quantity: "3.000",
      expected_quantity: null,
      received_quantity: null,
      unit_of_measure_code: "EACH",
      variance_reason: null,
      notes: null,
    });

    const draftLines: CorrectionDraftLine[] = addProductDraft(targetLines, {
      id: "product-2",
      code: "CONCHA-VAN",
      name: "Concha vainilla",
      quick_name: null,
      product_class_id: "class-2",
      product_class_code: "PAN-DULCE",
      product_class_name: "Pan dulce",
      display_order: 10,
    }).map((line) =>
      line.key === "product:product-2"
        ? {
            ...line,
            deltaQuantityText: "1.5",
          }
        : {
            ...line,
            deltaQuantityText: "-2",
          },
    );

    const payload = buildCorrectionCommitLines(draftLines);
    expect(payload).toEqual([
      {
        target_line_id: "line-1",
        product_id: "product-1",
        delta_quantity: "-2",
        notes: undefined,
      },
      {
        target_line_id: undefined,
        product_id: "product-2",
        delta_quantity: "1.5",
        notes: undefined,
      },
    ]);
    expect(getCorrectionDraftNetQuantityMilliUnits(draftLines)).toBe(-500);
    expect(getCorrectionDraftTotalAdjustedQuantityMilliUnits(draftLines)).toBe(3500);
  });
});
