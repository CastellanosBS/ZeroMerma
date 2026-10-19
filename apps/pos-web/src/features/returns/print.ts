import type { SaleReturnDetailResponse } from "../../lib/api-contracts";
import { writePrintableDocument } from "../../lib/browser-print";
import { formatCurrency, formatLocalDateTime } from "../../lib/formatters";

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
    maximumFractionDigits: 3,
    minimumFractionDigits: 0,
  }).format(Number(quantity));
}

function getRefundMethodLabel(code: string): string {
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

export function buildReturnReceiptDocument(document: SaleReturnDetailResponse): string {
  const linesMarkup = document.lines
    .map(
      (line) => `
        <tr>
          <td>${escapeHtml(line.original_catalog_name_snapshot)}
            ${line.allocations.map((allocation) => `<p class="muted">${formatQuantity(allocation.quantity)} ${escapeHtml(allocation.returned_product_name_snapshot)} / ${escapeHtml(allocation.disposition_code)}${allocation.lot_id ? ` / Lote ${escapeHtml(allocation.lot_id)}` : ""}</p>`).join("")}
          </td>
          <td class="numeric">${formatQuantity(line.returned_quantity)}</td>
          <td class="numeric">${formatCurrency(line.refund_unit_price)}</td>
          <td class="numeric">${formatCurrency(line.refund_line_total_amount)}</td>
        </tr>
      `,
    )
    .join("");

  return `<!doctype html>
<html lang="es-MX">
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(`Devolucion ${document.folio}`)}</title>
    <style>
      body { font-family: "Segoe UI", Arial, sans-serif; margin: 0; padding: 24px; color: #0f172a; background: #fff; }
      .receipt { max-width: 420px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; }
      h1, h2, p { margin: 0; }
      .header { border-bottom: 1px solid #e2e8f0; padding-bottom: 12px; margin-bottom: 12px; }
      .brand { font-size: 20px; font-weight: 700; }
      .muted { color: #475569; font-size: 12px; line-height: 1.5; }
      .folio { margin-top: 8px; font-size: 18px; font-weight: 700; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin-bottom: 16px; }
      .label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }
      .value { margin-top: 4px; font-size: 14px; font-weight: 600; }
      table { width: 100%; border-collapse: collapse; }
      th, td { padding: 8px 0; border-bottom: 1px solid #e2e8f0; font-size: 13px; text-align: left; }
      th { font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; color: #64748b; }
      .numeric { text-align: right; }
      .totals { margin-top: 16px; display: grid; gap: 8px; }
      .total-row { display: flex; align-items: center; justify-content: space-between; font-size: 14px; }
      .total-row.strong { font-size: 18px; font-weight: 700; }
      .footer { margin-top: 16px; color: #64748b; font-size: 12px; text-align: center; }
      @media print {
        body { padding: 0; }
        .receipt { border: none; border-radius: 0; padding: 0; }
      }
    </style>
  </head>
  <body>
    <main class="receipt">
      <section class="header">
        <p class="brand">${escapeHtml(document.branch.name)}</p>
        <p class="muted">${escapeHtml(document.workstation.name)} | ${escapeHtml(document.created_by.full_name)}</p>
        <p class="folio">${escapeHtml(document.folio)}</p>
        <p class="muted">${escapeHtml(
          formatLocalDateTime(document.created_at_utc, document.branch.timezone),
        )}</p>
      </section>

      <section class="grid">
        <div>
          <p class="label">Venta original</p>
          <p class="value">${escapeHtml(document.original_sale_folio)}</p>
        </div>
        <div>
          <p class="label">Metodo previsto</p>
          <p class="value">${escapeHtml(getRefundMethodLabel(document.refund_method_code))}</p>
        </div>
        <div>
          <p class="label">Motivo</p>
          <p class="value">${escapeHtml(document.reason_name)}</p>
        </div>
        <div>
          <p class="label">Caja</p>
          <p class="value">${escapeHtml(document.workstation.name)}</p>
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
        <div class="total-row strong">
          <span>Importe autorizado</span>
          <span>${formatCurrency(document.total_refund_amount)}</span>
        </div>
        ${
          document.financial_refund
            ? `
        <div class="total-row"><span>Entrega confirmada</span><span>${formatCurrency(document.financial_refund.amount_settled)}</span></div>
        <div class="total-row strong"><span>Pendiente de entregar</span><span>${formatCurrency(document.financial_refund.amount_pending)}</span></div>
        <div class="total-row"><span>Efectivo confirmado</span><span>${formatCurrency(document.financial_refund.cash_settled_amount)}</span></div>
        <div class="total-row"><span>Tarjeta confirmada</span><span>${formatCurrency(document.financial_refund.card_settled_amount)}</span></div>
        `
            : "<p>Sin evidencia financiera del reembolso; requiere revision.</p>"
        }
      </section>

      <p class="footer">Comprobante de devolucion generado desde la caja</p>
    </main>
  </body>
</html>`;
}

export function writeReturnReceiptToPrintWindow(
  printWindow: Window,
  document: SaleReturnDetailResponse,
): void {
  writePrintableDocument(printWindow, buildReturnReceiptDocument(document));
}
