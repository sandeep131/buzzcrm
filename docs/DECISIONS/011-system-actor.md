# ADR-011: System Actor — a Per-Tenant Non-Human Identity

**Status:** Accepted
**Date:** 2026-08-16
**By:** [L]

## Decision

Every tenant is seeded with exactly one **system actor** — a real `users` row,
flagged `is_system = true`, that exists solely to be pointed at as the actor for
records no human created.

Consequently `created_by` and `updated_by` are **NOT NULL** on every domain
table. There is no such thing as a record without an actor.

## Context

Rule 6 requires an audit entry with an actor on every create, update, and delete,
and ADR-007 makes that actor a **foreign key** (FK) to `users` — a column whose
value the database itself requires to match a real `users` row — so an audit
entry cannot reference a user who does not exist. Attribution is guaranteed by
Postgres rather than by application discipline. Two cases have no human actor:

1. **Bootstrap.** The first tenant and the first user are created by nobody.
2. **Non-human writes.** Import batches (#9, #10) and, later, AI-proposed
   changes (Milestone 3) write rows on behalf of a process, not a person.

The alternative was nullable `created_by`. Rejected: it makes the actor optional
everywhere to serve two narrow cases, forces a NULL branch through every audit
read and every UI that renders "changed by", and weakens rule 6 from an
invariant into a convention. A seeded identity keeps the FK total.

## Per-Tenant, Never Global

The system actor is scoped to its tenant like any other user. There is **one per
tenant**, seeded when the tenant is created.

A single global system actor was considered and rejected. It would need its own
tenant, which would make `created_by` on every row of every tenant point at a
user outside that tenant — a permanent, legitimate cross-tenant reference on
every record in the database. That contradicts ADR-006 constraint 5 ("No
cross-tenant joins. Ever.") and would force the #8 isolation suite to carve out
an exception, which is precisely the kind of exception that hides a real leak.

Per-tenant keeps `users.tenant_id` honest and the isolation rule absolute.

## System Actor ≠ Super Admin

This identity holds **no privileges**. It is a pointer target, not a principal.

- It **cannot authenticate.** `get_current_user()` must never return it.
- When the Buzz SSO adapter replaces the stub (ADR-007), **no credential may
  ever resolve to a user with `is_system = true`.** The adapter rejects such a
  resolution rather than honouring it.
- It holds no elevated rights and no cross-tenant reach. Within its tenant it is
  an ordinary row that happens to be the attributed author of machine writes.

The naming is deliberate. "Super admin" invites a future contributor to conclude
it should be able to log in and see everything, which would turn an attribution
record into a privilege-escalation surface. It is a *system actor*: inert.

## Hidden Means Not-Listed, Not Invisible

The system actor must stay resolvable — rendering an audit entry needs to
produce "Imported by System". It is therefore not hidden, but **excluded from
listing and selection**: user lists, assignee pickers, and owner dropdowns.

Per ADR-006 constraint 2 and ADR-009 constraint 1, that exclusion belongs in the
repository base with explicit opt-in — **not** in individual endpoints. It is a
third query invariant alongside tenant scope and soft delete, and lands with
them in issue #3:

1. `tenant_id = <current tenant>` (ADR-006)
2. `deleted_at IS NULL` (ADR-009)
3. `is_system = false` — for user listings, opt-in to include (this ADR)

Invariant 3 differs from 1 and 2: it applies to *listing* users, not to
resolving one by ID. An audit entry's `actor_id` always resolves.

## Implementation Constraints

**1. Bootstrap is self-referential.** UUID primary keys are generated
application-side, so the system actor is inserted with `created_by` set to its
own id. No NULL is ever written, not even transiently.

**2. Circular foreign keys are deferred, not avoided.** Read the two pointers
together: `tenants.created_by → users` (a tenant was created by some user) and
`users.tenant_id → tenants` (a user belongs to some tenant). Each table
references the other, so under immediate checking neither the first tenant nor
the first user can be inserted — the first one written always points at
something that does not exist yet.

The audit-actor foreign keys are therefore declared `DEFERRABLE INITIALLY
DEFERRED`: Postgres checks them at COMMIT instead of after each statement, so
the tenant and its system actor are inserted in one transaction that is briefly
inconsistent in the middle and fully consistent at the end. The guarantee is not
weakened — only the moment of checking moves. This resolves the table-level
cycle too, so one mechanism handles both.

Actor foreign keys also carry `ON DELETE RESTRICT`: users are soft-deleted
(ADR-009), so a physical delete that would orphan an audit actor is a bug. The
database refuses it rather than cascading and silently destroying attribution.

**3. One per tenant, enforced by the database.** Partial unique index on
`(tenant_id) WHERE is_system AND deleted_at IS NULL`. A second system actor is
a constraint violation, not a code review catch.

**4. The system actor is not soft-deletable in practice.** Nothing should ever
delete it; every audit entry in the tenant may point at it. Not enforced by a
constraint in #2 — revisit if a tenant-deactivation path appears.

**5. The auth stub seeds a human too.** ADR-007's stub resolves "a seeded user".
That is the seeded *human* user, never the system actor — see constraint 1 of
the previous section.

## Clarification to ADR-006

ADR-006 constraint 1 reads "`tenant_id` on every domain table. No exceptions for
'internal' tables." `tenants` itself is the exception, because it *is* the
scope — as `DOMAIN_MODEL.md` already states. Recorded here so a reviewer does
not flag correct code, and so a future contributor does not "fix" it by adding a
self-referential column. Every *other* table, including `users`, obeys the rule
without exception.

## Testing Requirement

- Every seeded tenant has exactly one system actor
- A second system actor in the same tenant violates the unique index
- The system actor's `created_by` resolves to itself
- Seeding is idempotent — re-running produces no duplicate tenant or actor
- `created_by` / `updated_by` reject NULL

## Consequences

- `created_by` is a total function. Audit reads and "changed by" UI need no NULL
  case, now or later.
- Import (#10) and AI writes (Milestone 3) have an attributable actor already
  present, rather than needing one retrofitted once rows exist.
- Tenant creation is never a bare INSERT — it is "create tenant + seed its
  system actor" in one transaction. Any future tenant-provisioning path must use
  it, or it produces a tenant whose records cannot be attributed.
- Three query invariants instead of two for user listings, all centralised in the
  issue #3 repository base.
