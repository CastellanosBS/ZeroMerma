# API contract policy

ZeroMerma has one HTTP contract chain:

```text
FastAPI/Pydantic
  -> runtime OpenAPI
  -> packages/api-client/openapi.json
  -> packages/api-client/src/generated/schema.ts
  -> packages/api-client/src/transport.ts
  -> POS and Backoffice adapters
```

The runtime application is authoritative. The tracked OpenAPI document, generated TypeScript
schema, and API contract inventory are derived artifacts. Do not edit them manually. The
versioned policy is `docs/architecture/API_CONTRACT_POLICY.json`; the derived per-operation
inventory is `docs/architecture/API_CONTRACT_INVENTORY.json`.

## Generate and check

Run these commands from the repository root with the canonical toolchain:

```powershell
corepack pnpm contracts:generate
corepack pnpm contracts:check
```

`contracts:generate` creates all three derived artifacts from the real app and the versioned
policy. `contracts:check` generates into a temporary directory, compares bytes, reports the
drifting artifact, removes its temporary directory, and never rewrites tracked files. The
foundation gate runs `contracts:check` after frozen Python and Node installs.

The old partial-generation PowerShell script and package `generate:types` command are
removed. `contracts:generate` is the sole command that updates the three derived artifacts.

Generation is deterministic: no timestamp, hostname, username, random identifier, or local
absolute path is emitted. The OpenAPI document is UTF-8 JSON with recursively stable key order;
the TypeScript file is produced by the lockfile-resolved `openapi-typescript` 7.13.0 dependency
(declared compatibly as `^7.4.4`; no dependency changed in ZM-FIN-009).

## Operation identity and visibility

Every included operation has a unique FastAPI-derived `operationId`. Existing IDs remain stable;
the gate fails on missing, duplicate, orphaned, or uncovered IDs. `GET /dev/audit/snapshot`
remains hidden (`include_in_schema=false`) and is not generated into the normal client.

## Errors

All API errors use `ApiErrorResponse`:

- `code`: stable protocol code for the HTTP status;
- `message`: safe user-facing message;
- `details`: optional structured context after sensitive-key redaction;
- `request_id`: the sanitized incoming `X-Request-ID`, when supplied;
- `field_errors`: structured locations/messages/types for request validation.

The contract covers 400, 401, 403, 404, 409, 422, and safe 500 responses. All consumers and
backend assertions use `message`; there is no legacy `detail` alias. POS and Backoffice
consume the canonical fields through the shared transport.

## Wire types

- UUID identifiers are JSON strings with OpenAPI `format: uuid`. Natural codes and visible
  folios remain strings and are not reinterpreted as internal identifiers.
- `Decimal`/PostgreSQL `Numeric` response values serialize as JSON decimal strings and generate
  TypeScript `string`. Existing request models accept JSON numbers or strings and generate
  `number | string`; callers should send decimal strings to preserve their original precision.
  The backend cannot recover precision already lost in a JavaScript number. Decimal annotations
  cover both unconstrained and digits/scale-constrained patterns, including number/string input
  unions. Domain rounding and request validation are unchanged.
- Calendar dates use ISO 8601 `date`. Datetimes serialize as ISO 8601 strings; aware values use
  RFC 3339 with UTC or a numeric offset. Pydantic preserves supplied offsets rather than forcing
  UTC. UTC remains the policy for authoritative instants, but existing request fields can accept
  naive datetimes and serialize them without a zone. The OpenAPI metadata reports representation;
  it does not enforce timezone validation. The owning business tasks must validate naive inputs
  before authoritative use. Local timezone remains a presentation or explicit configuration choice.
- Enums remain explicit closed values in OpenAPI. Adding a value requires consumer review.
- OpenAPI 3.1 nullability distinguishes a missing property, `null`, empty string, and zero.

## Collections, filters, and order

Every collection operation has one explicit versioned classification in the policy file:

- `PAGINATION_REQUIRED`: the existing `page`/`page_size` convention, default 25 and maximum 100,
  with a total-bearing response;
- `BOUNDED_OPERATIONAL_WINDOW`: a server-capped current/history window with an existing named or
  documented bound;
- `BOUNDED_REFERENCE_LIST`: a scoped configuration/reference registry;
- `EXPLICIT_COMPLETE_EXPORT`: an intentionally complete export selected by typed filters.

Each entry records expected growth, exact query parameters, its bound, fixed ordering, evidence,
and rationale. Unknown collections fail the gate. Client filters are contract inputs only; they
never replace backend branch, user, workstation, or cash-session scope enforcement.

## Frontend transport and local models

`packages/api-client/src/transport.ts` is the only production `fetch` boundary. It preserves auth,
request headers, request ID context, JSON bodies, typed responses, and canonical errors. Feature
adapters use generated schema aliases. Feature view models, form state, and derived UI models are
allowed, but handwritten wire request/response/error/pagination contracts are not.

The 65 operations without a connected local UI remain assigned to their vertical tasks; contract
normalization does not create those interfaces or close their functional gaps.

## Versioning and endpoint changes

The current path version is `/v1`. Additive optional fields and operations are normally
non-breaking. Deprecation requires an explicit replacement and removal window. A breaking change
requires a coordinated backend/OpenAPI/client/POS/Backoffice cutover in one task or a separately
approved API version; this task does not create `/v2`.

To add or modify an endpoint:

1. change the FastAPI/Pydantic source and preserve an explicit stable operation identity;
2. define real success and canonical error responses;
3. update the explicit collection policy when the response is a collection;
4. run `contracts:generate` and review the OpenAPI, TypeScript, and inventory diffs;
5. update central/feature adapters using generated request and response types;
6. add contract, error, precision, pagination/filter, and consumer tests as applicable;
7. run `contracts:check`, both frontend typechecks/tests/builds, and the functional-matrix gate;
8. classify compatibility and include the evidence in review.
