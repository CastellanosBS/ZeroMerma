import { apiRequest } from "@/services/http/client";
import type {
    AdminUserAccount,
    AdminUserAccountCreateInput,
    AdminUserAccountUpdateInput,
} from "@/types/admin/user-account";

export async function listAdminUserAccounts(params: {
    token: string;
    includeInactive?: boolean;
    q?: string;
}): Promise<AdminUserAccount[]> {
    const searchParams = new URLSearchParams();

    if (typeof params.includeInactive === "boolean") {
        searchParams.set("include_inactive", String(params.includeInactive));
    }

    if (params.q && params.q.trim()) {
        searchParams.set("q", params.q.trim());
    }

    const qs = searchParams.toString();
    const path = qs ? `/admin/user-accounts?${qs}` : "/admin/user-accounts";

    return apiRequest<AdminUserAccount[]>(path, {
        method: "GET",
        token: params.token,
    });
}

export async function getAdminUserAccount(params: {
    token: string;
    userId: number;
}): Promise<AdminUserAccount> {
    return apiRequest<AdminUserAccount>(
        `/admin/user-accounts/${params.userId}`,
        {
            method: "GET",
            token: params.token,
        },
    );
}

export async function createAdminUserAccount(params: {
    token: string;
    input: AdminUserAccountCreateInput;
}): Promise<AdminUserAccount> {
    return apiRequest<AdminUserAccount>("/admin/user-accounts", {
        method: "POST",
        token: params.token,
        body: JSON.stringify(params.input),
    });
}

export async function updateAdminUserAccount(params: {
    token: string;
    userId: number;
    input: AdminUserAccountUpdateInput;
}): Promise<AdminUserAccount> {
    return apiRequest<AdminUserAccount>(
        `/admin/user-accounts/${params.userId}`,
        {
            method: "PATCH",
            token: params.token,
            body: JSON.stringify(params.input),
        },
    );
}

export async function deactivateAdminUserAccount(params: {
    token: string;
    userId: number;
}): Promise<AdminUserAccount> {
    return apiRequest<AdminUserAccount>(
        `/admin/user-accounts/${params.userId}`,
        {
            method: "DELETE",
            token: params.token,
        },
    );
}
