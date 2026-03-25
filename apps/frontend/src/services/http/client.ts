import {
    clearStoredAuthSession,
    emitUnauthorizedEvent,
} from "@/lib/auth/storage";
import { parseApiError } from "./errors";

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? "";

export interface RequestOptions extends RequestInit {
    token?: string | null;
    handleUnauthorized?: boolean;
}

export async function apiRequest<T>(
    path: string,
    options: RequestOptions = {},
): Promise<T> {
    const { token, headers, handleUnauthorized = true, ...rest } = options;

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...rest,
        headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
            ...(headers ?? {}),
        },
        cache: "no-store",
    });

    if (!response.ok) {
        let payload: unknown = null;

        try {
            payload = await response.json();
        } catch {
            payload = null;
        }

        if (response.status === 401 && handleUnauthorized) {
            clearStoredAuthSession();
            emitUnauthorizedEvent();
        }

        throw parseApiError(response.status, payload);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return (await response.json()) as T;
}
