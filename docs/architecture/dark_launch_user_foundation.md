# CITY GO — Dark-Launch User Foundation

Status: implementation draft behind flags OFF  
Branch: `ai/dark-launch-user-foundation`  
Base commit: `d6a4429be452e1317f20e1b8228ddfe389a18424`

## Purpose

This foundation prepares future auth/profile/favorites/saved routes/route history/reviews/moderation/privacy/Telegram identity work without changing the current public user flow.

The implementation is intentionally dark-launched:

- no existing flow requires login;
- no visible login/profile/review UI is added;
- no public reviews are exposed;
- no public ratings are fabricated;
- no user-generated content is written into published places or routes;
- no public city/place/route read path joins user/review tables;
- all new API contracts are disabled by feature flags by default.

## Feature flags

Typed registry: `core/feature_flags.py`.

Required flags default to `False` in `core/config.py`:

- `auth.enabled`
- `profile.enabled`
- `favorites.enabled`
- `saved_routes.enabled`
- `route_history.enabled`
- `reviews.enabled`
- `public_reviews.enabled`
- `review_votes.enabled`
- `user_photos.enabled`
- `suggestions.enabled`
- `moderation.enabled`
- `telegram_identity.enabled`
- `account_linking.enabled`

Dependency rules:

- `public_reviews.enabled` requires `reviews.enabled` and `moderation.enabled`;
- `review_votes.enabled` requires `public_reviews.enabled`;
- `user_photos.enabled` requires `moderation.enabled`;
- `account_linking.enabled` requires `telegram_identity.enabled`;
- `profile.enabled` requires `auth.enabled` until an explicit anonymous profile strategy exists;
- `route_history.enabled` requires `auth.enabled` until explicit privacy consent exists.

Disabled API shape:

```json
{ "detail": { "code": "feature_disabled", "feature": "<flag>" } }
```

Endpoints are also hidden from `/openapi.json` and `/docs` (`include_in_schema=False` on the router) while flags are OFF, so the skeleton surface is not publicly discoverable. Direct calls still resolve and return the structured 404 above.

`core/feature_flags.py:validate_feature_flag_configuration()` checks configured (not effective) flag values against the dependency rules above and raises `ValueError` on startup if an operator enables a flag without its required dependency — this catches contradictory config early instead of silently no-oping.

## Schema foundation

Migration: `migrations/versions/b2c3d4e5f6a7_dark_launch_user_foundation.py`.

New additive tables only:

- `users`
- `anonymous_identities`
- `external_identities`
- `telegram_identities`
- `identity_link_events`
- `user_profiles`
- `user_preferences`
- `favorite_places`
- `saved_routes`
- `route_history`
- `reviews`
- `review_votes`
- `place_rating_aggregates`
- `user_photos`
- `user_suggestions`
- `moderation_items`
- `abuse_reports`
- `user_foundation_audit_logs`

No hot public table is altered.

Deploy warning: this migration adds FKs to `places` and `routes`. Before running it against production, validate migration timing on a staging/prod-like database (lock duration under real table size and concurrent traffic). Do not run it against production automatically as part of this fix.

## Telegram identity model

Canonical account identity is `users.id`.

Telegram is represented as an external provider identity, not as the canonical user id.

Rules:

- Telegram user id is stored and looked up by deterministic hash.
- Raw Telegram id is not logged or required by the schema.
- Username, first name, last name, phone or display name are never identity keys.
- A Telegram identity already linked to one user cannot silently link to another user.
- Conflicts are explicit through `identity_link_events.status = 'conflict'` and `telegram_identities.status = 'conflict'`.
- Live Telegram WebApp `initData` validation is not implemented yet; the endpoint remains OFF and requires official signature validation before enablement.

## API contracts

Router: `routers/user_foundation.py`.

All endpoints return `404 feature_disabled` while their flags are OFF:

- `GET /me`
- `PATCH /me/profile`
- `POST /identity/telegram/verify`
- `POST /identity/link`
- `GET /identity/links`
- `GET /me/favorites`
- `POST /me/favorites/places/{place_id}`
- `DELETE /me/favorites/places/{place_id}`
- `GET /me/saved-routes`
- `POST /me/saved-routes`
- `GET /places/{place_id}/reviews`
- `POST /places/{place_id}/reviews`
- `POST /reviews/{review_id}/vote`
- `POST /places/{place_id}/suggestions`
- `GET /admin/moderation`
- `POST /admin/moderation/{id}/approve`
- `POST /admin/moderation/{id}/reject`

When a flag is enabled before real auth/moderation exists, the skeleton returns explicit `auth_not_implemented` or `moderation_not_implemented` instead of fake success.

## Rating separation

Rating logic lives in `services/user_rating_foundation.py`.

Definitions stay separate:

- user review rating: one user-submitted rating on an approved review;
- aggregated place rating: derived only from approved reviews;
- place quality score: data completeness/trust, not stars;
- route recommendation score: internal route solver score;
- AI confidence: enrichment confidence;
- admin readiness score: admin/data readiness.

Rules:

- empty reviews produce no rating;
- pending/rejected/hidden/spam/duplicate/needs_more_info reviews are ignored;
- approved review ratings only are aggregated;
- invalid ratings outside 1–5 are rejected;
- no hardcoded default star rating is introduced.

## Tests added

- `tests/test_user_foundation_feature_flags_new.py`
- `tests/test_user_foundation_api_contracts_new.py`
- `tests/test_user_foundation_telegram_identity_new.py`
- `tests/test_user_foundation_rating_separation_new.py`

Coverage intent:

- flags default OFF;
- dependency rules;
- disabled endpoint contract;
- existing public `/health` and `/cities/` remain unauthenticated;
- same Telegram user hash maps to the same identity;
- conflict prevents silent double-link;
- Telegram and anonymous identity can coexist without forced merge;
- approved-only rating aggregation;
- no fake rating from empty/unapproved reviews.

## Explicitly not implemented

- live OAuth;
- mandatory login;
- Telegram WebApp login activation;
- public reviews;
- public ratings;
- user photo upload;
- visible profile/review/favorites UI;
- automatic route history writes;
- production flag enablement.

## Review notes

This branch was created because the execution environment could not clone the repo locally. GitHub connector writes create remote commits, so the work is isolated from `main` in `ai/dark-launch-user-foundation`. No deploy or GitHub Actions run was started.
