import { renderToString } from "react-dom/server";
import { expect, it } from "vitest";
import { FinancialRefundSummary } from "./FinancialRefundSummary";

it("separates refundable debt from confirmed cash and shows actual payment session", () => {
  const html = renderToString(
    <FinancialRefundSummary
      refund={{
        financial_operation_id: "refund",
        source_type: "ORDER_CANCELLATION",
        source_id: "order",
        amount_due: "100.00",
        amount_settled: "40.00",
        amount_pending: "60.00",
        state: "PARTIALLY_SETTLED",
        cash_settled_amount: "40.00",
        card_settled_amount: "0.00",
        original_collection_operation_ids: ["original"],
        entries: [
          {
            id: "entry",
            amount: "40.00",
            state: "CONFIRMED",
            execution_mode: "LOCAL",
            payment_method_code: "CASH",
            cash_session_id: "actual-refund-shift",
            occurred_at: "2026-10-19T18:00:00Z",
          },
        ],
      }}
    />,
  );
  expect(html).toContain("Pendiente de entregar:");
  expect(html).toContain("$60.00");
  expect(html).toContain("Entrega confirmada:");
  expect(html).toContain("$40.00");
  expect(html).toContain("actual-refund-shift");
});
