import { describe, expect, it } from "vitest";

import type { TicketDetailResponse } from "../../lib/api-contracts";
import { buildTicketPrintDocument } from "./print";

const ticketFixture: TicketDetailResponse = {
  id: "8ad4f881-faa9-41c7-aeb9-41d44f7cfb0b",
  folio: "TCK-8AD4F881",
  status: "CONFIRMED",
  confirmed_at: "2026-04-12T18:00:00Z",
  branch: {
    id: "c881ff94-0355-4fd6-bec2-65749165d4bd",
    code: "MAIN",
    name: "Main Branch",
    timezone: "America/Hermosillo",
    is_active: true,
  },
  workstation: {
    id: "75dcb77d-b1e3-4961-b961-63780a97f919",
    code: "POS-01",
    name: "Front Register 01",
    is_active: true,
  },
  operator: {
    id: "d96a84a0-0f69-412d-89cb-1c0b77c3490e",
    email: "cashier@zeromerma.local",
    full_name: "Cashier",
  },
  cash_session_id: "55a61db7-bf29-4c62-86c9-d0ef507ec588",
  currency_code: "MXN",
  item_count: 2,
  total_quantity: "3",
  subtotal_amount: "42.00",
  total_amount: "42.00",
  paid_amount: "50.00",
  change_amount: "8.00",
  return_count: 0,
  returned_amount: "0.00",
  return_status: "NOT_RETURNED",
  has_returnable_quantity: true,
  lines: [
    {
      id: "04354103-70bc-4a0b-86b6-a2af9d62862a",
      sequence: 1,
      name: "Pan dulce",
      quantity: "2",
      unit_price: "12.00",
      line_total_amount: "24.00",
    },
  ],
  payments: [
    {
      id: "2ac937a8-c4fd-49d2-b6c5-676d0bf81e16",
      sequence: 1,
      payment_method_code: "CASH",
      tendered_amount: "50.00",
      applied_amount: "42.00",
      change_amount: "8.00",
      currency_code: "MXN",
      received_at: "2026-04-12T18:00:00Z",
    },
  ],
  can_reprint: true,
};

describe("ticket print document", () => {
  it("renders a printable receipt with folio and line items", () => {
    const document = buildTicketPrintDocument(ticketFixture);

    expect(document).toContain("TCK-8AD4F881");
    expect(document).toContain("Pan dulce");
    expect(document).toContain("REIMPRESION");
    expect(document).toContain("Efectivo");
    expect(document).toContain("@page");
    expect(document).toContain("80mm");
    expect(document).toContain("RFC: No configurado");
    expect(document).toContain("Este ticket es comprobante de compra.");
    expect(document).toContain("No sustituye un CFDI.");
  });
});
