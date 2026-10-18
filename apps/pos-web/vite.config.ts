import { readFileSync } from "node:fs";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const isolated = process.env.ZM_WEB_INTEGRATION_ISOLATED === "1";
const localHttps = process.env.ZM_LOCAL_HTTPS === "1" && process.env.ZEROMERMA_API_ENVIRONMENT === "local";
const certPath = isolated ? process.env.ZM_E2E_TLS_CERT_FILE : localHttps ? process.env.ZM_LOCAL_TLS_CERT_FILE : undefined;
const keyPath = isolated ? process.env.ZM_E2E_TLS_KEY_FILE : localHttps ? process.env.ZM_LOCAL_TLS_KEY_FILE : undefined;
if ((isolated || localHttps) && (!certPath || !keyPath)) throw new Error("HTTPS requires both certificate and key paths.");
const developmentTls = certPath && keyPath ? { cert: readFileSync(certPath), key: readFileSync(keyPath) } : undefined;

export default defineConfig({
  plugins: [react()],
  preview: {
    host: "0.0.0.0",
    port: 4173,
    allowedHosts: [".trycloudflare.com"],
  },
  server: {
    https: developmentTls,
    host: "0.0.0.0",
    port: 5173,
    allowedHosts: [".trycloudflare.com"],
  },
  test: {
    globals: true,
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
