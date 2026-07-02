# ADR-005 — Route Architecture Decision

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-112

## Context

City GO currently has custom route generation logic. This is acceptable for early product validation, but physical walking/transport graph computation should not become a hand-rolled responsibility of the web application.

## Decision

City GO owns itinerary selection, scoring, constraints, diversity and route snapshots. A dedicated routing engine should own physical travel time/distance graph calculations when scale requires it.

The near-term route architecture remains modular-monolith based, but must separate:

- offline/precomputed graph or matrix data;
- online personalization/scoring;
- immutable route snapshots.

## Evaluation options

Routing engine options to evaluate in implementation planning:

- OSRM;
- Valhalla;
- GraphHopper.

No engine is hard-selected in this ADR. The decision is staged: keep current implementation as compatibility layer while preparing clear boundaries for engine integration.

## Offline responsibilities

- city walking graph or matrix preparation;
- published/eligible route projection;
- popular POI pair distances;
- cache warming;
- route quality baselines.

## Online responsibilities

- candidate selection from published projection;
- user constraint scoring;
- diversity rules;
- time budget fit;
- route ordering over matrix/engine output;
- route snapshot creation.

## RouteSnapshot

Generated routes are immutable snapshots. Store:

- route_id;
- city_id;
- user/session context reference;
- ordered place ids;
- place snapshot versions;
- travel times/distances;
- scoring explanation;
- warnings;
- created_at.

## Rules

- Routing reads published/eligible projection, not raw places.
- Hidden/rolled-back place invalidates affected route/search caches.
- Route generation must be reproducible from snapshot metadata.
- Route API must not perform heavy graph construction inline.

## Testing requirements

- hidden place not used in new route;
- rollback invalidates route projection/cache;
- route snapshot remains readable even if place changes later;
- route generation has query/runtime budget tests;
- matrix/engine adapter has contract tests.

## Consequences

Positive:

- route logic remains product-specific;
- graph computation can move to specialized engine later;
- route snapshots become reproducible.

Negative:

- more projection/cache logic;
- future engine integration work required.
