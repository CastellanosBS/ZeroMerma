import { useQuery } from "@tanstack/react-query";

import { getCurrentCashSession } from "@/services/pos/cashSessions";
import type { CashSession } from "@/types/pos/cash-session";

export function useCurrentCashSession(params: {
    branchId: number | null;
    token: string | null;
}) {
    return useQuery<CashSession | null>({
        queryKey: ["pos", "cash-session", "current", params.branchId],
        enabled: params.branchId !== null && Boolean(params.token),
        queryFn: async () => {
            if (params.branchId === null || !params.token) {
                throw new Error("No authenticated branch context available.");
            }

            return getCurrentCashSession({
                branchId: params.branchId,
                token: params.token,
            });
        },
    });
}
