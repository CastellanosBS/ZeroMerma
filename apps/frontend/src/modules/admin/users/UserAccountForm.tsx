"use client";

import { useState } from "react";

import type { AdminBranch } from "@/types/admin/branch";
import type { AdminRole } from "@/types/admin/role";
import type { UserAccountFormDraft } from "@/types/admin/user-account";

interface UserAccountFormProps {
    mode: "create" | "edit";
    initialDraft: UserAccountFormDraft;
    roles: AdminRole[];
    branches: AdminBranch[];
    isSubmitting: boolean;
    onCancel?: () => void;
    onSubmit: (draft: UserAccountFormDraft) => void | Promise<void>;
}

export function UserAccountForm({
    mode,
    initialDraft,
    roles,
    branches,
    isSubmitting,
    onCancel,
    onSubmit,
}: UserAccountFormProps) {
    const [email, setEmail] = useState(initialDraft.email);
    const [fullName, setFullName] = useState(initialDraft.full_name);
    const [roleId, setRoleId] = useState(initialDraft.role_id);
    const [branchId, setBranchId] = useState(initialDraft.branch_id);
    const [password, setPassword] = useState(initialDraft.password);
    const [isActive, setIsActive] = useState(initialDraft.is_active);

    function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
        event.preventDefault();

        onSubmit({
            email,
            full_name: fullName,
            role_id: Number(roleId),
            branch_id: Number(branchId),
            password,
            is_active: isActive,
        });
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div>
                <label
                    htmlFor="user-full-name"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Full name
                </label>
                <input
                    id="user-full-name"
                    type="text"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="Juan Pérez"
                    required
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="user-email"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Email
                </label>
                <input
                    id="user-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder="juan@example.com"
                    required
                    disabled={isSubmitting}
                />
            </div>

            <div>
                <label
                    htmlFor="user-role"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Role
                </label>
                <select
                    id="user-role"
                    value={roleId}
                    onChange={(event) => setRoleId(Number(event.target.value))}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    disabled={isSubmitting}
                    required
                >
                    {roles.map((role) => (
                        <option key={role.id} value={role.id}>
                            {role.code} — {role.name}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label
                    htmlFor="user-branch"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    Branch
                </label>
                <select
                    id="user-branch"
                    value={branchId}
                    onChange={(event) =>
                        setBranchId(Number(event.target.value))
                    }
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    disabled={isSubmitting}
                    required
                >
                    {branches.map((branch) => (
                        <option key={branch.id} value={branch.id}>
                            {branch.code} — {branch.name}
                        </option>
                    ))}
                </select>
            </div>

            <div>
                <label
                    htmlFor="user-password"
                    className="mb-2 block text-sm font-medium text-slate-700"
                >
                    {mode === "create" ? "Password" : "New password"}
                </label>
                <input
                    id="user-password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="w-full rounded-2xl border border-slate-300 px-4 py-3 outline-none transition focus:border-slate-900"
                    placeholder={
                        mode === "create"
                            ? "Minimum 8 characters"
                            : "Leave blank to keep current password"
                    }
                    required={mode === "create"}
                    disabled={isSubmitting}
                />
                {mode === "edit" ? (
                    <p className="mt-2 text-xs text-slate-500">
                        Leave blank to keep the existing password unchanged.
                    </p>
                ) : null}
            </div>

            <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3">
                <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(event) => setIsActive(event.target.checked)}
                    disabled={isSubmitting}
                />
                <span className="text-sm text-slate-700">Active user</span>
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
                          ? "Create user"
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
