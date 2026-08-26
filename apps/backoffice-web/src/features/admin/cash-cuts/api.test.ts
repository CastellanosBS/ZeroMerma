import { describe, expect, it } from "vitest";

import { buildAdminCashCutsListPath, mapAdminCashCutFromApi } from "./api";
import type { AdminCashCutListFilters } from "./types";

describe("admin cash cuts API helpers", () => {
  it("builds the cash cuts list path with supported filters only", () => {
    const filters: AdminCashCutListFilters = {
      branchId: "branch-1",
      cashierId: "cashier-1",
      dateFrom: "2026-05-01",
      dateTo: "2026-05-21",
      differenceState: "WITH_DIFFERENCE",
      hasOperationalPayments: "true",
      hasRefunds: "false",
      page: 2,
      pageSize: 50,
      paymentMethod: "CASH",
      search: "  CUT-100  ",
      status: "CLOSED_WITH_DIFFERENCE",
      workstationId: "station-1",
    };

    const path = buildAdminCashCutsListPath(filters);

    expect(path).toContain("/v1/admin/cash-cuts?");
    expect(path).toContain("page=2");
    expect(path).toContain("page_size=50");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("workstation_id=station-1");
    expect(path).toContain("cashier_id=cashier-1");
    expect(path).toContain("difference_state=WITH_DIFFERENCE");
    expect(path).toContain("has_operational_payments=true");
    expect(path).toContain("has_refunds=false");
    expect(path).toContain("payment_method=CASH");
    expect(path).toContain("status=CLOSED_WITH_DIFFERENCE");
    expect(path).toContain("search=CUT-100");
    expect(path).toContain("date_from=2026-05-01T00%3A00%3A00.000Z");
    expect(path).toContain("date_to=2026-05-21T23%3A59%3A59.999Z");
  });

  it("maps the backend cash cut list item without inventing values", () => {
    const mapped = mapAdminCashCutFromApi({
      branch_id: "branch-1",
      branch_name: "Centro",
      cash_session_id: "session-1",
      cashier_id: "user-1",
      cashier_name: "Admin",
      close_id: "close-1",
      closed_at: "2026-05-21T18:00:00Z",
      counted_cash_amount: "1125",
      difference_amount: "5",
      difference_state: "OVER",
      expected_cash_amount: "1120",
      folio: "CC-100",
      has_operational_payments: true,
      has_refunds: true,
      id: "session-1",
      opened_at: "2026-05-21T10:00:00Z",
      opening_amount: "500",
      payment_methods_summary: "CASH, CARD",
      status: "CLOSED_WITH_DIFFERENCE",
      total_sales_amount: "720",
      warning_count: 1,
      warning_state: "warning",
      workstation_code: "POS-1",
      workstation_id: "station-1",
      workstation_name: "Mostrador 1",
    });

    expect(mapped.folio).toBe("CC-100");
    expect(mapped.status).toBe("CLOSED_WITH_DIFFERENCE");
    expect(mapped.countedCashAmount).toBe("1125");
    expect(mapped.differenceAmount).toBe("5");
    expect(mapped.hasRefunds).toBe(true);
    expect(mapped.hasOperationalPayments).toBe(true);
  });
});
