import { useContext } from "react";

import { KeyboardShortcutRegistryContext } from "./keyboard-shortcut-registry-context";

export function useKeyboardShortcutRegistry() {
  const context = useContext(KeyboardShortcutRegistryContext);

  if (context === null) {
    throw new Error("useKeyboardShortcutRegistry must be used inside KeyboardShortcutRegistry.");
  }

  return context;
}
