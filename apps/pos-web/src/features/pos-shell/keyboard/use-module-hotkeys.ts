import { useEffect } from "react";

import { type KeyboardShortcutDefinition } from "./keyboard-shortcut-registry-context";
import { useKeyboardShortcutRegistry } from "./use-keyboard-shortcut-registry";

export function useModuleHotkeys(shortcuts: readonly KeyboardShortcutDefinition[], enabled = true) {
  const { registerShortcuts } = useKeyboardShortcutRegistry();

  useEffect(() => {
    if (!enabled || shortcuts.length === 0) {
      return;
    }

    return registerShortcuts(shortcuts);
  }, [enabled, registerShortcuts, shortcuts]);
}
