# ADR-002 — Bounded Contexts and Module Boundaries

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-109

## Context

City GO currently grows as one application where import, AI, publication, admin, routes, Telegram and catalog logic can reference the same models and services. This increases accidental coupling and makes regressions likely.

## Decision

City GO remains a modular monolith for now, but with explicit bounded contexts and dependency rules.

## Bounded contexts

1. Catalog — stable city/place identity, canonical geometry and approved catalog facts.
2. Ingestion — raw provider data, import lifecycle, idempotency, DLQ and source attribution.
3. AI Enrichment — prompt versions, AI task runs, candidates, confidence and cost.
4. Moderation and Publication — review decisions, publication events, quality gates, rollback and public state transitions.
5. Search and Discovery — rebuildable search projections, autocomplete, filters and ranking metadata.
6. Routing — route generation, route snapshots, route cache and routing engine integration.
7. Recommendation and Personalization — user signals, feature store, embeddings and ranking features.
8. Media — photo candidates, moderation, rights, derivatives and CDN metadata.
9. Identity and Access — users, admins, roles and permissions.
10. Client/BFF — Telegram Mini App and future client-specific payloads.

## Dependency rules

- Public APIs read projections, not raw observations.
- Import creates observations and candidates, not published state.
- AI creates candidates, not approved facts.
- Publication approves facts and emits publication events.
- Search/routing/recommendation consume projections and events.
- Admin actions must go through the owning context service.

## Forbidden dependencies

- User-facing API directly invoking LLM providers.
- Import/enrichment directly changing `City.is_active`, `City.launch_status` or published place flags.
- Telegram handlers directly mutating catalog/publication tables.
- Search/routing reading raw provider payloads.
- AI service writing approved/public catalog facts.
- Feature code using legacy models as source of truth.

## Source-of-truth chain rule

Every feature must state:

```text
client/API -> bounded context -> source-of-truth table/projection -> event/audit -> tests
```

If this chain is unclear, the feature must not be implemented.

## Consequences

Positive:

- reduced accidental coupling;
- easier service extraction later;
- clearer test ownership;
- fewer cross-context regressions.

Negative:

- more boilerplate;
- some existing shortcuts become forbidden;
- refactoring will require compatibility adapters.

## Extraction rule

Do not split microservices early. Extract only when a context has independent scale/failure/resource profile.

First extraction candidates:

1. AI Enrichment.
2. Media.
3. Search.
4. Routing.

Do not extract Catalog/Publication/Admin early.
