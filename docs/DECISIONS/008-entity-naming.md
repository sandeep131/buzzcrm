# ADR-008: Entity Naming — Tenant, Company, and the Buzz Boundary

**Status:** Accepted
**Date:** 2026-07-23
**By:** [L]

## Decision

| Term | Meaning | Where it lives |
|---|---|---|
| **Tenant** | Isolation boundary. One client organization's slice of BuzzCRM data. | BuzzCRM only |
| **Company** | A company in the sales pipeline. Sourced from a Salesforce Account. | BuzzCRM only |
| **Organization** | Existing Buzz concept. Reserved. | Buzz only — NOT used in BuzzCRM |

## Rationale

Three distinct concepts were converging on the word "Organization":

1. The tenancy boundary (a client org using BuzzCRM)
2. A company in the CRM pipeline (a Salesforce Account)
3. Whatever Buzz already means by Organization

One word for three things produces ambiguity in every model, query, and conversation — and worse, it surfaces at bridge time, when someone maps `buzz.organization → buzzcrm.organization` because the names happened to match.

Distinct words cost nothing now and prevent a rename after the schema, import mapper, and UI all reference the entity.

## Consequences

- The domain table is `companies`. The module is Companies, not Organizations. AGENTS.md service list updated accordingly.
- Salesforce Account is the **import source**, not the entity name — the field mapper translates Account → Company. The original identifier is retained as `sf_id` (ADR-006, unique per tenant).
- Any future Buzz bridge maps `buzz.organization` to whichever BuzzCRM concept is correct **explicitly**, with no name-matching shortcut available.
- "Organization" must not appear as an entity, table, or variable name in BuzzCRM code. @qa checks this in review.
