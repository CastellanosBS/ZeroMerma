import type { AuthSession } from "@/types/auth";

const AUTH_STORAGE_KEY = "zeromerma.auth.session";
export const AUTH_UNAUTHORIZED_EVENT = "zeromerma:auth-unauthorized";

function isBrowser(): boolean {
    return typeof window !== "undefined";
}

export function getStoredAuthSession(): AuthSession | null {
    if (!isBrowser()) {
        return null;
    }

    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) {
        return null;
    }

    try {
        const parsed = JSON.parse(raw) as AuthSession;

        if (
            !parsed ||
            !parsed.accessToken ||
            !parsed.tokenType ||
            typeof parsed.expiresAt !== "number" ||
            !parsed.user
        ) {
            window.localStorage.removeItem(AUTH_STORAGE_KEY);
            return null;
        }

        return parsed;
    } catch {
        window.localStorage.removeItem(AUTH_STORAGE_KEY);
        return null;
    }
}

export function setStoredAuthSession(session: AuthSession): void {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredAuthSession(): void {
    if (!isBrowser()) {
        return;
    }

    window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function isStoredSessionExpired(
    session: AuthSession,
    now: number = Date.now(),
): boolean {
    // Small safety window so we do not keep using a token that is about to expire.
    return session.expiresAt <= now + 5_000;
}

export function emitUnauthorizedEvent(): void {
    if (!isBrowser()) {
        return;
    }

    window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
}
