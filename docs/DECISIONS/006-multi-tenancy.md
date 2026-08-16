# ADR-006: Multi-Tenancy from Day One

**Status:** Accepted
**Date:** 2026-07-23
**By:** [L]

## Decision

BuzzCRM is multi-tenant from the first migration. Every domain table carries `tenant_id`, NOT NULL, indexed. Tenant isolation is enforced at the data-access layer, not per-endpoint.

## Context

BuzzCRM starts as an internal tool for Skyscape sales. It may become an offering for client organizations, in which case data is sliced by tenant. Retrofitting tenancy touches every model, query, endpoint, and test — adding it now costs one column and one index.

## Naming

`Tenant` is the isolation boundary. It deliberately does NOT reuse "Organization," which already has a meaning in Buzz. See ADR-008 for the full glossary.

## Implementation Constraints

1. `tenant_id UUID NOT NULL` on every domain table, with an index. No exceptions for "internal" tables.
2. **Filtering happens at the repository/session layer.** A shared base query applies the tenant filter. Individual endpoints MUST NOT be responsible for remembering `WHERE tenant_id = ...`.
3. `sf_id` is unique **per tenant** — composite unique index `(tenant_id, sf_id)`, not a global unique. Two tenants can legitimately hold identical Salesforce record IDs.
4. Composite indexes lead with `tenant_id` where the column participates in lookups.
5. No cross-tenant joins. Ever. There is no legitimate query that spans tenants in application code.
6. Import runs inside exactly one tenant. A CSV upload is tenant-scoped at the request boundary.

## Testing Requirement (non-negotiable)

Every list and detail endpoint gets a cross-tenant isolation test: seed two tenants, authenticate as tenant A, assert tenant B's records are invisible and unfetchable by direct ID.

A missing `WHERE` clause is a cross-customer data leak. For a client-facing offering that is the failure mode that ends the product — so it gets tested, not trusted.

## Consequences

- Slightly more schema ceremony on every table.
- Seed/fixture data must always specify a tenant.
- Single-tenant Skyscape use is just one Tenant row; no special-casing.
