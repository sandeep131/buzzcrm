# BuzzCRM — Operations Hub

**Team:** [L] only — [C] not yet onboarded. All work sequential. See `assignments.md`.

---

## Current Milestone
**Milestone 0: Foundation**
Target: TBD · Backlog detail: `ops/ISSUES.md`

**Success criteria:** import a real Salesforce Accounts CSV → see companies in the UI → edit one inline → find the audit row for that edit, with the correct actor and tenant. That loop closing is Milestone 0 done.

---

## ⚠ Open Verification Debt

| Item | Written | Verified | Blocker |
|---|---|---|---|
| #1 project skeleton | 2026-07-23, via MCP | **NO** | Needs terminal — checklist in `README.md` |

Written from the project chat, never executed. `pytest`, `alembic upgrade head`,
and `uvicorn` boot are all unconfirmed. Do NOT mark #1 done or start #2 against
it until the README checklist passes.

Nothing downstream of #1 should be *written* while this is outstanding either —
building on an unverified foundation compounds the debt.

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
| 1 | Project skeleton | @backend | [L] | `m0/01-skeleton` | **Written, UNVERIFIED** | root, src/core/ |
| 2 | Tenant + User models | @backend | [L] | `m0/02-tenant-user` | Blocked by #1 verification | src/models/ |
| 3 | Request scope + repository base | @backend | [L] | `m0/03-scoping` | Blocked by #2 + ADR-010 | src/core/ |
| 4 | Audit infrastructure | @backend | [L] | `m0/04-audit` | Blocked by #3 | src/models/, src/core/ |
| 5 | Company model + CRUD | @backend | [L] | `m0/05-company` | Blocked by #4 | src/models/, src/api/ |
| 6 | Contact, Opportunity, PipelineStage | @backend | [L] | `m0/06-entities` | Blocked by #5 | src/models/ |
| 7 | Contact + Opportunity endpoints | @backend | [L] | `m0/07-entity-api` | Blocked by #6 | src/api/ |
| 8 | Isolation test suite | @qa | [L] | `m0/08-isolation-tests` | Blocked by #7 | tests/ |
| 9 | CSV staging + field mapper | @data | [L] | `m0/09-import-staging` | Blocked by #8 | src/import/ |
| 10 | Match, classify, commit | @data | [L] | `m0/10-import-commit` | Blocked by #9 | src/matching/ |
| 11 | App shell + API client | @frontend | [L] | `m0/11-shell` | Blocked by #7 | client/ |
| 12 | Company list + detail | @frontend | [L] | `m0/12-company-ui` | Blocked by #11 | client/ |

**Next action at a terminal:** verify #1 against the README checklist.
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
| Repo split from Zeus | Branch workflow for #1–12 | Needs terminal |

---

## Blocked / Waiting

| Issue | Blocked By | Owner |
|---|---|---|
| #1 verification | No SSH access — deferred | [L]/@backend |
| Repo split from Zeus | No SSH access — branches unusable until done | [L]/@ops |
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
