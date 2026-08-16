# BuzzCRM

Internal operational CRM for Skyscape sales. FastAPI · PostgreSQL · SQLAlchemy · Alembic.

Start with `AGENTS.md`. Architecture decisions in `docs/DECISIONS/`. Current work in `ops/HUB.md`.

---

## Local Setup

```bash
cd buzzcrm

python3.11 -m venv .venv && source .venv/bin/activate   # 3.11+ required
pip install -e ".[dev]"

cp env.example .env          # edit if your ports differ
docker compose up -d db      # Postgres on host port 5433
                             # (on the EC2 box Postgres is native — see below)

alembic upgrade head         # no revisions yet — should be a clean no-op
pytest                       # should pass
uvicorn src.main:app --reload
```

Then: `curl localhost:8000/health` → `{"status":"ok","environment":"local"}`

---

## Issue #1 — Verification Checklist ✅ VERIFIED 2026-08-16

Executed on the EC2 box (Session B). **No code changes were required** — the
scaffold ran green as written.

- [x] `pip install -e ".[dev]"` resolves
- [x] `pytest` passes (2 tests)
- [x] Postgres healthy on 5433 — *native, not Docker; see below*
- [x] `alembic upgrade head` succeeds against the empty database (clean no-op)
- [x] `uvicorn src.main:app` boots, `/health` returns 200
      → `{"status":"ok","environment":"local"}`
- [x] No hardcoded connection string in `src/` (`alembic.ini` reads from env)

### Local environment deviation — Postgres is native here

`docker-compose.yml` is **unused on the EC2 box.** Docker is not installed
there, and the box also runs Zeus, RHTP, and PeakSpan — adding the Docker
daemon would insert its own iptables chains next to live services. Postgres 16
was installed natively instead ([L] decision, 2026-08-16):

```bash
sudo dnf install -y python3.11 postgresql16-server postgresql16
sudo postgresql-setup --initdb
# /var/lib/pgsql/data/postgresql.conf: port = 5433, listen_addresses = 'localhost'
# /var/lib/pgsql/data/pg_hba.conf:     127.0.0.1/32 + ::1/128 → scram-sha-256
sudo systemctl enable --now postgresql
sudo -u postgres psql -p 5433 \
  -c "CREATE ROLE buzzcrm LOGIN PASSWORD 'buzzcrm';" \
  -c "CREATE DATABASE buzzcrm OWNER buzzcrm;" \
  -c "CREATE DATABASE buzzcrm_test OWNER buzzcrm;"
```

Same host, same port, same credentials as the compose file — so `DATABASE_URL`
in `env.example` is unchanged and portable. The compose file stays committed
for machines that do have Docker. `scram-sha-256` replaces the AL2023 default
`ident`, which cannot accept the app's password login.

**Python 3.11 is required** (`requires-python = ">=3.11"`). The box's default
`python3` is 3.9 and is deliberately left alone — build the venv explicitly:

```bash
python3.11 -m venv .venv
```

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
