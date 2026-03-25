export interface AdminProductCategoryRef {
    id: number;
    code: string;
    name: string;
    quick_name: string | null;
    is_active: boolean;
}

export interface AdminProduct {
    id: number;
    sku: string | null;
    name: string;
    quick_name: string | null;
    category_id: number | null;
    uom: "PCS" | "KG" | "G" | "L" | "ML";
    is_input: boolean;
    show_in_pos: boolean;
    is_sellable_in_pos: boolean;
    default_pos_order: number;
    sale_price: string | null;
    standard_cost: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string;
    category: AdminProductCategoryRef | null;
}

export interface AdminProductCreateInput {
    sku: string | null;
    name: string;
    quick_name: string | null;
    category_id: number;
    uom: "PCS" | "KG" | "G" | "L" | "ML";
    is_input: boolean;
    show_in_pos: boolean;
    is_sellable_in_pos: boolean;
    default_pos_order: number;
    sale_price: string | null;
    standard_cost: string | null;
    is_active: boolean;
}

export interface AdminProductUpdateInput {
    sku?: string | null;
    name?: string;
    quick_name?: string | null;
    category_id?: number;
    uom?: "PCS" | "KG" | "G" | "L" | "ML";
    is_input?: boolean;
    show_in_pos?: boolean;
    is_sellable_in_pos?: boolean;
    default_pos_order?: number;
    sale_price?: string | null;
    standard_cost?: string | null;
    is_active?: boolean;
}

export interface ProductFormDraft {
    sku: string;
    name: string;
    quick_name: string;
    category_id: number;
    uom: "PCS" | "KG" | "G" | "L" | "ML";
    is_input: boolean;
    show_in_pos: boolean;
    is_sellable_in_pos: boolean;
    default_pos_order: number;
    sale_price: string;
    standard_cost: string;
    is_active: boolean;
}
