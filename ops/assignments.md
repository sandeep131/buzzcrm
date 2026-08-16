# BuzzCRM — Current Assignments

**Last updated:** 2026-08-16 by [L]
**Current milestone:** 0 — Foundation

---

## Team Status

**[C] is not yet onboarded.** [L] holds every agent. All work is sequential — one module at a time, one branch at a time.

When [C] joins, the intended split is @backend / @frontend / @qa to [C]. Until then this file reflects reality, not intent.

### Consequence: @qa is a self-review

With one human, the author of a PR is also its reviewer. The compensating control is to run `docs/brain/review-prompt.md` explicitly as a separate @qa pass — in a fresh session, against the diff, before merging. Do not skip it because the author and reviewer are the same person. That checklist is doing the work a second pair of eyes would.

---

## Agent Assignments

| Agent | Assigned To | Module Boundary | Status |
|---|---|---|---|
| @lead | [L] | All docs/, architecture, merge authority | Permanent |
| @backend | [L] | src/models/, src/api/, src/events/, migrations/ | Active |
| @data | [L] | src/import/, src/matching/ | Active |
| @frontend | [L] | client/ | Active |
| @ai | [L] | src/ai/, src/buzz/ | Not started (Milestone 3) |
| @qa | [L] | tests/, PR reviews | Active — self-review, see above |
| @ops | [L] | deploy, CI/CD, infra | As needed |
| @docs | [L] | docs/, ops/ | As needed |
| @status | [L] | Read-only | Always available |

---

## Module Lock Table

| Module | Locked By | Branch | Since | Issue |
|---|---|---|---|---|
| src/core/ | — | — | — | — |
| src/models/ | [L]/@backend | `m0/02-tenant-user` | 2026-08-16 | #2 |
| src/api/ | — | — | — | — |
| src/events/ | — | — | — | — |
| src/import/ | — | — | — | — |
| src/matching/ | — | — | — | — |
| src/ai/ | — | — | — | — |
| src/buzz/ | — | — | — | — |
| client/ | — | — | — | — |
| tests/ | [L]/@backend | `m0/02-tenant-user` | 2026-08-16 | #2 (own tests) |
| migrations/ | [L]/@backend | `m0/02-tenant-user` | 2026-08-16 | #2 |

*(All unlocked. Claim a module by creating your branch and filling in this row.)*

**Single-worker note:** with one human the lock table is less about collision and more about focus — it records what you are mid-way through, so an interrupted session can be resumed without re-deriving state.

---

## Reassignment Protocol

**To change an assignment:**
1. Module must be UNLOCKED (no active branch/PR)
2. [L] updates this file with new assignment
3. Both humans run @status in their next session
4. New assignee claims module by creating their branch + updating the lock table

**To hand off MID-WORK:**
1. Current owner commits and pushes branch (even if incomplete)
2. [L] updates this file with new owner
3. New owner pulls branch and continues
4. Note handoff in ops/HUB.md

**Quick scaling:**
- Onboard [C]: move @backend, @frontend, @qa to [C]; update this file; [C] reads AGENTS.md + cheatsheet.md + HUB.md before first task
- [C] unavailable: reclaim all to [L], update this file
- Add [C2]: split three ways, add row, update this file
