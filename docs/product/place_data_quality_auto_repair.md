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
- Import alert details include `auto_repair` alongside readiness and import warnings.

## Job status contract

Auto-repair is observability and safe post-processing. It must not turn a successful import/enrichment job into warning/failure status by itself.

- `auto_repair.needs_review_count > 0` creates visible review backlog details, but does not force `success_with_warnings`.
- `success_with_warnings` is reserved for real import/enrichment warnings, source warnings, or failed items from the primary job path.
- Photo enrichment with zero created photos can still finish as `success` while exposing the zero-created details and auto-repair summary in `step_details`.
- Full import status remains tied to import/source warning state; auto-repair review items are shown separately so publication state is not polluted by repair backlog.

## Tests

- `tests/test_place_auto_repair_service.py` covers each production-safe rule group.
- `tests/test_user_route_slot_session_and_import_repair.py` covers the admin import hook storing `auto_repair` summary in job details.
- `tests/test_admin_photo_enrichment_observability_new.py` protects the photo enrichment status/detail contract.
- `tests/test_unified_city_import_pipeline_new.py` protects full import status when auto-repair returns review items.

## Operational notes

- Auto-repair does not publish a city or bypass manual moderation.
- For city-wide enrichment jobs without explicit changed ids, the hook scans the newest city places up to `AUTO_REPAIR_CITY_SCAN_LIMIT` to avoid expensive full-table processing.
- Admin UI should show auto-repair as a separate block: `Исправлено автоматически`, `Требует проверки`, `Причины`, not as generic job failure.
