# Administrative authorization presentation

Scope: ZM-FIN-015–022, DEC-03 and DEC-04. The backend owns the capability vocabulary,
effective grants, assignment scope, authorization version and request decisions. The
Backoffice renders those decisions; hiding or disabling a control never authorizes a
request.

## Session and navigation

Backoffice obtains one current identity from `GET /v1/auth/me?surface=BACKOFFICE`.
POS introspection requests `surface=POS`. A grant resolved for another surface cannot
enable Backoffice navigation, even when its capability code is shared by both apps.
Neither a Backoffice surface, email address, role label nor the informational
`is_superadministrator` flag creates a capability in the client.

Navigation uses generated capability codes and omits sections without a permitted
released route. Direct navigation performs the same capability check before rendering
the module. The administrative landing selects the first permitted released route;
an account without grants sees an access-denied screen. Existing release exclusions
remain in force, including the roles/settings modules.

Current identity refreshes on window focus and every 60 seconds. A changed actor or
authorization version first cancels and removes administrative queries and mutation
results, then remounts administrative component state. Token replacement and logout
clear the complete query cache. A protected API 403 removes administrative results and
refreshes identity. A 401 clears the local session. Backend checks apply immediately
on each request; the refresh interval is a presentation limit, not a revocation window
for the API.

## Actions and scopes

Visible mutations require the corresponding generated capability and any known branch
IDs, in addition to the existing backend `available_actions` and document-state flags.
Transfers require both ends. Create-and-start/dispatch controls require both management
and execution. Viewing a report or audit record does not enable its export. Shared
master mutations require explicit GLOBAL; recipe standard-cost application also
requires pricing management. Branch creation requires GLOBAL branch management.

Users can be created without roles. Branch assignment is separate authority from user
profile management. The user detail supplies the flags for managing profile, application
access, branch assignments and role assignments. Role changes use the canonical
`POST /v1/admin/users/{id}/roles` with required `role_id`, `scope_type` and `branch_ids`.
GLOBAL carries an empty list; BRANCH_SET requires selected active target branches within
the actor's effective assignment scope. Revocation uses the existing `/roles/{id}/remove`
route. The hidden role panel points assignment management to this one editor instead of
maintaining a second implicit-scope workflow. Superadministrator changes remain subject
to the backend's separate approval procedure.

Unused client role-label and legacy scope constants were removed. Presentation DTO
adapters remain local to each module; authorization capability and scope types are
derived from the backend-generated contract.

## Verification

Unit tests cover missing/empty/inactive grants, application separation, differing read
and write scopes, both transfer ends, GLOBAL master mutations, independent export
authority, authorized landing/release exclusions and authorization cache disposal.
Component fixtures declare their required capabilities explicitly.

The real isolated browser seed grants its reader seven view capabilities for one
branch, creates a Backoffice account with no grants, and exports only disposable branch
IDs as scope evidence. Real browser checks cover route denial, valid-token API 403,
foreign branch rejection, disabled management/export and revocation while the original
token and browser session remain open. Reader revocation runs through the same guarded
disposable-database fixture script. The suite still prohibits API interception and
credential-bearing traces, screenshots or storage state.

Validated locally on 2026-09-12 with Node.js 22.23.2 and the canonical toolchain:

| Validation                                                                     | Result                                                                                                |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `check-foundation.ps1 -Stage Web`                                              | PASS: lint, typecheck, unit tests, production builds and existing browser suites.                     |
| Unit tests                                                                     | POS 48 files / 236 tests; Backoffice 60 files / 220 tests; shared packages 6 tests. Total 462 passed. |
| Existing browser suites                                                        | POS 8/8; Backoffice 1/1. Tracked screenshot artifacts remain unchanged.                               |
| `run-web-integration.ps1 -Surface All`                                         | PASS: POS 2/2, Backoffice 6/6, 40 migrations, API/worker readiness and cleanup.                       |
| `ruff check scripts/dev/seed-web-integration.py` and scoped `git diff --check` | PASS.                                                                                                 |

The final real run is `7227425c36864b02a666e9b91c6daccd`, under
`.tmp/validation/web/7227425c36864b02a666e9b91c6daccd/`. It verifies an exact one-branch
list and total, 404 for a foreign detail lookup, 403 for a declared foreign branch
filter and export without permission, plus live grant revocation. Preliminary runs
corrected test assumptions about foreign lookups and unsupported query parameters;
the final assertions use the canonical response semantics without permissive alternatives.

The Web stage record is
`.tmp/validation/foundation/32879e6f573249c5bc8ff021a4f691e8/Web.json`. It records the
modified working tree; hosted validation of the final candidate remains separate.
Existing warnings remain two router fast-refresh warnings per app and large production
chunks (approximately 952 kB POS and 1,628 kB Backoffice). This block does not certify
every business journey or complete hidden administrative modules.
