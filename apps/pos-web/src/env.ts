import { z } from "zod";

const envSchema = z.object({
  VITE_API_BASE_URL: z.string().url().default("http://localhost:8000"),
  VITE_POS_WORKSTATION_CODE: z.string().trim().min(1).default("POS-01"),
});

export function resolvePosEnv(source: Record<string, string | undefined>) {
  return envSchema.parse(source);
}

export const appEnv = resolvePosEnv({
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL,
  VITE_POS_WORKSTATION_CODE: import.meta.env.VITE_POS_WORKSTATION_CODE,
});
