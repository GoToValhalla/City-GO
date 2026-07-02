# City GO — Public Read Projections v2

Date: 2026-07-02
Status: implementation contract
Roadmap: Phase 3 — Public Read Projections
Jira: CITYGO-142, CITYGO-143, CITYGO-144, CITYGO-145

## Goal

Move public catalog, search and routing read paths away from write-side place tables and onto read projections with snapshot versioning and freshness guards.

## Existing implementation reused

The Stage 5 projection models already existed and were reused instead of being recreated:

- `models.search_routing_stage5.SearchPlaceDocument`;
- `models.search_routing_stage5.RoutingPlaceNode`;
- `models.search_routing_stage5.RouteCandidateSet`;
- `models.search_routing_stage5.ProjectionRebuildJob`.

## New service contract

Implemented in `services/public_read_projection_service.py`.

### Read path decision

`choose_public_read_path()` validates public read usage for:

- public catalog;
- search;
- routing.

Rules:

- public read paths use projections when projections are present and fresh;
- empty projection blocks public read unless fallback is explicitly allowed;
- stale projection blocks public read;
- unsupported read paths and projection types are rejected.

### Freshness guard

`is_projection_stale()` and `assert_projection_fresh()` detect:

- missing source snapshot version;
- missing projection snapshot version;
- projection version older than source version;
- non-fresh freshness status.

### Projection builders

`build_search_document_from_snapshot()` maps a published snapshot into `SearchPlaceDocument` shape.

`build_routing_node_from_snapshot()` maps a published snapshot into `RoutingPlaceNode` shape.

`build_route_candidate_set()` builds `RouteCandidateSet` payload from route-visible nodes only.

`build_projection_rebuild_summary()` creates deterministic rebuild status and counters.

## Test coverage

Covered in `tests/test_public_read_projection_service.py`:

- Stage 5 metadata tables exist;
- test database creates Stage 5 tables;
- search/routing/candidate/job table contracts;
- public catalog/search/routing choose projection read path;
- empty projection is blocked;
- stale projection is blocked;
- explicit fallback decision is visible;
- freshness helper detects version and status drift;
- search document builder maps public/search flags;
- routing node builder maps public/route flags;
- candidate set keeps only route-visible nodes;
- rebuild summary exposes status and counters.

## Exit criteria

- public catalog has a projection read-path decision contract;
- search has a projection read-path decision contract;
- routing has a projection read-path decision contract;
- stale projections are visible and blocking;
- rebuild summary is deterministic;
- repo docs and tests exist;
- CI is green.
