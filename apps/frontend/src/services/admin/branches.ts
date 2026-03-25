import { apiRequest } from "@/services/http/client";
import type { AdminBranch } from "@/types/admin/branch";

export async function listAdminBranches(params: {
    token: string;
    includeInactive?: boolean;
}): Promise<AdminBranch[]> {
    const searchParams = new URLSearchParams();

    if (typeof params.includeInactive === "boolean") {
        searchParams.set("include_inactive", String(params.includeInactive));
    }

    const qs = searchParams.toString();
    const path = qs ? `/admin/branches?${qs}` : "/admin/branches";

    return apiRequest<AdminBranch[]>(path, {
        method: "GET",
        token: params.token,
    });
}
