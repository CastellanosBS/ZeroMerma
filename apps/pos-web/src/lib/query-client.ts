import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    mutations: {
      // The browser's Internet hint must not pause commands to the local LAN server.
      // The transport checks local readiness and never queues or retries commands.
      networkMode: "always",
      retry: false,
    },
    queries: {
      networkMode: "always",
      refetchOnWindowFocus: false,
      retry: false,
    },
  },
});
