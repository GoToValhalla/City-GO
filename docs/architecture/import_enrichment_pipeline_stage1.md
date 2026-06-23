# Unified Import / Enrichment Pipeline

Last updated: 2026-06-23

City GO uses one background pipeline for both collecting missing places and enriching the complete city catalog. The separate synchronous enrichment launch is removed from the main admin flow.

## Admin Flow

1. Open `Обогащение данных` or the selected city workspace.
2. Select a city.
3. Click `Собрать и обогатить`.
4. Backend creates a queued `admin_city_import` job.
5. `import-worker` executes the full pipeline outside the HTTP request.
6. After completion, review conflicts, missing fields and photo candidates.
7. Publish the city only after readiness and manual review.

API launch:

```http
POST /admin/place-enrichment/pipeline/{city_slug}/run
```

The response has `status = queued`. Collection is not executed inside the API request.

Compatibility endpoints `/admin/import-jobs/{city_id}/run` and `/admin/import-jobs/{city_id}/enrich` now enqueue the same complete job.

## Complete Pipeline

```text
Admin: Собрать и обогатить
→ queue admin_city_import
→ import-worker
→ collect enabled OSM import scopes
→ normalize and upsert places
→ deduplicate imported entities
→ backfill missing addresses
→ collect legacy photo candidates
→ normalize categories and tags
→ Geoapify enrichment when GEOAPIFY_API_KEY is configured
→ Wikidata / Wikimedia enrichment
→ official website metadata enrichment
→ field-level confidence
→ source conflict review queue
→ photo candidate review queue
→ publication and route eligibility decisions
→ quality cleanup
→ city readiness
→ ready for manual review
```

## Collection Versus Enrichment

Collection creates or updates place entities:

- OSM is queried through enabled `city_import_scopes`;
- existing source IDs and deduplication rules prevent duplicate places;
- repeated runs are incremental and can discover newly added OSM objects;
- scope configuration controls which geographic areas are searched.

Enrichment fills missing fields for all places collected for the city:

- address;
- website;
- phone;
- opening hours;
- short description;
- atmosphere;
- inside;
- best-for profile;
- photo candidates.

Existing non-empty public values are not silently overwritten. Conflicting candidates are added to `review_queue_items`.

## Sources

- OSM / Overpass: discovery of places inside configured scopes.
- Geoapify: address, website, phone and opening hours near known coordinates.
- Wikidata / Wikimedia Commons: factual descriptions, official websites and photo candidates.
- Official websites: public metadata, JSON-LD, contacts, opening hours and photo candidates.
- City GO category rules: safe generic detail sections when source-backed details are missing.

Yandex Maps, 2GIS and Google are not scraped into the City GO database without an appropriate API plan or licence.

## Job And Audit Data

- `city_admin_import_jobs`: queue and top-level job state.
- `import_job_steps`: normalized source-enrichment step history.
- `source_observations`: raw provider observations and source URLs.
- `import_batches`: counters for each foundation pass.
- `place_field_confidence`: confidence and freshness per field.
- `place_photo_candidates`: photos awaiting approval.
- `review_queue_items`: missing fields and source conflicts.

The final job details include `unified_pipeline` with collection results, source-enrichment counters and the recalculated readiness score.

## Statuses

- `queued`: waiting for import-worker.
- `running`: collection or enrichment is running.
- `success`: full pipeline completed.
- `partial_success`: places were preserved, but one or more enrichment providers or later steps failed.
- `failed`: no usable city result was produced.
- `review_required`: city data exists and requires admin review before publication.

## Safety Rules

- Manual and human-verified confidence is protected.
- Missing ratings are not replaced with zero.
- Generic/category photos cannot silently become exact primary photos.
- Service, bank, police, medical, transport and similar categories are not route eligible.
- Low, stale or conflicting opening hours are excluded from `Открыто сейчас`.
- External-provider failure must not delete already collected places.

## Runtime Requirements

Backend environment:

```env
GEOAPIFY_API_KEY=
PLACE_ADDRESS_GEOCODER_USER_AGENT=CityGoAddressBackfill/1.0
```

`GEOAPIFY_API_KEY` is optional. Without it, the pipeline still runs OSM collection, Wikidata/Wikimedia, official-site enrichment and internal quality rules.

Required runtime service:

```text
import-worker
```

In Docker Compose it polls queued jobs and processes one city at a time.

## Verification

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_import_pipeline_foundation_new.py \
  tests/test_import_pipeline_foundation_safety_new.py \
  tests/test_import_pipeline_api_new.py \
  tests/test_place_enrichment_sources.py -q

npm --prefix frontend run lint
npm --prefix frontend run test:ci
npm --prefix frontend run build
```

## Current Limitation

New place discovery currently depends on OSM and the configured city scopes. Geoapify and Wikidata enrich/match collected places; they do not yet perform a separate city-wide discovery pass. Regional open-data and tourism-portal collectors can be added as licensed discovery providers without changing the rest of the pipeline.
