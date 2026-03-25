"use client";

import { useState } from "react";

import type { AdminRole, AdminRoleCreateInput } from "@/types/admin/role";

interface RoleFormProps {
    mode: "create" | "edit";
    initialRole?: AdminRole | null;
    isSubmitting: boolean;
    onCancel?: () => void;
    onSubmit: (input: AdminRoleCreateInput) => void;
}

function getInitialFormState(initialRole?: AdminRole | null) {
    if (initialRole) {
        return {
            code: initialRole.code,
            name: initialRole.name,
            description: initialRole.description ?? "",
            isActive: initialRole.is_active,
        };
    }

    return {
        code: "",
        name: "",
        description: "",
        isActive: true,
    };
}

export function RoleForm({
    mode,
    initialRole,
    isSubmitting,
    onCancel,
    onSubmit,
}: RoleFormProps) {
    const initialState = getInitialFormState(initialRole);

    const [code, setCode] = useState(initialState.code);
    const [name, setName] = useState(initialState.name);
    const [description, setDescription] = useState(initialState.description);
    const [isActive, setIsActive] = useState(initialState.isActive);

    function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        onSubmit({
            code,
            name,
            description: description.trim() ? description.trim() : null,
            is_active: isActive,
        });
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label
                    htmlFor="role-code"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Code
                </label>
                <input
                    id="role-code"
                    type="text"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="ADMIN"
                    required
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="role-name"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Name
                </label>
                <input
                    id="role-name"
                    type="text"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="Administrator"
                    required
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="role-description"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Description
                </label>
                <textarea
                    id="role-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    className="min-h-[120px] w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="Full access to administrative modules."
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
                <span className="text-sm text-slate-700">Active role</span>
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
                          ? "Create role"
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
