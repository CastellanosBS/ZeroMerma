import { getStoredAuthSession } from "@/lib/auth/storage";

export interface ActivePosContext {
    branchId: number | null;
    token: string | null;
    roleCode: string | null;
    userId: number | null;
    email: string | null;
}

export function getActivePosContext(): ActivePosContext {
    const session = getStoredAuthSession();

    if (!session) {
        return {
            branchId: null,
            token: null,
            roleCode: null,
            userId: null,
            email: null,
        };
    }

    return {
        branchId: session.user.branchId,
        token: session.accessToken,
        roleCode: session.user.roleCode,
        userId: session.user.id,
        email: session.user.email,
    };
}
