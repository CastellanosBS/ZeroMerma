import type { components } from "@zeromerma/api-client";
import type { ReturnCommitLineRequest, ReturnableSaleLineView } from "../../lib/api-contracts";
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
export const RETURN_DISPOSITION_QUARANTINE = "QUARANTINE";

export type ReturnAllocationDraft = Omit<
  components["schemas"]["ReturnDispositionAllocationRequest"],
  "quantity"
> & { key: string; quantityText: string };

export interface ReturnDraftLine {
  alreadyReturnedMilliUnits: number;
  alreadyRefundedCents: number;
  originalLineTotalCents: number;
  remainingRefundableCents: number;
  captureMode: string;
  allocations: ReturnAllocationDraft[];
  physicalOptions: NonNullable<ReturnableSaleLineView["physical_options"]>;
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
          quantityMilliUnits: parseQuantityToMilliUnits(sanitizeQuantityInput(quantityText)) ?? 0,
          allocations:
            line.allocations.length === 1
              ? [{ ...line.allocations[0]!, quantityText: sanitizeQuantityInput(quantityText) }]
              : line.allocations,
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
      allocations:
        line.allocations.length === 1
          ? [
              {
                ...line.allocations[0]!,
                quantityText: formatQuantityFromMilliUnits(nextQuantityMilliUnits),
              },
            ]
          : line.allocations,
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
      allocations:
        line.allocations.length === 1
          ? [
              {
                ...line.allocations[0]!,
                quantityText: formatQuantityFromMilliUnits(nextQuantityMilliUnits),
              },
            ]
          : line.allocations,
    };
  });
}

export function setReturnDraftLineAllocations(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
  allocations: ReturnAllocationDraft[],
): ReturnDraftLine[] {
  return lines.map((line) =>
    line.originalSaleLineId === originalSaleLineId ? { ...line, allocations } : line,
  );
}

export function setReturnDraftLineDisposition(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
  dispositionCode: ReturnAllocationDraft["disposition_code"],
): ReturnDraftLine[] {
  return lines.map((line) =>
    line.originalSaleLineId === originalSaleLineId
      ? {
          ...line,
          allocations: line.allocations.map((allocation) => ({
            ...allocation,
            disposition_code: dispositionCode,
            restock_safe_acknowledged: false,
          })),
        }
      : line,
  );
}

export function setReturnDraftLineExactProduct(
  lines: ReturnDraftLine[],
  originalSaleLineId: string,
  exactProductId: string,
): ReturnDraftLine[] {
  return lines.map((line) =>
    line.originalSaleLineId === originalSaleLineId
      ? {
          ...line,
          allocations: line.allocations.map((allocation) => ({
            ...allocation,
            exact_product_id: exactProductId,
            lot_id: null,
            restock_safe_acknowledged: false,
          })),
        }
      : line,
  );
}

export function getReturnAllocationError(line: ReturnDraftLine): string | null {
  let allocated = 0;
  for (const allocation of line.allocations) {
    const quantity = parseQuantityToMilliUnits(allocation.quantityText);
    if (quantity === null || quantity <= 0)
      return "Captura una cantidad valida en cada disposicion.";
    allocated += quantity;
    if (!allocation.exact_product_id) return "Selecciona el producto exacto requerido.";
    if (!allocation.disposition_code) return "Define el destino fisico de cada disposicion.";
    const options = line.physicalOptions.filter(
      (option) => option.product_id === allocation.exact_product_id,
    );
    const restock = ["RESTOCK_COUNTER", "RESTOCK_BACKROOM"].includes(allocation.disposition_code);
    if (restock && !allocation.restock_safe_acknowledged)
      return "Confirma la inspeccion del producto antes de reponerlo.";
    if (restock && options.some((option) => option.lot_tracking_enabled) && !allocation.lot_id)
      return "Identifica el lote original antes de reponer el producto.";
    if (
      allocation.disposition_code === "NO_STOCK" &&
      !options.some((option) => !option.is_inventory_tracked)
    )
      return "Sin inventario solo aplica a productos no inventariables.";
  }
  return allocated === line.quantityMilliUnits
    ? null
    : "Las disposiciones deben sumar la cantidad a devolver.";
}

