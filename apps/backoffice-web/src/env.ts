import { z } from "zod";

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default("http://localhost:8000"),
  VITE_POS_BASE_URL: z.string().url().default("http://localhost:5173"),
});

export function resolveBackofficeEnv(source: Record<string, string | undefined>) {
  return envSchema.parse(source);
}

export const appEnv = resolveBackofficeEnv({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_POS_BASE_URL: import.meta.env.VITE_POS_BASE_URL,
});
