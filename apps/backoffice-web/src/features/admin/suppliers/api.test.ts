import { afterEach, describe, expect, it, vi } from "vitest";

import {
  buildAdminSuppliersListPath,
  changeAdminSupplierStatus,
  createAdminSupplier,
  fetchAdminSupplierDetail,
  fetchAdminSuppliers,
} from "./api";
import type { AdminSupplierListFilters } from "./types";

const filters: AdminSupplierListFilters = {
  category: "all",
  page: 1,
  pageSize: 25,
  productKind: "all",
  search: "",
  status: "all",
  warningState: "all",
};

const apiSupplierItem = {
  branch_count: 1,
  category: "RAW_MATERIALS",
  code: "SUP-HARINA",
  commercial_name: "Harinas del Centro",
  id: "supplier-1",
  legal_name: "Harinas del Centro SA de CV",
  primary_contact_email: "compras@harinas.example",
  primary_contact_name: "Ana Lopez",
  primary_contact_phone: "555-0101",
  product_count: 2,
  status: "ACTIVE",
  tax_id: "HCE010101AA1",
  terms_summary: "Credito 15 dias",
  updated_at: "2026-05-20T10:00:00Z",
  warning_state: "warning",
  warnings: [{ code: "missing_branch", message: "Proveedor sin sucursales asociadas.", severity: "warning" }],
} as const;

const apiSupplierDetail = {
  available_actions: {
    can_add_contact: true,
    can_add_product: true,
    can_block: true,
    can_deactivate: true,
    can_edit: true,
  },
  branch_applicability: [
    {
      branch_code: "MAIN",
      branch_id: "branch-1",
      branch_name: "Centro",
      branch_status: "ACTIVE",
      delivery_notes: "Lunes",
      is_active: true,
    },
  ],
  commercial_terms: {
    credit_days: 15,
    default_currency: "MXN",
    delivery_notes: "Entrega matutina",
    lead_time_days: 2,
    minimum_order_amount: "500.00",
    payment_terms_type: "CREDIT",
    purchase_notes: "Confirmar un dia antes",
    summary: "Credito 15 dias",
  },
  contacts: [
    {
      email: "compras@harinas.example",
      id: "contact-1",
      is_active: true,
      is_primary: true,
      name: "Ana Lopez",
      notes: null,
      phone: "555-0101",
      role: "Ventas",
      whatsapp: null,
    },
  ],
  fiscal_legal: {
    fiscal_address: "Calle Central 123",
    fiscal_regime: null,
    legal_name: "Harinas del Centro SA de CV",
    notes: "Proveedor prioritario",
    payment_fiscal_email: "facturas@harinas.example",
    tax_id: "HCE010101AA1",
  },
  operational_activity: {
    integration_available: false,
    notes: "Purchase orders, receipts, invoices and supplier payments are pending canonical backend modules.",
    open_purchase_orders: null,
    recent_purchase_orders: null,
  },
  overview: {
    category: "RAW_MATERIALS",
    code: "SUP-HARINA",
    commercial_name: "Harinas del Centro",
    created_at: "2026-05-20T09:00:00Z",
    id: "supplier-1",
    legal_name: "Harinas del Centro SA de CV",
    readiness_state: "warning",
    status: "ACTIVE",
    tax_id: "HCE010101AA1",
    updated_at: "2026-05-20T10:00:00Z",
  },
  product_associations: [
    {
      currency: "MXN",
      id: "supplier-product-1",
      is_active: true,
      last_known_price: "18.50",
      lead_time_days: 2,
      minimum_order_qty: "25.000",
      notes: null,
      product_code: "HARINA-1KG",
      product_id: "product-1",
      product_kind: "RAW_MATERIAL",
      product_name: "Harina 1 kg",
      purchase_uom: "KG",
      supplier_sku: "H-1KG",
    },
  ],
  related_documents: [],
  warnings: [{ code: "missing_branch", message: "Proveedor sin sucursales asociadas.", severity: "warning" }],
} as const;

function mockJsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      headers: { "Content-Type": "application/json" },
      status,
    }),
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("admin suppliers API boundary", () => {
  it("builds supplier list query parameters", () => {
    const path = buildAdminSuppliersListPath({
      ...filters,
      branchId: "branch-1",
      category: "RAW_MATERIALS",
      productKind: "RAW_MATERIAL",
      search: "harina",
      status: "ACTIVE",
      warningState: "with_warnings",
    });

    expect(path).toContain("/v1/admin/suppliers?");
    expect(path).toContain("branch_id=branch-1");
    expect(path).toContain("category=RAW_MATERIALS");
    expect(path).toContain("product_kind=RAW_MATERIAL");
    expect(path).toContain("search=harina");
    expect(path).toContain("status=ACTIVE");
    expect(path).toContain("warning_state=with_warnings");
  });

  it("fetches and maps suppliers from backend", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      mockJsonResponse({
        backend_contract: undefined,
        filter_options: {
          branches: [{ id: "branch-1", label: "Centro - MAIN" }],
          categories: [{ id: "RAW_MATERIALS", label: "Materia prima" }],
          product_kinds: [{ id: "RAW_MATERIAL", label: "Materia prima" }],
          products: [{ id: "product-1", label: "Harina 1 kg - HARINA-1KG" }],
          statuses: [{ id: "ACTIVE", label: "Activo" }],
          warning_states: [{ id: "with_warnings", label: "Con advertencias" }],
        },
        is_backend_connected: true,
        items: [apiSupplierItem],
        metrics: {
          active_suppliers: 1,
          blocked_suppliers: 0,
          inactive_suppliers: 0,
          suppliers_with_recent_activity: 0,
          suppliers_with_warnings: 1,
          suppliers_without_products: 0,
          total_suppliers: 1,
        },
        page: 1,
        page_size: 25,
        total: 1,
      }),
    );

    const response = await fetchAdminSuppliers("token-1", filters);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/suppliers?page=1&page_size=25"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(response.items[0]?.legalName).toBe("Harinas del Centro SA de CV");
    expect(response.items[0]?.productCount).toBe(2);
    expect(response.filterOptions.productKinds[0]?.id).toBe("RAW_MATERIAL");
    expect(response.metrics.suppliersWithWarnings).toBe("1");
  });

  it("loads supplier detail", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiSupplierDetail));

    const detail = await fetchAdminSupplierDetail("token-1", "supplier-1");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/suppliers/supplier-1"),
      expect.objectContaining({ method: "GET" }),
    );
    expect(detail.overview.code).toBe("SUP-HARINA");
    expect(detail.contacts[0]?.name).toBe("Ana Lopez");
    expect(detail.productAssociations[0]?.productCode).toBe("HARINA-1KG");
  });

  it("creates supplier and changes supplier status through backend endpoints", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(() => mockJsonResponse(apiSupplierDetail, 201));

    await createAdminSupplier("token-1", {
      branchIds: ["branch-1"],
      category: "RAW_MATERIALS",
      code: "SUP-HARINA",
      commercialName: "Harinas del Centro",
      contacts: [{ email: "compras@harinas.example", isPrimary: true, name: "Ana Lopez", phone: "555-0101" }],
      creditDays: 15,
      defaultCurrency: "MXN",
      leadTimeDays: 2,
      legalName: "Harinas del Centro SA de CV",
      minimumOrderAmount: "500.00",
      paymentTermsType: "CREDIT",
      productRelations: [{ productId: "product-1" }],
      status: "ACTIVE",
      taxId: "HCE010101AA1",
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/v1/admin/suppliers"),
      expect.objectContaining({
        body: expect.stringContaining("\"legal_name\":\"Harinas del Centro SA de CV\""),
        method: "POST",
      }),
    );

    await changeAdminSupplierStatus("token-1", "supplier-1", { notes: "Bloqueo operativo", status: "BLOCKED" });
    expect(fetchSpy).toHaveBeenLastCalledWith(
      expect.stringContaining("/v1/admin/suppliers/supplier-1/status"),
      expect.objectContaining({
        body: JSON.stringify({ notes: "Bloqueo operativo", status: "BLOCKED" }),
        method: "POST",
      }),
    );
  });
});
