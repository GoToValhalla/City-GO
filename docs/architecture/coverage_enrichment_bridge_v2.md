# Coverage / Enrichment Bridge v2

Date: 2026-06-29.

## Goal

Coverage / Enrichment Bridge v2 improves place collection for every city while keeping the current `CityImportScope` pipeline.

The bridge separates:

- tourist catalogue places;
- food places;
- service infrastructure;
- transport infrastructure;
- admin evidence records.

## Existing foundation

The implementation builds on existing project objects:

- `CityImportScope`;
- `PlaceScopeLink`;
- `SourceObservation`;
- Data Coverage Assurance;
- OSM import wrapper `import_city_osm_v2.py`.

## New place fields

Migration `c8d4e6f9a102_place_route_layers.py` adds:

- `place_layer`;
- `route_policy`;
- `tourist_eligible`;
- `transport_required`.

## New services

- `services/osm_import_taxonomy.py` classifies OSM tags into place layers.
- `services/import_profiles.py` adds stricter semantic profiles.
- `services/coverage_scope_policy.py` resolves scope intent from `coverage_targets`.
- `services/place_layer_service.py` applies layers after import using source observations.
- `services/curated_poi_import_service.py` imports curated must-have POI as reviewable records.
- `services/coverage_scope_suggestion_service.py` proposes missing scopes from unresolved coverage gaps.

## Route safety

Walking routes now use only tourist/food layers and only records with:

- `tourist_eligible = true`;
- `transport_required = false`;
- city-walking-compatible route policy.

This keeps infrastructure and remote day-trip records out of normal walking candidate retrieval.

## Generic city model

Every city should start with baseline scopes:

- city core;
- food area;
- nearby nature;
- service infrastructure;
- transport hubs.

Then Data Coverage Assurance suggests additional scopes:

- heritage day trip;
- nature area;
- corridor;
- satellite town;
- must-have anchor.

## Kutaisi example

Kutaisi needs separate scopes:

- city core for Bagrati and central walking routes;
- heritage day-trip scope for Gelati and Motsameta;
- nature scope for Sataplia;
- service/transport scopes as separate infrastructure layers.

## Import flow

```text
import_city_osm_v2.py
  -> legacy OSM import
  -> apply_place_layers()
  -> run_data_coverage_assurance()
```

## Rules

- Avoid one large radius for every city.
- Add targeted scopes for missing clusters.
- Keep curated POI reviewable before publication.
- Use AI only for normalization and enrichment from evidence.
- Keep future Destination/Region migration possible.
