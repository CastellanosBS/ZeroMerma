import { describe, expect, it, vi } from "vitest";

import {
  buildAdminDiscountsListPath,
  createAdminDiscount,
  fetchAdminDiscounts,
  updateAdminDiscount,
} from "./api";
import type { AdminDiscountListFilters } from "./types";

const baseFilters: AdminDiscountListFilters = {
  page: 1,
  pageSize: 25,
  discountType: "all",
  search: "",
  status: "all",
  targetScope: "all",
  validity: "all",
  warningState: "all",
};

function mockFetch(payload: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(payload),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("admin discounts API", () => {
  it("builds list query params without all filters", () => {
    const path = buildAdminDiscountsListPath({
      ...baseFilters,
      brandId: "brand-1",
      classId: "class-1",
      discountType: "PERCENTAGE",
      search: "coca",
      status: "ACTIVE",
      targetScope: "PRODUCT",
      validity: "current",
      warningState: "with_warnings",
    });

    expect(path).toContain("/v1/admin/discounts?");
    expect(path).toContain("brand_id=brand-1");
    expect(path).toContain("class_id=class-1");
    expect(path).toContain("discount_type=PERCENTAGE");
    expect(path).toContain("search=coca");
    expect(path).toContain("status=ACTIVE");
    expect(path).toContain("target_scope=PRODUCT");
    expect(path).toContain("validity=current");
    expect(path).toContain("warning_state=with_warnings");
  });

  it("maps list response from API", async () => {
    mockFetch({
      backend_contract: {},
      filter_options: {
        brands: [{ id: "brand-1", label: "Brand" }],
        classes: [{ id: "class-1", label: "Class" }],
        products: [{ id: "product-1", label: "Product" }],
      },
      is_backend_connected: true,
      items: [
        {
          base_price: "30.00",
          brand_id: "brand-1",
          brand_name: "Brand",
          code: "DISC-10",
          created_at: "2026-05-20T00:00:00Z",
          currency_code: "MXN",
          description: null,
          discount_type: "PERCENTAGE",
          health: "healthy",
          id: "discount-1",
          is_pos_eligible: true,
          name: "Ten percent",
          preview_price: "27.00",
          priority: 1000,
          status: "ACTIVE",
          target_class_id: "class-1",
          target_class_name: "Class",
          target_code: "P1",
          target_id: "product-1",
          target_name: "Product",
          target_scope: "PRODUCT",
          target_status: "active",
          updated_at: "2026-05-20T00:00:00Z",
          valid_from_utc: null,
          valid_to_utc: null,
          validity_status: "not_scheduled",
          value: "10.0000",
          warnings: { codes: [], messages: [] },
        },
      ],
      metrics: {
        active_discounts: 1,
        class_scoped: 0,
        expired_discounts: 0,
        product_scoped: 1,
        total_discounts: 1,
        upcoming_discounts: 0,
        with_warnings: 0,
      },
      page: 1,
      page_size: 25,
      total: 1,
    });

    const response = await fetchAdminDiscounts("token", baseFilters);

    expect(response.items).toHaveLength(1);
    expect(response.items[0]?.name).toBe("Ten percent");
    expect(response.metrics.activeDiscounts).toBe("1");
    expect(response.filterOptions.products[0]?.label).toBe("Product");
  });

  it("posts and patches canonical payloads", async () => {
    const fetchMock = mockFetch({
      base_price: null,
      brand_id: null,
      brand_name: null,
      code: "DISC",
      created_at: "2026-05-20T00:00:00Z",
      currency_code: "MXN",
      description: null,
      discount_type: "PERCENTAGE",
      health: "healthy",
      id: "discount-1",
      is_pos_eligible: true,
      name: "Discount",
      preview_price: null,
      priority: 1000,
      status: "INACTIVE",
      target_class_id: null,
      target_class_name: null,
      target_code: null,
      target_id: null,
      target_name: "Alcance global",
      target_scope: "GLOBAL",
      target_status: null,
      updated_at: "2026-05-20T00:00:00Z",
      valid_from_utc: null,
      valid_to_utc: null,
      validity_status: "not_scheduled",
      value: "10.0000",
      warnings: { codes: [], messages: [] },
    });
    const payload = {
      code: "DISC",
      currencyCode: "MXN",
      description: null,
      discountType: "PERCENTAGE" as const,
      isPosEligible: true,
      name: "Discount",
      priority: 1000,
      status: "INACTIVE" as const,
      targetId: null,
      targetScope: "GLOBAL" as const,
      value: "10.0000",
    };

    await createAdminDiscount("token", payload);
    await updateAdminDiscount("token", "discount-1", payload);

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/v1/admin/discounts"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/v1/admin/discounts/discount-1"),
      expect.objectContaining({ method: "PATCH" }),
    );
  });
});
