# Place Cards & Data Refresh v1

Last updated: 2026-07-06

## Goal

Public place cards must show clean user-facing data while enrichment/import updates are mediated by a deterministic merge layer. Manual/admin decisions are protected from automated overwrites.

## Write Path

```text
EnrichmentTask payload
→ PlaceDataMergeService
→ safe full-batch apply OR ReviewItem
→ admin selective merge/reject
→ sanitized public place response
```

There are no mixed updates inside one `PlaceDataMergeService` call. If any field is protected, low-confidence, lower-priority, conflicting, or unsafe, the whole batch becomes a `ReviewItem`.

## Models

- `Place.version` supports optimistic locking.
- `Place.lineage` stores field-level source/confidence/priority metadata.
- `Place.internal_status='service_only'` hides service-only POI from public catalog and route candidates.
- `PlaceManualOverride` protects manually curated fields.
- `ReviewItem` stores batch diffs for selective admin merge.

## Merge Rules

Source priority:

- `MANUAL`: 100
- `EDITORIAL_CLEANSED`: 80
- `EXTERNAL_API_ENRICHED`: 50
- `OSM_INGESTION`: 20
- `UNKNOWN`: 0

Auto-apply requires confidence `>= 0.6`, an allowed field, sanitizer-safe value, no protected override, and no lower-priority/conflicting current value.

## Public API

`/places`, `/places/{id}` and `/places/by-slug/{slug}` use `PublicPlaceRead`.

The response keeps legacy aliases needed by the frontend (`title`, `short_description`, `lat`, `lng`) but excludes internal/source/audit/verification fields. `data_quality` exposes only user-safe degradation metadata.

## Admin UI

`/admin/reviews` shows pending merge reviews, maps backend reason codes to Russian copy, allows selecting fields, and handles version conflicts with a reload-oriented message.

## User Card UI

Place detail supports:

- skeleton while loading;
- degraded banner;
- fallback description/address/hours;
- category photo fallback;
- 45-second refresh only while a detail page is open.

## Verification

Relevant tests:

- `tests/test_place_card_data_refresh_new.py`
- `tests/test_admin_reviews_api_new.py`
- `frontend/src/pages/admin/AdminReviewsPage.test.tsx`
- `frontend/src/components/places/PlaceDetailSheet.test.tsx`
- `ui-tests/tests/place-card-refresh.spec.ts`
