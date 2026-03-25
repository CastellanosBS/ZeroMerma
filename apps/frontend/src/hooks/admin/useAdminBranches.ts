import { useQuery } from "@tanstack/react-query";

import { listAdminBranches } from "@/services/admin/branches";
import type { AdminBranch } from "@/types/admin/branch";

export function useAdminBranches(params: {
    token: string | null;
    includeInactive?: boolean;
}) {
    return useQuery<AdminBranch[]>({
        queryKey: ["admin", "branches", params.includeInactive ?? false],
        enabled: Boolean(params.token),
        queryFn: async () => {
            if (!params.token) {
                throw new Error("Missing authenticated token.");
            }

            return listAdminBranches({
                token: params.token,
                includeInactive: params.includeInactive ?? false,
            });
        },
    });
}
