import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    createAdminRole,
    deactivateAdminRole,
    listAdminRoles,
    updateAdminRole,
} from "@/services/admin/roles";
import type {
    AdminRole,
    AdminRoleCreateInput,
    AdminRoleUpdateInput,
} from "@/types/admin/role";

export function useAdminRoles(params: {
    token: string | null;
    includeInactive?: boolean;
}) {
    return useQuery<AdminRole[]>({
        queryKey: ["admin", "roles", params.includeInactive ?? true],
        enabled: Boolean(params.token),
        queryFn: async () => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return listAdminRoles({
                token: params.token,
                includeInactive: params.includeInactive ?? true,
            });
        },
    });
}

export function useCreateAdminRole(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<AdminRole, Error, AdminRoleCreateInput>({
        mutationFn: async (input) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return createAdminRole({
                token: params.token,
                input,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "roles"],
            });
        },
    });
}

export function useUpdateAdminRole(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<
        AdminRole,
        Error,
        { roleId: number; input: AdminRoleUpdateInput }
    >({
        mutationFn: async ({ roleId, input }) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return updateAdminRole({
                token: params.token,
                roleId,
                input,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "roles"],
            });
        },
    });
}

export function useDeactivateAdminRole(params: { token: string | null }) {
    const queryClient = useQueryClient();

    return useMutation<AdminRole, Error, { roleId: number }>({
        mutationFn: async ({ roleId }) => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return deactivateAdminRole({
                token: params.token,
                roleId,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["admin", "roles"],
            });
        },
    });
}
