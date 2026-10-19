import type { SaleReturnDetailResponse } from "../../lib/api-contracts";
import { buildOperationalReceiptPrintDocument } from "../tickets/print";

export function buildReturnReceiptDocument(document: SaleReturnDetailResponse): string {
  if (!document.receipt) {
    throw new Error("Esta devolución no conserva un comprobante inmutable.");
  }
  return buildOperationalReceiptPrintDocument(document.receipt, { variant: "sale" });
}