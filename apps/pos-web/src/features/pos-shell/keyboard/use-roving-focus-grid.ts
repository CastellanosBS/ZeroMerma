import { type KeyboardEvent as ReactKeyboardEvent, useCallback, useMemo, useRef, useState } from "react";

function normalizeIndex(index: number, itemCount: number, loop: boolean): number {
  if (itemCount === 0) {
    return -1;
  }

  if (loop) {
    return ((index % itemCount) + itemCount) % itemCount;
  }

  return Math.max(0, Math.min(index, itemCount - 1));
}

export function useRovingFocusGrid({
  columnCount = 1,
  itemCount,
  loop = true,
  onActivate,
}: {
  columnCount?: number;
  itemCount: number;
  loop?: boolean;
  onActivate?: (index: number) => void;
}) {
  const [activeIndex, setActiveIndex] = useState(0);
  const itemRefs = useRef<Array<HTMLElement | null>>([]);

  const clampedActiveIndex = useMemo(
    () => normalizeIndex(activeIndex, itemCount, false),
    [activeIndex, itemCount],
  );

  const focusIndex = useCallback(
    (index: number) => {
      const nextIndex = normalizeIndex(index, itemCount, loop);
      if (nextIndex < 0) {
        return;
      }

      setActiveIndex(nextIndex);
      itemRefs.current[nextIndex]?.focus();
    },
    [itemCount, loop],
  );

  const getItemProps = useCallback(
    (index: number) => ({
      "data-roving-focus-item": true,
      onFocus: () => setActiveIndex(index),
      onKeyDown: (event: ReactKeyboardEvent<HTMLElement>) => {
        let nextIndex: number | null = null;

        switch (event.key) {
          case "ArrowLeft":
            nextIndex = index - 1;
            break;
          case "ArrowRight":
            nextIndex = index + 1;
            break;
          case "ArrowUp":
            nextIndex = index - columnCount;
            break;
          case "ArrowDown":
            nextIndex = index + columnCount;
            break;
          case "Home":
            nextIndex = 0;
            break;
          case "End":
            nextIndex = itemCount - 1;
            break;
          case "Enter":
          case "NumpadEnter":
            if (onActivate) {
              event.preventDefault();
              onActivate(index);
            }
            return;
          default:
            return;
        }

        if (nextIndex === null) {
          return;
        }

        event.preventDefault();
        focusIndex(nextIndex);
      },
      ref: (node: HTMLElement | null) => {
        itemRefs.current[index] = node;
      },
      tabIndex: index === clampedActiveIndex ? 0 : -1,
    }),
    [clampedActiveIndex, columnCount, focusIndex, itemCount, onActivate],
  );

  return {
    activeIndex: clampedActiveIndex,
    focusIndex,
    getItemProps,
    setActiveIndex,
  };
}
