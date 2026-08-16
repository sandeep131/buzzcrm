# ADR-002: FastAPI for the Backend

**Status:** Accepted
**Date:** 2026-07-23
**By:** [L]

## Decision

Use Python FastAPI for the BuzzCRM backend.

## Context

The existing Buzz platform is mixed — Python Flask for some modules, Node for others. There is therefore no single stack to "match," so alignment carries no meaningful weight as a criterion.

## Rationale

- Pydantic is already the chosen validation layer; FastAPI is built on it, so schemas serve double duty as validation and API contract.
- Automatic OpenAPI schema generation gives the frontend generated TypeScript types — `@backend` and `@frontend` cannot drift silently.
- Async support matters for import jobs and future Buzz event delivery.
- Dependency-injection model makes the identity stub → SSO swap a single-function change.

## Consequences

- Team must be comfortable with async Python and type hints.
- OpenAPI schema becomes a tracked contract; breaking changes to it require a note in the PR.
- Flask-specific Buzz utilities cannot be imported directly; any shared logic crosses the service boundary via API or the outbox.
