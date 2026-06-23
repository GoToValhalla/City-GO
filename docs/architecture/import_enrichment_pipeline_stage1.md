# Import / Enrichment Pipeline Stage 1

Last updated: 2026-06-23

Stage 1 replaces the manual CSV-first enrichment flow with an admin-triggered pipeline foundation. CSV export/import remains available only as a legacy fallback for exceptional manual bulk editing.

The pipeline is already merged into `main` and is part of the deployed admin/data-quality surface.

## Goals

The pipeline exists to move city data from raw imported observations to publishable user-facing places without exposing imported trash to tourists.

It must:

- collect and normalize place candidates;
- preserve raw source observations for audit;
- calculate field-level confidence;
- create photo candidates without auto-promoting generic images;
- create review queue items for problematic fields;
- apply publication and route eligibility decisions;
- keep CSV as fallback, not as the main workflow.

It must not:

- overwrite manual/human-verified confidence with automated guesses;
- write AI placeholder descriptions as high-confidence content;
- publish service/bank/police/medical/transport categories as tourist route points;
- promote generic/category/Unsplash fallback photos as exact primary photos;
- treat low/stale/conflict opening hours as reliable open-now data.

## Admin Flow

1. Admin opens `Обогащение данных` in the admin UI.
2. Admin selects a city and starts the automated pipeline.
3. Backend creates or reuses the city enrichment job and records normalized `import_job_steps`.
4. Pipeline writes source snapshots, field confidence, photo candidates, publication decisions, and review queue items.
5. Admin reviews problematic fields/items instead of re-checking the whole city manually.
6. Approved data becomes available to public catalog, route building, route readiness, and Telegram bot flows through shared quality gates.

## Code Map

Routers:

```text
routers/admin_import_pipeline.py
```

Schemas:

```text
schemas/import_pipeline_foundation.py
```

Models:

```text
models/import_job_step.py
models/source_observation.py
models/place_field_confidence.py
models/place_photo_candidate.py
models/review_queue_item.py
```

Services:

```text
services/import_pipeline_foundation.py
services/import_pipeline_foundation_steps.py
services/import_pipeline_publication.py
services/place_field_confidence_service.py
services/place_photo_candidate_service.py
services/review_queue_service.py
services/quality_scoring.py
```

Frontend:

```text
frontend/src/pages/admin/AdminPlaceEnrichmentPage.tsx
frontend/src/pages/admin/AdminPipelineEnrichmentPanel.tsx
frontend/src/pages/admin/AdminLegacyEnrichmentPanel.tsx
frontend/src/pages/admin/adminPipelineLabels.ts
```

Migrations:

```text
migrations/versions/7b8c9d0e1f2a_add_import_pipeline_foundation.py
migrations/env.py
models/__init__.py
```

## Tables

- `city_admin_import_jobs`: existing city import/enrichment job shell.
- `import_job_steps`: normalized step history, status, counters, and errors.
- `source_observations`: source/staging snapshots for imported place payloads.
- `place_field_confidence`: field-level confidence snapshots.
- `place_photo_candidates`: candidate photos before exact/manual approval.
- `review_queue_items`: field/place issues requiring admin review.

## Pipeline Steps

Current normalized steps:

- `collect_places`
- `normalize_categories`
- `backfill_addresses`
- `generate_ai_descriptions`
- `fetch_photo_candidates`
- `calculate_field_confidence`
- `apply_publication_decisions`

`generate_ai_descriptions` and `fetch_photo_candidates` are non-critical in Stage 1. If they fail, the job can finish as `partial_success` and later steps can still run.

Critical source/confidence/publication failures mark the job as `failed`.

## Field Confidence

Confidence is tracked per field, not only per place.

Tracked fields include:

- title;
- coordinates;
- address;
- category;
- opening hours;
- photo;
- description.

Rules:

- manual/human-verified confidence rows are protected from automated overwrites;
- AI-generated descriptions are capped at medium confidence;
- AI-generated descriptions do not mutate coordinates, address, hours, phone, website, or publication status;
- missing/uncertain fields create field-level review items instead of vague place-level tasks.

## Publication Rules

The pipeline writes place visibility flags compatible with the public catalog, route builder, admin route readiness, route navigation, and Telegram bot.

Expected decisions:

| Decision | Meaning |
|---|---|
| `published` + route eligible | High-confidence tourist/recreational place. |
| `published` without route eligibility | Catalog-visible place that should not be used in routes. |
| `needs_review` | Low-confidence or conflicting data needs manual review. |
| `archived` | Invalid coordinates, hidden category, spam, or unusable object. |

Non-tourist categories are never route eligible by default:

```text
service, bank, atm, mvd, police, government, transport,
hospital, health, medical, pharmacy, military, cemetery,
industrial, waste_disposal, fuel, parking, car_service
```

## Photos

Photo safety rules:

- exact primary photo requires exact/manual approval;
- category fallback photos stay candidates;
- generic/placeholder/Unsplash-style images must not become exact primary photos automatically;
- broken photo send/render failures should fall back to text UI, not a gray placeholder.

## Open Now

`Открыто сейчас` must use only reliable opening hours.

Excluded from open-now:

- `confidence_level = low`;
- `freshness_status = stale`;
- conflict/conflicting hours;
- missing confidence for newly evaluated pipeline data.

Unknown legacy places keep compatibility only until evaluated by the pipeline. New pipeline output should prefer explicit confidence state over legacy assumptions.

## API

```http
POST /admin/place-enrichment/pipeline/{city_slug}/run
GET /admin/place-enrichment/jobs/{job_id}/steps
GET /admin/place-enrichment/places/{place_id}/confidence
GET /admin/place-enrichment/review-queue
POST /admin/place-enrichment/review-queue/{item_id}/resolve
POST /admin/place-enrichment/photo-candidates/{candidate_id}/approve
POST /admin/place-enrichment/photo-candidates/{candidate_id}/reject
POST /admin/place-enrichment/photo-candidates/{candidate_id}/set-primary
```

## Admin UI Rules

The admin UI must:

- use Russian user-facing labels;
- show loading, error, and empty states;
- make CSV clearly secondary/legacy;
- show field-level reasons where available;
- not expose raw debug labels as the primary admin explanation.

## Verification

Targeted backend checks:

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_alembic_single_head_new.py \
  tests/test_import_pipeline_foundation_new.py \
  tests/test_import_pipeline_foundation_safety_new.py \
  tests/test_import_pipeline_api_new.py \
  tests/test_import_pipeline_review_queue_new.py \
  tests/test_import_pipeline_photo_safety_new.py -q
```

Frontend checks for admin enrichment UI:

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
npm --prefix frontend run test -- adminEnrichment_new.test.tsx
```

Focused known regression:

```bash
.venv/bin/python -m pytest --no-cov tests/test_admin_places_searches_title_slug_and_address_new.py -q
```

General guards:

```bash
git diff --check
.venv/bin/python -m py_compile \
  routers/admin_import_pipeline.py \
  schemas/import_pipeline_foundation.py \
  services/import_pipeline_foundation.py
```

## Boundaries

Stage 1 is deterministic and testable without external provider secrets.

Not included in Stage 1:

- live external AI provider orchestration;
- live commercial photo provider integration;
- fully automated publication without review for ambiguous content;
- bulk city publication bypassing field-level confidence;
- replacing all legacy import/admin paths at once.

## Downstream Consumers

Pipeline decisions affect:

- public place catalog;
- route builder candidate retrieval;
- route readiness/admin diagnostics;
- route navigation quality gate;
- Telegram bot place lists, route mode, nearby, open-now, and search;
- admin analytics and review queue workload.