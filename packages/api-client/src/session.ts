import type { components } from "./generated/schema";

export type SessionResponse = components["schemas"]["LoginResponse"];
export type AuthSessionView = components["schemas"]["AuthSessionView"];

export function removeLegacyAuthStorage(storage?: Pick<Storage, "removeItem">): void {
  try {
    const target = storage ?? globalThis.localStorage;
    target?.removeItem("zeromerma-pos-auth");
    target?.removeItem("zeromerma-backoffice-auth");
  } catch {
    // Storage can be unavailable; authentication never depends on browser storage.
  }
}

export function observeOperatorActivity(
  target: Pick<Window, "addEventListener" | "removeEventListener">,
  onActivity: () => void,
  intervalMs = 30_000,
): () => void {
  let lastActivity = -Infinity;
  const listener = (event: Event) => {
    if (!event.isTrusted || Date.now() - lastActivity < intervalMs) return;
    lastActivity = Date.now();
    onActivity();
  };
  const events = ["keydown", "pointerdown", "touchstart"] as const;
  for (const event of events) target.addEventListener(event, listener, { passive: true });
  return () => {
    for (const event of events) target.removeEventListener(event, listener);
  };
}
