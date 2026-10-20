import type { TicketDetailResponse } from "../../lib/api-contracts";
import { writePrintableDocument } from "../../lib/browser-print";
import { formatLocalDateTime } from "../../lib/formatters";

type Receipt = NonNullable<TicketDetailResponse["receipt"]>;

type TicketPrintVariant = "reprint" | "sale";

const LINE_WIDTH = 42;
const PRODUCT_NAME_WIDTH = 18;

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatQuantity(quantity: number | string): string {
  return new Intl.NumberFormat("es-MX", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  }).format(Number(quantity));
}

function getPaymentMethodLabel(code: string): string {
  switch (code) {
    case "CASH":
      return "Efectivo";
    case "CARD":
      return "Tarjeta";
    case "MIXED":
      return "Mixto";
    case "TRANSFER":
      return "Transferencia";
    default:
      return code;
  }
}

function formatMoney(value: string | number, currencyCode: string): string {
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: currencyCode,
    minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(value)).replace(/\s/g, "");
}

function fitText(value: string, width: number): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= width) {
    return normalized.padEnd(width, " ");
  }

  return normalized.slice(0, Math.max(width - 1, 0)).padEnd(width, " ");
}

function rightText(value: string, width: number): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length <= width) {
    return normalized.padStart(width, " ");
  }

  return normalized;
}

function centerText(value: string): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (normalized.length >= LINE_WIDTH) {
    return normalized.slice(0, LINE_WIDTH);
  }

  const leftPadding = Math.floor((LINE_WIDTH - normalized.length) / 2);
  return `${" ".repeat(leftPadding)}${normalized}`;
}

function separator(): string {
  return "-".repeat(LINE_WIDTH);
}

function keyValue(label: string, value: string): string {
  const labelText = `${label}:`;
  const valueWidth = Math.max(LINE_WIDTH - labelText.length - 1, 0);
  return `${labelText} ${rightText(value, valueWidth)}`;
}

function wrapText(value: string, width: number): string[] {
  const words = value.replace(/\s+/g, " ").trim().split(" ").filter(Boolean);
  if (words.length === 0) {
    return [""];
  }

  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    if (word.length > width) {
      if (currentLine.length > 0) {
        lines.push(currentLine);
        currentLine = "";
      }

      for (let index = 0; index < word.length; index += width) {
        lines.push(word.slice(index, index + width));
      }
      continue;
    }

    const candidate = currentLine.length > 0 ? `${currentLine} ${word}` : word;
    if (candidate.length > width) {
      lines.push(currentLine);
      currentLine = word;
      continue;
    }

    currentLine = candidate;
  }

  if (currentLine.length > 0) {
    lines.push(currentLine);
  }

  return lines.length > 0 ? lines : [""];
}

function productLineRows(line: Receipt["lines"][number], currencyCode: string): string[] {
  const quantity = formatQuantity(line.quantity);
  const unitPrice = formatMoney(line.unit_price, currencyCode);
  const amount = formatMoney(line.total_amount, currencyCode);
  const nameLines = wrapText(line.name, PRODUCT_NAME_WIDTH);
  const [firstName = "", ...restNames] = nameLines;

  return [
    `${rightText(quantity, 5)} ${fitText(firstName, PRODUCT_NAME_WIDTH)} ${rightText(unitPrice, 8)} ${rightText(amount, 8)}`,
    ...restNames.map((name) => `${" ".repeat(6)}${fitText(name, PRODUCT_NAME_WIDTH)}`),
  ];
}

