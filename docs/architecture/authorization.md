# Capability and branch authorization

This implements DEC-03, DEC-04 and the owner designation in DEC-19 for
ZM-FIN-015–022. FastAPI remains the contract authority. Backoffice access alone
does not authorize an administrative operation.

## Capability authority

`modules/identity/application/permissions.py` declares the 55 approved capability
codes. Reading, management, execution, cancellation, export and role assignment
are separate authorities. The three retired broad capabilities have no runtime
aliases. Every API method has an explicit policy in `presentation/access_policy.py`;
an unclassified operation is denied and fails the policy coverage check.

Authentication identifies an active, unlocked account. Authorization resolves
active role assignments, active roles and active catalog permissions from the
database. Tokens carry identity, not permission grants. Database column projections
avoid stale ORM objects while preserving pending application edits.

`AuthenticatedUser.effective_grants` is generated into the shared TypeScript client.
Each grant contains a capability, `GLOBAL` or `BRANCH_SET`, and branch IDs.
`authorization_version` identifies the effective authority and surface. Backoffice
requests `/v1/auth/me?surface=BACKOFFICE`; POS requests `surface=POS`. Shared
capabilities do not combine the scopes of roles from different surfaces. The
operation's backend policy selects its own surface independently of `/me` input.

The frontend uses grants for route and action visibility. It clears administrative
query data when account or effective authority changes. Backend authorization is
required regardless of hidden buttons, cached grants or caller-supplied filters.

## Scope resolution and resources

`UserRoleAssignment.scope_type` is mandatory. The normalized
`UserRoleAssignmentBranchScope` relation has a composite assignment/branch key.
Deferred PostgreSQL constraints enforce these cardinalities at transaction commit:

- `GLOBAL` has no branch rows.
- `BRANCH_SET` has at least one branch row.
- An absent scope is invalid; an empty effective branch set grants nothing.

For one capability and surface, branch sets from active assignments are united,
then intersected with the user's active branch assignments. An explicit global
assignment grants global scope for its explicit capabilities only. A transfer
requires authority over both origin and destination. Inactive branches may remain
visible for historical review but cannot accept ordinary economic mutations.

Collection scopes are applied before aggregation, counting and pagination. Direct
resource IDs and linked branch, workstation, cash-session and document references
are checked within the same authorized operation. Audit and outbox retain the
causal actor, operation and branch context. Shared masters without a branch owner
require `GLOBAL` for mutations; inventing a branch owner for a shared product,
price, recipe, supplier or global setting would not provide branch isolation.

Omitting an optional branch filter returns the authorized subset. An explicitly
declared branch query parameter outside the grant is rejected with 403. A detail
lookup for an unavailable scoped resource returns 404, avoiding disclosure of its
existence. Client filters cannot widen the server scope.

`db/access_scope.py` classifies every persisted family by direct branch columns,
parent ownership, shared master, identity metadata or causal trace. The session
boundary rejects unclassified SQL and applies mapped criteria to aliases,
subqueries and aggregates. It clears previously loaded clean ORM identities before
installing a scope, so cached `Session.get` results cannot bypass a scoped query.
Flush validation checks foreign keys, both ends of transfers, active responsible
staff membership, and matching workstation/cash-session relationships. User and
role administration use the complete target scope; a scoped administrator cannot
inspect or change a global identity through an overlapping branch membership.

Report definition capabilities are mandatory and intersect with report access
before filter options, metrics, previews or exported rows are built. Shared
reference catalogs remain shared. Domain `available_actions` preserve business
state restrictions and additionally require the action's capability over the
displayed resource. A read permission never makes its write actions available.

Domain writes and changes to identity authority coordinate on the singleton
`identity_privilege_state`: domain mutations take a shared transaction lock and
identity mutations take the exclusive lock. A permission revocation therefore
cannot overtake an already authorized economic commit. A command that starts
after revocation resolves the revoked authority and is denied.

Economic writes lock active branch rows and read current workstation ownership and
activity under shared locks until commit. Station administration locks branches
in UUID order before taking the station's exclusive lock, then checks open cash
sessions. Branch deactivation takes its exclusive lock before checking open
sessions. These boundaries prevent moving or disabling a location during a cash
opening. Transfer receipts retain the original source branch but validate their
station against the receiving branch; authorization still covers both ends.

Outbox headers preserve the authorization context of the committed action. The
current worker only observes due metadata and does not execute domain jobs or
grant authority from those headers. Delayed observation after revocation leaves
the original causal context intact and does not authorize a fresh API mutation.
Future executing handlers must define their system authority and revalidation
policy before they can make new changes.

## Privileged administration

The reserved system role is `explicit_superadmin`. It has no wildcard permission
and cannot be inferred from email, seed role, surface access or missing branches.
The initial role receives the frozen list of 55 explicit `RolePermission` rows.
A later catalog addition never silently grants a new capability to it.

The designated initial identity is `ZEROMERMA_OWNER`. Provisioning creates a new
account, records the designation durably and creates exactly one initial global
assignment. It cannot promote an existing demo/legacy account or run twice.

Ordinary user management, role maintenance and role/scope assignment have separate
capabilities. Neither an ordinary role assignment nor a role edit may elevate its
actor. Superadministrator changes use durable proposals with an exact payload
digest, different initiator and approver, expiration, one-use consumption and
execution-time revalidation. The last active global authority is protected under
the exclusive transaction lock. Administrative recovery authority cannot be
removed from the last effective administrator.

With only one active Superadministrator, the approved exception is the dedicated
local CLI. It consumes independently generated recovery material on its designated
host, promotes a different active Backoffice account to the second administrator,
rotates the material, and records audit/outbox atomically. There is no HTTP
break-glass endpoint.

## Migration and recovery

Revision `20260912_0040_authorization` follows `20260520_0039_system_settings`.
Existing assignments receive explicit branch sets from their active user-branch
memberships. Unscopable assignments are removed after their complete previous
assignment is recorded in audit evidence. Roles using retired or unrecognized
capabilities are deactivated for review before those capabilities are removed.
The migration does not promote any existing account or create global assignments.
Review events are also emitted through the transactional outbox.

The migration adds normalized scopes, a serialized owner/privilege state, durable
approval records and hashed recovery credentials. Deferred constraints validate
both assignments when a scope row is moved. Database schema and ORM constraints
are covered by the exact schema-drift baseline.

There is no lossy downgrade to implicit authority. Roll forward with a reviewed
migration, or restore a verified database backup. Demo and test records remain
non-production data under DEC-19; this migration does not turn them into business
history.

See [the operating procedure and validation evidence](../implementation/authorization-validation.md).
