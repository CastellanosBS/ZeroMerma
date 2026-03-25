import { apiRequest } from "@/services/http/client";
import type {
    AdminProduct,
    AdminProductCreateInput,
    AdminProductUpdateInput,
} from "@/types/admin/product";

export async function listAdminProducts(params: {
    token: string;
    includeInactive?: boolean;
    q?: string;
    categoryId?: number;
    isInput?: boolean;
}): Promise<AdminProduct[]> {
    const searchParams = new URLSearchParams();

    if (typeof params.includeInactive === "boolean") {
        searchParams.set("include_inactive", String(params.includeInactive));
    }

    if (params.q && params.q.trim()) {
        searchParams.set("q", params.q.trim());
    }

    if (typeof params.categoryId === "number") {
        searchParams.set("category_id", String(params.categoryId));
    }

    if (typeof params.isInput === "boolean") {
        searchParams.set("is_input", String(params.isInput));
    }

    const qs = searchParams.toString();
    const path = qs ? `/admin/products?${qs}` : "/admin/products";

    return apiRequest<AdminProduct[]>(path, {
        method: "GET",
        token: params.token,
    });
}

export async function createAdminProduct(params: {
    token: string;
    input: AdminProductCreateInput;
}): Promise<AdminProduct> {
    return apiRequest<AdminProduct>("/admin/products", {
        method: "POST",
        token: params.token,
        body: JSON.stringify(params.input),
    });
}

export async function updateAdminProduct(params: {
    token: string;
    productId: number;
    input: AdminProductUpdateInput;
}): Promise<AdminProduct> {
    return apiRequest<AdminProduct>(`/admin/products/${params.productId}`, {
        method: "PATCH",
        token: params.token,
        body: JSON.stringify(params.input),
    });
}

export async function deactivateAdminProduct(params: {
    token: string;
    productId: number;
}): Promise<AdminProduct> {
    return apiRequest<AdminProduct>(`/admin/products/${params.productId}`, {
        method: "DELETE",
        token: params.token,
    });
}
