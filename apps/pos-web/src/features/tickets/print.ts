import type { TicketDetailResponse } from "../../lib/api-contracts";
import { writePrintableDocument } from "../../lib/browser-print";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";

type TicketPrintVariant = "reprint" | "sale";

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
    default:
      return code;
  }
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
  const footerLabel =
    variant === "sale"
      ? "Ticket generado desde la caja"
      : "Reimpresion generada desde la caja";

  const linesMarkup = ticket.lines
    .map(
      (line) => `
        <tr>
          <td>${escapeHtml(line.name)}</td>
          <td class="numeric">${formatQuantity(line.quantity)}</td>
          <td class="numeric">${formatCurrency(line.unit_price)}</td>
          <td class="numeric">${formatCurrency(line.line_total_amount)}</td>
        </tr>
      `,
    )
    .join("");

  const paymentsMarkup = ticket.payments
    .map(
      (payment) => `
        <tr>
          <td>${escapeHtml(getPaymentMethodLabel(payment.payment_method_code))}</td>
          <td class="numeric">${formatCurrency(payment.applied_amount)}</td>
        </tr>
      `,
    )
    .join("");

  return `<!doctype html>
<html lang="es-MX">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(documentTitle)}</title>
    <style>
      body {
        font-family: "Segoe UI", Arial, sans-serif;
        margin: 0;
        padding: 24px;
        color: #0f172a;
        background: #ffffff;
      }
      .ticket {
        max-width: 420px;
        margin: 0 auto;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
      }
      h1, h2, p {
        margin: 0;
      }
      .header {
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 12px;
        margin-bottom: 12px;
      }
      .brand {
        font-size: 20px;
        font-weight: 700;
      }
      .muted {
        color: #475569;
        font-size: 12px;
        line-height: 1.5;
      }
      .folio {
        margin-top: 8px;
        font-size: 18px;
        font-weight: 700;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 16px;
        margin-bottom: 16px;
      }
      .label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
      }
      .value {
        margin-top: 4px;
        font-size: 14px;
        font-weight: 600;
      }
      table {
        width: 100%;
        border-collapse: collapse;
      }
      th, td {
        padding: 8px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 13px;
        text-align: left;
      }
      th {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
      }
      .numeric {
        text-align: right;
      }
      .totals {
        margin-top: 16px;
        display: grid;
        gap: 8px;
      }
      .total-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 14px;
      }
      .total-row.strong {
        font-size: 18px;
        font-weight: 700;
      }
      .footer {
        margin-top: 16px;
        color: #64748b;
        font-size: 12px;
        text-align: center;
      }
      @media print {
        body {
          padding: 0;
        }
        .ticket {
          border: none;
          border-radius: 0;
          padding: 0;
        }
      }
    </style>
  </head>
  <body>
    <main class="ticket">
      <section class="header">
        <p class="brand">${escapeHtml(ticket.branch.name)}</p>
        <p class="muted">${escapeHtml(ticket.workstation.name)} • ${escapeHtml(ticket.operator.full_name)}</p>
        <p class="folio">${escapeHtml(ticket.folio)}</p>
        <p class="muted">${escapeHtml(
          formatLocalDateTime(ticket.confirmed_at, ticket.branch.timezone),
        )}</p>
      </section>

      <section class="grid">
        <div>
          <p class="label">Sucursal</p>
          <p class="value">${escapeHtml(ticket.branch.name)}</p>
        </div>
        <div>
          <p class="label">Caja</p>
          <p class="value">${escapeHtml(ticket.workstation.name)}</p>
        </div>
        <div>
          <p class="label">Cajero</p>
          <p class="value">${escapeHtml(ticket.operator.full_name)}</p>
        </div>
        <div>
          <p class="label">Articulos</p>
          <p class="value">${escapeHtml(String(ticket.item_count))}</p>
        </div>
      </section>

      <section>
        <table>
          <thead>
            <tr>
              <th>Articulo</th>
              <th class="numeric">Cant.</th>
              <th class="numeric">Precio</th>
              <th class="numeric">Importe</th>
            </tr>
          </thead>
          <tbody>${linesMarkup}</tbody>
        </table>
      </section>

      <section class="totals">
        <div class="total-row">
          <span>Subtotal</span>
          <span>${formatCurrency(ticket.subtotal_amount)}</span>
        </div>
        <div class="total-row strong">
          <span>Total</span>
          <span>${formatCurrency(ticket.total_amount)}</span>
        </div>
        <div class="total-row">
          <span>Pagado</span>
          <span>${formatCurrency(ticket.paid_amount)}</span>
        </div>
        <div class="total-row">
          <span>Cambio</span>
          <span>${formatCurrency(ticket.change_amount)}</span>
        </div>
      </section>

      <section style="margin-top: 16px;">
        <table>
          <thead>
            <tr>
              <th>Metodo de pago</th>
              <th class="numeric">Aplicado</th>
            </tr>
          </thead>
          <tbody>${paymentsMarkup}</tbody>
        </table>
      </section>

      <p class="footer">${escapeHtml(footerLabel)}</p>
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
