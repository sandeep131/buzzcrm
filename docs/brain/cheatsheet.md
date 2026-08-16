# BuzzCRM — Cheat Sheet

Quick reference. Full rules in `AGENTS.md`, live state in `ops/`.

---

## Agent → Module Map

| @mention | Does | Owns (write) | Reads first |
|---|---|---|---|
| `@lead` | Architecture, issue decomposition, merge | All `docs/`, decisions | AGENTS.md, PRODUCT_BRIEF.md |
| `@backend` | Schema, APIs, audit, events | `src/models/`, `src/api/`, `src/events/`, `migrations/` | API_CONVENTIONS.md |
| `@data` | Import, matching, dedup | `src/import/`, `src/matching/` | IMPORT_SPEC.md |
| `@frontend` | UI screens, components | `client/` | review-prompt.md |
| `@ai` | AI proposals, Buzz linkage | `src/ai/`, `src/buzz/` | review-prompt.md |
| `@qa` | Tests, security, PR review | `tests/` | review-prompt.md |
| `@ops` | Deploy, CI/CD, migrations run | infra | architecture.md |
| `@docs` | AGENTS.md, ADRs, HUB.md | `docs/`, `ops/` | all brain files |
| `@status` | Current state report | — (read-only) | ops/assignments.md, ops/HUB.md |

Everything not listed as "owns" is **read-only** for that agent.

---

## Current Assignment (see ops/assignments.md for truth)

- **[L]** — @lead (permanent), @data, @ai, @ops
- **[C]** — @backend, @frontend, @qa
- **Either** — @docs · **Both** — @status

---

## The 11 Rules (short form)

1. Check `ops/assignments.md` first — it's the lock file
2. One worker, one branch, one module
3. Tests are not optional
4. Migrations are reversible
5. AI proposes, humans approve
6. Audit everything
7. Modular monolith — extraction needs an ADR
8. Data migration is deterministic
9. [L] is merge authority
10. Update `ops/HUB.md` at session start + end
11. Writes confined to `buzzcrm/` — `git status` before any MCP commit

---

## Commit Format

```
[handle]/@agent: what changed
```
Example: `[C]/@backend: Add Organization schema and CRUD endpoints`

---

## Session Types

| Session | Where | For |
|---|---|---|
| A | Claude.ai (phone/desktop) | @lead planning, @status, reviews, decisions |
| B | Claude Code / terminal | Actual coding in branches |
| C | Cowork (scheduled) | Daily standup summary |

---

## Common Commands

```
@status                                    # who owns what, what's blocked
@lead decompose Milestone 0 into issues
@backend build Organization schema and CRUD
@qa review PR #3
@docs record decision: chose FastAPI over Flask
```

Chaining: `@data define import API shape → @frontend build the wizard against this`

---

## Key Paths

| Path | What |
|---|---|
| `AGENTS.md` | Project-wide rules |
| `ops/assignments.md` | Lock file — [L] only writes |
| `ops/HUB.md` | Sprint board — all write |
| `docs/brain/review-prompt.md` | PR review checklist |
| `docs/brain/cheatsheet.md` | This file |
| `docs/DECISIONS/` | ADRs |

---

## PR Verdicts

**MERGE** — all checks pass, CI green, [L] approves
**REVISE** — specific fixes listed
**REJECT** — boundary violation, architecture problem, or security issue
