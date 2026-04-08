import type { components } from "@zeromerma/api-client";

export type HealthResponse = components["schemas"]["HealthResponse"];

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function fetchApiHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`);

  if (!response.ok) {
    throw new Error("API health check failed.");
  }

  return (await response.json()) as HealthResponse;
}
