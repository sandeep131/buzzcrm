# ADR-001: Modular Monolith Architecture

**Status:** Accepted
**Decision:** Start as a modular monolith. Do not begin with microservices.
**Rationale:** Earn architectural complexity later. Faster to develop, easier to refactor, simpler to deploy for an internal tool.
**Consequences:** All modules share one process, one database. Module boundaries enforced by convention. Microservice extraction requires a new ADR.
