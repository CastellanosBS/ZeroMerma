# Local hardware boundary — ZM-FIN-059/064

Status: software foundation implemented; **ZM-FIN-064 remains partial**. No real
printer/drawer combination is certified, no physical adapter is installed in the
runtime, and no signed installer/update package has been validated. The entrypoint
has an intentionally empty device registry. Adding an active database binding does
not enable a device. The test adapter exists only in tests.

## Current behavior

- Sales, individual order payments, and returns retain immutable receipt snapshots
  inside the transaction that confirms their source. Database triggers reject edits
  and deletion. SHA-256 verification checks the saved document on read. Old records
  without a snapshot cannot acquire a fabricated original through a read/reprint.
- TCK, OPR, and DEV references use the complete source UUID. Original names,
  amounts, currency, branch timezone, workstation and operator remain frozen.
  Return settlement/pending amounts describe the instant the receipt was issued.
- The branch's commercial name, optional business descriptor and structured
  address are frozen into new receipts. Historical documents retain their original
  identity, including an absent commercial profile. Seller legal name, RFC and
  regime remain **UNCONFIGURED**; commercial configuration is not fiscal identity.
  The [Merenna profile](merenna-opening-profile.md) is prepared for a new real branch
  and has not been applied to demonstration branches. Fiscal review remains open.
  The receipt is operational; it is neither a CFDI nor a BBVA receipt. Rendering
  does not invent a QR, RFC, bank confirmation or digital-delivery result.
- Browser print is an **UNCERTIFIED fallback**. Opening the print dialog records
  a print request, not physical completion. Driver/dialog errors remain visible;
  printing cannot repeat a sale, payment, return or cash movement.
- The independent Python bridge listens on loopback port 17651. It imports the
  backend-owned device protocol but no business transaction service. Exact Origin,
  loopback peer/Host, branch, workstation, binding version, environment and device
  capability must match a short-lived HMAC authorization issued by the backend.
- The backend admits print commands only for an authorized immutable receipt.
  Drawer commands require an owned, confirmed, positive CASH ledger effect;
  a unique constraint permits one command identity per cash effect. PRINT carries
  no drawer cause. Manual drawer opening is disabled. Automatic POS drawer dispatch
  still requires integration and physical validation before use.
- SQLite stores only command/device IDs, a command digest, queue order, state and
  an opaque evidence reference. It never stores the receipt body, customer data,
  operator name, pairing key or provider diagnostic text. PostgreSQL remains the
  business authority. One process owns each spool; execution is FIFO per device.
- The adapter receives a five-second timeout contract. A certified adapter must
  enforce it at its transport boundary. The kernel does not forcibly kill an
  arbitrary driver that ignores its contract.

## Recovery and physical truth

The POS persists only canonical command-intention metadata (UUIDv7, actor/station,
source IDs, digest and state). Grants and command bodies are volatile and forgotten
at an authentication boundary. Lost acknowledgements are recovered with a GET by
the original idempotency key; refresh never invents a new job to resolve uncertainty.
Changing the selected receipt or authentication generation invalidates late UI results.

`/commands/status` is read-only. An absent job is UNKNOWN, never proof that a
physical action did not occur. After an explicit QUEUED result, the POS can resume
the **same** job with a renewed authorization and unchanged command digest. Queue
payloads are not persisted locally, so a queued job after restart needs that same
signed payload again. A crash with a PROCESSING job changes it to UNKNOWN; it is
never resent automatically. UNKNOWN requires inspection/reconciliation before
another physical copy. A device acknowledgement alone is ACKNOWLEDGED, not PRINTED.
PRINTED/OPENED require matching action and opaque adapter evidence.

Preserve spool continuity across upgrades/restarts. Deleting/restoring an older
spool may remove physical deduplication evidence; it is not an operational recovery
procedure. Signed installation/update, pairing/rotation/revocation provisioning,
device replacement, spool backup continuity and retention need deployment evidence
before any real adapter is enabled.

## Local diagnostics and validation

The existing canonical toolchain must be installed. Provision a random 256-bit-or-
stronger hex pairing value in a private file using the repository's
`core.runtime_secrets.write_private_secret`; never pass the value on a command line.
The bridge validates owner-only file access. Create a private spool directory and
run diagnostics in the foreground:

```powershell
./scripts/dev/run-local-hardware.ps1 -PairingKeyFile C:\private\pairing.hex -Spool C:\private\device-spool.sqlite3 -PosOrigin https://pos.example.test
```

This starts diagnostics only; it does not print, pulse a drawer, provision a device,
or install a Windows service. `/health` performs no physical action. The browser
must allow the origin's loopback request; browser/OS permission behavior must be
tested on the actual installation, including HTTPS and local-network restrictions.

```powershell
uv run --frozen pytest apps/api/unit_tests/test_local_hardware.py
./scripts/dev/run-api-tests.ps1 -TestTarget @('apps/api/tests/test_tickets_module.py','apps/api/tests/test_hardware_commands.py','apps/api/tests/test_admin_sales_tickets.py')
corepack pnpm --filter @zeromerma/pos-web exec vitest run src/features/tickets/hardware-receipt-action.test.tsx src/features/tickets/receipt-print-button.test.tsx src/lib/local-hardware-transport.test.ts src/features/tickets/print.test.ts
```

These tests also participate in the existing Backend/Web foundation stages; they
are not a separate certification pipeline. The focused PostgreSQL run
`pos-receipts-hardware-059-064-r3/4b4c6067b0c7430699b8b7aac5d310e5` passed 15 tests;
the local runtime unit suite passed 17 tests. This evidence demonstrates software
behavior with simulated devices, not an installed physical system.

## Evidence still required

| Decision or evidence | Why it remains required |
| --- | --- |
| Printer brand/model, firmware, 80 mm paper support, USB/Ethernet connection, OS/driver | Implement and certify an exact adapter; generic ESC/POS resemblance is insufficient. |
| Drawer model, interface, voltage/pulse specification and compatible printer port | Avoid guessing an electrical protocol; test causal opening once per cash effect. |
| Actual PC OS/browser and POS origin/network deployment | Validate loopback permissions, process startup, private files and secure pairing. |
| Physical normal print, paper-out, disconnect, timeout, restart, duplicate/reprint and drawer tests | Prove each physical state and recovery path without repeating economic effects. |
| Signed installer/version/update and provisioning/revocation process | The repository currently has a diagnostic entrypoint and test registrations only. |
| Apply the prepared commercial profile to the real branch and review operational ticket fields | Software supports frozen branch identity; real onboarding and printed samples remain pending. Fiscal identity is separate and unconfigured. |
| BBVA terminal model/firmware, merchant integration entitlement and official protocol/SDK | This bridge does not implement or certify a BBVA protocol. |

No printer, drawer or terminal compatibility is claimed by these software tests.
