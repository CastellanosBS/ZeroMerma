import { describe, expect, it } from "vitest";

import { buildAdminCashFlowListPath, mapAdminCashFlowMovementFromApi } from "./api";
import type { AdminCashFlowListFilters } from "./types";

describe("admin cash flow API helpers", () => {
  it("builds the cash flow list path with supported filters only", () => {
    const filters: AdminCashFlowListFilters = {
      amountMax: "500",
      amountMin: "10",
      branchId: "branch-1",
      category: "Pago operativo",
      dateFrom: "2026-05-01",
      dateTo: "2026-05-21",
      direction: "OUTFLOW",
      operatorId: "user-1",
      page: 2,
      pageSize: 50,
      paymentMethod: "CASH",
      reconciliationState: "PENDING",
      search: "  CF-100  ",
      sourceType: "OPERATIONAL_PAYMENT",
      workstationId: "station-1",
    };

    const path = buildAdminCashFlowListPath(filters);

    expect(path).toContain("/v1/admin/cash-flow?");
    expect(path).toContain("page=2");
    expect(path).toContain("page_size=50");
    expect(path).toContain("amount_min=10");
    expect(path).toContain("amount_max=500");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("workstation_id=station-1");
    expect(path).toContain("direction=OUTFLOW");
    expect(path).toContain("source_type=OPERATIONAL_PAYMENT");
    expect(path).toContain("payment_method=CASH");
    expect(path).toContain("reconciliation_state=PENDING");
    expect(path).toContain("category=Pago+operativo");
    expect(path).toContain("operator_id=user-1");
    expect(path).toContain("search=CF-100");
    expect(path).toContain("date_from=2026-05-01T00%3A00%3A00.000Z");
    expect(path).toContain("date_to=2026-05-21T23%3A59%3A59.999Z");
  });

  it("maps backend cash flow movements without inventing values", () => {
    const mapped = mapAdminCashFlowMovementFromApi({
      amount: "125.00",
      branch_id: "branch-1",
      branch_name: "Centro",
      category: "Pago operativo",
      currency: "MXN",
      direction: "OUTFLOW",
      id: "OPERATIONAL_PAYMENT:payment-1",
      occurred_at: "2026-05-21T18:00:00Z",
      operator_id: "user-1",
      operator_name: "Admin",
      payment_method: "CASH",
      reconciliation_status: "NOT_REQUIRED",
      source_document_id: "payment-1",
      source_reference: "PAGO-100",
      source_type: "OPERATIONAL_PAYMENT",
      warning_state: "ok",
      workstation_id: "station-1",
      workstation_name: "Mostrador 1",
    });

    expect(mapped.id).toBe("OPERATIONAL_PAYMENT:payment-1");
    expect(mapped.sourceReference).toBe("PAGO-100");
    expect(mapped.amount).toBe("125.00");
    expect(mapped.direction).toBe("OUTFLOW");
    expect(mapped.category).toBe("Pago operativo");
    expect(mapped.reconciliationStatus).toBe("NOT_REQUIRED");
  });
});
