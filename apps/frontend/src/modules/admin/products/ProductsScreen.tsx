"use client";

import { useMemo, useState } from "react";

import { useAdminProductCategories } from "@/hooks/admin/useAdminProductCategories";
import {
    useAdminProducts,
    useCreateAdminProduct,
    useDeactivateAdminProduct,
    useUpdateAdminProduct,
} from "@/hooks/admin/useAdminProducts";
import { useAuth } from "@/modules/auth/AuthProvider";
import { ApiClientError } from "@/services/http/errors";
import type { AdminProduct, ProductFormDraft } from "@/types/admin/product";
import { ProductForm } from "./ProductForm";

function formatDate(value: string): string {
    return new Date(value).toLocaleString();
}

function StatusBadge({ active }: { active: boolean }) {
    return (
        <span
            className={[
                "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
                active
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-200 text-slate-700",
            ].join(" ")}
        >
            {active ? "ACTIVE" : "INACTIVE"}
        </span>
    );
}

function TypeBadge({ isInput }: { isInput: boolean }) {
    return (
        <span
            className={[
                "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
                isInput
                    ? "bg-amber-100 text-amber-700"
                    : "bg-sky-100 text-sky-700",
            ].join(" ")}
        >
            {isInput ? "INPUT" : "SELLABLE"}
        </span>
    );
}

