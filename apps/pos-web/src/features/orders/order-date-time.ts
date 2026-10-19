function parts(instant: Date, timeZone: string): string {
  const values = Object.fromEntries(
    new Intl.DateTimeFormat("en-CA", {
      timeZone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hourCycle: "h23",
    })
      .formatToParts(instant)
      .map((part) => [part.type, part.value]),
  );
  return `${values.year}-${values.month}-${values.day}T${values.hour}:${values.minute}:${values.second}`;
}

export function orderDateTimeInput(instant: string, timeZone: string): string {
  return parts(new Date(instant), timeZone).slice(0, 16);
}

export function orderDateTimeLabel(value: string, timeZone: string | undefined): string {
  if (!value.trim()) return "Sin fecha de recoleccion";
  if (!timeZone) return "Consultando zona horaria de la sucursal";
  try {
    return formatLocalDateTime(orderDateTimeToUtc(value, timeZone), timeZone);
  } catch {
    return "Revisa la fecha y hora de recolección";
  }
}

/** Interpret the branch wall clock independently of the browser operating system zone. */
export function orderDateTimeToUtc(value: string, timeZone: string): string {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?$/.test(value)) {
    throw new Error("Captura una fecha y hora de entrega válidas.");
  }
  const normalized = value.length === 16 ? `${value}:00` : value;
  const wall = Date.parse(`${normalized}Z`);
  if (!Number.isFinite(wall)) throw new Error("La fecha de entrega no es válida.");
  const offsets = new Set<number>();
  for (const hours of [-36, -12, 0, 12, 36]) {
    const sample = wall + hours * 3_600_000;
    offsets.add(Date.parse(`${parts(new Date(sample), timeZone)}Z`) - sample);
  }
  const matches = [...offsets]
    .map((offset) => new Date(wall - offset))
    .filter((candidate) => parts(candidate, timeZone) === normalized);
  if (matches.length !== 1) {
    throw new Error("Esta hora es inexistente o ambigua en la sucursal. Elige otra hora.");
  }
  return matches[0]!.toISOString();
}
import { formatLocalDateTime } from "../../lib/formatters";
