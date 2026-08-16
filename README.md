# BuzzCRM

Internal operational CRM for Skyscape sales. FastAPI · PostgreSQL · SQLAlchemy · Alembic.

Start with `AGENTS.md`. Architecture decisions in `docs/DECISIONS/`. Current work in `ops/HUB.md`.

---

## Local Setup

```bash
cd buzzcrm

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

cp env.example .env          # edit if your ports differ
docker compose up -d db      # Postgres on host port 5433

alembic upgrade head         # no revisions yet — should be a clean no-op
pytest                       # should pass
uvicorn src.main:app --reload
```

Then: `curl localhost:8000/health` → `{"status":"ok","environment":"local"}`

---

## Issue #1 — Verification Checklist

This skeleton was written via MCP and has **not been executed**. Verify before
marking #1 done:

- [ ] `pip install -e ".[dev]"` resolves
- [ ] `pytest` passes (2 tests)
- [ ] `docker compose up -d db` — container healthy on 5433
- [ ] `alembic upgrade head` succeeds against the empty database
- [ ] `uvicorn src.main:app` boots, `/health` returns 200
- [ ] No hardcoded connection string anywhere (`alembic.ini` reads from env)

Fix whatever fails, then commit as `[L]/@backend: #1 project skeleton`.

---

## Layout

```
src/core/        config, database session, cross-cutting concerns
src/models/      SQLAlchemy models          (issue #2)
src/api/         FastAPI routers            (issue #5)
src/import/      CSV staging + mapping      (issue #9)
src/matching/    dedup and classification   (issue #10)
migrations/      Alembic revisions
tests/           pytest
client/          React SPA                  (issue #11)
```

---

## Open: Sync vs Async SQLAlchemy — needs ADR-010

Scaffolded **sync**. Rationale: the concurrency that actually matters
(import batches, event delivery) belongs in background workers, not the
request path; FastAPI runs sync routes in a threadpool; and sync keeps
Alembic, tests, and the repository base materially simpler.

ADR-002 cited async as a FastAPI benefit, so this is a deliberate
narrowing of that, not an oversight.

**Decide before issue #3.** The repository base is where sessions get used
everywhere — switching after that means rewriting every repository method.

---

## Conventions

- No hardcoded config. Everything through `src/core/config.py`.
- Every migration has a working downgrade (rule 4).
- Tenant and soft-delete filtering live in the repository base (issue #3),
  never in individual endpoints (ADR-006, ADR-009).
- No `Organization` — it is `Company` here, `Tenant` for the boundary (ADR-008).
