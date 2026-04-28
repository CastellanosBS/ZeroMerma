import type {
  CorrectionCommitLineRequest,
  CorrectionProductOptionView,
  OperationDocumentLineView,
} from "../../lib/api-contracts";
import {
  formatQuantityFromMilliUnits,
  sanitizeQuantityInput,
} from "../pos-terminal/model";

export type CorrectionDirection = "INCREASE" | "DECREASE";

export interface CorrectionDraftLine {
  key: string;
  lineNumber: number | null;
  notes: string;
  productClassCode: string;
  productClassId: string;
  productClassName: string;
  productCode: string;
  productId: string;
  productName: string;
  sourceKind: "TARGET_LINE" | "ADDED_PRODUCT";
  targetLineId: string | null;
  deltaQuantityText: string;
}

export interface CorrectionDraftState {
  correctedDestinationBranchId: string | null;
  lines: CorrectionDraftLine[];
  notes: string;
  productSearchText: string;
  reasonCode: string;
}

export function createInitialCorrectionDraftState(): CorrectionDraftState {
  return {
    correctedDestinationBranchId: null,
    lines: [],
    notes: "",
    productSearchText: "",
    reasonCode: "",
  };
}

export function addTargetLineDraft(
  lines: CorrectionDraftLine[],
  line: OperationDocumentLineView,
): CorrectionDraftLine[] {
  const key = buildTargetLineKey(line.id);
  if (lines.some((draftLine) => draftLine.key === key)) {
    return lines;
  }

  return [
    ...lines,
    {
      key,
      lineNumber: line.line_number,
      notes: "",
      productClassCode: line.product_class_code_snapshot,
      productClassId: line.product_class_id,
      productClassName: line.product_class_name_snapshot,
      productCode: line.product_code_snapshot,
      productId: line.product_id,
      productName: line.product_name_snapshot,
      sourceKind: "TARGET_LINE",
      targetLineId: line.id,
      deltaQuantityText: "-1",
    },
  ];
}

export function upsertTargetLineDraftAdjustment(
  lines: CorrectionDraftLine[],
  line: OperationDocumentLineView,
  direction: CorrectionDirection,
  magnitudeText: string,
): CorrectionDraftLine[] {
  const key = buildTargetLineKey(line.id);
  const nextLines = lines.some((draftLine) => draftLine.key === key)
    ? lines
    : addTargetLineDraft(lines, line);

  return setCorrectionDraftLineMagnitudeText(
    setCorrectionDraftLineDirection(nextLines, key, direction),
    key,
    magnitudeText,
  );
}

export function addProductDraft(
  lines: CorrectionDraftLine[],
  product: CorrectionProductOptionView,
): CorrectionDraftLine[] {
  const key = buildProductKey(product.id);
  if (lines.some((draftLine) => draftLine.key === key)) {
    return lines;
  }

  return [
    ...lines,
    {
      key,
      lineNumber: null,
      notes: "",
      productClassCode: product.product_class_code,
      productClassId: product.product_class_id,
      productClassName: product.product_class_name,
      productCode: product.code,
      productId: product.id,
      productName: product.name,
      sourceKind: "ADDED_PRODUCT",
      targetLineId: null,
      deltaQuantityText: "1",
    },
  ];
}

export function upsertAddedProductDraftAdjustment(
  lines: CorrectionDraftLine[],
  product: CorrectionProductOptionView,
  magnitudeText: string,
): CorrectionDraftLine[] {
  const nextLines = addProductDraft(lines, product);
  return setCorrectionDraftLineMagnitudeText(nextLines, buildProductKey(product.id), magnitudeText);
}

export function removeCorrectionDraftLine(
  lines: CorrectionDraftLine[],
  draftLineKey: string,
): CorrectionDraftLine[] {
  return lines.filter((line) => line.key !== draftLineKey);
}

export function setCorrectionDraftLineDirection(
  lines: CorrectionDraftLine[],
  draftLineKey: string,
  direction: CorrectionDirection,
): CorrectionDraftLine[] {
  return lines.map((line) =>
    line.key === draftLineKey
      ? {
          ...line,
          deltaQuantityText: buildSignedQuantityText(
            direction,
            getCorrectionDraftLineMagnitudeText(line),
          ),
        }
      : line,
  );
}

export function setCorrectionDraftLineMagnitudeText(
  lines: CorrectionDraftLine[],
  draftLineKey: string,
  value: string,
): CorrectionDraftLine[] {
  return lines.map((line) =>
    line.key === draftLineKey
      ? {
          ...line,
          deltaQuantityText: buildSignedQuantityText(
            getCorrectionDraftLineDirection(line),
            value,
          ),
        }
      : line,
  );
}

