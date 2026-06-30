# Admin import jobs flow

## Current production contract

Admin import pages use CQRS-lite:

- `GET /admin/import-jobs` is read-only and lightweight.
- `GET /admin/import-queue` is read-only and returns only active queued/running jobs.
- `GET /admin/import-jobs/{city_id}` is read-only and reads cached snapshot data when available.
- Heavy recalculation is triggered by explicit `POST` commands and processed by import-worker.
- GET endpoints must not mark jobs as stalled, recover failed jobs, or change city launch status.

## List endpoint

`GET /admin/import-jobs` returns only lightweight fields:

- city and latest job identity;
- status/current step;
- progress counters already stored on the job;
- coverage/change counters only if a cached snapshot exists;
- available UI actions.

The list endpoint must not calculate address/photo/description coverage by scanning all places for every city.

## Detail endpoint

`GET /admin/import-jobs/{city_id}` returns detail for one city. It reads `admin_import_snapshot` from `CityAdminImportJob.step_details`.

When snapshot is missing, the UI shows `snapshot не создан` and offers `Обновить snapshot`.

## Snapshot transition layer

Until dedicated snapshot tables are added, snapshot data is stored in:

```text
CityAdminImportJob.step_details.admin_import_snapshot
```

The snapshot contains:

- `data_coverage`: address/photo/description coverage;
- `change_summary`: created/updated/rejected/hidden/needs_review/unchanged;
- `taken_at`, `source`, `version`.

Snapshot refresh may update coverage counters, but change counters are copied only from cached `CityAdminImportJob.step_details.change_summary`. If that cache is missing, all change counters are returned as zero. Refreshing a snapshot must not scan `city_admin_import_job_changes`.

This is a transition layer. Target tables:

- `city_coverage_counters` for list counters;
- `city_import_snapshots` for full import detail snapshots;
- `import_job_steps` for per-step status and result.

## Commands

Current POST commands:

- `POST /admin/import-jobs/{city_id}/run`
- `POST /admin/import-jobs/{city_id}/retry`
- `POST /admin/import-jobs/{city_id}/cancel`
- `POST /admin/import-jobs/{city_id}/publish`
- `POST /admin/import-jobs/{city_id}/snapshot/refresh`
- `POST /admin/import-jobs/{city_id}/snapshot/refresh-now`
- `POST /admin/import-jobs/{city_id}/enrich-addresses`
- `POST /admin/import-jobs/{city_id}/enrich-photos`
- `POST /admin/import-queue/mark-stalled`

`refresh-now` is a temporary admin operation for one city. For batch operations prefer queued `snapshot/refresh`.

## Worker source routing

Import-worker must route queued jobs by `CityAdminImportJob.source`:

- `admin_city_import` -> full import pipeline;
- `admin_city_enrichment` -> enrichment-only pipeline;
- `admin_snapshot_refresh` -> refresh cached snapshot;
- `admin_address_enrichment` -> address enrichment then snapshot refresh;
- `admin_photo_enrichment` -> photo enrichment then snapshot refresh.

If a worker task raises an exception, the active job is marked `failed`, moves to `error`, stores `last_error` and `step_details.worker_exception`, and gets `finished_at`. The job must not stay indefinitely in `running`.

## Stuck queue recovery

`GET /admin/import-queue` is still read-only, but it reports hard-stuck running jobs:

- `stalled_running`;
- `longest_running_seconds`;
- `running_job_ids`;
- `stale_job_ids`.

A running job is considered hard-stuck when it has been running for more than one hour. The admin UI then shows `Пометить зависшие`, which calls `POST /admin/import-queue/mark-stalled`.

That POST action marks only hard-stuck running jobs:

- `status = stalled`;
- `current_step = error`;
- `finished_at = now`;
- `step_details.manual_stalled_recovery` with actor and runtime;
- non-published city gets `launch_status = import_failed`.

This keeps GET read-only and gives admins a manual escape hatch when import-worker leaves jobs in `running`.

## Admin UI

Desktop may render a table. Mobile must render cards:

- city name/status;
- places/published/job-type-aware status;
- address/photo/description coverage from snapshot;
- actions: details, changes, logs, refresh snapshot, enrich addresses, enrich photos.

The list page does not full-page poll or reload. It fetches queue state from `GET /admin/import-queue`; actions refresh the affected data silently after the POST completes. While a city has an active queued/running job, mutating actions for that city are disabled except supported cancellation.

Job-type display rules:

- full import shows percent/progress and found/saved counters;
- snapshot shows snapshot status/time, not `0/0` progress;
- address/photo enrichment shows its enrichment result block;
- snapshot timestamps are formatted for humans in the admin UI.

The detail page must not duplicate `Добрать адреса`, `Добрать фото`, or `Обновить snapshot` outside the coverage block.

## Known remaining work

`services/import_pipeline_foundation_steps.py` still needs a narrow safe patch:

- replace `backfill_addresses = lambda: None` with actual address backfill;
- make `fetch_photo_candidates` search/fill missing photos, not only convert existing `image_url` into candidates.

Photo enrichment must return a visible result when no candidates are found. The current UI surfaces the blocker when many places lack photos and pending candidates are zero.

A previous full-file replacement was blocked by the connector safety filter, so this must be applied as a small isolated patch.

## Next target architecture

After stabilizing this transition layer, add real tables and migration:

- `city_coverage_counters`;
- `city_import_snapshots`;
- `import_job_steps`;
- state transition log.

Then move all snapshot writes from JSON field to dedicated tables.
