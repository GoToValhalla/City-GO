# City Import Pipeline

## Lifecycle

1. Admin creates a city through `/admin/cities/import`.
2. Backend creates the city, default import scopes and a queued `CityAdminImportJob`.
3. `import-worker` runs `data/scripts/run_admin_import_queue.py`.
4. The worker imports OSM/source places first, then runs enrichment steps.
5. If at least one place exists after source import, the city moves to `review_required`.
6. Admin publishes the city. Publication sets `City.launch_status=published`, `City.is_active=true` and publishes safe places.
7. Admin unpublishes the city. The city becomes inactive and its places are hidden from public catalog and route retrieval.

## Default Scopes

New admin-created cities get only tourist scopes:

- `tourist_core`
- `food_area`

`useful_services` is intentionally not created by default because it can pull pharmacies, parking, ATMs, hospitals and other non-tourist POI. Existing cities/scopes are not modified.

## Blocking Steps

These steps can fail the city import when they cannot produce usable data:

- OSM/source collection
- normalization
- `Place` creation
- readiness calculation

If source import finishes with zero places, the job fails with `last_error` and the city becomes `import_failed`.

## Non-Blocking Steps

These steps improve quality but do not block the catalog when places already exist:

- address enrichment
- photo enrichment
- description enrichment
- tags enrichment

Failures are stored in `CityAdminImportJob.step_details.warnings`. The job finishes as `success_with_warnings`, and the city still moves to `review_required`.

## OSM Normalization

`SourceObservation` is saved for every normalized raw object, accepted or rejected.

`Place` is created when the object has coordinates and a public tourist category. Photo, address and description are not required for creation.

Nameless parks, beaches, viewpoints, walks, museums and cultural objects receive a safe title such as `Парк OSM 123`. Nameless cafes/restaurants are rejected with `missing_name`, but their `SourceObservation` remains for diagnostics.

Common rejection reasons:

- `missing_name`
- `bad_name`
- `missing_coordinates`
- `unsupported_category`
- `hidden_category`
- `source_closed`
- `source_temporarily_closed`
- `source_removed_from_source`

## Low-Yield Fallback

When an apply import saves fewer than the minimum useful place count, `run_due_import_jobs.py` expands the scope bbox once and repeats the same idempotent OSM import. The result includes:

- `fallback_applied`
- `fallback_level`
- `fallback_reason`
- `fallback_result`

Existing source matching by `source_url`, slug and source presence prevents duplicate places on the fallback pass.

## Job Heartbeat And Stalled Jobs

Every pipeline step updates:

- `current_step`
- `updated_at`
- `total_items`
- `processed_items`
- `successful_items`
- `failed_items`
- `step_details`

`import-worker` also emits JSON step logs with `city_slug`, `job_id`, `step`, `status` and available counters.

A running job is stalled when it has no heartbeat longer than `STALL_THRESHOLD_MINUTES`. `mark_stalled_import_jobs()` marks it as:

- `status=stalled`
- `current_step=error`
- `last_error=Import job stalled: no heartbeat before timeout`
- `City.launch_status=import_failed`
- `City.is_active=false`

The admin payload exposes `is_stalled`, `last_error`, `step_details`, `can_retry`, `can_publish` and `can_unpublish`.

## Operator Checks

Queue summary:

```bash
docker compose exec backend python - <<'PY'
from db.session import SessionLocal
from services.admin_city_import_tasks import import_queue_summary
with SessionLocal() as db:
    print(import_queue_summary(db))
PY
```

Run queued jobs manually:

```bash
docker compose exec backend python data/scripts/run_admin_import_queue.py --limit 1
```

Admin endpoints to inspect:

- `GET /admin/import-jobs/queue`
- `GET /admin/import-jobs`
- `POST /admin/import-jobs/{city_id}/run`
- `POST /admin/import-jobs/{city_id}/retry`
- `POST /admin/import-jobs/{city_id}/publish`
- `POST /admin/cities/{city_id}/unpublish`
