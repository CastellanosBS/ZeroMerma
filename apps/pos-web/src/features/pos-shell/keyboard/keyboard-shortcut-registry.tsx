import {
  type PropsWithChildren,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import { isEditableTarget } from "../../../lib/keyboard-shortcuts";
import {
  KeyboardShortcutRegistryContext,
  type KeyboardShortcutDefinition,
  type KeyboardShortcutRegistryContextValue,
  type RegisteredKeyboardShortcut,
} from "./keyboard-shortcut-registry-context";

const builtinShortcuts: RegisteredKeyboardShortcut[] = [
  {
    chords: ["F1", "Ctrl+/", "Meta+/"],
    description: "Abre la ayuda de atajos del POS.",
    group: "General",
    handler: () => undefined,
    id: "keyboard-help",
    label: "Abrir ayuda de teclado",
    order: 0,
    priority: 1000,
    source: "builtin",
  },
];

function normalizeShortcutKey(key: string): string {
  if (key === " ") {
    return "Space";
  }

  if (key.length === 1) {
    return key.toUpperCase() === key.toLowerCase() ? key : key.toUpperCase();
  }

  if (key === "Esc") {
    return "Escape";
  }

  return key;
}

function normalizeShortcutChord(chord: string): string {
  const parts = chord
    .split("+")
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) {
    return "";
  }

  const key = normalizeShortcutKey(parts[parts.length - 1]!);
  const modifiers = new Set(parts.slice(0, -1).map((part) => part[0]!.toUpperCase() + part.slice(1).toLowerCase()));
  const normalizedParts: string[] = [];

  if (modifiers.has("Ctrl")) {
    normalizedParts.push("Ctrl");
  }
  if (modifiers.has("Meta") || modifiers.has("Cmd")) {
    normalizedParts.push("Meta");
  }
  if (modifiers.has("Alt")) {
    normalizedParts.push("Alt");
  }
  if (modifiers.has("Shift")) {
    normalizedParts.push("Shift");
  }

  normalizedParts.push(key);
  return normalizedParts.join("+");
}

function getKeyboardEventChord(event: KeyboardEvent): string {
  const parts: string[] = [];

  if (event.ctrlKey) {
    parts.push("Ctrl");
  }
  if (event.metaKey) {
    parts.push("Meta");
  }
  if (event.altKey) {
    parts.push("Alt");
  }
  if (event.shiftKey) {
    parts.push("Shift");
  }

  parts.push(normalizeShortcutKey(event.key));
  return parts.join("+");
}

function matchesHelpShortcut(event: KeyboardEvent): boolean {
  if (event.key === "F1") {
    return true;
  }

  if (!(event.ctrlKey || event.metaKey)) {
    return false;
  }

  return event.key === "/" || event.key === "?";
}

function sortShortcuts(shortcuts: RegisteredKeyboardShortcut[]): RegisteredKeyboardShortcut[] {
  return [...shortcuts].sort((left, right) => {
    const priorityDelta = (right.priority ?? 0) - (left.priority ?? 0);
    if (priorityDelta !== 0) {
      return priorityDelta;
    }

    const groupDelta = left.group.localeCompare(right.group);
    if (groupDelta !== 0) {
      return groupDelta;
    }

    return (left.order ?? 0) - (right.order ?? 0);
  });
}

export function KeyboardShortcutRegistry({ children }: PropsWithChildren) {
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [registeredShortcuts, setRegisteredShortcuts] = useState<RegisteredKeyboardShortcut[]>([]);

  const openHelp = useCallback(() => setIsHelpOpen(true), []);
  const closeHelp = useCallback(() => setIsHelpOpen(false), []);
  const toggleHelp = useCallback(() => setIsHelpOpen((current) => !current), []);

  const registerShortcuts = useCallback((shortcuts: readonly KeyboardShortcutDefinition[]) => {
    const entries = shortcuts.map((shortcut) => ({
      ...shortcut,
      source: "module" as const,
    }));

    setRegisteredShortcuts((current) => [...current, ...entries]);

    return () => {
      setRegisteredShortcuts((current) =>
        current.filter((shortcut) => !entries.some((entry) => entry.id === shortcut.id)),
      );
    };
  }, []);

  const shortcuts = useMemo(
    () => sortShortcuts([...builtinShortcuts, ...registeredShortcuts]),
    [registeredShortcuts],
  );

  useEffect(() => {
    function handleKeyboard(event: KeyboardEvent) {
      if (matchesHelpShortcut(event)) {
        event.preventDefault();
        toggleHelp();
        return;
      }

      if (isHelpOpen && event.key === "Escape") {
        event.preventDefault();
        closeHelp();
        return;
      }

      const chord = getKeyboardEventChord(event);

      for (const shortcut of shortcuts) {
        if (!shortcut.chords.map(normalizeShortcutChord).includes(chord)) {
          continue;
        }

        if (shortcut.isEnabled && !shortcut.isEnabled()) {
          continue;
        }

        if (!shortcut.allowInEditable && isEditableTarget(event.target)) {
          continue;
        }

        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }

        if (shortcut.stopPropagation) {
          event.stopPropagation();
        }

        shortcut.handler(event);
        return;
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [closeHelp, isHelpOpen, shortcuts, toggleHelp]);

  const value = useMemo<KeyboardShortcutRegistryContextValue>(
    () => ({
      closeHelp,
      isHelpOpen,
      openHelp,
      registerShortcuts,
      shortcuts,
      toggleHelp,
    }),
    [closeHelp, isHelpOpen, openHelp, registerShortcuts, shortcuts, toggleHelp],
  );

  return (
    <KeyboardShortcutRegistryContext.Provider value={value}>
      {children}
    </KeyboardShortcutRegistryContext.Provider>
  );
}
