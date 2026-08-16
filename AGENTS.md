# BuzzCRM — Agent & Contributor Rules

## What This Is

BuzzCRM is an internal operational CRM for Skyscape sales. It replaces the daily Salesforce layer — not Salesforce itself. It answers three questions: Who needs attention? What happened? What should happen next?

## Project-Wide Rules

1. **Check `ops/assignments.md` before starting any work.** It's the lock file.
2. **One worker, one branch, one module.** No concurrent edits to the same subsystem. Human or AI — same rule.
3. **Tests are not optional.** Every PR adds or updates tests for the code it touches.
4. **Migrations are reversible.** Every Alembic migration has a working downgrade.
5. **AI proposes, humans approve.** No autonomous changes to CRM records in production.
6. **Audit everything.** Every create, update, delete gets an audit trail entry with timestamp and actor.
7. **Modular monolith.** No microservice extraction without an Architecture Decision Record.
8. **Data migration is deterministic.** Agents create and review code; production data movement follows explicit, testable steps. No free-form agent handoffs for import processing.
9. **[L] is merge authority.** PRs merge only after [L] approves.
10. **Update `ops/HUB.md` at session start (claim) and end (report).**
11. ~~**Zeus repo boundary.**~~ **RETIRED 2026-08-16** — BuzzCRM is now its own repo (`sandeep131/buzzcrm`), so the boundary is structural rather than behavioural. Rule number kept to avoid renumbering 12 and 13, which are referenced elsewhere. The instinct behind it still stands: this repo shares a box with Zeus, RHTP, and PeakSpan — never touch their processes, ports, or files, and keep BuzzCRM's Postgres its own (host port 5433).
12. **Tenant scoping is not optional.** Every domain table has `tenant_id`. Filtering happens at the data-access layer, never per-endpoint. Every list/detail endpoint has a cross-tenant isolation test. (ADR-006)
13. **Naming is fixed.** Tenant = isolation boundary. Company = a company in the pipeline. "Organization" is a Buzz term and must not appear in BuzzCRM code. (ADR-008)

## TODO (Infra)

- [x] ~~Add a path-scoped commit command to Zeus `mcp-server.js`~~ — moot; the repo split makes rule 11 structural
- [x] ~~Split BuzzCRM into its own repo~~ — done 2026-08-16, `sandeep131/buzzcrm` with fresh history
- [ ] Remove `buzzcrm/` from the Zeus repo — optional cleanup, step 3 of `docs/brain/session-b-runbook.md`. Safe to do now that the standalone repo is verified working.
- [ ] CI — branch/PR checks (`pytest`) now that branch workflow is actually usable

## Architecture

- **Framework:** Python FastAPI (ADR-002)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Validation:** Pydantic schemas
- **Tenancy:** Multi-tenant from migration one — `tenant_id` everywhere (ADR-006)
- **Auth:** Stubbed for MVP; Buzz SSO via adapter, single swap point (ADR-007)
- **Background jobs:** Queue (implementation TBD)
- **Events:** Outbox pattern for reliable BuzzStream+ delivery
- **API style:** REST, OpenAPI schema drives generated frontend types
- **Frontend:** React + Vite SPA, design tokens only (ADR-005)
- **Deployment:** Standalone service, own database (ADR-003). Target pending — ADR-004
- **Architecture:** Modular monolith

## File Ownership

| Directory | Owner Agent | Others May |
|---|---|---|
| src/models/, src/api/, src/events/ | @backend | Read only |
| src/import/, src/matching/ | @data | Read only |
| client/ | @frontend | Read only |
| src/ai/, src/buzz/ | @ai | Read only |
| tests/ | @qa (primary), all agents contribute | All write own tests |
| migrations/ | @backend creates | @lead approves |
| docs/ | @lead, @docs | All may propose via PR |
| ops/assignments.md | @lead ([L]) only | Read by all |
| ops/HUB.md | All | Update at session start/end |

Agent-to-human assignment is in `ops/assignments.md`. Check it — assignments are dynamic.

## Commit Convention

Include the human handle and agent in commit messages:
```
[L]/@lead: Scaffold repo and add AGENTS.md
[C]/@backend: Add Company schema and CRUD endpoints
[L]/@data: Implement Salesforce CSV field mapper
[L]/@lead: ADR-002: Choose FastAPI over Flask
```

## Merge Rules

- @qa reviews every PR
- @lead ([L]) merges every PR (final authority)
- CI must pass before merge
- No force-pushes to main

## Services / Modules

```
BuzzCRM
├── Tenancy and identity
├── Companies
├── Contacts
├── Opportunities
├── Activities and tasks
├── Import and migration
├── Search
├── AI orchestration
├── Buzz integration
├── Event publishing
└── Audit and reconciliation
```

## Design Principles

1. One next action per opportunity, one owner, one due date
2. Progressive disclosure — useful fields first
3. Inline editing — no modals for routine edits
4. Timeline over scattered notes
5. Import imperfect data — clean in staging
6. AI proposes; people approve
7. Views before customization
8. Modular monolith first
9. Buzz and CRM stay distinct — connect tightly, don't duplicate
10. Every feature must justify daily use
