# Critical Data Coverage / Quality Rules v2

## Purpose

City GO must maximize coverage of critical place data without turning every missing field into manual work.

The contract separates two different questions:

1. Route readiness: can the route engine safely use this place?
2. Card completeness: can the app show this place with enough user-facing content?

A place can be route-ready and still have an incomplete card. Missing photo or weak description must not collapse a city route to 0-1 points.

## Stage 1 Implementation

Stage 1 is read-only and deterministic.

Code:

- `services/data_quality/critical_coverage.py`
- `services/admin_platform_quality.py`
- `/admin/quality`
- `frontend/src/pages/admin/AdminQualityPage.tsx`

No database mutation happens in this stage. The triage result is returned in `critical_coverage` and mirrored into top-level summary fields:

- `route_candidate_total`
- `route_ready_total`
- `route_blockers_total`
- `card_ready_total`
- `card_blockers_total`
- `auto_enrichment_total`
- `critical_manual_review_total`
- `optional_gaps_total`
- `not_applicable_total`

This shape is intentionally compatible with a future materialized `Place.quality_bucket` / `PlaceQualityState` implementation.

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

`/admin/quality` must show separate operational counters:

- route blockers;
- card blockers;
- auto-enrichment candidates;
- manual review;
- coverage for photos, hours, addresses, and descriptions.

The mobile card must be readable in one column and must not imply that import completion equals launch readiness.

## Future Stage

After validating Stage 1 metrics on real cities, materialize the same contract:

- `Place.quality_bucket` or `PlaceQualityState`;
- composite index by `city_id`, `quality_bucket`;
- `CityQualitySnapshot` for history/trends;
- async recalculation after import/enrichment/photo approval/review resolution;
- filters by bucket in `/admin/places` and review queues.
