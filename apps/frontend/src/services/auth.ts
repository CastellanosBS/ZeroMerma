import { apiRequest } from "@/services/http/client";
import type {
    AuthenticatedUser,
    CurrentUserApiResponse,
    LoginInput,
    TokenResponse,
} from "@/types/auth";

const AUTH_LOGIN_PATH =
    process.env.NEXT_PUBLIC_AUTH_LOGIN_PATH ?? "/auth/login";

const AUTH_ME_PATH = process.env.NEXT_PUBLIC_AUTH_ME_PATH ?? "/auth/me";

function mapCurrentUser(payload: CurrentUserApiResponse): AuthenticatedUser {
    return {
        id: payload.id,
        email: payload.email,
        fullName: payload.full_name,
        isActive: payload.is_active,
        branchId: payload.branch_id,
        roleId: payload.role_id,
        roleCode: payload.role_code,
    };
}

export async function loginRequest(input: LoginInput): Promise<TokenResponse> {
    return apiRequest<TokenResponse>(AUTH_LOGIN_PATH, {
        method: "POST",
        body: JSON.stringify(input),
        handleUnauthorized: false,
    });
}

export async function getCurrentUser(
    token: string,
): Promise<AuthenticatedUser> {
    const payload = await apiRequest<CurrentUserApiResponse>(AUTH_ME_PATH, {
        method: "GET",
        token,
    });

    return mapCurrentUser(payload);
}
