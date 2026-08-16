# ADR-003: Standalone Service, Bridge Later

**Status:** Accepted
**Date:** 2026-07-23
**By:** [L]

## Decision

BuzzCRM runs as a standalone service with its own database, migrations, and release cadence. It is NOT a module inside WebBuzz. A bridge to Buzz is expected later and must not be pre-built.

## Rationale

- Independent release cadence: CRM changes must not require a WebBuzz deploy.
- Own Postgres and Alembic history — no migration entanglement.
- Failure isolation: a CRM import job cannot degrade WebBuzz.
- Coupling now would have to be undone later; the reverse (adding a bridge) is additive and cheap.

## Consequences

- Identity must be solved at the boundary, not inherited. Buzz SSO arrives via an adapter (see pending ADR on identity).
- Integration with Buzz uses the outbox pattern (AGENTS.md architecture), never direct in-process calls.
- Separate deploy target required (see ADR-004, pending).
- Some duplication of shared concepts is acceptable; per design principle 9, Buzz and CRM stay distinct.

## Explicitly Deferred

Bridge design — event consumers, shared identity, cross-links to BuzzStream+ — is out of scope until Milestone 3. Do not build integration seams speculatively.
