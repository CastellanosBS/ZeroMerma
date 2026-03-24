import { parseApiError } from "./errors";

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? "";

export interface RequestOptions extends RequestInit {
    token?: string | null;
}

export async function apiRequest<T>(
    path: string,
    options: RequestOptions = {},
): Promise<T> {
    const { token, headers, ...rest } = options;

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

        throw parseApiError(response.status, payload);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return (await response.json()) as T;
}
