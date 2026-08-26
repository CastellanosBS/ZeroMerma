import { describe, expect, it, vi } from "vitest";

import {
  buildAdminCorrectionsListPath,
  buildAdminReturnsListPath,
  fetchAdminCorrectionDetail,
  fetchAdminCorrections,
  fetchAdminReturnDetail,
  fetchAdminReturns,
  mapAdminCorrectionFromApi,
  mapAdminReturnFromApi,
} from "./api";
import type { AdminCorrectionListFilters, AdminReturnListFilters } from "./types";

const apiBase = "http://localhost:8000";

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json" },
    status: 200,
  });
}

const returnFilters: AdminReturnListFilters = {
  branchId: "all",
  dateFrom: null,
  dateTo: null,
  maxAmount: null,
  minAmount: null,
  operatorId: "all",
  page: 1,
  pageSize: 25,
  refundMethod: "all",
  search: "",
  status: "all",
};

const correctionFilters: AdminCorrectionListFilters = {
  branchId: "all",
  correctionType: "all",
  dateFrom: null,
  dateTo: null,
  netEffect: "all",
  operatorId: "all",
  page: 1,
  pageSize: 25,
  reasonCode: "all",
  search: "",
  status: "all",
  targetDocumentType: "all",
};

const returnListItem = {
  branch_id: "branch-1",
  branch_name: "Main Branch",
  created_at: "2026-05-20T10:00:00Z",
  folio: "DEV-123",
  id: "return-1",
  operator_id: "user-1",
  operator_name: "Cashier",
  original_sale_id: "sale-1",
  original_ticket_folio: "TCK-123",
  refunded_amount: "12.00",
  refund_method: "CASH",
  returned_line_count: 1,
  status: "COMMITTED",
  warning_state: null,
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register",
};

const correctionListItem = {
  branch_id: "branch-1",
  branch_name: "Main Branch",
  correction_type: "QUANTITY_ADJUSTMENT",
  created_at: "2026-05-20T11:00:00Z",
  folio: "COR-123",
  id: "correction-1",
  line_count: 1,
  net_effect: "NEGATIVE",
  net_effect_quantity: "-1.000",
  operator_id: "user-1",
  operator_name: "Cashier",
  original_document_folio: "OP-123",
  original_document_id: "document-1",
  original_document_type: "COUNTER_TRANSFER",
  reason_code: "COUNT_ERROR",
  reason_name: "Error de conteo",
  status: "COMMITTED",
  total_units_affected: "1.000",
  warning_state: null,
  workstation_code: "POS-01",
  workstation_id: "workstation-1",
  workstation_name: "Front Register",
};

const returnsPayload = {
  backend_contract: {
    create_endpoint: null,
    detail_endpoint: "GET /v1/admin/returns-corrections/returns/{return_id}",
    list_endpoint: "GET /v1/admin/returns-corrections/returns",
    reprint_endpoint: null,
  },
  filter_options: {
    branches: [{ id: "branch-1", label: "Main Branch" }],
    operators: [{ id: "user-1", label: "Cashier" }],
    refund_methods: [{ id: "CASH", label: "Efectivo" }],
    statuses: [{ id: "COMMITTED", label: "Confirmado" }],
  },
  is_backend_connected: true,
  items: [returnListItem],
  metrics: {
    cash_refunded_amount: "12.00",
    pending_review_count: 0,
    refunded_amount: "12.00",
    returned_line_count: 1,
    returns_count: 1,
  },
  page: 1,
  page_size: 25,
  total: 1,
};

const correctionsPayload = {
  backend_contract: {
    create_endpoint: null,
    detail_endpoint: "GET /v1/admin/returns-corrections/corrections/{correction_id}",
    list_endpoint: "GET /v1/admin/returns-corrections/corrections",
    print_endpoint: null,
  },
  filter_options: {
    branches: [{ id: "branch-1", label: "Main Branch" }],
    correction_types: [{ id: "QUANTITY_ADJUSTMENT", label: "Ajuste de cantidad" }],
    operators: [{ id: "user-1", label: "Cashier" }],
    reasons: [{ id: "COUNT_ERROR", label: "Error de conteo" }],
    statuses: [{ id: "COMMITTED", label: "Confirmado" }],
    target_document_types: [{ id: "COUNTER_TRANSFER", label: "Paso a mostrador" }],
  },
  is_backend_connected: true,
  items: [correctionListItem],
  metrics: {
    corrections_count: 1,
    negative_effect_count: 1,
    pending_review_count: 0,
    positive_effect_count: 0,
    total_units_affected: "1.000",
  },
  page: 1,
  page_size: 25,
  total: 1,
};

