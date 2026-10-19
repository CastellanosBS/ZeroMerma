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
  setReturnDraftLineAllocations,
  setReturnDraftLineDisposition,
  setReturnDraftLineExactProduct,
  setReturnDraftLineQuantityText,
} from "./model";

const classCaptureLine: ReturnableSaleLineView = {
  already_returned_quantity: "0.000",
  already_refunded_amount: "0.00",
  capture_mode: "CLASS_CAPTURE",
  catalog_code_snapshot: "PAN-DULCE",
  catalog_name_snapshot: "Pan dulce",
  id: "sale-line-class",
  line_total_amount: "24.00",
  remaining_refundable_amount: "24.00",
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
  already_refunded_amount: "0.00",
  capture_mode: "PRODUCT_DIRECT",
  catalog_code_snapshot: "COCA-355",
  catalog_name_snapshot: "Coca-Cola 355 ml",
  id: "sale-line-direct",
  line_total_amount: "18.00",
  remaining_refundable_amount: "18.00",
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
  it("splits physical dispositions without multiplying the economic refund", () => {
    const [line] = addReturnDraftLine([], productDirectLine);
    const split = setReturnDraftLineAllocations([line!], line!.originalSaleLineId, [
      { ...line!.allocations[0]!, quantityText: "0.4" },
      {
        ...line!.allocations[0]!,
        key: "second",
        quantityText: "0.6",
        disposition_code: "SEND_TO_WASTE",
      },
    ]);
    expect(getReturnDraftTotalRefundCents(split)).toBe(1800);
    expect(buildReturnCommitLines(split)[0]?.allocations.map((item) => item.quantity)).toEqual([
      "0.4",
      "0.6",
    ]);
    const mismatch = setReturnDraftLineQuantityText(split, line!.originalSaleLineId, "0.5");
    expect(isReturnDraftLineValid(mismatch[0]!)).toBe(false);
    expect(() => buildReturnCommitLines(mismatch)).toThrow(/sumar/);
  });

  it("requires the original lot and inspection for restock but accepts unidentified quarantine", () => {
    const [line] = addReturnDraftLine([], {
      ...productDirectLine,
      physical_options: [
        {
          product_id: "product-coca",
          product_code: "COCA-355",
          product_name: "Coca-Cola",
          lot_id: "original-lot",
          lot_code: "LOT-1",
          expires_at: "2026-12-01T00:00:00Z",
          remaining_quantity: "1",
          is_inventory_tracked: true,
          lot_tracking_enabled: true,
        },
      ],
    });
    expect(isReturnDraftLineValid(line!)).toBe(true);
    const restock = setReturnDraftLineAllocations([line!], line!.originalSaleLineId, [
      {
        ...line!.allocations[0]!,
        disposition_code: "RESTOCK_COUNTER",
        restock_safe_acknowledged: true,
      },
    ]);
    expect(isReturnDraftLineValid(restock[0]!)).toBe(false);
    const identified = setReturnDraftLineAllocations(restock, line!.originalSaleLineId, [
      {
        ...restock[0]!.allocations[0]!,
        lot_id: "original-lot",
      },
    ]);
    expect(isReturnDraftLineValid(identified[0]!)).toBe(true);
  });
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
    );
    expect(isReturnDraftLineValid(linesWithExactProduct[0]!)).toBe(true);

    const linesReadyToCommit = setReturnDraftLineDisposition(
      linesWithExactProduct,
      draftLine!.originalSaleLineId,
      "RESTOCK_COUNTER",
    );
    expect(isReturnDraftLineValid(linesReadyToCommit[0]!)).toBe(false);
    const inspected = setReturnDraftLineAllocations(
      linesReadyToCommit,
      draftLine!.originalSaleLineId,
      linesReadyToCommit[0]!.allocations.map((allocation) => ({
        ...allocation,
        restock_safe_acknowledged: true,
      })),
    );
    expect(isReturnDraftLineValid(inspected[0]!)).toBe(true);
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
      "QUARANTINE",
    );
    expect(buildReturnCommitLines(correctedLines)).toEqual([
      {
        allocations: [
          {
            exact_product_id: "product-coca",
            quantity: "1",
            disposition_code: "QUARANTINE",
            lot_id: null,
            restock_safe_acknowledged: false,
          },
        ],
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
    ).toEqual(["Selecciona una venta original."]);

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

it.each([
  ["0.000", "0.00", "0.05", "1", 2],
  ["1.000", "0.02", "0.03", "1", 1],
  ["2.000", "0.03", "0.02", "1", 2],
])(
  "allocates cumulative HALF_UP refunds and exhausts the final balance (%s)",
  (returned, refunded, remaining, quantity, expected) => {
    const source = {
      ...productDirectLine,
      quantity: "3.000",
      line_total_amount: "0.05",
      unit_price: "0.02",
      already_returned_quantity: returned,
      already_refunded_amount: refunded,
      remaining_refundable_amount: remaining,
      remaining_returnable_quantity: String(3 - Number(returned)),
    };
    const lines = setReturnDraftLineQuantityText(
      addReturnDraftLine([], source),
      source.id,
      quantity,
    );
    expect(getReturnDraftTotalRefundCents(lines)).toBe(expected);
  },
);
it("uses exact integer multiplication for large fractional allocations", () => {
  const source = {
    ...productDirectLine,
    quantity: "999999999.999",
    remaining_returnable_quantity: "999999999.999",
    line_total_amount: "999999999.99",
    remaining_refundable_amount: "999999999.99",
  };
  const lines = setReturnDraftLineQuantityText(
    addReturnDraftLine([], source),
    source.id,
    "500000000.001",
  );
  expect(getReturnDraftTotalRefundCents(lines)).toBe(50000000000);
});
it("refunds the paid line total including discounts rather than the original unit price", () => {
  const source = {
    ...productDirectLine,
    quantity: "3.000",
    remaining_returnable_quantity: "3.000",
    line_total_amount: "27.00",
    remaining_refundable_amount: "27.00",
    unit_price: "12.00",
  };
  const lines = setReturnDraftLineQuantityText(addReturnDraftLine([], source), source.id, "1");
  expect(getReturnDraftTotalRefundCents(lines)).toBe(900);
});

it.each(["0.00", "1.00"])(
  "preserves a valid zero refund balance for a fractional line priced at %s",
  (unitPrice) => {
    const source = {
      ...productDirectLine,
      quantity: "0.001",
      remaining_returnable_quantity: "0.001",
      line_total_amount: "0.00",
      remaining_refundable_amount: "0.00",
      unit_price: unitPrice,
    };
    expect(getReturnDraftTotalRefundCents(addReturnDraftLine([], source))).toBe(0);
  },
);
