import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    createAdminUserAccount,
    deactivateAdminUserAccount,
    listAdminUserAccounts,
    updateAdminUserAccount,
} from "@/services/admin/userAccounts";
import type {
    AdminUserAccount,
    AdminUserAccountCreateInput,
    AdminUserAccountUpdateInput,
} from "@/types/admin/user-account";

export function useAdminUserAccounts(params: {
    token: string | null;
    includeInactive?: boolean;
    q?: string;
}) {
    return useQuery<AdminUserAccount[]>({
        queryKey: [
            "admin",
            "user-accounts",
            params.includeInactive ?? true,
            params.q ?? "",
        ],
        enabled: Boolean(params.token),
        queryFn: async () => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return listAdminUserAccounts({
                token: params.token,
                includeInactive: params.includeInactive ?? true,
                q: params.q,
            });
        },
    });
}

export function useCreateAdminUserAccount(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<AdminUserAccount, Error, AdminUserAccountCreateInput>({
        mutationFn: async (input) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return createAdminUserAccount({
                token: params.token,
                input,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "user-accounts"],
            });
        },
    });
}

export function useUpdateAdminUserAccount(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<
        AdminUserAccount,
        Error,
        { userId: number; input: AdminUserAccountUpdateInput }
    >({
        mutationFn: async ({ userId, input }) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return updateAdminUserAccount({
                token: params.token,
                userId,
                input,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "user-accounts"],
            });
        },
    });
}

export function useDeactivateAdminUserAccount(params: {
    token: string | null;
}) {
    const queryClient = useQueryClient();

    return useMutation<AdminUserAccount, Error, { userId: number }>({
        mutationFn: async ({ userId }) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return deactivateAdminUserAccount({
                token: params.token,
                userId,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "user-accounts"],
            });
        },
    });
}