export function setCorrectionDraftLineDeltaQuantityText(
  lines: CorrectionDraftLine[],
  draftLineKey: string,
  value: string,
): CorrectionDraftLine[] {
  return lines.map((line) =>
    line.key === draftLineKey
      ? {
          ...line,
          deltaQuantityText: sanitizeSignedQuantityInput(value),
        }
      : line,
  );
}

export function setCorrectionDraftLineNotes(
  lines: CorrectionDraftLine[],
  draftLineKey: string,
  value: string,
): CorrectionDraftLine[] {
  return lines.map((line) =>
    line.key === draftLineKey
      ? {
          ...line,
          notes: value,
        }
      : line,
  );
}

export function sanitizeSignedQuantityInput(value: string): string {
  let sign = "";
  let wholePart = "";
  let decimalPart = "";
  let hasDecimalSeparator = false;

  for (const character of value.trim()) {
    if ((character === "-" || character === "+") && sign === "" && wholePart === "" && !hasDecimalSeparator) {
      sign = character;
      continue;
    }

    if (character >= "0" && character <= "9") {
      if (hasDecimalSeparator) {
        if (decimalPart.length < 3) {
          decimalPart += character;
        }
      } else {
        wholePart += character;
      }
      continue;
    }

    if (character === "." && !hasDecimalSeparator) {
      hasDecimalSeparator = true;
    }
  }

  if (sign !== "" && wholePart === "" && !hasDecimalSeparator) {
    return sign;
  }

  if (hasDecimalSeparator) {
    const normalizedWholePart = wholePart.length > 0 ? wholePart : "0";
    return decimalPart.length > 0
      ? `${sign}${normalizedWholePart}.${decimalPart}`
      : `${sign}${normalizedWholePart}.`;
  }

  return `${sign}${wholePart}`;
}

export function parseSignedQuantityToMilliUnits(value: string): number | null {
  const normalizedValue = value.trim();
  if (!/^[+-]?\d+(\.\d+)?$/.test(normalizedValue)) {
    return null;
  }

  const sign = normalizedValue.startsWith("-") ? -1 : 1;
  const unsignedValue = normalizedValue.replace(/^[+-]/, "");
  const [wholePart, decimalPart = ""] = unsignedValue.split(".");
  if (decimalPart.length > 3) {
    return null;
  }

  const paddedDecimalPart = decimalPart.padEnd(3, "0");
  const integerUnits =
    Number.parseInt(wholePart, 10) * 1000 + Number.parseInt(paddedDecimalPart, 10);

  if (integerUnits === 0) {
    return null;
  }

  return sign * integerUnits;
}

export function formatSignedQuantityFromMilliUnits(value: number): string {
  const sign = value < 0 ? "-" : "";
  return `${sign}${formatQuantityFromMilliUnits(Math.abs(value))}`;
}

export function getCorrectionDraftLineDirection(
  line: Pick<CorrectionDraftLine, "deltaQuantityText" | "sourceKind">,
): CorrectionDirection {
  const parsedValue = parseSignedQuantityToMilliUnits(line.deltaQuantityText);
  if (parsedValue !== null) {
    return parsedValue < 0 ? "DECREASE" : "INCREASE";
  }

  const trimmedValue = line.deltaQuantityText.trim();
  if (trimmedValue.startsWith("-")) {
    return "DECREASE";
  }
  if (trimmedValue.startsWith("+")) {
    return "INCREASE";
  }

  return line.sourceKind === "TARGET_LINE" ? "DECREASE" : "INCREASE";
}

export function getCorrectionDraftLineMagnitudeText(
  line: Pick<CorrectionDraftLine, "deltaQuantityText">,
): string {
  return sanitizeQuantityInput(line.deltaQuantityText.replace(/^[+-]/, ""));
}

export function isCorrectionDraftLineValid(line: CorrectionDraftLine): boolean {
  return parseSignedQuantityToMilliUnits(line.deltaQuantityText) !== null;
}

export function hasCorrectionDraftInvalidQuantity(lines: CorrectionDraftLine[]): boolean {
  return lines.some((line) => !isCorrectionDraftLineValid(line));
}

export function hasCorrectionDraftMissingReason(reasonCode: string): boolean {
  return reasonCode.trim().length === 0;
}

export function hasCorrectionDraftMissingDestination(
  correctedDestinationBranchId: string | null,
): boolean {
  return correctedDestinationBranchId === null || correctedDestinationBranchId.trim().length === 0;
}

