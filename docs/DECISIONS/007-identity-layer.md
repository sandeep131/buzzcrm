# ADR-007: Identity Layer — Stub Now, SSO Adapter Later

**Status:** Accepted
**Date:** 2026-07-23
**By:** [L]

## Decision

Identity is the first layer built, before any CRM entity. A real `users` table exists from migration one, tenant-scoped. Authentication for MVP is a stub; the Buzz SSO adapter replaces it later without schema change.

## Why Identity Comes First

Rule 6 requires an audit entry with an actor on every create, update, and delete. The actor is a foreign key to `users` — a database-enforced pointer, so an audit row cannot reference a user who does not exist. A foreign key cannot point at a table that does not exist yet. Therefore `users` precedes `companies`, `contacts`, and `opportunities`.

The same applies to tenancy: `users.tenant_id` is what makes `get_current_user()` able to establish tenant scope for the request.

## Structure

- `tenants` — the isolation boundary (ADR-006)
- `users` — `tenant_id` FK, email, display name, active flag, audit fields
- `get_current_user()` — a single FastAPI dependency returning the authenticated user **and** their tenant. Every route depends on it. Tenant scope flows from here into the repository layer.

## MVP Stub

`get_current_user()` returns a seeded user from a seeded tenant. No password handling, no session management, no token validation.

**Constraint:** the stub means there is effectively no authentication. The MVP must NOT be deployed to a public network. Local and trusted-network only until the adapter lands. This is recorded so it cannot be forgotten at deploy time — see ADR-004 (deployment target, pending).

## Swap Path

Replacing the stub touches exactly one function. The SSO adapter validates the Buzz credential, resolves it to a `users` row, and returns the same object. No model changes, no endpoint changes, no audit changes.

Per ADR-003, the adapter is a boundary — BuzzCRM never calls into Buzz internals.

## Deliberately Out of Scope for MVP

Roles, permissions, and field-level access. MVP has one permission level: authenticated. Granular permissions need the sales roles list from the Skyscape team (open handoff in HUB.md) and get their own ADR.

## Consequences

- Audit trail is real from the first record, not retrofitted.
- Tenant scoping has a single source of truth per request.
- Deployment is gated on the auth swap — accepted and tracked.
