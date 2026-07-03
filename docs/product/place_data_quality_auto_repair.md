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
- Auto-repair is now wired into active admin import/enrichment jobs in `services/admin_city_import_job_service.py`:
  - full city import;
  - enrichment-only job;
  - address enrichment job;
  - photo enrichment job.
- Job `step_details` and light snapshot include `auto_repair`, so admin/import summary can show what was fixed automatically and what still needs review.
- Import alert details include `auto_repair` alongside readiness and warnings.

## Tests

- `tests/test_place_auto_repair_service.py` covers each production-safe rule group.
- `tests/test_user_route_slot_session_and_import_repair.py` covers the admin import hook storing `auto_repair` summary in job details.

## Operational notes

- Auto-repair does not publish a city or bypass manual moderation.
- For city-wide enrichment jobs without explicit changed ids, the hook scans the newest city places up to `AUTO_REPAIR_CITY_SCAN_LIMIT` to avoid expensive full-table processing.
