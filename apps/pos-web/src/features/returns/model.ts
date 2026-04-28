import type {
  ReturnCommitLineRequest,
  ReturnableSaleLineView,
} from "../../lib/api-contracts";
import {
  formatMoneyFromCents,
  formatQuantityFromMilliUnits,
  parseMoneyToCents,
  parseQuantityToMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";

export const RETURN_DISPOSITION_RESTOCK_COUNTER = "RESTOCK_COUNTER";
export const RETURN_DISPOSITION_RESTOCK_BACKROOM = "RESTOCK_BACKROOM";
export const RETURN_DISPOSITION_SEND_TO_WASTE = "SEND_TO_WASTE";

export interface ReturnDraftLine {
  alreadyReturnedMilliUnits: number;
  captureMode: string;
  dispositionCode: string;
  exactProductId: string;
  exactProductName: string | null;
  exactProductRequired: boolean;
  fixedProductName: string | null;
  key: string;
  lineName: string;
  originalQuantityMilliUnits: number;
  originalSaleLineId: string;
  productClassId: string;
  productClassName: string;
  quantityMilliUnits: number;
  quantityText: string;
  refundUnitPriceCents: number;
  remainingReturnableMilliUnits: number;
  sequence: number;
}

export interface ReturnDraftState {
  highRiskAcknowledged: boolean;
  lines: ReturnDraftLine[];
  notes: string;
  reasonCode: string;
  refundMethodCode: string;
}

export function createInitialReturnDraftState(): ReturnDraftState {
  return {
    highRiskAcknowledged: false,
    lines: [],
    notes: "",
    reasonCode: "",
    refundMethodCode: "",
  };
}

export function addReturnDraftLine(
  lines: ReturnDraftLine[],
  originalLine: ReturnableSaleLineView,
): ReturnDraftLine[] {
  const existingLine = lines.find((line) => line.originalSaleLineId === originalLine.id);
  if (existingLine) {
    return lines;
  }

  return [...lines, buildReturnDraftLine(originalLine)];
}

export function removeReturnDraftLine(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
): ReturnDraftLine[] {
  return lines.filter((line) => line.originalSaleLineId !== originalSaleLineId);
}

export function setReturnDraftLineQuantityText(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
  quantityText: string,
): ReturnDraftLine[] {
  return lines.map((line) =>
    line.originalSaleLineId === originalSaleLineId
      ? {
          ...line,
          quantityText: sanitizeQuantityInput(quantityText),
          quantityMilliUnits:
            parseQuantityToMilliUnits(sanitizeQuantityInput(quantityText)) ?? 0,
        }
      : line,
  );
}

export function incrementReturnDraftLineQuantity(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
): ReturnDraftLine[] {
  return lines.map((line) => {
    if (line.originalSaleLineId !== originalSaleLineId) {
      return line;
    }

    const nextQuantityMilliUnits = Math.min(
      line.quantityMilliUnits + 1000,
      line.remainingReturnableMilliUnits,
    );
    return {
      ...line,
      quantityMilliUnits: nextQuantityMilliUnits,
      quantityText: formatQuantityFromMilliUnits(nextQuantityMilliUnits),
    };
  });
}

export function decrementReturnDraftLineQuantity(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
): ReturnDraftLine[] {
  return lines.map((line) => {
    if (line.originalSaleLineId !== originalSaleLineId) {
      return line;
    }

    const nextQuantityMilliUnits = Math.max(line.quantityMilliUnits - 1000, 1000);
    return {
      ...line,
      quantityMilliUnits: nextQuantityMilliUnits,
      quantityText: formatQuantityFromMilliUnits(nextQuantityMilliUnits),
    };
  });
}

export function setReturnDraftLineDisposition(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
  dispositionCode: string,
): ReturnDraftLine[] {
  return lines.map((line) =>
    line.originalSaleLineId === originalSaleLineId
      ? {
          ...line,
          dispositionCode,
        }
      : line,
  );
}

export function setReturnDraftLineExactProduct(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
  exactProductId: string,
  exactProductName: string | null,
): ReturnDraftLine[] {
  return lines.map((line) =>
    line.originalSaleLineId === originalSaleLineId
      ? {
          ...line,
          exactProductId,
          exactProductName,
        }
      : line,
  );
}

export function getReturnDraftLineRefundCents(line: ReturnDraftLine): number {
  return Math.round((line.quantityMilliUnits * line.refundUnitPriceCents) / 1000);
}

export function getReturnDraftTotalRefundCents(lines: ReturnDraftLine[]): number {
  return lines.reduce((sum, line) => sum + getReturnDraftLineRefundCents(line), 0);
}

export function isReturnDraftLineValid(line: ReturnDraftLine): boolean {
  const quantityMilliUnits = parseQuantityToMilliUnits(line.quantityText);
  if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
    return false;
  }
  if (quantityMilliUnits > line.remainingReturnableMilliUnits) {
    return false;
  }
  if (line.dispositionCode.trim().length === 0) {
    return false;
  }
  if (line.exactProductRequired && line.exactProductId.trim().length === 0) {
    return false;
  }
  return true;
}

