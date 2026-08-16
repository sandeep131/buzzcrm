# ADR-005: Frontend — React SPA, Neutral Design Tokens

**Status:** Accepted (visual direction provisional)
**Date:** 2026-07-23
**By:** [L]

## Decision

React + Vite SPA, consuming the FastAPI OpenAPI schema via generated TypeScript types.

Visual treatment: clean, simple, elegant — explicitly NOT internal-utility-looking, and NOT yet aligned to the Skyscape brand CSS system. Look and feel gets settled jointly once MVP screens exist.

## Rationale

**SPA over server-rendered:** the design principles describe an application, not documents — inline editing without modals, progressive disclosure, timeline views, one-next-action surfaces. Astro or server-rendered templates fight all four.

**Design deferral:** committing to the brand system before any screen exists means either retrofitting the CRM's information density onto a marketing component library, or discarding that work. Building on neutral tokens first keeps the choice reversible.

## Implementation Constraint

All styling goes through CSS custom properties (design tokens) — colors, spacing, type scale, radii. No hardcoded hex values, no magic pixel numbers in components.

This is the whole point: when the look and feel is settled, adopting the Skyscape brand system is a token-file swap, not a component rewrite.

## Consequences

- Frontend needs an auth token/session mechanism at the boundary (blocked on the identity decision).
- Generated API types are a build step; schema changes surface as type errors, which is the intent.
- MVP screens are deliberately plain. Judge structure and interaction, not polish, at first review.

## Revisit

After the first MVP screens ship — Organization list + detail with inline edit. At that point [L] and [C] settle the visual direction and this ADR gets a follow-up.
