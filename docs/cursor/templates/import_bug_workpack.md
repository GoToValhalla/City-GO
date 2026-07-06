# Workpack: Import / enrichment bug

## Goal
<Describe failure: step, city, job id, FK/error>

## Read first
- `docs/cursor/TASK_SCOPES.md` → Import row
- `services/review_queue_service.py`
- `data/scripts/import_city_osm.py`
- `services/import_pipeline/runner.py`

## Do not touch
- Discovery bulk-create defaults
- DB FK constraints (no weakening)
- Destination publication logic unrelated to import

## Likely files
- `services/admin_city_import_runner.py`
- `services/admin_city_import_job_payload.py`
- `data/scripts/run_due_import_jobs.py`

## Hard rules
- `review_queue_items.job_id` = `city_admin_import_jobs.id`
- `ImportBatch.id` → `import_batch_id` in payload only
- Import status ≠ publication status in admin UI

## Tests
```bash
.venv/bin/python -m pytest tests/test_import_review_queue_job_link_new.py tests/test_review_queue_service.py -q --no-cov
.venv/bin/python -m pytest tests/test_admin_import_status_display_new.py -q --no-cov
```

## Final response
Root cause · job id vs batch id · files · tests · risks · post-deploy checklist
