import { type KeyboardEvent as ReactKeyboardEvent, useCallback } from "react";

export function useNumpadSubmit({
  enabled = true,
  onEscape,
  onSubmit,
}: {
  enabled?: boolean;
  onEscape?: () => void;
  onSubmit: () => void;
}) {
  return useCallback(
    (event: ReactKeyboardEvent<HTMLElement>) => {
      if (!enabled) {
        return;
      }

      if (event.key === "Enter" || event.key === "NumpadEnter") {
        event.preventDefault();
        onSubmit();
        return;
      }

      if (event.key === "Escape" && onEscape) {
        event.preventDefault();
        onEscape();
      }
    },
    [enabled, onEscape, onSubmit],
  );
}
