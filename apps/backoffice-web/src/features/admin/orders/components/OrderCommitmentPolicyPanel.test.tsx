// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { OrderCommitmentPolicyPanel } from "./OrderCommitmentPolicyPanel";

it("does not preselect an unapproved branch, lead time or reason", () => {
  localStorage.clear();
  const client = new QueryClient();
  const markup = renderToStaticMarkup(<QueryClientProvider client={client}>
    <OrderCommitmentPolicyPanel branches={[{ id: "branch", label: "Sucursal Matriz" }]} />
  </QueryClientProvider>);
  const node = document.createElement("div"); node.innerHTML = markup;
  expect(node.querySelector("select")?.value).toBe("");
  expect(Array.from(node.querySelectorAll("input")).map(input => input.value)).toEqual(["", ""]);
  expect(node.querySelector<HTMLButtonElement>("button[type='submit']")?.disabled).toBe(true);
  expect(node.textContent).toContain("No hay un plazo predeterminado");
  client.clear();
});
