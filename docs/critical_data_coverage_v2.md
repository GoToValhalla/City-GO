# Critical Data Coverage / Quality Rules v2

## Purpose

City GO must maximize coverage of critical place data without turning every missing field into manual work.

The contract separates two different questions:

1. Route readiness: can the route engine safely use this place?
2. Card completeness: can the app show this place with enough user-facing content?

A place can be route-ready and still have an incomplete card. Missing photo or weak description must not collapse a city route to 0-1 points.

## Implemented Stages

### Stage 1: Read-Only Deterministic Triage

Code:

- `services/data_quality/critical_coverage.py`
- `services/admin_platform_quality.py`
- `routers/admin_data_quality.py`
- `/admin/quality`
- `frontend/src/pages/admin/AdminQualityPage.tsx`

The triage result is returned in `critical_coverage` and mirrored into top-level summary fields:

- `route_candidate_total`
- `route_ready_total`
- `route_blockers_total`
- `card_ready_total`
- `card_blockers_total`
- `auto_enrichment_total`
- `critical_manual_review_total`
- `optional_gaps_total`
- `not_applicable_total`

### Stage 2: Drill-Down and Real Admin Actions

`/admin/quality` counters are actionable:

- route/card/auto/manual counters open the place drill-down endpoint with preserved city/category filters;
- place rows link to the exact admin place page;
- auto-enrichment rows link to the enrichment/review workspace;
- manual-review rows link to the same review workspace;
- photo work links to the photo moderation screen;
- the city pipeline button calls `POST /admin/place-enrichment/pipeline/{city_slug}/run` and queues the real import-worker enrichment job.

### Stage 3: No-Migration Materialization

Code:

- `services/data_quality/critical_coverage_state.py`
- `POST /admin/data-quality/cities/{city_slug}/critical-coverage/refresh`

This stage deliberately avoids an Alembic migration while the rules are still being validated on real cities. It persists the current per-place Critical Coverage state into existing `data_quality_issues` rows:

- `issue_type = critical_coverage_state`
- `source = critical_coverage_v2`
- `reason = state`
- `status = current`
- `evidence.bucket = route_blocker|card_blocker|auto_enrichment_candidate|manual_review|optional_gap|not_applicable|ready`

The refresh is idempotent. Re-running it without data changes does not create duplicate rows and reports unchanged rows separately from real updates.

When category is omitted, stale materialized states for the city are resolved. Category-limited refreshes are safe for inspection and do not resolve unrelated categories.

A future dedicated `PlaceQualityState` table can replace this without changing the triage contract.

## Endpoints

### City Summary

```text
GET /admin/data-quality/cities/{city_slug}/critical-coverage?category=<category>
```

Returns city-level route/card/auto/manual buckets, coverage, breakdowns and `next_actions`.

### Place Drill-Down

```text
GET /admin/data-quality/cities/{city_slug}/critical-coverage/places?bucket=<bucket>&reason=<reason>&category=<category>&limit=50&offset=0
```

Supported buckets:

- `route_blocker`
- `route_ready`
- `card_blocker`
- `card_ready`
- `auto_enrichment_candidate`
- `manual_review`
- `optional_gap`
- `not_applicable`
- `route_excluded`

Every visible counter in the admin UI must be able to open this endpoint or a more specific queue. A counter without a list is not actionable.

### Materialized Refresh

```text
POST /admin/data-quality/cities/{city_slug}/critical-coverage/refresh?category=<category>&limit=<limit>
```

Returns:

- `scanned`
- `created`
- `updated`
- `unchanged`
- `resolved`
- `by_bucket`
- `issue_type`
- `source`

## Category Profiles

### Landmark / Monument / Square / Viewpoint

Route critical:

- title
- coordinates
- canonical/category signal

Card required:

- approved primary photo cache in `Place.image_url`
- short description

Not applicable by default:

- opening hours

### Museum / Gallery / Paid Attraction

Route critical:

- title
- coordinates
- canonical/category signal
- opening hours or normalized schedule

Card required:

- approved primary photo cache in `Place.image_url`
- address
- short description

### Park / Promenade / Beach

Route critical:

- title
- coordinates
- canonical/category signal

Card required:

- approved primary photo cache
- short description

Optional:

- address
- opening hours, unless later category rules mark the place as fenced/paid

### Restaurant / Cafe / Bar

Route critical:

- title
- coordinates
- canonical/category signal
- opening hours or normalized schedule

Card required:

- address
- approved primary photo cache

Auto-enrichable:

- short description candidate

### Service / Utility Categories

Examples:

- pharmacy
- bank
- ATM
- bus/transit stop
- parking
- toilet
- hospital/clinic
- police/government/service/utility

These are `not_applicable` for tourist routes by default and must not inflate tourist data quality gaps.

## Buckets

The triage tracks several buckets per place. A place may have multiple detailed issues, but city counters count affected places distinctly.

- `route_blocker`: prevents safe use in route generation.
- `card_blocker`: route may work, but the user-facing card is incomplete.
- `auto_enrichment_candidate`: deterministic data gap that can be sent to enrichment.
- `manual_review_required`: source conflict, low-confidence critical field, open review item, or pending photo candidate.
- `optional_gap`: missing non-critical field.
- `not_applicable`: non-tourist/service object excluded by design.

## Photo Policy

`Place.image_url` is treated as a cache of the approved primary image, not as the source of truth.

Photo candidates are not applied silently. A pending photo candidate increases the photo review queue and may improve card completeness only after an admin approves it and license/attribution are safe.

Never automate:

- photo approval without license check;
- unclear attribution;
- user/social photos without safe reuse rights;
- setting an unreviewed photo as primary.

## Hours Policy

Opening hours are route-critical for museums, galleries, paid attractions, restaurants, cafes, and bars.

Opening hours are not route-critical for landmarks, monuments, viewpoints, and open squares.

For parks, beaches, and promenades hours are optional in Stage 1 unless future source rules identify a fenced/paid place.

`PlaceSchedule` rows count as hours coverage even when legacy `Place.opening_hours` JSON is empty.

## Auto-Enrichment Policy

Can be triggered automatically or by an admin action after triage:

- address geocoding when source observations or high-confidence field candidate exist;
- AI description candidate generation from evidence;
- opening-hours enrichment from structured sources.

AI descriptions remain candidates. They must not become source of truth without review or clear source evidence.

## Manual Review Policy

Requires explicit admin action:

- source conflicts;
- low-confidence critical fields;
- pending photo candidates;
- open review queue items;
- ambiguous categories;
- possible duplicates;
- route eligibility changes for borderline cases.

## Admin UI Contract

`/admin/quality` shows separate operational counters:

- route blockers;
- card blockers;
- auto-enrichment candidates;
- manual review;
- coverage for photos, hours, addresses, and descriptions.

The mobile card must be readable in one column and must not imply that import completion equals launch readiness.

Operator actions from the card:

- `Запустить enrichment` queues the existing city pipeline;
- `Фото` opens photo moderation for the city;
- `Review queue` opens enrichment/review queue;
- `Материализовать` persists the current Critical Coverage state into `data_quality_issues`.

## Future Stage

After validating materialized `critical_coverage_state` on real cities, introduce a dedicated indexed state table:

- `PlaceQualityState` or `Place.quality_bucket`;
- composite index by `city_id`, `quality_bucket`;
- `CityQualitySnapshot` for history/trends;
- async recalculation after import/enrichment/photo approval/review resolution;
- filters by bucket in `/admin/places` and review queues.
