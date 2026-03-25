export interface AdminProductCategory {
    id: number;
    code: string;
    name: string;
    quick_name: string | null;
    show_in_pos: boolean;
    default_pos_order: number;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}
