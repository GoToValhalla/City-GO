# City GO — Search and Routing Projections Stage 5

Date: 2026-07-22
Status: implemented
Jira: CITYGO-142

## Goal

Stage 5 separates public search/routing reads from write-side catalog/import/publication tables.

## Entities

### SearchPlaceDocument

Read projection for search and catalog discovery.

Required fields: place id, city id, snapshot version, locale, title, searchable text, category, tags, visibility flags, ranking score, freshness status.

### RoutingPlaceNode

Read projection for route builder.

Required fields: place id, city id, snapshot version, coordinates, category, route policy, visit duration, route eligibility, quality score, freshness status.

### RouteCandidateSet

Precomputed candidate set for a city/profile/policy.

Required fields: city id, profile, route policy, candidate count, payload, freshness status.

### ProjectionRebuildJob

Operational job for rebuilding projections.

Required fields: projection type, city id, status, source snapshot version, counters and error summary.

## Rules

- Search reads SearchPlaceDocument.
- Routing reads RoutingPlaceNode and RouteCandidateSet.
- Projections store source snapshot version.
- Stale projections are detectable.
- Projection rebuild does not mutate master facts or publication decisions.

## Live-path architecture

All toggles default OFF. OFF retains the Stage 3/4 paths without altered filters or schemas.

| Read path | Toggle | Enabled authority | Shared boundary |
|---|---|---|---|
| `/places/search/`, Telegram search | `search_projection_reads_enabled` | `SearchPlaceDocument` | `search_projection_read_service` |
| `/places/`, place detail, nearby, Telegram catalog | `catalog_projection_reads_enabled` | `SearchPlaceDocument.public_payload` | `catalog_projection_read_service` |
| canonical build/preview/TMA slot builder and legacy generate | `routing_projection_reads_enabled` | `RoutingPlaceNode` + `RouteCandidateSet` | `routing_projection_candidate_service` |
| session correction, alternatives, add/replace/reorder | `routing_projection_reads_enabled` | `RoutingPlaceNode` + `RouteCandidateSet` | `routing_projection_candidate_service` |

`open-now` is intentionally not projected in Stage 5. Its authoritative reader combines
`PlaceSchedule` with `PlaceFieldConfidence`; neither fact exists in the Stage 5 read models.
It therefore remains the unchanged Stage 4 path under both catalog toggle states. Adding it
requires a schedule projection contract, not an approximation from display hours.

## Rebuild transaction and concurrency model

- `PublishedPlaceSnapshot` is the only rebuild source and the latest version per place wins.
- PostgreSQL holds a transaction-scoped `SHARE ROW EXCLUSIVE` lock on the rebuild-job table.
  This serializes global and city replacements, including stale workers.
- Source validation completes before old rows are removed. Replacement rows and the successful
  `ProjectionRebuildJob` commit together; readers therefore never accept a partial generation.
- A failed preflight writes a failed job but retains the last successful projection rows.
- Retrying is idempotent; the requested scope is fully replaced in deterministic place-id order.
- Running duplicates are recorded as skipped and never replace rows.
- Rebuilds never update `Place`, publication decisions, or published snapshots.

## Readiness and activation

Readiness compares the current authoritative source with the latest rebuild and physical rows.
It rejects missing, empty-nonempty, running, failed, incomplete, stale, mixed-scope, and
version-incompatible generations. A successful zero-count job distinguishes a genuinely empty
source from a missing rebuild. Freshness expires after 24 hours.

Admin operations:

- `POST /admin/projections/rebuild` — city/global search, routing-node, or candidate-set rebuild;
- `GET /admin/projections/readiness` — source/projection versions, counts, reason, activation safety;
- `GET /admin/projections/jobs/{id}` — actor/source/audit context and execution evidence.

Enabling any Stage 5 toggle through the canonical feature-toggle service is rejected unless every
published source city is ready for every projection required by that toggle. There is no override.

## Failure and observability contract

Public failures use HTTP 503 with `code=public_read_projection_unavailable`, a stable reason code,
and the read path. Structured logs record legacy/projection usage, read latency, projection type,
scope, versions, unavailable reasons, and rebuild results using the existing application logger.

## Rollback

1. Disable only the affected projection toggle.
2. Verify the corresponding legacy endpoint recovers.
3. Retain projection rows and rebuild jobs as evidence.
4. Rebuild and re-check readiness before reactivation.
5. Never delete snapshots or mutate publication state during rollback.

## Tests

Required:

- metadata contains Stage 5 tables;
- test DB creates Stage 5 tables;
- search projection contract exists;
- routing projection contract exists;
- rebuild job contract exists;
- helper detects stale projection.
