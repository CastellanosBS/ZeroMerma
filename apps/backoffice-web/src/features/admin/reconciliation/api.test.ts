import { describe, expect, it } from "vitest";

import { buildAdminReconciliationListPath, mapAdminReconciliationItemFromApi } from "./api";
import type { AdminReconciliationListFilters } from "./types";

describe("admin reconciliation API helpers", () => {
  it("builds the reconciliation list path with supported filters only", () => {
    const filters: AdminReconciliationListFilters = {
      amountMax: "250",
      amountMin: "10",
      branchId: "branch-1",
      cashierId: "user-1",
      dateFrom: "2026-05-01",
      dateTo: "2026-05-21",
      discrepancyType: "OVERAGE",
      evidenceState: "WITH_EVIDENCE",
      page: 2,
      pageSize: 50,
      paymentMethod: "CASH",
      search: "  CON-100  ",
      sourceType: "CASH_CUT",
      status: "IN_REVIEW",
      workstationId: "station-1",
    };

    const path = buildAdminReconciliationListPath(filters);

    expect(path).toContain("/v1/admin/reconciliation?");
    expect(path).toContain("page=2");
    expect(path).toContain("page_size=50");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("workstation_id=station-1");
    expect(path).toContain("cashier_id=user-1");
    expect(path).toContain("discrepancy_type=OVERAGE");
    expect(path).toContain("evidence_state=WITH_EVIDENCE");
    expect(path).toContain("payment_method=CASH");
    expect(path).toContain("source_type=CASH_CUT");
    expect(path).toContain("status=IN_REVIEW");
    expect(path).toContain("amount_min=10");
    expect(path).toContain("amount_max=250");
    expect(path).toContain("search=CON-100");
    expect(path).toContain("date_from=2026-05-01T00%3A00%3A00.000Z");
    expect(path).toContain("date_to=2026-05-21T23%3A59%3A59.999Z");
  });

  it("maps backend reconciliation list items without inventing values", () => {
    const mapped = mapAdminReconciliationItemFromApi({
      actual_amount: "1125.00",
      branch_id: "branch-1",
      branch_name: "Centro",
      difference_amount: "5.00",
      difference_direction: "OVERAGE",
      expected_amount: "1120.00",
      folio: "CON-100",
      has_evidence: true,
      id: "reconciliation-1",
      occurred_at: "2026-05-21T18:00:00Z",
      operator_id: "user-1",
      operator_name: "Admin",
      payment_method: "CASH",
      reason_code: "COUNTING_ERROR",
      source_document_id: "close-1",
      source_reference: "CC-100",
      source_type: "CASH_CUT",
      status: "IN_REVIEW",
      updated_at: "2026-05-21T19:00:00Z",
      warning_state: "warning",
      workstation_id: "station-1",
      workstation_name: "Mostrador 1",
    });

    expect(mapped.folio).toBe("CON-100");
    expect(mapped.sourceReference).toBe("CC-100");
    expect(mapped.status).toBe("IN_REVIEW");
    expect(mapped.differenceDirection).toBe("OVERAGE");
    expect(mapped.hasEvidence).toBe(true);
    expect(mapped.operatorName).toBe("Admin");
  });
});
