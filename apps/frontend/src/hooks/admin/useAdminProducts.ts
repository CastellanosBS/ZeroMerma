import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    createAdminProduct,
    deactivateAdminProduct,
    listAdminProducts,
    updateAdminProduct,
} from "@/services/admin/products";
import type {
    AdminProduct,
    AdminProductCreateInput,
    AdminProductUpdateInput,
} from "@/types/admin/product";

export function useAdminProducts(params: {
    token: string | null;
    includeInactive?: boolean;
    q?: string;
    categoryId?: number;
    isInput?: boolean;
}) {
    return useQuery<AdminProduct[]>({
        queryKey: [
            "admin",
            "products",
            params.includeInactive ?? true,
            params.q ?? "",
            params.categoryId ?? "all",
            params.isInput ?? "all",
        ],
        enabled: Boolean(params.token),
        queryFn: async () => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return listAdminProducts({
                token: params.token,
                includeInactive: params.includeInactive ?? true,
                q: params.q,
                categoryId: params.categoryId,
                isInput: params.isInput,
            });
        },
    });
}

export function useCreateAdminProduct(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<AdminProduct, Error, AdminProductCreateInput>({
        mutationFn: async (input) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return createAdminProduct({
                token: params.token,
                input,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "products"],
            });
        },
    });
}

export function useUpdateAdminProduct(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<
        AdminProduct,
        Error,
        { productId: number; input: AdminProductUpdateInput }
    >({
        mutationFn: async ({ productId, input }) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return updateAdminProduct({
                token: params.token,
                productId,
                input,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "products"],
            });
        },
    });
}

export function useDeactivateAdminProduct(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<AdminProduct, Error, { productId: number }>({
        mutationFn: async ({ productId }) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return deactivateAdminProduct({
                token: params.token,
                productId,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "products"],
            });
        },
    });
}