export function getCorrectionDraftBlockingMessages({
  additionalBlockingMessages = [],
  correctedDestinationBranchId,
  hasHighImpactAcknowledgement = true,
  hasSelectedTarget,
  isCorrectable,
  lines,
  highImpactAcknowledgementRequired = false,
  reasonAllowsDestinationCorrection,
  reasonCode,
}: {
  additionalBlockingMessages?: string[];
  correctedDestinationBranchId: string | null;
  hasHighImpactAcknowledgement?: boolean;
  hasSelectedTarget: boolean;
  isCorrectable: boolean;
  lines: CorrectionDraftLine[];
  highImpactAcknowledgementRequired?: boolean;
  reasonAllowsDestinationCorrection: boolean;
  reasonCode: string;
}): string[] {
  if (!hasSelectedTarget) {
    return ["Selecciona un documento original."];
  }

  if (!isCorrectable) {
    return ["Este documento ya no admite correcciones."];
  }

  const messages: string[] = [];
  if (reasonAllowsDestinationCorrection) {
    if (hasCorrectionDraftMissingReason(reasonCode)) {
      messages.push("Selecciona un motivo para continuar.");
    }
    if (hasCorrectionDraftMissingDestination(correctedDestinationBranchId)) {
      messages.push("Selecciona una sucursal destino para continuar.");
    }
    if (lines.length > 0) {
      messages.push("Quita los ajustes de lineas para corregir solo el destino.");
    }
    return messages;
  }

  if (lines.length === 0) {
    messages.push("Agrega al menos una linea al borrador.");
  }
  if (hasCorrectionDraftInvalidQuantity(lines)) {
    messages.push("Revisa cantidades y direccion del ajuste.");
  }
  if (hasCorrectionDraftMissingReason(reasonCode)) {
    messages.push("Selecciona un motivo para continuar.");
  }
  if (highImpactAcknowledgementRequired && !hasHighImpactAcknowledgement) {
    messages.push("Confirma el ajuste de alto impacto antes de registrarlo.");
  }
  if (additionalBlockingMessages.length > 0) {
    messages.push(...additionalBlockingMessages);
  }
  return messages;
}

export function getCorrectionDraftBlockedReason({
  additionalBlockingMessages,
  correctedDestinationBranchId,
  hasHighImpactAcknowledgement,
  hasSelectedTarget,
  isCorrectable,
  lines,
  highImpactAcknowledgementRequired,
  reasonAllowsDestinationCorrection,
  reasonCode,
}: {
  additionalBlockingMessages?: string[];
  correctedDestinationBranchId: string | null;
  hasHighImpactAcknowledgement?: boolean;
  hasSelectedTarget: boolean;
  isCorrectable: boolean;
  lines: CorrectionDraftLine[];
  highImpactAcknowledgementRequired?: boolean;
  reasonAllowsDestinationCorrection: boolean;
  reasonCode: string;
}): string | null {
  return (
    getCorrectionDraftBlockingMessages({
      additionalBlockingMessages,
      correctedDestinationBranchId,
      hasHighImpactAcknowledgement,
      hasSelectedTarget,
      isCorrectable,
      lines,
      highImpactAcknowledgementRequired,
      reasonAllowsDestinationCorrection,
      reasonCode,
    })[0] ?? null
  );
}

export function buildCorrectionCommitLines(
  lines: CorrectionDraftLine[],
): CorrectionCommitLineRequest[] {
  if (lines.length === 0) {
    throw new Error("Agrega al menos una linea al borrador antes de confirmar.");
  }

  return lines.map((line) => {
    const deltaQuantityMilliUnits = parseSignedQuantityToMilliUnits(line.deltaQuantityText);
    if (deltaQuantityMilliUnits === null) {
      throw new Error("Captura una cantidad valida mayor que cero en cada ajuste.");
    }

    return {
      target_line_id: line.targetLineId ?? undefined,
      product_id: line.productId,
      delta_quantity: formatSignedQuantityFromMilliUnits(deltaQuantityMilliUnits),
      notes: line.notes.trim().length > 0 ? line.notes.trim() : undefined,
    };
  });
}

export function getCorrectionDraftLineCount(lines: CorrectionDraftLine[]): number {
  return lines.length;
}

export function getCorrectionDraftNetQuantityMilliUnits(lines: CorrectionDraftLine[]): number {
  return lines.reduce(
    (sum, line) => sum + (parseSignedQuantityToMilliUnits(line.deltaQuantityText) ?? 0),
    0,
  );
}

export function getCorrectionDraftTotalAdjustedQuantityMilliUnits(
  lines: CorrectionDraftLine[],
): number {
  return lines.reduce(
    (sum, line) => sum + Math.abs(parseSignedQuantityToMilliUnits(line.deltaQuantityText) ?? 0),
    0,
  );
}

function buildTargetLineKey(targetLineId: string): string {
  return `target:${targetLineId}`;
}

function buildProductKey(productId: string): string {
  return `product:${productId}`;
}

function buildSignedQuantityText(
  direction: CorrectionDirection,
  rawMagnitudeText: string,
): string {
  const magnitudeText = sanitizeQuantityInput(rawMagnitudeText);
  if (magnitudeText.length === 0) {
    return "";
  }

  return direction === "DECREASE" ? `-${magnitudeText}` : magnitudeText;
}
