# BuzzCRM — Review Prompt

PR review checklist. @qa runs this on every PR. @lead checks before merge.

---

## Boundary Check (First — Reject Early)

- [ ] Author checked ops/assignments.md before working
- [ ] Changes stay within the assigned module boundary
- [ ] No cross-boundary edits without @lead pre-approval
- [ ] Commit messages include [L]/[C] handle + @agent

---

## Code Quality

- [ ] Follows API_CONVENTIONS.md (error format, naming, pagination)
- [ ] Follows AGENTS.md project-wide rules
- [ ] No hardcoded secrets, credentials, or connection strings
- [ ] No hardcoded config — use environment variables
- [ ] SQLAlchemy models include base audit fields (created_at, updated_at, created_by, updated_by)
- [ ] Alembic migration present for schema changes
- [ ] Alembic migration is reversible (has working downgrade)
- [ ] Pydantic schemas validate all input
- [ ] API endpoints return consistent error format
- [ ] No print statements — use logging

---

## Testing

- [ ] New code has tests (unit minimum, integration preferred)
- [ ] Tests pass locally
- [ ] Import/migration code has abuse-case tests:
  - Malformed CSV (wrong encoding, missing headers, extra columns)
  - Large files (100K+ rows)
  - Duplicate explosion (same record 1000x)
  - SQL injection in field values
  - Empty file
- [ ] Permission-sensitive endpoints have auth tests
- [ ] Edge cases covered (empty strings, nulls, max-length)

---

## Security

- [ ] No SQL injection vectors (parameterized queries or ORM only)
- [ ] Permission check on every API endpoint
- [ ] Audit trail entry on every create/update/delete
- [ ] No PII in logs
- [ ] Import staging data cleaned after commit/rollback
- [ ] File upload validates type and size
- [ ] No mass-assignment vulnerabilities (explicit field lists)

---

## Architecture

- [ ] No new dependencies without ADR discussion
- [ ] No microservice extraction without ADR
- [ ] Event outbox pattern for Buzz integration (not direct calls)
- [ ] Domain model changes match docs/DOMAIN_MODEL.md (or update it)
- [ ] API changes match docs/API_CONVENTIONS.md (or update it)
- [ ] No circular imports between modules

---

## Data Migration (Import-Specific)

- [ ] Migration is idempotent (re-runnable without duplicates)
- [ ] Rollback tested and working
- [ ] No data loss on schema change
- [ ] Staging tables cleaned after batch commit
- [ ] Batch audit trail entry created
- [ ] Duplicate classification correct (exact/likely/possible/new/conflict)

---

## Collaboration

- [ ] ops/HUB.md updated with completion status
- [ ] Handoff noted if another worker is unblocked by this PR
- [ ] No edits to ops/assignments.md (only [L]/@lead changes this)
- [ ] PR description states: issue #, what changed, what's unblocked

---

## Verdict

**MERGE** — all checks pass, CI green, @lead approves
**REVISE** — specific items to fix (list them)
**REJECT** — boundary violation, architectural problem, or security issue
