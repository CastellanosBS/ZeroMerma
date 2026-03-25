import { apiRequest } from "@/services/http/client";
import type {
    CashSession,
    CloseCashSessionInput,
    OpenCashSessionInput,
} from "@/types/pos/cash-session";

export async function getCurrentCashSession(params: {
    branchId: number;
    token: string | null;
}): Promise<CashSession | null> {
    const searchParams = new URLSearchParams({
        branch_id: String(params.branchId),
    });

    return apiRequest<CashSession | null>(
        `/pos/cash-sessions/current?${searchParams.toString()}`,
        {
            method: "GET",
            token: params.token,
        },
    );
}

export async function openCashSession(params: {
    input: OpenCashSessionInput;
    token: string | null;
}): Promise<CashSession> {
    return apiRequest<CashSession>("/pos/cash-sessions/open", {
        method: "POST",
        token: params.token,
        body: JSON.stringify(params.input),
    });
}

export async function closeCashSession(params: {
    sessionId: number;
    input: CloseCashSessionInput;
    token: string | null;
}): Promise<CashSession> {
    return apiRequest<CashSession>(
        `/pos/cash-sessions/${params.sessionId}/close`,
        {
            method: "POST",
            token: params.token,
            body: JSON.stringify(params.input),
        },
    );
}