export function getReturnDraftLineRefundCents(line: ReturnDraftLine): number {
  if (line.quantityMilliUnits <= 0 || line.originalQuantityMilliUnits <= 0) return 0;
  const cumulativeQuantity = Math.min(
    line.originalQuantityMilliUnits,
    line.alreadyReturnedMilliUnits + line.quantityMilliUnits,
  );
  if (cumulativeQuantity === line.originalQuantityMilliUnits) return line.remainingRefundableCents;
  // Calculate positive HALF_UP cumulative entitlement without binary floating-point products.
  const numerator = BigInt(line.originalLineTotalCents) * BigInt(cumulativeQuantity);
  const denominator = BigInt(line.originalQuantityMilliUnits);
  const cumulativeCents = (2n * numerator + denominator) / (2n * denominator);
  return Math.max(
    0,
    Math.min(line.remainingRefundableCents, Number(cumulativeCents) - line.alreadyRefundedCents),
  );
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
  return getReturnAllocationError(line) === null;
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
  return lines.some((line) => line.allocations.some((allocation) => !allocation.exact_product_id));
}

export function hasReturnDraftMissingDisposition(lines: ReturnDraftLine[]): boolean {
  return lines.some((line) => line.allocations.some((allocation) => !allocation.disposition_code));
}

export function hasReturnDraftMissingReason(reasonCode: string): boolean {
  return reasonCode.trim().length === 0;
}

export function hasReturnDraftMissingRefundMethod(refundMethodCode: string): boolean {
  return refundMethodCode.trim().length === 0;
}

export function getReturnDraftBlockingMessages({
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
}): string[] {
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
  const allocationError = lines.map(getReturnAllocationError).find(Boolean);
  if (allocationError && !messages.includes(allocationError)) messages.push(allocationError);
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

export function getReturnDraftBlockedReason({
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
}): string | null {
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

export function buildReturnCommitLines(lines: ReturnDraftLine[]): ReturnCommitLineRequest[] {
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
    const allocationError = getReturnAllocationError(line);
    if (allocationError) throw new Error(allocationError);
    return {
      original_sale_line_id: line.originalSaleLineId,
      returned_quantity: formatQuantityFromMilliUnits(quantityMilliUnits),
      allocations: line.allocations.map((allocation) => ({
        exact_product_id: allocation.exact_product_id,
        disposition_code: allocation.disposition_code,
        lot_id: allocation.lot_id,
        restock_safe_acknowledged: allocation.restock_safe_acknowledged,
        quantity: formatQuantityFromMilliUnits(parseQuantityToMilliUnits(allocation.quantityText)!),
      })),
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
  const refundUnitPriceCents = parseRefundBalanceCents(String(originalLine.unit_price));
  if (refundUnitPriceCents === null) {
    throw new Error("No fue posible interpretar el precio de la linea original.");
  }

  const originalLineTotalCents = parseRefundBalanceCents(String(originalLine.line_total_amount));
  const alreadyRefundedCents = parseRefundBalanceCents(
    String(originalLine.already_refunded_amount),
  );
  const remainingRefundableCents = parseRefundBalanceCents(
    String(originalLine.remaining_refundable_amount),
  );
  if (
    originalLineTotalCents === null ||
    alreadyRefundedCents === null ||
    remainingRefundableCents === null
  ) {
    throw new Error("No fue posible interpretar el saldo de reembolso de la linea original.");
  }
  const remainingReturnableMilliUnits = parseQuantityToMilliUnits(
    String(originalLine.remaining_returnable_quantity),
  );
  const originalQuantityMilliUnits = parseQuantityToMilliUnitsAllowZero(
    String(originalLine.quantity),
  );
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
    alreadyRefundedCents,
    originalLineTotalCents,
    remainingRefundableCents,
    captureMode: originalLine.capture_mode,
    allocations: [
      {
        key: crypto.randomUUID(),
        exact_product_id: originalLine.product_id ?? "",
        quantityText: formatQuantityFromMilliUnits(remainingReturnableMilliUnits),
        disposition_code: "QUARANTINE",
        lot_id: null,
        restock_safe_acknowledged: false,
      },
    ],
    physicalOptions: originalLine.physical_options ?? [],
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

function parseRefundBalanceCents(value: string): number | null {
  return /^0+(\.0{1,2})?$/.test(value.trim()) ? 0 : parseMoneyToCents(value);
}
