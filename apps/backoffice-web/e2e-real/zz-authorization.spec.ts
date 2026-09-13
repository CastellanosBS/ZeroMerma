import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Page } from "@playwright/test";
import type { components } from "@zeromerma/api-client";

import { environment, expect, test } from "./fixtures";

type CurrentUser = components["schemas"]["AuthenticatedUser"];
const scope: { allowed_branch_id: string; other_branch_id: string } = JSON.parse(
  readFileSync(join(environment.artifactDir, "fixture-scope.json"), "utf8"),
);

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Correo", { exact: true }).fill(email);
  await page.getByLabel("Contraseña", { exact: true }).fill(environment.password);
  const response = page.waitForResponse(
    (entry) =>
      new URL(entry.url()).pathname === "/v1/auth/login" && entry.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Entrar al backoffice" }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  const body: components["schemas"]["LoginResponse"] = await result.json();
  return body.access_token;
}

test("a Backoffice account without grants cannot read a protected route or API", async ({
  page,
  request,
  network,
}) => {
  const token = await login(page, `denied-${environment.runId}@example.invalid`);
  await expect(page.getByRole("heading", { name: "Sin acceso autorizado" })).toBeVisible();
  await page.goto("/admin/productos");
  await expect(page.getByRole("heading", { name: "Sin acceso autorizado" })).toBeVisible();
  expect(network.some((entry) => entry.path.startsWith("/v1/admin/"))).toBe(false);
  const response = await request.get(`${environment.apiUrl}/v1/admin/products`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(response.status()).toBe(403);
});

test("read grants expose only their branch and never enable management or export", async ({
  page,
  request,
}) => {
  const token = await login(page, environment.email);
  await expect(page.getByRole("heading", { name: "Productos", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Nuevo producto", exact: true })).toHaveCount(0);
  const headers = { Authorization: `Bearer ${token}` };
  const current = await request.get(`${environment.apiUrl}/v1/auth/me?surface=BACKOFFICE`, {
    headers,
  });
  expect(current.status()).toBe(200);
  const user: CurrentUser = await current.json();
  expect(user.authorization_surface).toBe("BACKOFFICE");
  expect(user.is_superadministrator).toBe(false);
  expect(user.effective_grants).toHaveLength(7);
  for (const grant of user.effective_grants ?? []) {
    expect(grant.scope_type).toBe("BRANCH_SET");
    expect(grant.branch_ids).toEqual([scope.allowed_branch_id]);
  }
  expect(
    (
      await request.get(`${environment.apiUrl}/v1/admin/branches/${scope.allowed_branch_id}`, {
        headers,
      })
    ).status(),
  ).toBe(200);
  expect(
    (
      await request.get(`${environment.apiUrl}/v1/admin/branches/${scope.other_branch_id}`, {
        headers,
      })
    ).status(),
  ).toBe(404);
  const branches = await request.get(`${environment.apiUrl}/v1/admin/branches`, { headers });
  expect(branches.status()).toBe(200);
  const branchList: components["schemas"]["AdminBranchesListResponse"] = await branches.json();
  expect(branchList.items.map((branch) => branch.id)).toEqual([scope.allowed_branch_id]);
  expect(branchList.total).toBe(1);
  const cashCuts = await request.get(
    `${environment.apiUrl}/v1/admin/cash-cuts?branch_id=${scope.other_branch_id}`,
    { headers },
  );
  expect(cashCuts.status()).toBe(403);
  expect(
    (await request.get(`${environment.apiUrl}/v1/admin/audit/export`, { headers })).status(),
  ).toBe(403);
  await page.goto("/admin/auditoria");
  await expect(page.getByRole("button", { name: /Exportar/ })).toBeDisabled();
});

test("revocation refreshes the open session and removes prior data without issuing a new token", async ({
  page,
  request,
}) => {
  const token = await login(page, environment.email);
  await expect(page.getByRole("heading", { name: "Productos", exact: true })).toBeVisible();
  const headers = { Authorization: `Bearer ${token}` };
  const before: CurrentUser = await (
    await request.get(`${environment.apiUrl}/v1/auth/me?surface=BACKOFFICE`, { headers })
  ).json();
  execFileSync(
    "uv",
    ["run", "--frozen", "python", "scripts/dev/seed-web-integration.py", "--revoke-reader"],
    {
      cwd: fileURLToPath(new URL("../../../", import.meta.url)),
      env: process.env,
      stdio: "pipe",
    },
  );
  const refresh = page.waitForResponse(
    (response) => new URL(response.url()).pathname === "/v1/auth/me",
  );
  await page.evaluate(() => window.dispatchEvent(new Event("visibilitychange")));
  const after: CurrentUser = await (await refresh).json();
  expect(after.authorization_version === before.authorization_version).toBe(false);
  expect(after.effective_grants).toEqual([]);
  await expect(page.getByRole("heading", { name: "Sin acceso autorizado" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Productos", exact: true })).toHaveCount(0);
  await expect(page.getByRole("table")).toHaveCount(0);
  expect((await request.get(`${environment.apiUrl}/v1/admin/products`, { headers })).status()).toBe(
    403,
  );
});
