export interface LoginInput {
    email: string;
    password: string;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
}

export interface CurrentUserApiResponse {
    id: number;
    email: string;
    full_name: string;
    is_active: boolean;
    branch_id: number;
    role_id: number;
    role_code: string;
}

export interface AuthenticatedUser {
    id: number;
    email: string;
    fullName: string;
    isActive: boolean;
    branchId: number;
    roleId: number;
    roleCode: string;
}

export interface AuthSession {
    accessToken: string;
    tokenType: string;
    expiresAt: number;
    user: AuthenticatedUser;
}
