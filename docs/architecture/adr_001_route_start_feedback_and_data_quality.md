# ADR-001: route start, data confidence and feedback loop

## Status

Accepted.

## Context

City Go has several route layers. New user-facing route scenarios must use one predictable entry point, otherwise web and Telegram can produce different route results.

Place data comes from OSM, source observations, manual review and user feedback. Photo quality and place existence quality are separate concerns and must be tracked separately.

## Decision

1. New user route creation uses `/v1/user-routes/build`.
2. Route correction uses `/v1/user-routes/correct`.
3. `/v1/recommendations/route` remains a recommendation/showcase endpoint.
4. Legacy route generation is not the main user route flow.
5. Route build accepts start context from coordinates, browser geolocation or typed address.
6. Typed address is resolved through Geoapify when `GEOAPIFY_API_KEY` is configured.
7. If geocoding fails, route build falls back to client coordinates.
8. Place photo confidence is represented by `image_confidence`, `image_status`, `image_reviewed_at`.
9. Place existence confidence is represented by `existence_confidence_score`, `existence_confidence_level`, `verification_status`.
10. Route rating is stored as `user_signals.signal_type = route_feedback`.

## Consequences

- Auto-approved photos can be visible immediately and still require later manual confirmation.
- Manual confirmation of photo and place existence updates the confidence state.
- Route rating from UI and Telegram becomes input for future ranking and personalization.
- Start address no longer disappears silently: it is geocoded or explicitly falls back to passed coordinates.

## Test requirements

- Route feedback endpoint: successful save and rating validation.
- Geocoding service: successful provider response and no-key fallback.
- Cleanup script: technical/non-tourist place detection.
- New tests keep `_new` in the test name until they are run locally.
