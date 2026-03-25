"use client";

import {
    createContext,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useState,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import {
    AUTH_UNAUTHORIZED_EVENT,
    clearStoredAuthSession,
    getStoredAuthSession,
    isStoredSessionExpired,
    setStoredAuthSession,
} from "@/lib/auth/storage";
import { getCurrentUser, loginRequest } from "@/services/auth";
import type {
    AuthenticatedUser,
    AuthSession,
    LoginInput,
    TokenResponse,
} from "@/types/auth";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
    status: AuthStatus;
    session: AuthSession | null;
    login: (input: LoginInput) => Promise<AuthSession>;
    logout: () => void;
    refreshUser: () => Promise<AuthenticatedUser | null>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function buildSession(
    tokenPayload: TokenResponse,
    user: AuthenticatedUser,
): AuthSession {
    return {
        accessToken: tokenPayload.access_token,
        tokenType: tokenPayload.token_type,
        expiresAt: Date.now() + tokenPayload.expires_in * 1000,
        user,
    };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const queryClient = useQueryClient();

    const [status, setStatus] = useState<AuthStatus>("loading");
    const [session, setSession] = useState<AuthSession | null>(null);

    const applyAuthenticatedSession = useCallback((next: AuthSession) => {
        setStoredAuthSession(next);
        setSession(next);
        setStatus("authenticated");
    }, []);

    const applyAnonymousState = useCallback(() => {
        clearStoredAuthSession();
        setSession(null);
        setStatus("anonymous");
        queryClient.clear();
    }, [queryClient]);

    const login = useCallback(
        async (input: LoginInput): Promise<AuthSession> => {
            const tokenPayload = await loginRequest(input);
            const user = await getCurrentUser(tokenPayload.access_token);

            const next = buildSession(tokenPayload, user);

            queryClient.clear();
            applyAuthenticatedSession(next);

            return next;
        },
        [applyAuthenticatedSession, queryClient],
    );

    const logout = useCallback(() => {
        applyAnonymousState();
    }, [applyAnonymousState]);

    const refreshUser =
        useCallback(async (): Promise<AuthenticatedUser | null> => {
            const current = getStoredAuthSession();

            if (!current || isStoredSessionExpired(current)) {
                applyAnonymousState();
                return null;
            }

            const user = await getCurrentUser(current.accessToken);
            const next: AuthSession = {
                ...current,
                user,
            };

            applyAuthenticatedSession(next);
            return user;
        }, [applyAnonymousState, applyAuthenticatedSession]);

    useEffect(() => {
        let cancelled = false;

        async function bootstrap(): Promise<void> {
            const stored = getStoredAuthSession();

            if (!stored || isStoredSessionExpired(stored)) {
                if (!cancelled) {
                    applyAnonymousState();
                }
                return;
            }

            try {
                const user = await getCurrentUser(stored.accessToken);

                if (cancelled) {
                    return;
                }

                applyAuthenticatedSession({
                    ...stored,
                    user,
                });
            } catch {
                if (!cancelled) {
                    applyAnonymousState();
                }
            }
        }

        void bootstrap();

        return () => {
            cancelled = true;
        };
    }, [applyAnonymousState, applyAuthenticatedSession]);

    useEffect(() => {
        const handleUnauthorized = () => {
            applyAnonymousState();
        };

        window.addEventListener(
            AUTH_UNAUTHORIZED_EVENT,
            handleUnauthorized as EventListener,
        );

        return () => {
            window.removeEventListener(
                AUTH_UNAUTHORIZED_EVENT,
                handleUnauthorized as EventListener,
            );
        };
    }, [applyAnonymousState]);

    const value = useMemo<AuthContextValue>(
        () => ({
            status,
            session,
            login,
            logout,
            refreshUser,
        }),
        [status, session, login, logout, refreshUser],
    );

    return (
        <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
    );
}

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error("useAuth must be used within <AuthProvider>.");
    }

    return context;
}
