export const selectionShortcutLimit = 10;
export const focusableElementSelector =
  'button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function getSelectionShortcutLabel(index: number): string | null {
  if (index < 0 || index >= selectionShortcutLimit) {
    return null;
  }

  if (index === 9) {
    return "0";
  }

  return String(index + 1);
}

export function getSelectionShortcutIndex(key: string): number | null {
  if (key >= "1" && key <= "9") {
    return Number.parseInt(key, 10) - 1;
  }

  if (key === "0") {
    return 9;
  }

  return null;
}

export function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  if (target.isContentEditable) {
    return true;
  }

  const tagName = target.tagName;
  return tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT";
}

export function getFocusableElements(
  container: ParentNode | null,
  selector: string = focusableElementSelector,
): HTMLElement[] {
  if (!container) {
    return [];
  }

  return Array.from(container.querySelectorAll<HTMLElement>(selector)).filter(
    (element) => !element.hasAttribute("disabled") && element.getAttribute("aria-disabled") !== "true",
  );
}

export function focusRelativeItem({
  currentTarget,
  direction,
  scope,
  selector,
}: {
  currentTarget: HTMLElement;
  direction: -1 | 1;
  scope?: ParentNode | null;
  selector: string;
}): boolean {
  const items = getFocusableElements(scope ?? currentTarget.parentElement, selector);
  const currentIndex = items.indexOf(currentTarget);

  if (currentIndex === -1) {
    return false;
  }

  const nextItem = items[currentIndex + direction];
  if (!nextItem) {
    return false;
  }

  nextItem.focus();
  return true;
}

export function focusEdgeItem({
  currentTarget,
  edge,
  scope,
  selector,
}: {
  currentTarget: HTMLElement;
  edge: "first" | "last";
  scope?: ParentNode | null;
  selector: string;
}): boolean {
  const items = getFocusableElements(scope ?? currentTarget.parentElement, selector);
  const target = edge === "first" ? items[0] : items[items.length - 1];

  if (!target) {
    return false;
  }

  target.focus();
  return true;
}
