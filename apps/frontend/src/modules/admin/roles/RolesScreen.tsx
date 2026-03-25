"use client";

import { useMemo, useState } from "react";

import {
    useAdminRoles,
    useCreateAdminRole,
    useDeactivateAdminRole,
    useUpdateAdminRole,
} from "@/hooks/admin/useAdminRoles";
import { useAuth } from "@/modules/auth/AuthProvider";
import { ApiClientError } from "@/services/http/errors";
import type { AdminRole } from "@/types/admin/role";
import { RoleForm } from "./RoleForm";

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

export function RolesScreen() {
    const { session } = useAuth();
    const token = session?.accessToken ?? null;

    const [selectedRole, setSelectedRole] = useState<AdminRole | null>(null);
    const [showInactive, setShowInactive] = useState(true);
    const [message, setMessage] = useState<string | null>(null);

    const rolesQuery = useAdminRoles({
        token,
        includeInactive: showInactive,
    });

    const createMutation = useCreateAdminRole({ token });
    const updateMutation = useUpdateAdminRole({ token });
    const deactivateMutation = useDeactivateAdminRole({ token });

    const isEditing = Boolean(selectedRole);

    const currentErrorMessage = useMemo(() => {
        const error =
            createMutation.error ??
            updateMutation.error ??
            deactivateMutation.error ??
            rolesQuery.error;

        if (!error) {
            return null;
        }

        if (error instanceof ApiClientError) {
            return error.message;
        }

        return error.message ?? "Unexpected administrative error.";
    }, [
        createMutation.error,
        updateMutation.error,
        deactivateMutation.error,
        rolesQuery.error,
    ]);

    async function handleCreate(input: {
        code: string;
        name: string;
        description: string | null;
        is_active: boolean;
    }) {
        setMessage(null);
        const created = await createMutation.mutateAsync(input);
        setMessage(`Role ${created.code} created successfully.`);
    }

    async function handleUpdate(input: {
        code: string;
        name: string;
        description: string | null;
        is_active: boolean;
    }) {
        if (!selectedRole) {
            return;
        }

        setMessage(null);

        const updated = await updateMutation.mutateAsync({
            roleId: selectedRole.id,
            input,
        });

        setSelectedRole(updated);
        setMessage(`Role ${updated.code} updated successfully.`);
    }

    async function handleDeactivate(role: AdminRole) {
        setMessage(null);
        const updated = await deactivateMutation.mutateAsync({
            roleId: role.id,
        });

        if (selectedRole?.id === updated.id) {
            setSelectedRole(updated);
        }

        setMessage(`Role ${updated.code} deactivated.`);
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
                        Administration / Roles
                    </p>
                    <h2 className="mt-2 text-3xl font-semibold">
                        Role catalog
                    </h2>
                    <p className="mt-2 max-w-3xl text-sm text-slate-600">
                        Create, edit and deactivate roles used by the
                        authentication and authorization layers.
                    </p>
                </div>

                <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                    <input
                        type="checkbox"
                        checked={showInactive}
                        onChange={(event) =>
                            setShowInactive(event.target.checked)
                        }
                    />
                    Show inactive roles
                </label>
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

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.4fr_0.9fr]">
                <section className="rounded-3xl border border-slate-200 p-4">
                    <div className="mb-4 flex items-center justify-between">
                        <h3 className="text-lg font-semibold">
                            Existing roles
                        </h3>
                    </div>

                    {rolesQuery.isLoading ? (
                        <p className="text-sm text-slate-500">
                            Loading roles...
                        </p>
                    ) : null}

                    {!rolesQuery.isLoading && rolesQuery.data?.length === 0 ? (
                        <p className="text-sm text-slate-500">
                            No roles available yet.
                        </p>
                    ) : null}

                    {!rolesQuery.isLoading && rolesQuery.data?.length ? (
                        <div className="overflow-x-auto">
                            <table className="min-w-full border-separate border-spacing-y-2">
                                <thead>
                                    <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                                        <th className="px-3 py-2">Code</th>
                                        <th className="px-3 py-2">Name</th>
                                        <th className="px-3 py-2">Status</th>
                                        <th className="px-3 py-2">Updated</th>
                                        <th className="px-3 py-2">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {rolesQuery.data.map((role) => (
                                        <tr
                                            key={role.id}
                                            className="rounded-2xl bg-slate-50 text-sm"
                                        >
                                            <td className="px-3 py-3 font-semibold">
                                                {role.code}
                                            </td>
                                            <td className="px-3 py-3">
                                                <div className="font-medium text-slate-800">
                                                    {role.name}
                                                </div>
                                                <div className="mt-1 text-xs text-slate-500">
                                                    {role.description ??
                                                        "No description"}
                                                </div>
                                            </td>
                                            <td className="px-3 py-3">
                                                <StatusBadge
                                                    active={role.is_active}
                                                />
                                            </td>
                                            <td className="px-3 py-3 text-xs text-slate-500">
                                                {formatDate(role.updated_at)}
                                            </td>
                                            <td className="px-3 py-3">
                                                <div className="flex flex-wrap gap-2">
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            setSelectedRole(
                                                                role,
                                                            )
                                                        }
                                                        className="rounded-xl border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-white"
                                                    >
                                                        Edit
                                                    </button>

                                                    {role.is_active ? (
                                                        <button
                                                            type="button"
                                                            onClick={() =>
                                                                handleDeactivate(
                                                                    role,
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
                            {isEditing ? "Edit role" : "Create role"}
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                            {isEditing
                                ? "Modify an existing role definition."
                                : "Add a new administrative or operational role."}
                        </p>
                    </div>

                    <RoleForm
                        key={
                            selectedRole
                                ? `edit-${selectedRole.id}-${selectedRole.updated_at}`
                                : "create-role"
                        }
                        mode={isEditing ? "edit" : "create"}
                        initialRole={selectedRole}
                        isSubmitting={
                            createMutation.isPending || updateMutation.isPending
                        }
                        onCancel={
                            isEditing ? () => setSelectedRole(null) : undefined
                        }
                        onSubmit={isEditing ? handleUpdate : handleCreate}
                    />
                </section>
            </div>
        </div>
    );
}
