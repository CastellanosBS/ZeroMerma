"use client";

import { useMemo, useState } from "react";

import { useAdminBranches } from "@/hooks/admin/useAdminBranches";
import {
    useAdminUserAccounts,
    useCreateAdminUserAccount,
    useDeactivateAdminUserAccount,
    useUpdateAdminUserAccount,
} from "@/hooks/admin/useAdminUserAccounts";
import { useAdminRoles } from "@/hooks/admin/useAdminRoles";
import { useAuth } from "@/modules/auth/AuthProvider";
import { ApiClientError } from "@/services/http/errors";
import type {
    UserAccountFormDraft,
    AdminUserAccount,
} from "@/types/admin/user-account";
import { UserAccountForm } from "./UserAccountForm";

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

function PasswordBadge({ hasPassword }: { hasPassword: boolean }) {
    return (
        <span
            className={[
                "inline-flex rounded-full px-3 py-1 text-xs font-semibold",
                hasPassword
                    ? "bg-sky-100 text-sky-700"
                    : "bg-amber-100 text-amber-700",
            ].join(" ")}
        >
            {hasPassword ? "PASSWORD OK" : "NO PASSWORD"}
        </span>
    );
}

export function UserAccountsScreen() {
    const { session } = useAuth();
    const token = session?.accessToken ?? null;

    const [selectedUser, setSelectedUser] = useState<AdminUserAccount | null>(
        null,
    );
    const [showInactive, setShowInactive] = useState(true);
    const [search, setSearch] = useState("");
    const [message, setMessage] = useState<string | null>(null);

    const usersQuery = useAdminUserAccounts({
        token,
        includeInactive: showInactive,
        q: search,
    });

    const rolesQuery = useAdminRoles({
        token,
        includeInactive: false,
    });

    const branchesQuery = useAdminBranches({
        token,
        includeInactive: false,
    });

    const createMutation = useCreateAdminUserAccount({ token });
    const updateMutation = useUpdateAdminUserAccount({ token });
    const deactivateMutation = useDeactivateAdminUserAccount({ token });

    const isEditing = Boolean(selectedUser);

    const currentErrorMessage = useMemo(() => {
        const error =
            usersQuery.error ??
            rolesQuery.error ??
            branchesQuery.error ??
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
        usersQuery.error,
        rolesQuery.error,
        branchesQuery.error,
        createMutation.error,
        updateMutation.error,
        deactivateMutation.error,
    ]);

    const canRenderForm =
        Boolean(rolesQuery.data?.length) && Boolean(branchesQuery.data?.length);

    const initialDraft = useMemo<UserAccountFormDraft>(() => {
        const firstRoleId = rolesQuery.data?.[0]?.id ?? 0;
        const firstBranchId = branchesQuery.data?.[0]?.id ?? 0;

        if (selectedUser) {
            return {
                email: selectedUser.email,
                full_name: selectedUser.full_name,
                role_id: selectedUser.role_id,
                branch_id: selectedUser.branch_id,
                password: "",
                is_active: selectedUser.is_active,
            };
        }

        return {
            email: "",
            full_name: "",
            role_id: firstRoleId,
            branch_id: firstBranchId,
            password: "",
            is_active: true,
        };
    }, [selectedUser, rolesQuery.data, branchesQuery.data]);

    async function handleCreate(draft: UserAccountFormDraft) {
        setMessage(null);

        const created = await createMutation.mutateAsync({
            email: draft.email,
            full_name: draft.full_name,
            role_id: draft.role_id,
            branch_id: draft.branch_id,
            password: draft.password,
            is_active: draft.is_active,
        });

        setMessage(`User ${created.email} created successfully.`);
    }

    async function handleUpdate(draft: UserAccountFormDraft) {
        if (!selectedUser) {
            return;
        }

        setMessage(null);

        const updated = await updateMutation.mutateAsync({
            userId: selectedUser.id,
            input: {
                email: draft.email,
                full_name: draft.full_name,
                role_id: draft.role_id,
                branch_id: draft.branch_id,
                is_active: draft.is_active,
                new_password: draft.password.trim()
                    ? draft.password.trim()
                    : undefined,
            },
        });

        setSelectedUser(updated);
        setMessage(`User ${updated.email} updated successfully.`);
    }

    async function handleDeactivate(user: AdminUserAccount) {
        setMessage(null);

        const updated = await deactivateMutation.mutateAsync({
            userId: user.id,
        });

        if (selectedUser?.id === updated.id) {
            setSelectedUser(updated);
        }

        setMessage(`User ${updated.email} deactivated.`);
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        Administration / User Accounts
                    </p>
                    <h2 className="mt-2 text-3xl font-semibold">
                        User accounts
                    </h2>
                    <p className="mt-2 max-w-3xl text-sm text-slate-600">
                        Create, update and deactivate employee accounts used to
                        access ZeroMerma.
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
                        Show inactive users
                    </label>

                    <input
                        type="text"
                        value={search}
                        onChange={(event) => setSearch(event.target.value)}
                        placeholder="Search by name or email"
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

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.5fr_0.9fr]">
                <section className="rounded-3xl border border-slate-200 p-4">
                    <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-semibold">
                            Existing users
                        </h3>
                    </div>

                    {usersQuery.isLoading ? (
                        <p className="text-sm text-slate-500">
                            Loading users...
                        </p>
                    ) : null}

                    {!usersQuery.isLoading && usersQuery.data?.length === 0 ? (
                        <p className="text-sm text-slate-500">
                            No user accounts found.
                        </p>
                    ) : null}

                    {!usersQuery.isLoading && usersQuery.data?.length ? (
                        <div className="overflow-x-auto">
                            <table className="min-w-full border-separate border-spacing-y-2">
                                <thead>
                                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                                        <th className="px-3 py-2">User</th>
                                        <th className="px-3 py-2">Role</th>
                                        <th className="px-3 py-2">Branch</th>
                                        <th className="px-3 py-2">Status</th>
                                        <th className="px-3 py-2">Password</th>
                                        <th className="px-3 py-2">Updated</th>
                                        <th className="px-3 py-2">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {usersQuery.data.map((user) => (
                                        <tr
                                            key={user.id}
                                            className="rounded-2xl bg-slate-50 text-sm"
                                        >
                                            <td className="px-3 py-3">
                                                <div className="font-medium text-slate-800">
                                                    {user.full_name}
                                                </div>
                                                <div className="mt-1 text-xs text-slate-500">
                                                    {user.email}
                                                </div>
                                            </td>
                                            <td className="px-3 py-3">
                                                <div className="font-medium text-slate-800">
                                                    {user.role.code}
                                                </div>
                                                <div className="mt-1 text-xs text-slate-500">
                                                    {user.role.name}
                                                </div>
                                            </td>
                                            <td className="px-3 py-3">
                                                <div className="font-medium text-slate-800">
                                                    {user.branch.code}
                                                </div>
                                                <div className="mt-1 text-xs text-slate-500">
                                                    {user.branch.name}
                                                </div>
                                            </td>
                                            <td className="px-3 py-3">
                                                <StatusBadge
                                                    active={user.is_active}
                                                />
                                            </td>
                                            <td className="px-3 py-3">
                                                <PasswordBadge
                                                    hasPassword={
                                                        user.has_password
                                                    }
                                                />
                                            </td>
                                            <td className="px-3 py-3 text-xs text-slate-500">
                                                {formatDate(user.updated_at)}
                                            </td>
                                            <td className="px-3 py-3">
                                                <div className="flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            setSelectedUser(
                                                                user,
                                                            )
                                                        }
                                                        className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-white"
                                                    >
                                                        Edit
                                                    </button>

                                                    {user.is_active ? (
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                handleDeactivate(
                                                                    user,
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
                            {isEditing ? "Edit user" : "Create user"}
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                            {isEditing
                                ? "Modify an existing employee account."
                                : "Create a new employee account for testing and system access."}
                        </p>
                    </div>

                    {!canRenderForm ? (
                        <p className="text-sm text-slate-500">
                            Loading branches and roles...
                        </p>
                    ) : (
                        <UserAccountForm
                            key={
                                selectedUser
                                    ? `edit-user-${selectedUser.id}-${selectedUser.updated_at}`
                                    : `create-user-${rolesQuery.data?.[0]?.id ?? 0}-${branchesQuery.data?.[0]?.id ?? 0}`
                            }
                            mode={isEditing ? "edit" : "create"}
                            initialDraft={initialDraft}
                            roles={rolesQuery.data ?? []}
                            branches={branchesQuery.data ?? []}
                            isSubmitting={
                                createMutation.isPending ||
                                updateMutation.isPending
                            }
                            onCancel={
                                isEditing
                                    ? () => setSelectedUser(null)
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
