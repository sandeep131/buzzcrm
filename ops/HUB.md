# BuzzCRM — Operations Hub

**Team:** [L] only — [C] not yet onboarded. All work sequential. See `assignments.md`.

---

## Current Milestone
**Milestone 0: Foundation**
Target: TBD · Backlog detail: `ops/ISSUES.md`

**Success criteria:** import a real Salesforce Accounts CSV → see companies in the UI → edit one inline → find the audit row for that edit, with the correct actor and tenant. That loop closing is Milestone 0 done.

---

## ✅ Verification Debt — CLEARED 2026-08-16

| Item | Written | Verified | Result |
|---|---|---|---|
| #1 project skeleton | 2026-07-23, via MCP | **YES** — 2026-08-16, Session B | Green, no code changes needed |

Full README checklist executed on the EC2 box: `pip install -e ".[dev]"` resolved,
`pytest` 2 passed, `alembic upgrade head` a clean no-op against an empty database,
`uvicorn` booted and `/health` returned 200 `{"status":"ok","environment":"local"}`,
and no connection string is hardcoded in `src/`.

The scaffold ran correctly as written — the MCP-authored code needed no repair.
**#2 is unblocked.**

**Environment note:** Docker is not installed on the EC2 box, and the box runs
Zeus / RHTP / PeakSpan, so the Docker daemon's iptables chains were judged not
worth adding next to live services. Postgres 16 runs natively on 5433 instead,
with identical credentials — `docker-compose.yml` is untouched and still valid
elsewhere. Setup steps and rationale are in `README.md`. Python 3.11 was
installed alongside the box's 3.9, which remains the untouched system default.

---

## Decisions Needed ([L] Only)

- [x] ~~FastAPI vs Flask~~ → ADR-002
- [x] ~~Standalone vs module inside WebBuzz~~ → ADR-003
- [x] ~~Frontend framework~~ → ADR-005
- [x] ~~Tenancy model~~ → ADR-006
- [x] ~~Identity for MVP~~ → ADR-007
- [x] ~~Entity naming~~ → ADR-008
- [x] ~~Soft delete + orphan contacts~~ → ADR-009
- [ ] **ADR-010 — sync vs async SQLAlchemy.** Scaffolded sync; rationale in `README.md`. **Must settle before #3** — the repository base bakes session style into every query path. Cheap now, a rewrite later.
- [ ] **Deployment target — ADR-004.** Gated on the auth stub (ADR-007). MVP must not be publicly reachable until the SSO adapter lands.
- [ ] Sales roles / permissions model — needs role list from Skyscape team
- [ ] Initial Salesforce export samples from sales team

---

## Active Issues

Detail and acceptance criteria in `ops/ISSUES.md`. **Sequential — dependencies are load-bearing.**

| # | Issue | Agent | Human | Branch | Status | Module |
|---|---|---|---|---|---|---|
| 1 | Project skeleton | @backend | [L] | `m0/01-skeleton` | ✅ **DONE — verified 2026-08-16** | root, src/core/ |
| 2 | Tenant + User models | @backend | [L] | `m0/02-tenant-user` | **READY — next up** | src/models/ |
| 3 | Request scope + repository base | @backend | [L] | `m0/03-scoping` | Blocked by #2 + **ADR-010** | src/core/ |
| 4 | Audit infrastructure | @backend | [L] | `m0/04-audit` | Blocked by #3 | src/models/, src/core/ |
| 5 | Company model + CRUD | @backend | [L] | `m0/05-company` | Blocked by #4 | src/models/, src/api/ |
| 6 | Contact, Opportunity, PipelineStage | @backend | [L] | `m0/06-entities` | Blocked by #5 | src/models/ |
| 7 | Contact + Opportunity endpoints | @backend | [L] | `m0/07-entity-api` | Blocked by #6 | src/api/ |
| 8 | Isolation test suite | @qa | [L] | `m0/08-isolation-tests` | Blocked by #7 | tests/ |
| 9 | CSV staging + field mapper | @data | [L] | `m0/09-import-staging` | Blocked by #8 | src/import/ |
| 10 | Match, classify, commit | @data | [L] | `m0/10-import-commit` | Blocked by #9 | src/matching/ |
| 11 | App shell + API client | @frontend | [L] | `m0/11-shell` | Blocked by #7 | client/ |
| 12 | Company list + detail | @frontend | [L] | `m0/12-company-ui` | Blocked by #11 | client/ |

