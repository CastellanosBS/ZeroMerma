export interface ActivePosContext {
    branchId: number;
    token: string | null;
}

export function getActivePosContext(): ActivePosContext {
    if (typeof window === "undefined") {
        return {
            branchId: 1,
            token: null,
        };
    }

    return {
        branchId: 1,
        token: window.localStorage.getItem("access_token"),
    };
}
