# CITYGO-163 · Place/Data Quality Auto-Repair Loop

## Implemented

- Added deterministic service: `services/place_auto_repair_service.py`.
- Safe auto-repair rules:
  - category alias normalization;
  - route exclusion for non-tourist utility/service/transport/health categories;
  - address whitespace normalization;
  - safe main photo selection from public, non-rejected image candidates;
  - draft description generation for route-safe categories when title/category evidence exists.
- Unsafe cases are returned as review backlog items:
  - missing photo without safe candidate;
  - missing or weak address;
  - missing or invalid opening hours;
  - duplicate candidate;
  - low confidence;
  - weak description without enough evidence.
- Summary includes `repaired_count`, `needs_review_count`, `skipped_count`, `by_reason`, `by_category`, and item-level reasons.

## Tests

- `tests/test_place_auto_repair_service.py` covers each production-safe rule group.

## Remaining

- The service is ready for import/enrichment integration, but this pass did not attach it to a specific import job hook because that requires checking the current migration/import lifecycle in a longer pass.
