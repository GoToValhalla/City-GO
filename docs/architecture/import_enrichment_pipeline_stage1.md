# Import / Enrichment Pipeline Stage 1

Stage 1 replaces the manual CSV-first enrichment flow with an admin-triggered
pipeline foundation. CSV export/import remains available only as a legacy
fallback for cases that still need manual bulk editing.

## Admin Flow

1. Admin opens `Обогащение данных`.
2. Admin selects a city and starts the automated pipeline.
3. Backend creates or reuses the city enrichment job and records normalized
   `import_job_steps`.
4. The pipeline writes source snapshots, field confidence, photo candidates,
   publication decisions, and review queue items.
5. Admin reviews only problematic fields/items instead of the whole city.

## Tables

- `city_admin_import_jobs`: existing import/enrichment job shell.
- `import_job_steps`: normalized step history and counters.
- `source_observations`: staging snapshots for imported place payloads.
- `place_field_confidence`: field-level confidence snapshots.
- `place_photo_candidates`: candidate photos before exact/manual approval.
- `review_queue_items`: field/place issues that require admin review.

## Pipeline Steps

- `collect_places`
- `normalize_categories`
- `backfill_addresses`
- `generate_ai_descriptions`
- `fetch_photo_candidates`
- `calculate_field_confidence`
- `apply_publication_decisions`

`generate_ai_descriptions` and `fetch_photo_candidates` are non-critical in
Stage 1. If they fail, the job is marked `partial_success` and later steps can
still finish. Critical source/confidence/publication failures mark the job
`failed`.

## Field Confidence

Confidence is tracked per field: title, coordinates, address, category,
opening hours, photo, and description. Manual or human-verified confidence rows
are protected from automated overwrites. AI-generated descriptions are capped at
medium confidence and cannot change coordinates, address, hours, phone, website,
or publication status.

## Publication Rules

The pipeline uses the existing import quality gate and writes compatible place
visibility flags:

- `published` with route eligibility for high-confidence tourist places.
- `published` without route eligibility for catalog-visible limited places.
- `needs_review` for low-confidence or non-tourist categories.
- `archived` for invalid coordinates or hidden categories.

Health, service, and similar non-tourist places are never route eligible by
default.

## Photos And Open Now

Category fallback and generic photos become candidates only. They are not exact
primary photos and cannot be set as primary by automated flow.

`Открыто сейчас` ignores opening hours marked low confidence, stale, or
conflicting in `place_field_confidence`. Unknown confidence keeps legacy
behavior for existing places until they are evaluated by the pipeline.

## API

- `POST /admin/place-enrichment/pipeline/{city_slug}/run`
- `GET /admin/place-enrichment/jobs/{job_id}/steps`
- `GET /admin/place-enrichment/places/{place_id}/confidence`
- `GET /admin/place-enrichment/review-queue`
- `POST /admin/place-enrichment/review-queue/{item_id}/resolve`
- `POST /admin/place-enrichment/photo-candidates/{candidate_id}/approve`
- `POST /admin/place-enrichment/photo-candidates/{candidate_id}/reject`
- `POST /admin/place-enrichment/photo-candidates/{candidate_id}/set-primary`

## Stage 1 Boundaries

No external AI or photo provider secrets are required for tests. The worker
foundation is deterministic and keeps provider integration behind service/API
boundaries for the next stage.
