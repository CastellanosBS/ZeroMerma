export interface AdminRole {
    id: number;
    code: string;
    name: string;
    description: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface AdminRoleCreateInput {
    code: string;
    name: string;
    description: string | null;
    is_active: boolean;
}

export interface AdminRoleUpdateInput {
    code?: string;
    name?: string;
    description?: string | null;
    is_active?: boolean;
}
