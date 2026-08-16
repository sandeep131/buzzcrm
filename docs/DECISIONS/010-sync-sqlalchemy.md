# ADR-010: Synchronous SQLAlchemy

**Status:** Accepted
**Date:** 2026-08-16
**By:** [L]

## Decision

BuzzCRM uses **synchronous** SQLAlchemy — `Session`, not `AsyncSession`. The
issue #3 repository base is built on the sync session, and every query path
follows from it.

## Why This Needed Deciding Before #3

The repository base is where sessions get used everywhere. Switching session
style after it exists means rewriting every repository method, every dependency
that yields a session, and every test that opens one. Cheap now; a broad
mechanical rewrite later. That is why it gated #3 rather than #2 — models and
migrations are identical either way.

## Rationale

**The concurrency that actually matters is not in the request path.** The
genuinely concurrent work in this system is import batches (#9, #10) and event
delivery to BuzzStream+. Both belong in background workers, where the
concurrency model is the worker's concern, not the web framework's. Async in the
request path would buy little and complicate everything it touches.

**FastAPI runs sync routes in a threadpool.** A sync route does not block the
event loop. The framework benefit cited in ADR-002 does not require async
database access to be realised.

**Async's advantage appears under high concurrent I/O.** BuzzCRM is an internal
tool for one sales team. That load profile is nowhere near where async pays for
itself, and MVP is explicitly not public (ADR-007).

**Sync keeps Alembic, tests, and the repository base materially simpler.**
Alembic's migration path is sync regardless, so async would mean two session
styles in one codebase — one for migrations and one for everything else.

This is a deliberate narrowing of ADR-002, which cited async among FastAPI's
benefits. Recorded so it reads as a decision rather than an oversight.

## Evidence from Issues #2 and #3

The scaffold was written sync provisionally. Building on it tested that
assumption against real code rather than argument.

**From #2 (models, migration, seed):**

- The tenant/system-actor bootstrap is a single transaction whose correctness
  depends on commit timing (deferred constraints, ADR-011). Reasoning about
  *when COMMIT happens* was already the subtle part — a bug in the test harness
  turned on exactly that. Async would have added a second axis of timing
  subtlety to the same code.
- The test harness needs real commits and truncation between cases. Sync keeps
  that a plain fixture.
- Nothing in #2 wanted async. No await would have improved any of it.

**From #3 (request scope and repository base) — the decision this ADR gated:**

- The repository base was built sync end to end: `_scoped_select()`, all reads,
  all writes, and the `get_current_user()` dependency. This is the code whose
  session style the ADR exists to fix, and it is now written.
- FastAPI resolves the sync `get_current_user()` dependency through `Depends()`
  without ceremony — proven by test, not assumed.
- The three query invariants are expressed as plain `Select` construction. No
  part of that logic would be clearer, safer, or shorter async.

No counter-evidence appeared in either issue. This confirms the scaffold's
provisional choice rather than reversing it.

**Reversal cost, now concrete.** Every method on `TenantScopedRepository`, the
`get_session()` dependency, and the whole test harness (which relies on real
COMMITs to check deferred constraints) would need rewriting. That cost grows
with each repository added from #5 onward. It was cheapest to settle here, which
is exactly why #3 was gated on it.

## Consequences

- `get_session()` yields a `Session`; the #3 repository base is sync throughout.
- Route handlers are `def`, not `async def`, wherever they touch the database.
  A route mixing `async def` with a sync session blocks the event loop — the one
  real footgun this decision creates. @qa checks for it in review.
- Background workers (#9, #10, events) choose their own concurrency model. They
  are not bound by this decision.
- Reversal cost grows with every repository method written after #3. If async is
  ever wanted, the trigger would be a measured request-path bottleneck that
  threadpool sizing cannot fix — not a preference.

## Revisit If

- BuzzCRM becomes a multi-client offering with a materially different load
  profile (the ADR-006 scenario), **and** profiling shows the request path
  bottlenecked on database I/O concurrency rather than query cost.
- Not before. "Async is more modern" is not a trigger.
