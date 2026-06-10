# Place And Route UI Data Contract

## Purpose

The web UI must render places and generated routes from database-backed API
payloads. Demo JSON is only a fallback for local frontend mode.

## Place Cards

Place cards use the public place API payload and normalize it on the frontend:

- `average_visit_duration_minutes` is exposed to UI as `visit_minutes`.
- missing duration is exposed as a category default for UI/runtime use, without
  overwriting the canonical DB field.
- missing opening hours are exposed as `estimated_default` runtime hours for
  route/card display, not as verified source data.
- raw import descriptions like `coffee: Title` are not shown as final copy.
- missing or unverified images render a deterministic category fallback.
- an image is treated as an exact place photo only when `image.match_status` is
  `exact_place_photo` or `image_is_exact` is true.

## Route Points

Route builders return route points with presentation fields copied from the
canonical `places` table:

- `title`
- `address`
- `image_url`
- `short_description`
- `source`
- `city_slug`

This keeps the route result explainable: the UI can show which DB place was
selected, why it was selected, and what data quality caveats apply.

Route point images use the same public image policy as catalog cards. The route
pipeline attaches approved/active `place_images` as transient public image
fields; legacy `places.image_url` is not exposed as a route photo.

The frontend rejects route results when a point has `city_slug` that differs
from the selected city. Points without `city_slug` are accepted only for
backward compatibility.

## City Scope

The frontend sends the selected city slug in `city_id` for route requests.
Candidate retrieval interprets this field as the route city slug and restricts
published candidates to that city.

## Route Time

`route_time_mode` defaults to `flexible`. In flexible mode, `closed_now` and
unknown opening hours are not hard filters; they affect scoring and warnings
only. `closed_now` becomes a hard filter only when the request explicitly uses
`route_time_mode: now` or `time_of_day: now`.

`time_of_day` still informs scoring and time-aware ordering. A user choosing
`afternoon` at night gets an afternoon-flavoured route instead of a route
filtered against the current real-world night-time window.

## Route Status

Route responses expose `status`:

- `ready` — enough points for a normal route.
- `partial_route` — at least one point was found, but fewer than expected.
- `no_route` — no route points were selected.

`quality_breakdown.completeness` penalizes incomplete routes, so a one-point
route cannot receive an excellent quality score.

## Candidate Diagnostics

Debug trace for route building includes city/radius diagnostics:

- `city_slug`
- `city_db_id`
- `radius_meters`
- `places_with_city_id`
- `places_public`
- `places_with_coords`

This separates data problems from algorithm problems when a city has imported
places but route candidate retrieval returns too few points.

## Public Visibility

Public place visibility hides technical/seed placeholders such as working
`Dog-friendly cafe 01` records. They may remain in the database for import and
test history, but they are not returned by public catalog queries or route
candidate retrieval.

## Operational Notes

If code was updated but the web still shows old photos or old route behavior,
check for a stale backend process on port `8000`. The frontend calls the running
process; pulling GitHub changes is not enough until uvicorn is restarted.

If `place_images` has no approved/active rows for a city, the public API
correctly returns `image_url: null`. That is a data coverage issue, not a web
rendering bug.

## Image Honesty

The UI must not present an unverified image as a real place photo. If an image
has no exact-match signal, the card shows a fallback with a badge such as
`Фото требует проверки` or `Нет проверенного фото`.
