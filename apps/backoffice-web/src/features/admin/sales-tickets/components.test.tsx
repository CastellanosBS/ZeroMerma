import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { AdminSalesTicketDetailPanel } from "./components/AdminSalesTicketDetailPanel";
import { AdminSalesTicketsTable } from "./components/AdminSalesTicketsTable";
import type { AdminSalesTicketDetail, AdminSalesTicketListItem } from "./types";

const ticket: AdminSalesTicketListItem = {
  branchId: "branch-1",
  branchName: "Centro",
  cashierId: "user-1",
  cashierName: "Cajero",
  currencyCode: "MXN",
  folio: "TCK-123",
  hasReturns: false,
  id: "ticket-1",
  itemCount: 1,
  occurredAt: "2026-05-20T10:00:00Z",
  paymentMethodsLabel: "CASH",
  paymentSummary: [{ amount: "25.00", currencyCode: "MXN", paymentMethodCode: "CASH" }],
  returnCount: 0,
  returnStatus: "NONE",
  saleId: "sale-1",
  status: "CONFIRMED",
  totalAmount: "25.00",
  unitCount: "1.000",
  workstationCode: "POS-01",
  workstationId: "workstation-1",
  workstationName: "Mostrador",
};

const detail: AdminSalesTicketDetail = {
  lines: [
    {
      captureMode: "PRODUCT_DIRECT",
      catalogCode: "PAN-1",
      catalogName: "Pan dulce",
      discountAmount: "0.00",
      id: "line-1",
      lineTotalAmount: "25.00",
      physicalAttributionStatus: "ATTRIBUTED",
      productClassId: null,
      productId: "product-1",
      quantity: "1.000",
      sequence: 1,
      unitPrice: "25.00",
    },
  ],
  operationalContext: {
    branchId: "branch-1",
    branchName: "Centro",
    cashSessionId: "session-1",
    cashierEmail: "cashier@zeromerma.local",
    cashierId: "user-1",
    cashierName: "Cajero",
    confirmedAt: "2026-05-20T10:00:00Z",
    createdAt: "2026-05-20T10:00:00Z",
    saleId: "sale-1",
    workstationCode: "POS-01",
    workstationId: "workstation-1",
    workstationName: "Mostrador",
  },
  overview: {
    changeAmount: "0.00",
    confirmedAt: "2026-05-20T10:00:00Z",
    currencyCode: "MXN",
    folio: "TCK-123",
    id: "ticket-1",
    itemCount: 1,
    paidAmount: "25.00",
    returnCount: 0,
    returnStatus: "NONE",
    returnedAmount: "0.00",
    status: "CONFIRMED",
    subtotalAmount: "25.00",
    totalAmount: "25.00",
    unitCount: "1.000",
  },
  payments: [
    {
      appliedAmount: "25.00",
      changeAmount: "0.00",
      currencyCode: "MXN",
      id: "payment-1",
      paymentMethodCode: "CASH",
      receivedAt: "2026-05-20T10:00:00Z",
      sequence: 1,
      tenderedAmount: "25.00",
    },
  ],
  printableTicket: { canReprint: true, note: null, previewAvailable: true },
  relatedDocuments: [],
};

describe("admin sales ticket visibility controls", () => {
  it("keeps the list and read actions while disabling reprint", () => {
    const copyFolio = vi.fn();
    const html = renderToString(
      <AdminSalesTicketsTable
        backendContract={{
          detailEndpoint: "GET /v1/admin/sales-tickets/{ticket_id}",
          listEndpoint: "GET /v1/admin/sales-tickets",
          reprintEndpoint: "POST /v1/admin/sales-tickets/{ticket_id}/reprint",
        }}
        onCopyFolio={copyFolio}
        onPageChange={() => undefined}
        onSelectTicket={() => undefined}
        page={1}
        pageSize={25}
        tickets={[ticket]}
        total={1}
      />,
    );

    expect(html).toContain("TCK-123");
    expect(html).toContain("Copiar");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*title="Reimpresion no disponible en Backoffice"[^>]*>Reimprimir<\/button>/);
    expect(copyFolio).not.toHaveBeenCalled();
  });

  it("keeps ticket detail visible while reprint remains non-operational", () => {
    const copyFolio = vi.fn();
    const html = renderToString(
      <AdminSalesTicketDetailPanel
        detail={detail}
        onCopyFolio={copyFolio}
        selectedTicket={ticket}
      />,
    );

    expect(html).toContain("TCK-123");
    expect(html).toContain("Pan dulce");
    expect(html).toContain("Copiar folio");
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*title="Reimpresion no disponible en Backoffice"[^>]*>Reimprimir<\/button>/);
    expect(copyFolio).not.toHaveBeenCalled();
  });
});
