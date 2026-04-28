export function getCloseToneClasses(
  tone: "danger" | "info" | "success" | "warning",
): string {
  if (tone === "success") {
    return "border-[var(--ui-color-success-soft)] bg-[var(--ui-color-success-soft)] text-[var(--ui-color-success)]";
  }

  if (tone === "warning") {
    return "border-[var(--ui-color-warning-soft)] bg-[var(--ui-color-warning-soft)] text-[var(--ui-color-warning)]";
  }

  if (tone === "danger") {
    return "border-[var(--ui-color-danger-soft)] bg-[var(--ui-color-danger-soft)] text-[var(--ui-color-danger)]";
  }

  return "border-[var(--ui-color-info-soft)] bg-[var(--ui-color-info-soft)] text-[var(--ui-color-info)]";
}
