import { useQuery } from "@tanstack/react-query";

import { listAdminProductCategories } from "@/services/admin/productCategories";
import type { AdminProductCategory } from "@/types/admin/product-category";

export function useAdminProductCategories(params: {
    token: string | null;
    includeInactive?: boolean;
}) {
    return useQuery<AdminProductCategory[]>({
        queryKey: [
            "admin",
            "product-categories",
            params.includeInactive ?? false,
        ],
        enabled: Boolean(params.token),
        queryFn: async () => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return listAdminProductCategories({
                token: params.token,
                includeInactive: params.includeInactive ?? false,
            });
        },
    });
}
