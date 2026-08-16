# BuzzCRM — Domain Model

Canonical entity definitions. Changes here require a PR; code must match this document (review-prompt.md checks it).

---

## Glossary (ADR-008)

- **Tenant** — isolation boundary. One client organization's slice of data.
- **Company** — a company in the sales pipeline. Sourced from a Salesforce Account.
- **Organization** — Buzz concept. Reserved. Does not appear in BuzzCRM.

---

## Entity Relationships

```
Tenant
├── User            (actor for all audit entries)
├── Company         (from Salesforce Account)
│   ├── Contact     (from Salesforce Contact — company_id nullable)
│   └── Opportunity (from Salesforce Opportunity)
├── PipelineStage   (ordered, tenant-configurable)
└── AuditEntry      (every create / update / delete)
```

- A Company has many Contacts and many Opportunities.
- An Opportunity belongs to exactly one Company and sits in exactly one PipelineStage.
- A Contact belongs to zero or one Company. Orphans are permitted (ADR-009).

---

## Base Fields — Every Domain Table

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `tenant_id` | UUID FK → tenants | NOT NULL, indexed (ADR-006) |
| `sf_id` | text, nullable | Salesforce source ID |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `created_by` | UUID FK → users | |
| `updated_by` | UUID FK → users | |
| `deleted_at` | timestamptz, nullable | Soft delete (ADR-009) |
| `deleted_by` | UUID FK → users, nullable | |

`sf_id` is NULL for records created natively in BuzzCRM. Non-NULL means imported, and it is what makes re-import idempotent.

**Uniqueness on `sf_id` is a PARTIAL index** — `(tenant_id, sf_id) WHERE deleted_at IS NULL AND sf_id IS NOT NULL`. A plain unique index breaks re-import of soft-deleted records. See ADR-009.

---

## Entities

### Tenant
Isolation boundary. `name`, `slug`, `is_active`. Not tenant-scoped itself (it *is* the scope).

### User
`tenant_id`, `email`, `display_name`, `is_active`. Audit actor for everything. Auth is stubbed for MVP (ADR-007).

### Company
`name`, `domain`, `industry`, `owner_id` (FK → users), plus base fields. The pipeline's central entity.

### Contact
`company_id` (**nullable** — ADR-009), `first_name`, `last_name`, `email`, `phone`, `title`, plus base fields.

### Opportunity
`company_id`, `name`, `stage_id`, `amount`, `close_date`, `owner_id`, plus base fields.

Per design principle 1 — one next action, one owner, one due date. Next-action fields land in Milestone 1.

### PipelineStage
`name`, `order`, `is_active`, plus base fields. A table, not an enum — stages are tenant-configurable and the real Skyscape stage list is still pending. Seeded with placeholders so work is not blocked.

### AuditEntry
`entity_type`, `entity_id`, `action` (create/update/delete), `actor_id` (FK → users), `changes` (JSONB), `occurred_at`, `tenant_id`. No PII in the diff beyond what the record already holds. Not soft-deletable — audit entries are immutable and permanent.

---

## Query Invariants

Two predicates are applied by the repository base layer on every read, never by individual endpoints:

1. `tenant_id = <current tenant>` (ADR-006)
2. `deleted_at IS NULL` (ADR-009)

Explicit opt-in is required to bypass either. Both have mandatory tests.

---

## Open Questions

- Company hierarchy (parent/child accounts) — Salesforce supports it. Deferred unless export samples show it in use.
- Currency and timezone handling. Deferred to Milestone 1.
- Physical purge / retention policy. Needs its own ADR (ADR-009).

---

## Not in MVP

Activities, tasks, notes, attachments, search indexing, roles and permissions, Buzz event consumers, orphan-contact resolution UI.
