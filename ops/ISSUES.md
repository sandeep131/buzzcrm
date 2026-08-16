# BuzzCRM — Milestone 0 Issue Backlog

Decomposed by @lead, 2026-07-23. Detail lives here; live status lives in `HUB.md`.

**Sequential order is load-bearing.** Each layer's foundation must exist before the next can carry an audit FK or a tenant scope. Do not start out of order to feel productive — reordering costs a rewrite.

All issues: [L]/@agent. One branch per issue. Update the lock table in `assignments.md` when claiming.

---

## Layer 0 — Foundation (@backend)

### #1 — Project skeleton
**Branch:** `m0/01-skeleton` · **Module:** repo root, `src/core/`

FastAPI app factory, config from environment (no hardcoded values, rule per review-prompt), Alembic initialised, `docker-compose.yml` for local Postgres, pytest harness with a test database fixture.

**Done when:** `pytest` runs green with zero tests, app boots, `alembic upgrade head` succeeds on an empty database, `/health` returns 200.

---

### #2 — Tenant and User models
**Branch:** `m0/02-tenant-user` · **Module:** `src/models/`, `migrations/` · **Depends:** #1

`tenants` (name, slug, is_active). `users` (tenant_id FK, email, display_name, is_active) + audit base fields. One reversible Alembic migration. Seed script: one tenant, one user.

**Done when:** migration applies and downgrades cleanly, seed produces a usable tenant + user, models match DOMAIN_MODEL.md.

---

### #3 — Request scope and repository base
**Branch:** `m0/03-scoping` · **Module:** `src/core/` · **Depends:** #2

`get_current_user()` FastAPI dependency returning user **and** tenant (stub: resolves the seeded user — ADR-007). Repository base class applying both query invariants automatically: `tenant_id = current` and `deleted_at IS NULL`. Explicit opt-in required to bypass either.

**Done when:** a query through the base class cannot return another tenant's rows or soft-deleted rows without an explicit override, proven by test.

**This is the highest-risk issue in Milestone 0.** Every later guarantee rests on it. Review it hardest.

---

### #4 — Audit infrastructure
**Branch:** `m0/04-audit` · **Module:** `src/models/`, `src/core/` · **Depends:** #3

`audit_entries` (entity_type, entity_id, action, actor_id FK → users, changes JSONB, occurred_at, tenant_id). Immutable — not soft-deletable. Write hook so create/update/delete produce an entry with the correct actor and tenant, without each endpoint remembering to call it.

**Done when:** any create/update/delete through the repository layer produces exactly one audit entry with the correct actor, tenant, and diff.

---

## Layer 1 — CRM Entities (@backend)

### #5 — Company model, migration, CRUD
**Branch:** `m0/05-company` · **Module:** `src/models/`, `src/api/`, `migrations/` · **Depends:** #4

Company per DOMAIN_MODEL.md + base fields. **Partial unique index** `(tenant_id, sf_id) WHERE deleted_at IS NULL AND sf_id IS NOT NULL` — ADR-009. Pydantic schemas with explicit field lists (no mass assignment). CRUD + paginated list endpoint.

**Done when:** CRUD works, soft delete hides the record, the same `sf_id` can be re-created after a soft delete without constraint violation.

---

### #6 — Contact, Opportunity, PipelineStage
**Branch:** `m0/06-entities` · **Module:** `src/models/`, `migrations/` · **Depends:** #5

Contact (`company_id` **nullable** — ADR-009), Opportunity, PipelineStage (name, order, is_active). Seed placeholder stages — real Skyscape list is still pending and must not block this.

**Done when:** migration applies and downgrades, an orphan Contact (no company) can be created, stages seed in order.

---

### #7 — Contact and Opportunity endpoints
**Branch:** `m0/07-entity-api` · **Module:** `src/api/` · **Depends:** #6

CRUD + list for both. Contacts filterable by company. Consistent error format per API_CONVENTIONS.md — **which #7 must write, as it does not exist yet.**

**Done when:** endpoints work, error format documented and consistent, OpenAPI schema is clean enough to generate frontend types from.

---

### #8 — Isolation test suite (@qa)
**Branch:** `m0/08-isolation-tests` · **Module:** `tests/` · **Depends:** #7

The non-negotiable suite from ADR-006 and ADR-009. Seed two tenants. For every list and detail endpoint: authenticate as tenant A, assert tenant B's records are invisible **and unfetchable by direct ID**. Plus: soft-deleted records absent from all reads; audit entry for a delete still resolves to the record.

**Done when:** every endpoint is covered. A missing tenant filter is a cross-customer data leak — this suite is what makes rule 12 real rather than aspirational.

---

## Layer 2 — Import (@data)

### #9 — CSV staging and field mapper
**Branch:** `m0/09-import-staging` · **Module:** `src/import/` · **Depends:** #8

Upload → staging table (tenant-scoped) → Salesforce Account → Company field mapping. Companies only. Abuse-case tests per review-prompt.md: malformed CSV, wrong encoding, missing headers, extra columns, empty file, 100K rows, SQL injection in values.

**Blocked on:** real Salesforce export samples. Build against a synthetic fixture; the mapper will need revision when real samples arrive.

**Done when:** a CSV lands in staging with no partial writes to live tables, and every abuse case fails safely with a clear error.

---

### #10 — Match, classify, commit
**Branch:** `m0/10-import-commit` · **Module:** `src/matching/`, `src/import/` · **Depends:** #9

Classify staged rows: exact / likely / possible / new / conflict. Commit to live tables. Idempotent — re-running the same file creates no duplicates (this is what `sf_id` is for). Batch audit entry. Staging cleaned after commit or rollback.

**Done when:** the same file imported twice produces identical row counts, and the batch report shows classification totals.

---

## Layer 3 — Frontend (@frontend)

### #11 — App shell and API client
**Branch:** `m0/11-shell` · **Module:** `client/` · **Depends:** #7

React + Vite, routing, TypeScript types **generated from the OpenAPI schema** (not hand-written), TanStack Query, auth stub wiring. Design tokens as CSS custom properties — no hardcoded colours, spacing, or type sizes anywhere (ADR-005).

**Done when:** the app boots, fetches an authenticated endpoint, and a token file change restyles the whole shell.

---

### #12 — Company list and detail
**Branch:** `m0/12-company-ui` · **Module:** `client/` · **Depends:** #11

List with pagination. Detail with **inline editing — no modals** (design principle 3). Progressive disclosure: useful fields first.

**Done when:** the Milestone 0 success loop closes — import a real Salesforce Accounts CSV, see companies in the UI, edit one inline, and find the audit row for that edit with the correct actor and tenant.

---

## Not in Milestone 0

Activities, tasks, notes, attachments, search, roles and permissions, Buzz events, orphan-contact resolution UI, deployment (ADR-004 pending — and gated on the auth stub, ADR-007).
