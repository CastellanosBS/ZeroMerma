import type { components } from "@zeromerma/api-client";

type Grant = components["schemas"]["SignedDeviceCommand"];
type Result = components["schemas"]["DeviceCommandResult"];
const states = ["QUEUED", "PROCESSING", "ACKNOWLEDGED", "PRINTED", "OPENED", "UNAVAILABLE", "UNKNOWN"] as const satisfies readonly Result["state"][];

/** Loopback transport only. The signed backend grant is the device authority. */
export async function requestLocalHardware(grant: Grant, consult: boolean): Promise<Result> {
  const response = await fetch(`http://127.0.0.1:17651/commands${consult ? "/status" : ""}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(grant), signal: AbortSignal.timeout(7_000), credentials: "omit", cache: "no-store",
  });
  if (!response.ok) throw new Error("Bridge unavailable");
  const body: unknown = await response.json();
  if (typeof body !== "object" || body === null || !("command_id" in body) || body.command_id !== grant.command.id
    || !("state" in body) || typeof body.state !== "string"
    || !states.some((state) => state === body.state)
    || ("evidence_reference" in body && body.evidence_reference !== null
      && (typeof body.evidence_reference !== "string" || !/^[A-Za-z0-9_.:-]{1,120}$/.test(body.evidence_reference)))) {
    throw new Error("Invalid local device response");
  }
  if ((body.state === "PRINTED" || body.state === "OPENED")
    && ((body.state === "PRINTED") !== (grant.command.kind === "PRINT")
      || !("evidence_reference" in body) || !body.evidence_reference)) {
    throw new Error("Physical completion requires matching device evidence");
  }
  return body as Result;
}
