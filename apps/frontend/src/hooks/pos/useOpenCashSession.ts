import { useMutation, useQueryClient } from "@tanstack/react-query";

import { openCashSession } from "@/services/pos/cashSessions";
import type {
    CashSession,
    OpenCashSessionInput,
} from "@/types/pos/cash-session";

export function useOpenCashSession(params: {
    branchId: number | null;
    token: string | null;
}) {
    const queryClient = useQueryClient();

    return useMutation<CashSession, Error, OpenCashSessionInput>({
        mutationFn: async (input) => {
            if (params.branchId === null || !params.token) {
                throw new Error("No authenticated branch context available.");
            }

            return openCashSession({
                input,
                token: params.token,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["pos", "cash-session", "current", params.branchId],
            });
        },
    });
}