export function ProductsScreen() {
    const { session } = useAuth();
    const token = session?.accessToken ?? null;

    const [selectedProduct, setSelectedProduct] = useState<AdminProduct | null>(
        null,
    );
    const [showInactive, setShowInactive] = useState(true);
    const [search, setSearch] = useState("");
    const [message, setMessage] = useState<string | null>(null);

    const categoriesQuery = useAdminProductCategories({
        token,
        includeInactive: false,
    });

    const productsQuery = useAdminProducts({
        token,
        includeInactive: showInactive,
        q: search,
    });

    const createMutation = useCreateAdminProduct({ token });
    const updateMutation = useUpdateAdminProduct({ token });
    const deactivateMutation = useDeactivateAdminProduct({ token });

    const isEditing = Boolean(selectedProduct);

    const currentErrorMessage = useMemo(() => {
        const error =
            categoriesQuery.error ??
            productsQuery.error ??
            createMutation.error ??
            updateMutation.error ??
            deactivateMutation.error;

        if (!error) {
            return null;
        }

        if (error instanceof ApiClientError) {
            return error.message;
        }

        return error.message ?? "Unexpected administrative error.";
    }, [
        categoriesQuery.error,
        productsQuery.error,
        createMutation.error,
        updateMutation.error,
        deactivateMutation.error,
    ]);

    const canRenderForm = Boolean(categoriesQuery.data?.length);

    const initialDraft = useMemo<ProductFormDraft>(() => {
        const firstCategoryId = categoriesQuery.data?.[0]?.id ?? 0;

        if (selectedProduct) {
            return {
                sku: selectedProduct.sku ?? "",
                name: selectedProduct.name,
                quick_name: selectedProduct.quick_name ?? "",
                category_id: selectedProduct.category_id ?? firstCategoryId,
                uom: selectedProduct.uom,
                is_input: selectedProduct.is_input,
                show_in_pos: selectedProduct.show_in_pos,
                is_sellable_in_pos: selectedProduct.is_sellable_in_pos,
                default_pos_order: selectedProduct.default_pos_order,
                sale_price: selectedProduct.sale_price ?? "",
                standard_cost: selectedProduct.standard_cost ?? "",
                is_active: selectedProduct.is_active,
            };
        }

        return {
            sku: "",
            name: "",
            quick_name: "",
            category_id: firstCategoryId,
            uom: "PCS",
            is_input: false,
            show_in_pos: true,
            is_sellable_in_pos: true,
            default_pos_order: 100,
            sale_price: "",
            standard_cost: "",
            is_active: true,
        };
    }, [selectedProduct, categoriesQuery.data]);

    async function handleCreate(draft: ProductFormDraft) {
        setMessage(null);

        const created = await createMutation.mutateAsync({
            sku: draft.sku.trim() ? draft.sku.trim() : null,
            name: draft.name,
            quick_name: draft.quick_name.trim()
                ? draft.quick_name.trim()
                : null,
            category_id: draft.category_id,
            uom: draft.uom,
            is_input: draft.is_input,
            show_in_pos: draft.is_input ? false : draft.show_in_pos,
            is_sellable_in_pos: draft.is_input
                ? false
                : draft.is_sellable_in_pos,
            default_pos_order: draft.default_pos_order,
            sale_price: draft.sale_price.trim()
                ? draft.sale_price.trim()
                : null,
            standard_cost: draft.standard_cost.trim()
                ? draft.standard_cost.trim()
                : null,
            is_active: draft.is_active,
        });

        setMessage(`Product ${created.name} created successfully.`);
    }

    async function handleUpdate(draft: ProductFormDraft) {
        if (!selectedProduct) {
            return;
        }

        setMessage(null);

        const updated = await updateMutation.mutateAsync({
            productId: selectedProduct.id,
            input: {
                sku: draft.sku.trim() ? draft.sku.trim() : null,
                name: draft.name,
                quick_name: draft.quick_name.trim()
                    ? draft.quick_name.trim()
                    : null,
                category_id: draft.category_id,
                uom: draft.uom,
                is_input: draft.is_input,
                show_in_pos: draft.is_input ? false : draft.show_in_pos,
                is_sellable_in_pos: draft.is_input
                    ? false
                    : draft.is_sellable_in_pos,
                default_pos_order: draft.default_pos_order,
                sale_price: draft.sale_price.trim()
                    ? draft.sale_price.trim()
                    : null,
                standard_cost: draft.standard_cost.trim()
                    ? draft.standard_cost.trim()
                    : null,
                is_active: draft.is_active,
            },
        });

        setSelectedProduct(updated);
        setMessage(`Product ${updated.name} updated successfully.`);
    }

    async function handleDeactivate(product: AdminProduct) {
        setMessage(null);

        const updated = await deactivateMutation.mutateAsync({
            productId: product.id,
        });

        if (selectedProduct?.id === updated.id) {
            setSelectedProduct(updated);
        }

        setMessage(`Product ${updated.name} deactivated.`);
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        Administration / Products
                    </p>
                    <h2 className="mt-2 text-3xl font-semibold">Products</h2>
                    <p className="mt-2 max-w-3xl text-sm text-slate-600">
                        Manage the product catalog used across POS, inventory,
                        pricing and production.
                    </p>
                </div>

                <div className="flex flex-wrap gap-3">
                    <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                        <input
                            type="checkbox"
                            checked={showInactive}
                            onChange={(event) =>
                                setShowInactive(event.target.checked)
                            }
                        />
                        Show inactive products
                    </label>

                    <input
                        type="text"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search by name, quick name or SKU"
                        className="rounded-2xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-slate-900"
                    />
                </div>
            </div>

            {message ? (
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {message}
                </div>
            ) : null}

            {currentErrorMessage ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {currentErrorMessage}
                </div>
            ) : null}

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.55fr_0.9fr]">
                <section className="rounded-3xl border border-slate-200 p-4">
                    <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-semibold">
                            Existing products
                        </h3>
                    </div>

                    {productsQuery.isLoading ? (
                        <p className="text-sm text-slate-500">
                            Loading products...
                        </p>
                    ) : null}

                    {!productsQuery.isLoading &&
                    productsQuery.data?.length === 0 ? (
                        <p className="text-sm text-slate-500">
                            No products found.
                        </p>
                    ) : null}

                    {!productsQuery.isLoading && productsQuery.data?.length ? (
                        <div className="overflow-x-auto">
                            <table className="min-w-full border-separate border-spacing-y-2">
                                <thead>
                                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                                        <th className="px-3 py-2">Product</th>
                                        <th className="px-3 py-2">Category</th>
                                        <th className="px-3 py-2">Type</th>
                                        <th className="px-3 py-2">POS</th>
                                        <th className="px-3 py-2">Price</th>
                                        <th className="px-3 py-2">Status</th>
                                        <th className="px-3 py-2">Updated</th>
                                        <th className="px-3 py-2">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {productsQuery.data.map((product) => (
                                        <tr
                                            key={product.id}
                                            className="rounded-2xl bg-slate-50 text-sm"
                                        >
                                            <td className="px-3 py-3">
                                                <div className="font-medium text-slate-800">
                                                    {product.name}
                                                </div>
                                                <div className="mt-1 text-xs text-slate-500">
                                                    SKU: {product.sku ?? "—"} ·
                                                    Quick:{" "}
                                                    {product.quick_name ?? "—"}{" "}
                                                    · UOM: {product.uom}
                                                </div>
                                            </td>

                                            <td className="px-3 py-3">
                                                <div className="font-medium text-slate-800">
                                                    {product.category?.code ??
                                                        "UNCATEGORIZED"}
                                                </div>
                                                <div className="mt-1 text-xs text-slate-500">
                                                    {product.category?.name ??
                                                        "No category assigned"}
                                                </div>
                                            </td>

                                            <td className="px-3 py-3">
                                                <TypeBadge
                                                    isInput={product.is_input}
                                                />
                                            </td>

                                            <td className="px-3 py-3 text-xs text-slate-600">
                                                show=
                                                {String(product.show_in_pos)} ·
                                                sellable=
                                                {String(
                                                    product.is_sellable_in_pos,
                                                )}
                                            </td>

                                            <td className="px-3 py-3 text-xs text-slate-600">
                                                sale={product.sale_price ?? "—"}{" "}
                                                · cost=
                                                {product.standard_cost ?? "—"}
                                            </td>

                                            <td className="px-3 py-3">
                                                <StatusBadge
                                                    active={product.is_active}
                                                />
                                            </td>

                                            <td className="px-3 py-3 text-xs text-slate-500">
                                                {formatDate(product.updated_at)}
                                            </td>

                                            <td className="px-3 py-3">
                                                <div className="flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            setSelectedProduct(
                                                                product,
                                                            )
                                                        }
                                                        className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-white"
                                                    >
                                                        Edit
                                                    </button>

                                                    {product.is_active ? (
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                handleDeactivate(
                                                                    product,
                                                                )
                                                            }
                                                            disabled={
                                                                deactivateMutation.isPending
                                                            }
                                                            className="rounded-xl border border-rose-300 px-3 py-2 text-xs font-semibold text-rose-700 transition hover:bg-white disabled:opacity-50"
                                                        >
                                                            Deactivate
                                                        </button>
                                                    ) : null}
                                                </div>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : null}
                </section>

                <section className="rounded-3xl border border-slate-200 p-4">
                    <div className="mb-4">
                        <h3 className="text-lg font-semibold">
                            {isEditing ? "Edit product" : "Create product"}
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                            {isEditing
                                ? "Modify an existing product definition."
                                : "Create a new sellable product or input/raw material."}
                        </p>
                    </div>

                    {!canRenderForm ? (
                        <p className="text-sm text-slate-500">
                            Loading product categories...
                        </p>
                    ) : (
                        <ProductForm
                            key={
                                selectedProduct
                                    ? `edit-product-${selectedProduct.id}-${selectedProduct.updated_at}`
                                    : `create-product-${categoriesQuery.data?.[0]?.id ?? 0}`
                            }
                            mode={isEditing ? "edit" : "create"}
                            initialDraft={initialDraft}
                            categories={categoriesQuery.data ?? []}
                            isSubmitting={
                                createMutation.isPending ||
                                updateMutation.isPending
                            }
                            onCancel={
                                isEditing
                                    ? () => setSelectedProduct(null)
                                    : undefined
                            }
                            onSubmit={isEditing ? handleUpdate : handleCreate}
                        />
                    )}
                </section>
            </div>
        </div>
    );
}