function buildTicketText(receipt: Receipt, variant: TicketPrintVariant): string {
  const context = receipt.context;
  const currencyCode = receipt.currency_code ?? "MXN";
  const money = (value: string | number) => formatMoney(value, currencyCode);
  const seller = receipt.seller ?? { configuration_status: "UNCONFIGURED" };
  const title = receipt.source_kind === "RETURN" ? "COMPROBANTE DE DEVOLUCION"
    : receipt.source_kind === "ORDER_PAYMENT" ? "PAGO DE PEDIDO" : "NOTA DE VENTA";
  const rows: string[] = [
    ...wrapText(seller.commercial_name ?? context.branch_name.toUpperCase(), LINE_WIDTH).map(centerText),
    ...(seller.business_descriptor ? wrapText(seller.business_descriptor, LINE_WIDTH).map(centerText) : []),
    ...wrapText(`Direccion: ${seller.address ?? "No configurada"}`, LINE_WIDTH),
    centerText(variant === "reprint" ? "REIMPRESION" : title),
    ...wrapText(`Razon social: ${seller.legal_name ?? "No configurada"}`, LINE_WIDTH),
    ...wrapText(`RFC: ${seller.tax_identifier ?? "No configurado"}`, LINE_WIDTH),
    ...wrapText(`Regimen fiscal: ${seller.fiscal_regime ?? "No configurado"}`, LINE_WIDTH),
    ...wrapText(`Sucursal: ${context.branch_name}`, LINE_WIDTH),
    ...(seller.configuration_status === "UNCONFIGURED" ? ["Identidad fiscal pendiente de configurar."] : []),
    separator(),
    ...wrapText(`Ticket: ${receipt.folio}`, LINE_WIDTH),
    `Fecha: ${formatLocalDateTime(receipt.occurred_at, context.timezone)}`,
    ...wrapText(`Caja: ${context.workstation_name}`, LINE_WIDTH),
    ...wrapText(`Cajero: ${context.actor_name}`, LINE_WIDTH),
    `Turno: ${context.cash_session_id.slice(0, 8).toUpperCase()}`,
    `Moneda: ${currencyCode}`,
    ...(receipt.related_document_folio ? wrapText(`Documento: ${receipt.related_document_folio}`, LINE_WIDTH) : []),
    separator(),
    " Cant Producto             P.Unit  Importe",
    separator(),
    ...receipt.lines.flatMap((line) => productLineRows(line, currencyCode)),
    separator(),
    keyValue("Subtotal", money(receipt.subtotal_amount)),
    keyValue("Descuento", money(receipt.discount_amount)),
    keyValue("TOTAL", money(receipt.total_amount)),
    "",
    ...receipt.payments.flatMap((payment) => [
      keyValue(`Pago ${getPaymentMethodLabel(payment.method)}`, money(payment.amount)),
      ...(payment.execution_mode === "ACCOUNTING_ONLY" ? ["Registro de cobro externo."] : []),
      ...(payment.method === "CASH" ? [keyValue("Efectivo recibido", money(payment.tendered_amount))] : []),
    ]),
    keyValue("Cambio", money(receipt.change_amount)),
    ...(receipt.settled_amount != null ? [keyValue("Reembolsado", money(receipt.settled_amount))] : []),
    ...(receipt.pending_amount != null ? [keyValue("Pendiente", money(receipt.pending_amount)),
      "Importes al emitir este comprobante."] : []),
    separator(),
    "Comprobante operativo de ZeroMerma.",
    "No sustituye un CFDI.",
    "No es un comprobante emitido por BBVA.",
    "",
    "Gracias por su compra.",
    ...wrapText(`Referencia: ${receipt.source_id}`, LINE_WIDTH),
  ];
  return rows.join("\n");
}
export function buildTicketPrintDocument(
  ticket: TicketDetailResponse,
  options?: {
    variant?: TicketPrintVariant;
  },
): string {
  if (!ticket.receipt) {
    throw new Error("Este ticket no conserva un documento inmutable para imprimir.");
  }
  return buildOperationalReceiptPrintDocument(ticket.receipt, options);
}

export function buildOperationalReceiptPrintDocument(
  receipt: Receipt,
  options?: { variant?: TicketPrintVariant },
): string {
  const variant = options?.variant ?? "reprint";
  const documentTitle =
    variant === "sale" ? `Ticket ${receipt.folio}` : `Reimpresion ${receipt.folio}`;
  const ticketText = buildTicketText(receipt, variant);

  return `<!doctype html>
<html lang="es-MX">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(documentTitle)}</title>
    <style>
      @page {
        size: 80mm auto;
        margin: 0;
      }

      html,
      body {
        margin: 0;
        padding: 0;
        background: #ffffff;
        color: #000000;
      }

      body {
        width: 80mm;
        font-family: "Courier New", ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 11px;
        line-height: 1.28;
      }

      .ticket {
        box-sizing: border-box;
        width: 80mm;
        padding: 4mm;
      }

      pre {
        margin: 0;
        white-space: pre-wrap;
        overflow-wrap: break-word;
      }

      @media print {
        .ticket {
          padding: 3mm;
        }
      }
    </style>
  </head>
  <body>
    <main class="ticket">
      <pre>${escapeHtml(ticketText)}</pre>
    </main>
  </body>
</html>`;
}

export function writeTicketToPrintWindow(
  printWindow: Window,
  ticket: TicketDetailResponse,
  options?: {
    variant?: TicketPrintVariant;
  },
): void {
  writePrintableDocument(printWindow, buildTicketPrintDocument(ticket, options));
}