export function hasReturnDraftInvalidQuantity(lines: ReturnDraftLine[]): boolean {
  return lines.some((line) => {
    const quantityMilliUnits = parseQuantityToMilliUnits(line.quantityText);
    return (
      quantityMilliUnits === null ||
      quantityMilliUnits <= 0 ||
      quantityMilliUnits > line.remainingReturnableMilliUnits
    );
  });
}

export function hasReturnDraftMissingExactProduct(lines: ReturnDraftLine[]): boolean {
  return lines.some(
    (line) => line.exactProductRequired && line.exactProductId.trim().length === 0,
  );
}

export function hasReturnDraftMissingDisposition(lines: ReturnDraftLine[]): boolean {
  return lines.some((line) => line.dispositionCode.trim().length === 0);
}

export function hasReturnDraftMissingReason(reasonCode: string): boolean {
  return reasonCode.trim().length === 0;
}

export function hasReturnDraftMissingRefundMethod(refundMethodCode: string): boolean {
  return refundMethodCode.trim().length === 0;
}

export function getReturnDraftBlockingMessages(
  {
    additionalBlockingMessages = [],
    hasHighRiskAcknowledgement = true,
    hasSelectedSale,
    highRiskAcknowledgementRequired = false,
    lines,
    reasonCode,
    refundMethodCode,
  }: {
    additionalBlockingMessages?: string[];
    hasHighRiskAcknowledgement?: boolean;
    hasSelectedSale: boolean;
    highRiskAcknowledgementRequired?: boolean;
    lines: ReturnDraftLine[];
    reasonCode: string;
    refundMethodCode: string;
  },
): string[] {
  if (!hasSelectedSale) {
    return ["Selecciona una venta original."];
  }

  if (lines.length === 0) {
    return ["Agrega al menos una linea al borrador."];
  }

  const messages: string[] = [];
  if (hasReturnDraftInvalidQuantity(lines)) {
    messages.push("Revisa las cantidades de devolucion.");
  }
  if (hasReturnDraftMissingExactProduct(lines)) {
    messages.push("Selecciona el producto exacto requerido.");
  }
  if (hasReturnDraftMissingDisposition(lines)) {
    messages.push("Define el destino fisico de cada linea.");
  }
  if (hasReturnDraftMissingReason(reasonCode)) {
    messages.push("Selecciona un motivo para continuar.");
  }
  if (hasReturnDraftMissingRefundMethod(refundMethodCode)) {
    messages.push("Selecciona el metodo de reembolso.");
  }
  if (highRiskAcknowledgementRequired && !hasHighRiskAcknowledgement) {
    messages.push("Confirma la devolucion de alto riesgo antes de registrarla.");
  }
  if (additionalBlockingMessages.length > 0) {
    messages.push(...additionalBlockingMessages);
  }
  return messages;
}

export function getReturnDraftBlockedReason(
  {
    additionalBlockingMessages,
    hasHighRiskAcknowledgement,
    hasSelectedSale,
    highRiskAcknowledgementRequired,
    lines,
    reasonCode,
    refundMethodCode,
  }: {
    additionalBlockingMessages?: string[];
    hasHighRiskAcknowledgement?: boolean;
    hasSelectedSale: boolean;
    highRiskAcknowledgementRequired?: boolean;
    lines: ReturnDraftLine[];
    reasonCode: string;
    refundMethodCode: string;
  },
): string | null {
  return (
    getReturnDraftBlockingMessages({
      additionalBlockingMessages,
      hasHighRiskAcknowledgement,
      hasSelectedSale,
      highRiskAcknowledgementRequired,
      lines,
      reasonCode,
      refundMethodCode,
    })[0] ?? null
  );
}

