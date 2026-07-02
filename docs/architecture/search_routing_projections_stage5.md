# City GO — Search and Routing Projections Stage 5

Date: 2026-07-02
Status: implementation baseline
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

## Tests

Required:

- metadata contains Stage 5 tables;
- test DB creates Stage 5 tables;
- search projection contract exists;
- routing projection contract exists;
- rebuild job contract exists;
- helper detects stale projection.
