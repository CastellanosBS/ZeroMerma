import { type KeyboardEvent as ReactKeyboardEvent, type RefObject, useCallback } from "react";

import { getFocusableElements } from "../../../lib/keyboard-shortcuts";

export function useFocusFlow({
  containerRef,
  enabled = true,
  loop = true,
}: {
  containerRef: RefObject<HTMLElement>;
  enabled?: boolean;
  loop?: boolean;
}) {
  const focusFirst = useCallback(() => {
    const first = getFocusableElements(containerRef.current)[0];
    first?.focus();
    return Boolean(first);
  }, [containerRef]);

  const focusLast = useCallback(() => {
    const items = getFocusableElements(containerRef.current);
    const last = items[items.length - 1];
    last?.focus();
    return Boolean(last);
  }, [containerRef]);

  const onKeyDownCapture = useCallback(
    (event: ReactKeyboardEvent<HTMLElement>) => {
      if (!enabled || event.key !== "Tab") {
        return;
      }

      const items = getFocusableElements(containerRef.current);
      if (items.length === 0) {
        return;
      }

      const activeElement = document.activeElement as HTMLElement | null;
      const currentIndex = activeElement ? items.indexOf(activeElement) : -1;
      if (currentIndex === -1) {
        return;
      }

      const isBackward = event.shiftKey;
      const isAtBoundary =
        (isBackward && currentIndex === 0) || (!isBackward && currentIndex === items.length - 1);

      if (!isAtBoundary || !loop) {
        return;
      }

      event.preventDefault();
      if (isBackward) {
        items[items.length - 1]?.focus();
        return;
      }

      items[0]?.focus();
    },
    [containerRef, enabled, loop],
  );

  return {
    focusFirst,
    focusLast,
    scopeProps: {
      "data-pos-focus-flow": true,
      onKeyDownCapture,
    },
  };
}
