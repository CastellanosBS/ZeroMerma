import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { CustomerOrderDetailResponse } from "../../lib/api-contracts";
import { OrderPaymentHistory } from "./order-payment-history";

const payment: CustomerOrderDetailResponse["payments"][number] = {
  id: "payment-1",
  sequence: 1,
  payment_type: "ADVANCE",
  payment_method_code: "CARD",
  amount: "6.00",
  currency_code: "MXN",
  recorded_at_utc: "2026-10-19T18:00:00Z",
  recorded_by_user_id: "actor-1",
  recorded_by_user_full_name: "Cashier",
  cash_session_id: "actual-shift-2",
  workstation_id: "station-2",
  financial_operation_id: "financial-operation-1",
  financial_entry_id: "financial-entry-1",
};

describe("order payment history", () => {
  it("explains recorded card and retains the actual payment, entry and turn identities", () => {
    const html = renderToString(<OrderPaymentHistory payments={[payment]} />);
    for (const text of [
      "Anticipo",
      "Tarjeta",
      "$6.00",
      "actual-shift-2",
      "station-2",
      "financial-entry-1",
      "financial-operation-1",
      "no afecta el efectivo ni confirma una captura del proveedor",
    ]) {
      expect(html).toContain(text);
    }
  });

  it("does not invent a canonical posting for a historical payment", () => {
    const html = renderToString(
      <OrderPaymentHistory
        payments={[
          {
            ...payment,
            payment_type: "REFUND",
            payment_method_code: "CASH",
            financial_operation_id: null,
            financial_entry_id: null,
          },
        ]}
      />,
    );
    expect(html).toContain("Reembolso");
    expect(html).toContain("Efectivo");
    expect(html).toContain("sin asiento financiero vinculado");
    expect(html).not.toContain("captura del proveedor");
  });

  it("does not invent a payment history for an unpaid order", () => {
    expect(renderToString(<OrderPaymentHistory payments={[]} />)).toBe("");
  });
});
