import { apiRequest } from "@/services/http/client";
import type {
    AdminRole,
    AdminRoleCreateInput,
    AdminRoleUpdateInput,
} from "@/types/admin/role";

export async function listAdminRoles(params: {
    token: string;
    includeInactive?: boolean;
}): Promise<AdminRole[]> {
    const searchParams = new URLSearchParams();

    if (typeof params.includeInactive === "boolean") {
        searchParams.set("include_inactive", String(params.includeInactive));
    }

    const qs = searchParams.toString();
    const path = qs ? `/admin/roles?${qs}` : "/admin/roles";

    return apiRequest<AdminRole[]>(path, {
        method: "GET",
        token: params.token,
    });
}

export async function createAdminRole(params: {
    token: string;
    input: AdminRoleCreateInput;
}): Promise<AdminRole> {
    return apiRequest<AdminRole>("/admin/roles", {
        method: "POST",
        token: params.token,
        body: JSON.stringify(params.input),
    });
}

export async function updateAdminRole(params: {
    token: string;
    roleId: number;
    input: AdminRoleUpdateInput;
}): Promise<AdminRole> {
    return apiRequest<AdminRole>(`/admin/roles/${params.roleId}`, {
        method: "PATCH",
        token: params.token,
        body: JSON.stringify(params.input),
    });
}

export async function deactivateAdminRole(params: {
    token: string;
    roleId: number;
}): Promise<AdminRole> {
    return apiRequest<AdminRole>(`/admin/roles/${params.roleId}`, {
        method: "DELETE",
        token: params.token,
    });
}
