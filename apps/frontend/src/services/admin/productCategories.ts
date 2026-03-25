import { apiRequest } from "@/services/http/client";
import type { AdminProductCategory } from "@/types/admin/product-category";

export async function listAdminProductCategories(params: {
    token: string;
    includeInactive?: boolean;
}): Promise<AdminProductCategory[]> {
    const searchParams = new URLSearchParams();

    if (typeof params.includeInactive === "boolean") {
        searchParams.set("include_inactive", String(params.includeInactive));
    }

    const qs = searchParams.toString();
    const path = qs
        ? `/admin/product-categories?${qs}`
        : "/admin/product-categories";

    return apiRequest<AdminProductCategory[]>(path, {
        method: "GET",
        token: params.token,
    });
}
