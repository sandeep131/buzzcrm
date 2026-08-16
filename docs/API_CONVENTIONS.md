# BuzzCRM — API Conventions

Binding on every endpoint. @qa checks against this; @lead checks before merge.
Issue #7 is the first consumer; issue #11 generates TypeScript types from the
resulting OpenAPI schema, so inconsistency here becomes inconsistency in the
frontend.

---

## Base

- Prefix: `/api/v1`
- JSON in, JSON out. UTF-8.
- Version bump only for breaking changes. Additive fields are not breaking.

---

## Resource Naming

Plural nouns, lowercase, hyphens between words. Nesting one level deep at most.

```
GET    /api/v1/companies
POST   /api/v1/companies
GET    /api/v1/companies/{id}
PATCH  /api/v1/companies/{id}
DELETE /api/v1/companies/{id}          # soft delete (ADR-009)

GET    /api/v1/companies/{id}/contacts # nested read is fine
POST   /api/v1/contacts                # writes go to the top-level resource
```

Never `Organization` in a path (ADR-008). Never verbs in paths — actions that
resist REST get their own sub-resource, decided case by case, not invented ad hoc.

---

## Identifiers

- All IDs are UUIDs, serialised as strings.
- `tenant_id` is NEVER accepted from the client. It comes from the authenticated
  session (ADR-006/007). Accepting it from a request body is a tenant-crossing
  vulnerability, not a convenience.
- `sf_id` is readable and settable by import only, never by general CRUD.

---

## Timestamps

ISO 8601, UTC, `Z` suffix: `2026-07-23T14:30:00Z`. Field names end in `_at`.
No local times anywhere in the API.

---

## Methods and Status Codes

| Method | Success | Notes |
|---|---|---|
| `GET` list | 200 | Always paginated. Never an unbounded array. |
| `GET` detail | 200 | 404 if absent, soft-deleted, or another tenant's |
| `POST` | 201 | Returns the created resource, `Location` header set |
| `PATCH` | 200 | Partial update. Returns the full updated resource. |
| `DELETE` | 204 | Soft delete. Idempotent — deleting twice is still 204. |

`PUT` is not used. Partial update is the norm for inline editing (design
principle 3), and `PUT` invites accidental field clobbering.

**404, not 403, for another tenant's record.** A 403 confirms the record exists,
which leaks across the tenant boundary. Cross-tenant records are indistinguishable
from nonexistent ones.

---

## Errors

One shape, every time:

```json
{
  "error": {
    "code": "validation_failed",
    "message": "Request could not be processed.",
    "details": [
      { "field": "email", "issue": "not a valid email address" }
    ]
  }
}
```

- `code` — stable, machine-readable, snake_case. Clients branch on this, never on `message`.
- `message` — human-readable, safe to display. No stack traces, no SQL, no internal identifiers.
- `details` — optional, array, field-level. Omitted when not applicable.

| Status | `code` | When |
|---|---|---|
| 400 | `bad_request` | Malformed request |
| 401 | `unauthenticated` | No or invalid credentials |
| 403 | `forbidden` | Authenticated but not permitted (NOT for cross-tenant) |
| 404 | `not_found` | Absent, soft-deleted, or another tenant's |
| 409 | `conflict` | Uniqueness violation, e.g. duplicate `sf_id` in tenant |
| 422 | `validation_failed` | Well-formed but invalid — Pydantic failures |
| 429 | `rate_limited` | Reserved, not implemented in MVP |
| 500 | `internal_error` | Never leak internals. Log with a correlation id. |

FastAPI's default `{"detail": ...}` shape must be overridden with exception
handlers so validation errors match the above.

---

## Pagination

Offset-based for MVP. Cursor pagination when a list outgrows it — that is a
breaking change and needs its own decision.

```
GET /api/v1/companies?limit=50&offset=100
```

- `limit` default 50, maximum 200. Over the maximum is clamped, not an error.
- Response envelope for every list:

```json
{
  "items": [],
  "total": 1284,
  "limit": 50,
  "offset": 100
}
```

`items` is always the key. Never a bare array — a bare array cannot grow
metadata without breaking clients.

---

## Filtering, Sorting, Search

- Filter by exact match on a field: `?owner_id=<uuid>&industry=logistics`
- Sort: `?sort=name` ascending, `?sort=-created_at` descending. Whitelist
  sortable fields; never interpolate the parameter into SQL.
- Free-text: `?q=acme`. Simple `ILIKE` for MVP. Real search is post-MVP.
- Unknown query parameters are ignored, not errors — forward compatibility.

Soft-deleted records are never returned. There is no `?include_deleted` in MVP;
if it is added later it requires an explicit permission.

---

## Request Bodies

- Explicit field lists in Pydantic schemas. No mass assignment
  (review-prompt.md). Separate `Create` and `Update` schemas per resource.
- Server-controlled fields (`id`, `tenant_id`, `created_at`, `created_by`,
  `updated_at`, `updated_by`, `deleted_at`) are rejected in request bodies,
  not silently ignored — silent ignoring hides client bugs.
- Unknown fields are rejected (`extra="forbid"`).

---

## Response Bodies

- Return the full resource after create and update. Saves the client a refetch
  and keeps inline editing responsive.
- `null` for absent values. Never omit a field to mean null — an optional key
  produces an optional type in the generated client, which infects every caller.
- Audit fields (`created_at`, `updated_at`, `created_by`, `updated_by`) are
  returned on every resource. `deleted_at` is not, since deleted records are
  never returned.

---

## OpenAPI

The schema is a tracked contract. Every endpoint carries `response_model`,
`status_code`, and a `summary`. Every operation gets a stable `operation_id` —
it becomes the generated client's method name, so renaming one is a frontend
breaking change.

Schema changes get a line in the PR description.

---

## Not in MVP

Rate limiting, ETags and conditional requests, bulk endpoints, webhooks,
field selection (`?fields=`), cursor pagination, `include_deleted`.
