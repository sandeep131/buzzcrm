# BuzzCRM — Agent Entry Point

This file is a pointer, not a copy. The rules live in `AGENTS.md` and the live
state lives in `ops/HUB.md`; duplicating either here would guarantee drift.

## Read these first, in order

1. **`ops/HUB.md`** — current state. Opens with a "Session Start" header: what
   is done, what is next, what blocks. **Update it at session start (claim) and
   end (report)** — AGENTS.md rule 10.
2. **`AGENTS.md`** — the 13 project-wide rules, module ownership, and commit
   convention. Rules 12 (tenant scoping) and 13 (naming) are load-bearing.
3. **`ops/assignments.md`** — module lock table. Claim your module before
   working in it.
4. **`ops/ISSUES.md`** — acceptance criteria for the issue you are picking up.
5. **`docs/DECISIONS/`** — ADRs. Read ADR-006, 009, 010, and 011 before touching
   data access; they define the invariants everything else assumes.

## Non-obvious things that will cost you time

- **Postgres is native on port 5433 on this box, not Docker.**
  `docker-compose.yml` is committed but unused here — Docker is not installed.
  See the environment note in `README.md`.
- **Build the venv with `python3.11`**, not `python3`. The box default is 3.9
  and does not satisfy `requires-python`.
- **Migrations must downgrade, not just upgrade** (rule 4). `tenants` and
  `users` reference each other, so the downgrade must drop the foreign key
  constraints before the tables. Alembic's autogenerate gets this wrong — it
  emits the circular constraints inline and the migration fails. Hand-adjust it.
- **Tests commit for real and truncate between cases.** Do not "optimise" this
  into transaction rollback: the actor foreign keys are DEFERRABLE INITIALLY
  DEFERRED, so under rollback-based isolation `commit()` only releases a
  savepoint and those constraints are never checked. Violations would pass
  silently and the bootstrap tests would prove nothing while appearing green.
- **Query invariants live in `src/core/repository.py`, never in endpoints.**
  Three of them: tenant scope, soft delete, and system-actor exclusion from user
  listings. There is deliberately no way to query across tenants.

## Before opening a PR

Run `docs/brain/review-prompt.md` against your diff as an explicit @qa pass.
With one person on the project the author is also the reviewer, so that
checklist is doing the work a second pair of eyes would. Do not skip it.

## Verify rather than assume

Nothing in this repo should be marked done on the strength of having been
written — issue #1 was authored via MCP and sat unverified for three weeks.

```bash
python3.11 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/alembic upgrade head && .venv/bin/pytest
```
