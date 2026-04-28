import { describe, expect, it } from "vitest";

import type { ReturnableSaleLineView } from "../../lib/api-contracts";
import {
  addReturnDraftLine,
  buildReturnCommitLines,
  getReturnDraftBlockingMessages,
  getReturnDraftTotalRefundCents,
  hasReturnDraftMissingRefundMethod,
  hasReturnDraftMissingReason,
  isReturnDraftLineValid,
  setReturnDraftLineDisposition,
  setReturnDraftLineExactProduct,
  setReturnDraftLineQuantityText,
} from "./model";

const classCaptureLine: ReturnableSaleLineView = {
  already_returned_quantity: "0.000",
  capture_mode: "CLASS_CAPTURE",
  catalog_code_snapshot: "PAN-DULCE",
  catalog_name_snapshot: "Pan dulce",
  id: "sale-line-class",
  line_total_amount: "24.00",
  product_class_code: "PAN-DULCE",
  product_class_id: "class-pan-dulce",
  product_class_name: "Pan dulce",
  product_code: null,
  product_id: null,
  product_name: null,
  quantity: "2.000",
  remaining_returnable_quantity: "2.000",
  requires_exact_product_selection: true,
  sequence: 1,
  unit_price: "12.00",
};

const productDirectLine: ReturnableSaleLineView = {
  already_returned_quantity: "0.000",
  capture_mode: "PRODUCT_DIRECT",
  catalog_code_snapshot: "COCA-355",
  catalog_name_snapshot: "Coca-Cola 355 ml",
  id: "sale-line-direct",
  line_total_amount: "18.00",
  product_class_code: "BEBIDAS",
  product_class_id: "class-bebidas",
  product_class_name: "Bebidas",
  product_code: "COCA-355",
  product_id: "product-coca",
  product_name: "Coca-Cola 355 ml",
  quantity: "1.000",
  remaining_returnable_quantity: "1.000",
  requires_exact_product_selection: false,
  sequence: 2,
  unit_price: "18.00",
};

describe("returns model", () => {
  it("creates draft lines with full remaining quantity and computes refund total", () => {
    const draftLines = addReturnDraftLine([], classCaptureLine);
    const mixedLines = addReturnDraftLine(draftLines, productDirectLine);

    expect(mixedLines).toHaveLength(2);
    expect(mixedLines[0]?.quantityText).toBe("2");
    expect(getReturnDraftTotalRefundCents(mixedLines)).toBe(4200);
  });

  it("requires exact product for class-capture return lines", () => {
    const [draftLine] = addReturnDraftLine([], classCaptureLine);
    expect(isReturnDraftLineValid(draftLine!)).toBe(false);

    const linesWithExactProduct = setReturnDraftLineExactProduct(
      [draftLine!],
      draftLine!.originalSaleLineId,
      "product-concha-van",
      "Vanilla Concha",
    );
    expect(isReturnDraftLineValid(linesWithExactProduct[0]!)).toBe(false);

    const linesReadyToCommit = setReturnDraftLineDisposition(
      linesWithExactProduct,
      draftLine!.originalSaleLineId,
      "RESTOCK_COUNTER",
    );
    expect(isReturnDraftLineValid(linesReadyToCommit[0]!)).toBe(true);
  });

  it("builds commit payload and blocks over-return in the draft", () => {
    const draftLines = setReturnDraftLineQuantityText(
      addReturnDraftLine([], productDirectLine),
      productDirectLine.id,
      "1.5",
    );

    expect(isReturnDraftLineValid(draftLines[0]!)).toBe(false);
    expect(() => buildReturnCommitLines(draftLines)).toThrow(/supera/i);

    const correctedLines = setReturnDraftLineDisposition(
      setReturnDraftLineQuantityText(draftLines, productDirectLine.id, "1"),
      productDirectLine.id,
      "RESTOCK_COUNTER",
    );
    expect(buildReturnCommitLines(correctedLines)).toEqual([
      {
        disposition_code: "RESTOCK_COUNTER",
        exact_product_id: undefined,
        original_sale_line_id: "sale-line-direct",
        returned_quantity: "1",
      },
    ]);
  });

  it("reports blocking reasons before commit", () => {
    expect(
      getReturnDraftBlockingMessages({
        hasSelectedSale: false,
        lines: [],
        reasonCode: "",
        refundMethodCode: "",
      }),
    ).toEqual([
      "Selecciona una venta original.",
    ]);

    const [draftLine] = addReturnDraftLine([], classCaptureLine);
    expect(
      getReturnDraftBlockingMessages({
        hasSelectedSale: true,
        lines: [draftLine!],
        reasonCode: "",
        refundMethodCode: "",
      }),
    ).toEqual([
      "Selecciona el producto exacto requerido.",
      "Define el destino fisico de cada linea.",
      "Selecciona un motivo para continuar.",
      "Selecciona el metodo de reembolso.",
    ]);
  });

  it("tracks missing reason, refund method, and high-risk acknowledgement", () => {
    expect(hasReturnDraftMissingReason("")).toBe(true);
    expect(hasReturnDraftMissingRefundMethod("")).toBe(true);
    expect(
      getReturnDraftBlockingMessages({
        hasHighRiskAcknowledgement: false,
        hasSelectedSale: true,
        highRiskAcknowledgementRequired: true,
        lines: addReturnDraftLine([], productDirectLine),
        reasonCode: "WRONG_ITEM",
        refundMethodCode: "CASH",
      }),
    ).toContain("Confirma la devolucion de alto riesgo antes de registrarla.");
  });
});
