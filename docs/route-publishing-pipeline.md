# Route Publishing Pipeline

## Purpose

Admin users can turn imported city places into published walking routes:

1. inspect route eligibility diagnostics;
2. run route generation without saving;
3. save selected points as a draft route;
4. adjust the draft through existing draft editing APIs;
5. publish the draft as an editorial `Route`.

## Backend Endpoints

Dry run without persistence:

```http
POST /admin/routes/dry-run
```

Save a draft from the same generation request:

```http
POST /admin/routes/drafts/generate
```

Publish a draft route:

```http
POST /admin/routes/drafts/{draft_id}/publish
```

The publish step creates an active `Route` and ordered `RoutePlace` rows from `RouteDraftPoint`.

## Admin UI

`Маршруты → Dry Run` shows:

- whether a route can be assembled;
- selected places and selection reasons;
- rejected places and blocker reasons;
- draft save action;
- draft publish action.

## City Readiness

City readiness components include:

- `eligible_places`
- `route_eligibility_pct`
- `published_routes`
- `has_published_routes`

The existing readiness score thresholds remain compatible with current CI; route publication metrics are exposed for admin decisions.

## Tests

Regression coverage:

- `tests/test_admin_route_publishing_pipeline_new.py`
- `tests/test_admin_route_dry_run_new.py`
- `frontend/src/pages/admin/adminRoutes_new.test.tsx`