export function buildReturnCommitLines(
  lines: ReturnDraftLine[],
): ReturnCommitLineRequest[] {
  if (lines.length === 0) {
    throw new Error("Selecciona al menos una linea para devolver.");
  }

  return lines.map((line) => {
    const quantityMilliUnits = parseQuantityToMilliUnits(line.quantityText);
    if (quantityMilliUnits === null || quantityMilliUnits <= 0) {
      throw new Error("Captura una cantidad valida para cada linea seleccionada.");
    }
    if (quantityMilliUnits > line.remainingReturnableMilliUnits) {
      throw new Error("La cantidad a devolver supera lo que aun se puede devolver.");
    }
    if (line.dispositionCode.trim().length === 0) {
      throw new Error("Define el destino fisico de cada linea.");
    }
    if (line.exactProductRequired && line.exactProductId.trim().length === 0) {
      throw new Error("Selecciona el producto exacto para las ventas por clase.");
    }

    return {
      original_sale_line_id: line.originalSaleLineId,
      returned_quantity: formatQuantityFromMilliUnits(quantityMilliUnits),
      disposition_code: line.dispositionCode,
      exact_product_id: line.exactProductRequired ? line.exactProductId : undefined,
    };
  });
}

export function getReturnLineCount(lines: ReturnDraftLine[]): number {
  return lines.length;
}

export function getReturnTotalUnitsMilli(lines: ReturnDraftLine[]): number {
  return lines.reduce((sum, line) => sum + line.quantityMilliUnits, 0);
}

function buildReturnDraftLine(originalLine: ReturnableSaleLineView): ReturnDraftLine {
  const refundUnitPriceCents = parseMoneyToCents(String(originalLine.unit_price));
  if (refundUnitPriceCents === null) {
    throw new Error("No fue posible interpretar el precio de la linea original.");
  }

  const remainingReturnableMilliUnits = parseQuantityToMilliUnits(
    String(originalLine.remaining_returnable_quantity),
  );
  const originalQuantityMilliUnits = parseQuantityToMilliUnitsAllowZero(String(originalLine.quantity));
  const alreadyReturnedMilliUnits = parseQuantityToMilliUnitsAllowZero(
    String(originalLine.already_returned_quantity),
  );

  if (
    remainingReturnableMilliUnits === null ||
    originalQuantityMilliUnits === null ||
    alreadyReturnedMilliUnits === null
  ) {
    throw new Error("No fue posible interpretar las cantidades de la linea original.");
  }

  return {
    alreadyReturnedMilliUnits,
    captureMode: originalLine.capture_mode,
    dispositionCode: "",
    exactProductId: "",
    exactProductName: null,
    exactProductRequired: originalLine.requires_exact_product_selection,
    fixedProductName: originalLine.product_name ?? null,
    key: originalLine.id,
    lineName: originalLine.catalog_name_snapshot,
    originalQuantityMilliUnits,
    originalSaleLineId: originalLine.id,
    productClassId: originalLine.product_class_id,
    productClassName: originalLine.product_class_name,
    quantityMilliUnits: remainingReturnableMilliUnits,
    quantityText: formatQuantityFromMilliUnits(remainingReturnableMilliUnits),
    refundUnitPriceCents,
    remainingReturnableMilliUnits,
    sequence: originalLine.sequence,
  };
}

export function formatReturnMoney(cents: number): string {
  return formatMoneyFromCents(cents);
}

function parseQuantityToMilliUnitsAllowZero(value: string): number | null {
  const normalizedValue = value.trim();
  if (!/^\d+(\.\d+)?$/.test(normalizedValue)) {
    return null;
  }

  const [wholePart, decimalPart = ""] = normalizedValue.split(".");
  if (decimalPart.length > 3) {
    return null;
  }

  const paddedDecimalPart = decimalPart.padEnd(3, "0");
  return Number.parseInt(wholePart, 10) * 1000 + Number.parseInt(paddedDecimalPart, 10);
}
