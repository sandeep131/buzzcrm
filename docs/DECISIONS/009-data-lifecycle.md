# ADR-009: Data Lifecycle — Soft Delete and Orphan Contacts

**Status:** Accepted
**Date:** 2026-07-23
**By:** [L]

## Decisions

1. **Soft delete.** Domain records are never physically removed. `deleted_at timestamptz NULL` + `deleted_by UUID FK → users`.
2. **Orphan Contacts are permitted.** `contacts.company_id` is nullable. A Contact with no Company imports successfully rather than failing the batch.

## Rationale — Soft Delete

Rule 6 requires an audit trail for deletes. A hard delete destroys the row the audit entry refers to, leaving an audit log pointing at nothing. Soft delete keeps the record resolvable and makes accidental deletion recoverable — which matters when the delete arrives via a bulk import path.

## Rationale — Orphan Contacts

Design principle 5: import imperfect data, clean in staging. Real Salesforce exports contain contacts whose account reference is missing, stale, or points at a record excluded from the export. Rejecting them loses data; blocking the batch on them makes import brittle. They land, flagged, and get resolved in the UI.

## Implementation Constraints

**1. Filtering is layered, not per-endpoint.** The same rule as tenant scoping (ADR-006): the repository base query applies `deleted_at IS NULL`. Endpoints do not remember to filter. An explicit opt-in is required to see deleted rows.

**2. Unique indexes must be partial.** This is the trap. A plain unique index on `(tenant_id, sf_id)` will reject a re-import of a record that was soft-deleted — the row still exists, so the constraint still fires. Use:

```sql
CREATE UNIQUE INDEX ... ON companies (tenant_id, sf_id)
WHERE deleted_at IS NULL AND sf_id IS NOT NULL;
```

Every uniqueness constraint on a soft-deletable table follows this pattern. @qa checks it in review.

**3. Cascade is logical, not physical.** Soft-deleting a Company does NOT delete its Contacts and Opportunities in the database. Decide and document the display behaviour — the children are then effectively orphaned, which the orphan decision above already tolerates.

**4. Orphan Contacts still carry `tenant_id`.** Nullable company, never nullable tenant.

**5. Import surfaces orphans.** A contact arriving with an unresolvable account reference is committed with `company_id = NULL` and counted in the batch report, not silently swallowed.

## Testing Requirement

- Soft-deleted records are absent from list and detail endpoints
- A soft-deleted record's `sf_id` can be re-imported without constraint violation
- Audit entry for a delete resolves to the still-present record
- Import batch containing orphan contacts completes and reports the orphan count

## Consequences

- Every query path carries a `deleted_at` predicate. Enforced centrally, so the cost is one base class.
- Physical purge (retention, GDPR erasure) is a separate future concern needing its own ADR.
- Frontend needs an "unassigned" view for orphan contacts. Milestone 1, not MVP.