const returnDetailPayload = {
  ...returnsPayload,
  audit_summary: null,
  available_actions: {
    can_create_from_backoffice: false,
    can_open_original_ticket: true,
    can_reprint: false,
    creation_note: "Las devoluciones nuevas requieren caja abierta.",
  },
  backend_contract: returnsPayload.backend_contract,
  original_ticket: {
    branch_name: "Main Branch",
    cash_session_id: "cash-1",
    cashier_name: "Cashier",
    folio: "TCK-123",
    payment_methods_label: "CASH",
    sale_date: "2026-05-20T09:55:00Z",
    sale_id: "sale-1",
    status: "CONFIRMED",
    total_amount: "24.00",
    workstation_name: "Front Register",
  },
  overview: {
    branch_id: "branch-1",
    branch_name: "Main Branch",
    created_at: "2026-05-20T10:00:00Z",
    folio: "DEV-123",
    id: "return-1",
    is_partial_return: true,
    notes: null,
    operator_id: "user-1",
    operator_name: "Cashier",
    reason_code: "DAMAGED",
    reason_name: "Producto dañado",
    refund_method: "CASH",
    status: "COMMITTED",
    total_refund_amount: "12.00",
    workstation_code: "POS-01",
    workstation_id: "workstation-1",
    workstation_name: "Front Register",
  },
  refund_impact: {
    cash_impact_amount: "12.00",
    cash_session_id: "cash-1",
    currency_code: "MXN",
    linked_cash_movement_id: "cash-movement-1",
    refund_amount: "12.00",
    refund_method: "CASH",
  },
  related_documents: [],
  returned_lines: [
    {
      disposition_code: "WASTE",
      id: "return-line-1",
      line_status: "RETURNED",
      original_quantity: "2.000",
      original_sale_line_id: "sale-line-1",
      product_class_code: "PAN-DULCE",
      product_class_name: "Pan dulce",
      product_code: "CONCHA",
      product_name: "Concha",
      refund_amount: "12.00",
      returned_quantity: "1.000",
      unit_price: "12.00",
    },
  ],
};

const correctionDetailPayload = {
  affected_lines: [
    {
      corrected_quantity: "1.000",
      difference_quantity: "-1.000",
      id: "correction-line-1",
      notes: null,
      original_quantity: "2.000",
      product_class_code: "PAN-DULCE",
      product_class_name: "Pan dulce",
      product_code: "CONCHA",
      product_name: "Concha",
      target_line_id: "line-1",
      unit_of_measure_code: "PIECE",
    },
  ],
  available_actions: {
    can_create_from_backoffice: false,
    can_open_original_document: true,
    can_print: false,
    creation_note: "Las correcciones nuevas requieren caja/workstation operativo.",
  },
  backend_contract: correctionsPayload.backend_contract,
  net_effect: {
    cash_effect: "Sin impacto directo de caja",
    inventory_effect: "Afecta conteo operativo",
    net_effect: "NEGATIVE",
    total_amount_affected: null,
    total_units_affected: "1.000",
  },
  original_document: {
    branch_name: "Main Branch",
    document_type: "COUNTER_TRANSFER",
    folio: "OP-123",
    id: "document-1",
    occurred_at: "2026-05-20T09:00:00Z",
    operator_name: "Cashier",
    route_hint: null,
    status: "COMMITTED",
    workstation_name: "Front Register",
  },
  overview: correctionListItem,
  reason_notes: {
    audit_summary: null,
    notes: "Conteo corregido",
    reason_code: "COUNT_ERROR",
    reason_name: "Error de conteo",
  },
  related_documents: [],
};

describe("admin returns corrections api", () => {
  it("builds return and correction query params", () => {
    expect(
      buildAdminReturnsListPath({
        ...returnFilters,
        branchId: "branch-1",
        dateFrom: "2026-05-20",
        dateTo: "2026-05-21",
        refundMethod: "CASH",
        search: " DEV-123 ",
        status: "COMMITTED",
      }),
    ).toBe(
      "/v1/admin/returns-corrections/returns?page=1&page_size=25&branch_id=branch-1&date_from=2026-05-20&date_to=2026-05-21&refund_method=CASH&search=DEV-123&status=COMMITTED",
    );

    expect(
      buildAdminCorrectionsListPath({
        ...correctionFilters,
        correctionType: "QUANTITY_ADJUSTMENT",
        netEffect: "NEGATIVE",
        search: " COR-123 ",
        targetDocumentType: "COUNTER_TRANSFER",
      }),
    ).toBe(
      "/v1/admin/returns-corrections/corrections?page=1&page_size=25&correction_type=QUANTITY_ADJUSTMENT&net_effect=NEGATIVE&search=COR-123&target_document_type=COUNTER_TRANSFER",
    );
  });

  it("maps list item shapes", () => {
    expect(mapAdminReturnFromApi(returnListItem).folio).toBe("DEV-123");
    expect(mapAdminCorrectionFromApi(correctionListItem).netEffect).toBe("NEGATIVE");
  });

  it("fetches returns and corrections list/detail endpoints", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(jsonResponse(returnsPayload))
      .mockResolvedValueOnce(jsonResponse(correctionsPayload))
      .mockResolvedValueOnce(jsonResponse(returnDetailPayload))
      .mockResolvedValueOnce(jsonResponse(correctionDetailPayload));

    const returns = await fetchAdminReturns("token", returnFilters);
    const corrections = await fetchAdminCorrections("token", correctionFilters);
    const returnDetail = await fetchAdminReturnDetail("token", "return-1");
    const correctionDetail = await fetchAdminCorrectionDetail("token", "correction-1");

    expect(returns.items[0]?.folio).toBe("DEV-123");
    expect(corrections.items[0]?.folio).toBe("COR-123");
    expect(returnDetail.returnedLines[0]?.productName).toBe("Concha");
    expect(correctionDetail.affectedLines[0]?.differenceQuantity).toBe("-1.000");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `${apiBase}/v1/admin/returns-corrections/returns?page=1&page_size=25`,
      expect.objectContaining({ method: "GET" }),
    );
    fetchMock.mockRestore();
  });
});
