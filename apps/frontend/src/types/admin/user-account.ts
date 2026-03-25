export interface AdminUserAccountRoleRef {
    id: number;
    code: string;
    name: string;
    is_active: boolean;
}

export interface AdminUserAccountBranchRef {
    id: number;
    code: string;
    name: string;
    is_active: boolean;
}

export interface AdminUserAccount {
    id: number;
    email: string;
    full_name: string;
    is_active: boolean;
    branch_id: number;
    role_id: number;
    has_password: boolean;
    created_at: string;
    updated_at: string;
    role: AdminUserAccountRoleRef;
    branch: AdminUserAccountBranchRef;
}

export interface AdminUserAccountCreateInput {
    email: string;
    full_name: string;
    branch_id: number;
    role_id: number;
    password: string;
    is_active: boolean;
}

export interface AdminUserAccountUpdateInput {
    email?: string;
    full_name?: string;
    branch_id?: number;
    role_id?: number;
    new_password?: string;
    is_active?: boolean;
}

export interface UserAccountFormDraft {
    email: string;
    full_name: string;
    branch_id: number;
    role_id: number;
    password: string;
    is_active: boolean;
}
