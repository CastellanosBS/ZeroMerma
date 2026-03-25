"use client";

import { useState } from "react";

import type { AdminProductCategory } from "@/types/admin/product-category";
import type { ProductFormDraft } from "@/types/admin/product";

const UOM_OPTIONS = ["PCS", "KG", "G", "L", "ML"] as const;

interface ProductFormProps {
    mode: "create" | "edit";
    initialDraft: ProductFormDraft;
    categories: AdminProductCategory[];
    isSubmitting: boolean;
    onCancel?: () => void;
    onSubmit: (draft: ProductFormDraft) => void | Promise<void>;
}

export function ProductForm({
    mode,
    initialDraft,
    categories,
    isSubmitting,
    onCancel,
    onSubmit,
}: ProductFormProps) {
    const [sku, setSku] = useState(initialDraft.sku);
    const [name, setName] = useState(initialDraft.name);
    const [quickName, setQuickName] = useState(initialDraft.quick_name);
    const [categoryId, setCategoryId] = useState(initialDraft.category_id);
    const [uom, setUom] = useState(initialDraft.uom);
    const [isInput, setIsInput] = useState(initialDraft.is_input);
    const [showInPos, setShowInPos] = useState(initialDraft.show_in_pos);
    const [isSellableInPos, setIsSellableInPos] = useState(
        initialDraft.is_sellable_in_pos,
    );
    const [defaultPosOrder, setDefaultPosOrder] = useState(
        initialDraft.default_pos_order,
    );
    const [salePrice, setSalePrice] = useState(initialDraft.sale_price);
    const [standardCost, setStandardCost] = useState(
        initialDraft.standard_cost,
    );
    const [isActive, setIsActive] = useState(initialDraft.is_active);

    function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        onSubmit({
            sku,
            name,
            quick_name: quickName,
            category_id: Number(categoryId),
            uom,
            is_input: isInput,
            show_in_pos: isInput ? false : showInPos,
            is_sellable_in_pos: isInput ? false : isSellableInPos,
            default_pos_order: Number(defaultPosOrder),
            sale_price: salePrice,
            standard_cost: standardCost,
            is_active: isActive,
        });
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label
                    htmlFor="product-sku"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    SKU
                </label>
                <input
                    id="product-sku"
                    type="text"
                    value={sku}
                    onChange={(event) => setSku(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="DONA-CHOCO-001"
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="product-name"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Name
                </label>
                <input
                    id="product-name"
                    type="text"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="Chocolate Donut"
                    required
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="product-quick-name"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Quick name
                </label>
                <input
                    id="product-quick-name"
                    type="text"
                    value={quickName}
                    onChange={(event) => setQuickName(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="Choco Dona"
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="product-category"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Category
                </label>
                <select
                    id="product-category"
                    value={categoryId}
                    onChange={(event) =>
                        setCategoryId(Number(event.target.value))
                    }
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    disabled={isSubmitting}
                    required
                >
                    {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                            {category.code} — {category.name}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label
                    htmlFor="product-uom"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Unit of measure
                </label>
                <select
                    id="product-uom"
                    value={uom}
                    onChange={(event) =>
                        setUom(event.target.value as ProductFormDraft["uom"])
                    }
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    disabled={isSubmitting}
                >
                    {UOM_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                            {option}
                        </option>
                    ))}
                </select>
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input
                    type="checkbox"
                    checked={isInput}
                    onChange={(event) => {
                        const next = event.target.checked;
                        setIsInput(next);

                        if (next) {
                            setShowInPos(false);
                            setIsSellableInPos(false);
                        }
                    }}
                    disabled={isSubmitting}
                />
                <span className="text-sm text-slate-700">
                    Input / raw-material product
                </span>
            </label>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input
                    type="checkbox"
                    checked={showInPos}
                    onChange={(event) => setShowInPos(event.target.checked)}
                    disabled={isSubmitting || isInput}
                />
                <span className="text-sm text-slate-700">Show in POS</span>
            </label>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input
                    type="checkbox"
                    checked={isSellableInPos}
                    onChange={(event) =>
                        setIsSellableInPos(event.target.checked)
                    }
                    disabled={isSubmitting || isInput}
                />
                <span className="text-sm text-slate-700">Sellable in POS</span>
            </label>

            <div>
                <label
                    htmlFor="default-pos-order"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Default POS order
                </label>
                <input
                    id="default-pos-order"
                    type="number"
                    min={0}
                    value={defaultPosOrder}
                    onChange={(event) =>
                        setDefaultPosOrder(Number(event.target.value))
                    }
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="sale-price"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Sale price
                </label>
                <input
                    id="sale-price"
                    type="text"
                    inputMode="decimal"
                    value={salePrice}
                    onChange={(event) => setSalePrice(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="25.00"
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="standard-cost"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Standard cost
                </label>
                <input
                    id="standard-cost"
                    type="text"
                    inputMode="decimal"
                    value={standardCost}
                    onChange={(event) => setStandardCost(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="12.50"
                    disabled={isSubmitting}
                />
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(event) => setIsActive(event.target.checked)}
                    disabled={isSubmitting}
                />
                <span className="text-sm text-slate-700">Active product</span>
            </label>

            <div className="flex flex-wrap gap-3">
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
                >
                    {isSubmitting
                        ? mode === "create"
                            ? "Creating..."
                            : "Saving..."
                        : mode === "create"
                          ? "Create product"
                          : "Save changes"}
                </button>

                {onCancel ? (
                    <button
                        type="button"
                        onClick={onCancel}
                        disabled={isSubmitting}
                        className="rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                        Cancel
                    </button>
                ) : null}
            </div>
        </form>
    );
}
