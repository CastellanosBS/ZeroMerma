import type { TicketDetailResponse } from "../../lib/api-contracts";
import { writePrintableDocument } from "../../lib/browser-print";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";

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

function parseMoney(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function formatMoney(value: string | number): string {
  return formatCurrency(typeof value === "number" ? value.toFixed(2) : value).replace(/\s/g, "");
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

  return normalized.slice(normalized.length - width);
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

function productLineRows(line: TicketDetailResponse["lines"][number]): string[] {
  const quantity = formatQuantity(line.quantity);
  const unitPrice = formatMoney(line.unit_price);
  const amount = formatMoney(line.line_total_amount);
  const nameLines = wrapText(line.name, PRODUCT_NAME_WIDTH);
  const [firstName = "", ...restNames] = nameLines;

  return [
    `${rightText(quantity, 5)} ${fitText(firstName, PRODUCT_NAME_WIDTH)} ${rightText(unitPrice, 8)} ${rightText(amount, 8)}`,
    ...restNames.map((name) => `${" ".repeat(6)}${fitText(name, PRODUCT_NAME_WIDTH)}`),
  ];
}

function buildTicketText(ticket: TicketDetailResponse, variant: TicketPrintVariant): string {
  const subtotal = parseMoney(ticket.subtotal_amount);
  const total = parseMoney(ticket.total_amount);
  const discount = Math.max(subtotal - total, 0);
  const internalReference = ticket.id.slice(0, 8).toUpperCase();

  const rows: string[] = [
    centerText(ticket.branch.name.toUpperCase()),
    centerText(variant === "reprint" ? "REIMPRESION" : "NOTA DE VENTA"),
    "RFC: No configurado",
    "Regimen fiscal: No configurado",
    `Sucursal: ${ticket.branch.name}`,
    "Direccion: No configurada",
    separator(),
    `Ticket: ${ticket.folio}`,
    `Fecha: ${formatLocalDateTime(ticket.confirmed_at, ticket.branch.timezone)}`,
    `Caja: ${ticket.workstation.name}`,
    `Cajero: ${ticket.operator.full_name}`,
    `Turno: ${ticket.cash_session_id.slice(0, 8).toUpperCase()}`,
    separator(),
    " Cant Producto             P.Unit  Importe",
    separator(),
    ...ticket.lines.flatMap(productLineRows),
    separator(),
    keyValue("Subtotal", formatMoney(ticket.subtotal_amount)),
    keyValue("Descuento", formatMoney(discount)),
    keyValue("TOTAL", formatMoney(ticket.total_amount)),
    "",
    ...ticket.payments.map((payment) =>
      keyValue(`Pago ${getPaymentMethodLabel(payment.payment_method_code)}`, formatMoney(payment.tendered_amount)),
    ),
    keyValue("Cambio", formatMoney(ticket.change_amount)),
    separator(),
    "Este ticket es comprobante de compra.",
    "No sustituye un CFDI.",
    "Solicite su factura con este folio.",
    "",
    "Gracias por su compra.",
    `Referencia: ${internalReference}`,
    `QR: ${ticket.id}`,
  ];

  return rows.join("\n");
}

export function buildTicketPrintDocument(
  ticket: TicketDetailResponse,
  options?: {
    variant?: TicketPrintVariant;
  },
): string {
  const variant = options?.variant ?? "reprint";
  const documentTitle =
    variant === "sale" ? `Ticket ${ticket.folio}` : `Reimpresion ${ticket.folio}`;
  const ticketText = buildTicketText(ticket, variant);

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
