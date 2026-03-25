import { useMutation, useQueryClient } from "@tanstack/react-query";

import { closeCashSession } from "@/services/pos/cashSessions";
import type {
    CashSession,
    CloseCashSessionInput,
} from "@/types/pos/cash-session";

export function useCloseCashSession(params: {
    branchId: number | null;
    token: string | null;
}) {
    const queryClient = useQueryClient();

    return useMutation<
        CashSession,
        Error,
        { sessionId: number; input: CloseCashSessionInput }
    >({
        mutationFn: async ({ sessionId, input }) => {
            if (!params.token) {
                throw new Error("No authenticated token available.");
            }

            return closeCashSession({
                sessionId,
                input,
                token: params.token,
            });
        },
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["pos", "cash-session", "current", params.branchId],
            });

            if (params.branchId !== null) {
                await queryClient.invalidateQueries({
                    queryKey: ["pos", "bootstrap", params.branchId],
                });
            }
        },
    });
}
