import { onlineManager } from "@tanstack/react-query";
import { afterEach, expect, it, vi } from "vitest";
import { queryClient } from "./query-client";

afterEach(() => { onlineManager.setOnline(true); queryClient.clear(); });

it("runs LAN reads and one command attempt even when the browser reports offline", async () => {
  onlineManager.setOnline(false);
  const read = vi.fn().mockResolvedValue("local data");
  const command = vi.fn().mockRejectedValue(new Error("local server unavailable"));
  await expect(queryClient.fetchQuery({ queryKey: ["local-read"], queryFn: read })).resolves.toBe("local data");
  const mutation = queryClient.getMutationCache().build(queryClient, { mutationFn: command });
  await expect(mutation.execute(undefined)).rejects.toThrow("local server unavailable");
  onlineManager.setOnline(true);
  expect(read).toHaveBeenCalledTimes(1);
  expect(command).toHaveBeenCalledTimes(1);
  expect(mutation.state.isPaused).toBe(false);
});
