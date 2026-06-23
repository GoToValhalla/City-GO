# Place Information Sources

City GO needs full, reliable place profiles without inventing facts. The implemented model is source-first: collect observations, store source and freshness, calculate field confidence, then publish only fields that pass quality rules.

## Implemented enrichment flow

The legal enrichment implementation lives in `services/place_enrichment_sources.py` and is wired into the foundation import pipeline as the `enrich_external_sources` step.

Current providers:

1. Geoapify Places API, enabled by `GEOAPIFY_API_KEY`.
   - Used for address, website, phone and opening hours near the existing place coordinates.
   - Stored as `SourceObservation.source_type = "geoapify"`.
   - Safe fields are applied only when the public field is empty.

2. Wikidata / Wikimedia Commons.
   - Used for cultural objects, landmarks, official website links, short factual descriptions and Commons photo candidates.
   - Stored as `SourceObservation.source_type = "wikidata"`.
   - Best match is selected by title similarity; weak matches are ignored.

3. Official website metadata.
   - Uses `place.website`, `place.source_url`, or a website found by Geoapify/Wikidata in the same enrichment run.
   - Reads public HTML metadata, Open Graph, JSON-LD/schema.org, phone and opening-hours hints.
   - Stored as `SourceObservation.source_type = "official_site"`.
   - Photo URLs become `PlacePhotoCandidate` rows for admin review; they are not silently published as primary photos.

4. City GO category rules.
   - Adds safe generic detail sections for `atmosphere`, `inside` and `best_for` when they are missing.
   - This keeps Place Detail useful while real source-backed descriptions are still incomplete.

## Files involved

- `services/place_enrichment_sources.py` - provider orchestration, source observations, safe field application, conflict review items and photo candidates.
- `services/import_pipeline_foundation.py` - includes `enrich_external_sources` in the pipeline after address backfill.
- `services/import_pipeline_foundation_steps.py` - exposes the enrichment step and expands confidence fields.
- `models/place.py` - stores `website`, `phone`, `atmosphere`, `inside`, `best_for`.
- `schemas/place.py` - exposes the same fields to API consumers.
- `migrations/versions/fb7e3c2a91d4_add_place_enrichment_profile_fields.py` - database migration for the new place profile fields.
- `tests/test_place_enrichment_sources.py` - coverage for legal provider enrichment, source observations, confidence rows, photo candidates and conflict review queue.

## Field policy

The enrichment step may fill only missing public fields:

- `address`
- `website`
- `phone`
- `opening_hours`
- `short_description`
- `atmosphere`
- `inside`
- `best_for`

If a provider returns a different value for an already populated field, the public field is preserved and a `ReviewQueueItem` with `reason = "source_conflict"` is created.

Photo URLs are saved as candidates, not directly as `place.image_url`. Public photos still require the existing candidate approval flow.

## Missing data handling

After enrichment, missing critical fields are queued for review with `reason = "missing_after_enrichment"`:

- address
- website
- phone
- opening hours
- description
- photo

Public UI must never show `null`, raw backend keys or invented values. If a field is missing, the block is hidden or shown as `Уточнить` only where uncertainty is useful to the user.

## Yandex, 2GIS and Google policy

Yandex Maps, 2GIS and Google Places can be used as map UI providers or external outbound links where their terms allow it. They must not be scraped or used to copy/store proprietary place databases, photos, reviews or ratings unless City GO has an explicit license/API plan that allows persistence and display.

For the current implementation, enrichment uses Geoapify, Wikidata/Wikimedia and official pages. Yandex/2GIS are intentionally excluded from ingestion to avoid ToS and data-license risk.

## Recommended next data work

1. Configure `GEOAPIFY_API_KEY` in backend environment and run the pipeline for one city.
2. Review `source_observations`, `place_field_confidence`, `place_photo_candidates` and `review_queue_items` for sample places.
3. Add city/regional open-data and tourism-portal importers as additional licensed providers.
4. Add an admin screen for resolving enrichment conflicts and approving photo candidates at scale.
5. Add a scheduled re-verification job for opening hours, website and phone freshness.
