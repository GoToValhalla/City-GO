# Debug Reports and Review Queue Job Links

## Purpose

This change fixes two production-support gaps:

- review queue items created by import/enrichment must link to the real `city_admin_import_jobs.id`;
- public users and admins need a safe way to send diagnostics without exposing secrets or precise location by default.

## Review Queue Job Link

`review_queue_items.job_id` remains a foreign key to `city_admin_import_jobs.id`.
Import scripts must pass `--city-admin-import-job-id` when review items are created from an admin import job.

`ImportBatch.id`, enrichment task ids and run ids must not be written into `review_queue_items.job_id`.
If an invalid job id is passed, `ReviewQueueJobLinkError` is raised before the database foreign key fails.

The raw import batch id is kept in the review payload as `import_batch_id` for traceability.

## Debug Reports

Public endpoint:

- `POST /debug-reports`

Admin endpoints:

- `GET /admin/debug-reports`
- `GET /admin/debug-reports/{id_or_public_id}`

Reports store sanitized frontend state, request/response summaries, route traces, warning codes and coarse location context.
Keys containing token, secret, password, cookie or authorization are redacted recursively.
Latitude/longitude values are rounded unless `allow_precise_coordinates=true` is explicitly sent.

Telegram notification is opt-in:

- `CITYGO_DEBUG_REPORTS_TELEGRAM_ENABLED=false` by default;
- existing admin alert delivery is reused;
- report creation must still succeed if Telegram delivery fails.

## Frontend Debug Mode

`?debug=1` stores `citygo.debug=true` in local storage.
`?debug=0` stores `citygo.debug=false`.

Normal mode shows only compact “Сообщить о проблеме” actions.
Debug mode additionally shows the debug badge, copy action and raw diagnostics/details.

Admin operators can review reports at `/admin/debug-reports`.
