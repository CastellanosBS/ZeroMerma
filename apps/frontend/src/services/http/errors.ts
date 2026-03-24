export interface ApiErrorEnvelope {
    error?: {
        code?: string;
        message?: string;
        details?: unknown;
    };
    detail?: string;
}

export class ApiClientError extends Error {
    public readonly status: number;
    public readonly code: string | null;
    public readonly details: unknown;

    constructor(params: {
        status: number;
        message: string;
        code?: string | null;
        details?: unknown;
    }) {
        super(params.message);
        this.name = "ApiClientError";
        this.status = params.status;
        this.code = params.code ?? null;
        this.details = params.details;
    }
}

export function parseApiError(
    status: number,
    payload: unknown,
): ApiClientError {
    const body = (payload ?? {}) as ApiErrorEnvelope;

    if (body?.error) {
        return new ApiClientError({
            status,
            message: body.error.message ?? "Unknown API error.",
            code: body.error.code ?? null,
            details: body.error.details ?? null,
        });
    }

    if (typeof body?.detail === "string") {
        return new ApiClientError({
            status,
            message: body.detail,
            code: null,
            details: null,
        });
    }

    return new ApiClientError({
        status,
        message: "Unexpected API error.",
        code: null,
        details: payload,
    });
}
