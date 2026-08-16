# Session B Runbook — Claude Code on EC2

How to go from "SSH into the box" to "Claude Code building verified issues in
branches." This is the coding session the blueprint names but never scripted.

Session A (the project chat) settles architecture and decomposes issues.
Session B (this runbook) writes and **verifies** code. Issue #1 was scaffolded
in Session A via MCP because SSH was down — which is why it is unverified.
Step 3 below is where that debt clears.

---

> **STATUS 2026-08-16 — the one-time setup below is DONE.** Repo split complete
> (`sandeep131/buzzcrm`, fresh history) and issue #1 verified green with no code
> fixes needed. Skip to "Then — Issues #2 Onward". Two carry-overs: removing
> `buzzcrm/` from the Zeus repo (step 3, optional) and the environment deviation
> — Postgres is **native on 5433, not Docker**, on this box. See `README.md`.

## One-Time Setup — Repo Split *(completed)*

BuzzCRM currently lives as `buzzcrm/` inside the Zeus repo. The 12 issues each
need their own branch, and Zeus deploys from `main`, so BuzzCRM needs to be its
own repo before branch work begins. Fresh init — a week-old scaffold has no
history worth preserving, and this leaves the old `.env.bak` / `.passkey`
near-misses out of BuzzCRM's past entirely (ADR advice, this session).

### 0. First, commit the loose files still in Zeus

The `buzzcrm/` folder and unrelated `public/` work are uncommitted in Zeus. Do
NOT sweep them together (rule 11). From the Zeus checkout:

```bash
cd /path/to/zeus
git status                        # confirm what's dirty
git add buzzcrm/
git commit -m "[L]/@lead: BuzzCRM scaffold + architecture + issue #1 (pre-split snapshot)"
git push
```

This is the backup that has been deferred all session. Do it first, so the split
copies from a clean, pushed source. Handle the `public/` RHTP/brand files in
their own session as planned.

### 1. Create the empty GitHub repo

github.com → New repository → name `buzzcrm` → do NOT initialize with README,
.gitignore, or license → Create.

### 2. Split the folder into it

```bash
# Fresh working copy of just the buzzcrm folder contents
mkdir -p ~/buzzcrm && cd ~/buzzcrm
cp -r /path/to/zeus/buzzcrm/. .
rm -rf .git                        # ensure no inherited Zeus history

git init
git branch -M main
git add .
git commit -m "[L]/@lead: Initial BuzzCRM — scaffold, architecture, issue #1"
git remote add origin https://github.com/sandeep131/buzzcrm.git
git push -u origin main
```

Refresh the GitHub repo page — files should be present. Repo split done.
From here, all BuzzCRM git is normal, path-scoped, and rule 11 no longer applies
(the boundary is now structural). Update AGENTS.md to retire rule 11 and the
repo-split TODO once this is confirmed.

### 3. Remove buzzcrm/ from Zeus (optional, once the new repo is confirmed good)

```bash
cd /path/to/zeus
git rm -r buzzcrm/
git commit -m "[L]/@lead: Move BuzzCRM to its own repo"
git push
```

Leave it until the new repo is verified working. No rush.

---

## Per-Session — Launching Claude Code

```bash
cd ~/buzzcrm
claude
```

Claude Code now runs in the actual repo, with a real shell. It can write a file,
run pytest, read the failure, fix it, and re-run — the verify loop closes inside
the session instead of being deferred.

### Guardrails (agent running next to live services)

The EC2 box also runs Zeus, the RHTP/brand site, and PeakSpan. An agent in a
shell can reach all of it. Keep it boxed:

- **Work only inside `~/buzzcrm`.** Claude Code should not `cd` out of the repo.
- **Never touch the other services' processes, ports, or files.**
- **Postgres for BuzzCRM is its own container** (docker-compose, host port 5433)
  — it must not point at any database another service uses.
- **One branch per issue**, per the issue backlog. Never commit straight to main.
- If Claude Code proposes a command that touches anything outside `~/buzzcrm`,
  stop and review it. Same instinct that produced rule 11.

---

## Verify Issue #1 (the outstanding debt) — ✅ CLEARED 2026-08-16

All green on first run; the MCP-authored scaffold needed no repair. Kept below as
the reproducible recipe. Note `python3.11` and native Postgres, which differ from
what was written here originally.

From `~/buzzcrm`:

```bash
python3.11 -m venv .venv && source .venv/bin/activate   # NOT python3 — box default is 3.9
pip install -e ".[dev]"

cp env.example .env               # edit if ports differ
# Postgres: native on this box, already running via systemd on 5433.
# (docker compose up -d db only on machines that have Docker.)
sudo systemctl status postgresql --no-pager | head -3

alembic upgrade head              # clean no-op — no revisions yet
pytest                            # expect: 2 passed
uvicorn src.main:app --reload &
curl -s localhost:8000/health     # {"status":"ok","environment":"local"}
```

All green → mark #1 verified in HUB.md, tick the README checklist, commit any
fixes as `[L]/@backend: #1 verified`. Then #1 is truly done and #2 unblocks.

Anything red → fix in place. This is the whole point of Session B: the failure is
visible and fixable in the loop, not shipped and hoped.

---

## Then — Issues #2 Onward

Per `ops/ISSUES.md`, in order. For each:

1. `git checkout -b m0/NN-slug`
2. Claim it in `ops/assignments.md` lock table; note it in `ops/HUB.md`
3. Build with Claude Code — write, test, fix, loop until acceptance criteria pass
4. Run the `@qa` pass: `docs/brain/review-prompt.md` against the diff, in a fresh
   pass (solo-review discipline — see assignments.md)
5. Merge to main, update HUB.md
6. Next issue

**#3 (repository base) is the highest-risk issue** — every tenancy and
soft-delete guarantee rests on it. Settle ADR-010 (sync vs async) before starting
it, and review it hardest.
