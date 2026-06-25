# Data Coverage Assurance

## Problem

Kutaisi showed a systemic coverage gap: a city can be imported, but important POI can still be absent from the catalog or invisible to routes. The importer must not rely only on source data, bbox and profile filters.

## Implemented contour

The contour consists of:

- `known_missing_poi` as the operational registry of expected POI;
- `data/config/known_missing_poi.json` as versioned seed data;
- `services/data_coverage_contract.py` as the shared status, reason, scope and acceptance contract;
- `services/data_coverage_assurance.py` as the assurance pass;
- `services/osm_import_taxonomy.py` as the shared global OSM tag mapper;
- `data/scripts/import_city_osm_v2.py` as the coverage-aware import wrapper;
- `/admin/coverage-gaps` as the admin API and dashboard entry point;
- `services/coverage_readiness_gate.py` as the city readiness blocker.

## Gap reasons

- `outside_bbox`: expected POI is outside every configured import scope.
- `unsupported_tag`: source object exists but taxonomy/profile does not support it.
- `source_absent`: no matching place or source observation was found.
- `hidden_by_policy`: matched object is hidden by lifecycle/status/policy.
- `missing_name`: source object cannot be safely published without a valid name.
- `missing_coordinates`: source object cannot be matched without coordinates.
- `duplicate_candidate`: matched object is a likely duplicate.
- `not_imported_scope`: point is inside the area, but the expected scope/profile is missing or the source object did not become a place.
- `not_visible_in_catalog`: place exists but is not visible in the catalog.
- `not_route_eligible`: place exists but route engine will not use it.

## Scope types

The target scope vocabulary is:

- `urban_core`;
- `food_core`;
- `heritage_ring`;
- `nature_daytrip`;
- `regional_attractions`;
- `useful_services`.

Legacy aliases are kept in `services/data_coverage_contract.py`, so old config codes like `tourist_core`, `food_area`, `heritage_ne_ring` and `sataplia_nature` still work.

## City acceptance rule

A city is not accepted for ready publication when:

1. critical must-have coverage is below threshold;
2. at least one critical POI has no explanation;
3. at least one critical POI has a blocking gap reason.

The readiness gate uses this acceptance verdict and caps a city that is not accepted.

## Import behavior

`data/scripts/import_city_osm_v2.py` installs the coverage-aware OSM profile filters and shared taxonomy. After apply-mode import it runs Data Coverage Assurance and returns:

- evaluated rows;
- changed rows;
- changed rows caused by assurance;
- summary;
- acceptance verdict;
- recommended actions.

## Kutaisi regression

Kutaisi is the first seed regression case. It covers:

- Bagrati Cathedral;
- Gelati Monastery;
- Motsameta Monastery;
- Sataplia Cave;
- local food POI;
- amusement/leisure POI.

## Next expansion

- Add auto-candidate collection from Wikidata and Wikivoyage.
- Add user reports for missing places.
- Add scheduled weekly execution.
- Add richer admin action flows for merge, manual place creation and scope expansion.
