# Route Readiness Diagnostics

## Scope

Admin route readiness diagnostics explains why city places are or are not ready for route generation.

## Backend

Endpoint:

```http
GET /admin/routes/eligibility/{city_slug}
```

Response fields:

- `city_slug`, `city_name`
- `places_total`, `eligible_places`, `published_places`
- `blockers_count_by_reason`
- `near_ready_places`
- `sample_blocked_places`

Supported blocker reasons:

- `no_photo`
- `no_address`
- `hidden_category`
- `draft_or_unpublished`
- `inactive`
- `low_quality`
- `missing_coordinates`

`near_ready_places` returns up to 20 blocked places with 1 or 2 blockers, ordered by fewer blockers, higher quality score, then place id.

## Frontend

The admin page `Маршруты → Eligibility` shows:

- city selector and `city_slug` input
- summary cards
- blockers table
- near-ready places table
- sample blocked places table
- loading, error, and empty states

The page accepts both `city_slug` and legacy `city` query parameters.

## Verification

Regression coverage:

- `tests/test_route_readiness_diagnostics_new.py`
- `frontend/src/pages/admin/AdminRouteEligibilityPage_new.test.tsx`