**Next action:** start #2 — `git checkout -b m0/02-tenant-user`, claim `src/models/` + `migrations/` in the lock table.
**Decide before #3:** ADR-010 (sync vs async). It is now the only thing standing between #2 and #3.
**Highest-risk issue:** #3 — every tenancy and soft-delete guarantee rests on the repository base.

---

## Orthogonal Work — No Terminal Required

Doc work that does not depend on unverified code:

| Item | Unblocks | Status |
|---|---|---|
| `docs/API_CONVENTIONS.md` | #7 (must follow it), #11 (generated types) | Done |
| ADR-010 sync/async | #3 | Needs [L] decision |
| ADR-004 deployment | Deploy | Needs [L] decision |
| `docs/IMPORT_SPEC.md` structure | #9 | Awaiting real Salesforce samples |
| Repo split from Zeus | Branch workflow for #1–12 | Done — 2026-08-16 |

---

## Blocked / Waiting

| Issue | Blocked By | Owner |
|---|---|---|
| ~~#1 verification~~ | ~~No SSH access~~ — **cleared 2026-08-16** | [L]/@backend |
| ~~Repo split from Zeus~~ | **Done** — standalone repo at `sandeep131/buzzcrm`, fresh history, branches usable | [L]/@ops |
| #9 field mapping (real data) | Need Salesforce export samples — synthetic fixture meanwhile | [L]/@data |
| #6 stage seed (real stages) | Need Skyscape stage list — placeholders unblock the work | [L]/@lead |
| Permissions model | Need sales roles list | [L]/@lead |
| Deployment (ADR-004) | Auth stub — not public-safe (ADR-007) | [L]/@ops |
| Frontend visual direction | Needs MVP screens first (by design, ADR-005) | [L] |

---

## Handoffs: Agent → Agent

*(none yet)*

---

## Handoffs: Agent → Human

- [ ] [L]/@lead → Need Salesforce export samples (Accounts, Contacts, Opportunities CSVs)
- [ ] [L]/@lead → Need pipeline stage list + order from Skyscape sales team
- [ ] [L]/@lead → Need sales roles / permission requirements

---

## Completed

- Repo scaffold — AGENTS.md, ops/, docs/brain/, placeholder docs, ADR-001 (commit `3b6f1b4`)
- Architecture settled — ADR-002 through ADR-009; DOMAIN_MODEL.md written
- Milestone 0 decomposed — 12 issues in `ops/ISSUES.md`
- API conventions written — `docs/API_CONVENTIONS.md`
- **Repo split from Zeus — standalone `sandeep131/buzzcrm`, fresh history (2026-08-16)**
- **Issue #1 verified end-to-end on the EC2 box — green, no fixes needed (2026-08-16)**

---

## Decision Log

| # | Decision | Status | By | Date |
|---|---|---|---|---|
| ADR-001 | Modular monolith (no microservices) | Accepted | [L] | Pre-brief |
| ADR-002 | FastAPI over Flask | Accepted | [L] | 2026-07-23 |
| ADR-003 | Standalone service, bridge later | Accepted | [L] | 2026-07-23 |
| ADR-004 | Deployment target | Pending | [L] | |
| ADR-005 | React + Vite SPA, neutral design tokens | Accepted | [L] | 2026-07-23 |
| ADR-006 | Multi-tenant from day one | Accepted | [L] | 2026-07-23 |
| ADR-007 | Identity first — stub, SSO adapter later | Accepted | [L] | 2026-07-23 |
| ADR-008 | Entity naming — Tenant, Company | Accepted | [L] | 2026-07-23 |
| ADR-009 | Soft delete + orphan contacts permitted | Accepted | [L] | 2026-07-23 |
| ADR-010 | Sync vs async SQLAlchemy | **Pending — blocks #3** | [L] | |
