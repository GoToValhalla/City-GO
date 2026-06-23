# City GO — Current System Overview

Last updated: 2026-06-23

This document is the operational map of the current `main` branch. It is intentionally practical: what exists, where the code lives, what contracts matter, and what to check before deploy.

## 1. Product Surface

City GO currently has four user/admin surfaces:

1. Public web app: cities, places, routes, route detail, route navigation MVP.
2. Admin web app: place/catalog operations, route readiness, import/enrichment pipeline, review queues.
3. Telegram bot: lightweight guide with city selection, routes, places, nearby, open-now, favorites, search, and route mode.
4. Backend APIs: public catalog, user route build, admin operations, bot webhook.

The system must not expose raw imported data directly to users. Every user-facing surface should pass through quality gates.

## 2. Repository Map

```text
core/                 FastAPI config, auth, router registration
models/               SQLAlchemy ORM models
schemas/              Pydantic API schemas
routers/              FastAPI endpoints
services/             Business logic and quality/pipeline services
migrations/versions/  Alembic migrations
frontend/             React/Vite frontend
telegram_bot/         aiogram Telegram bot
tests/                Backend regression tests
docs/                 Architecture and operations documentation
.github/workflows/    CI and deploy workflows
```

## 3. Runtime Services

Production Docker Compose services:

| Service | Purpose |
|---|---|
| `db` | PostgreSQL 16 database. |
| `migrate` | One-shot Alembic migration runner. |
| `backend` | FastAPI app on port 8000. |
| `frontend` | Nginx-served React build on port 80. |
| `bot` | Telegram bot polling process. |
| `import-worker` | Background admin import/enrichment queue runner. |
| `seed`, `address-backfill`, `place-enrichment-export` | Ops-only profiles. |

Important token behavior:

- Telegram bot runtime accepts `BOT_TOKEN` or `TELEGRAM_BOT_TOKEN`.
- Deploy workflow writes `TELEGRAM_BOT_TOKEN` into production `.env` if it is missing.
- Webhook endpoint also accepts either token variable.

## 4. Backend Contracts

### Public Catalog

Core endpoints:

```http
GET /cities/
GET /cities/by-slug/{slug}
GET /places/
GET /places/{place_id}
GET /routes/{route_id}
GET /nearby
GET /open-now
```

Places are expected to use publication and visibility flags:

- `is_active`
- `is_published`
- `is_visible_in_catalog`
- `is_route_eligible`
- `publication_status`
- `quality_score`
- `quality_tier`

### User Route Build

Primary endpoint:

```http
POST /v1/user-routes/build
```

Expected statuses:

| Status | Meaning |
|---|---|
| `ready` | Useful route. |
| `partial_route` | Usable but limited route with warnings. |
| `no_route` | No route, should include reason/debug trace. |
| `failed` | System or quality failure. |

### Route Detail For Navigation

Route detail now includes read-only point fields for route navigation MVP:

- `lat`, `lng`
- `category`
- `address`
- `is_published`
- `is_route_eligible`
- `publication_status`
- `is_active`
- `status`

Backend does not create route sessions for Stage 1 navigation. State is frontend-only.

## 5. Route Navigation MVP

Code:

```text
frontend/src/features/route-navigation/model/
frontend/src/widgets/route-navigation/
frontend/src/pages/routes/RouteDetailPage.tsx
frontend/src/pages/routes/RouteDetailPage.css
```

Implemented behavior:

- `not_started` → `active` → `completed` state machine.
- Manual controls: start, mark visited, next, finish, restart.
- `localStorage` persistence by route id.
- SVG/HTML route schematic using straight segments.
- Frontend quality gate before rendering navigation points.

Quality blockers for navigation point:

- no coordinates;
- inactive/unpublished/hidden;
- not route eligible;
- service/non-tourist category;
- invalid publication status.

Stage 1 intentionally does not include MapLibre, GPS, OSRM, off-route, backend session history, or voice guidance.

## 6. Import / Enrichment Pipeline

Code:

```text
routers/admin_import_pipeline.py
services/import_pipeline_foundation.py
services/import_pipeline_foundation_steps.py
services/import_pipeline_publication.py
services/place_field_confidence_service.py
services/place_photo_candidate_service.py
services/review_queue_service.py
```

Tables:

- `import_job_steps`
- `source_observations`
- `place_field_confidence`
- `place_photo_candidates`
- `review_queue_items`

Admin endpoints:

```http
POST /admin/place-enrichment/pipeline/{city_slug}/run
GET /admin/place-enrichment/jobs/{job_id}/steps
GET /admin/place-enrichment/places/{place_id}/confidence
GET /admin/place-enrichment/review-queue
POST /admin/place-enrichment/review-queue/{item_id}/resolve
POST /admin/place-enrichment/photo-candidates/{candidate_id}/approve
POST /admin/place-enrichment/photo-candidates/{candidate_id}/reject
POST /admin/place-enrichment/photo-candidates/{candidate_id}/set-primary
```

Rules:

- Manual confidence overrides dominate automated imports.
- AI descriptions are capped at medium confidence and cannot mutate factual fields.
- Generic/category photos stay candidates and must not become exact primary photos automatically.
- Low/stale/conflict opening hours are not used for `open now`.

## 7. Telegram Bot

Code:

```text
telegram_bot/main.py
telegram_bot/handlers/catalog.py
telegram_bot/keyboards/catalog.py
telegram_bot/renderers.py
telegram_bot/session.py
telegram_bot/services/facade.py
telegram_bot/quality.py
telegram_bot/analytics.py
routers/telegram_bot_webhook.py
routers/admin_bot_analytics.py
services/admin_bot_analytics_service.py
```

Tables:

- `bot_sessions`
- `bot_events`

User flows:

- `/start`
- city selection
- main menu
- route list/detail
- Telegram route mode
- category places
- place card
- nearby by Telegram location
- open now
- favorites
- text search
- back navigation

Callback rules:

- Telegram `callback_data` must remain <= 64 bytes.
- Long ids are stored in `bot_sessions.short_ids`.
- New favorite callbacks use `fav:add:{type}:{short_id}` and `fav:del:{type}:{short_id}`.
- Old `fav:toggle` is still supported for already rendered messages.

Admin analytics:

```http
GET /admin/telegram-bot/analytics?days=7
```

Returns:

- active users;
- events by type;
- top cities;
- route started/completed funnel;
- no-result searches;
- latest events.

## 8. Data Quality Rules

User-facing surfaces should not show:

- technical OSM names: `node/123`, `way/123`, `relation/123`, `OSM 123`, generated `Культурное место OSM ...`;
- service categories: `service`, `bank`, `atm`, `mvd`, `police`, `government`, `transport`, `hospital`, `health`, `medical`, `pharmacy`, `military`, `cemetery`, `industrial`, `waste_disposal`, `fuel`, `parking`, `car_service`;
- low/stale/conflict opening hours in open-now flows;
- placeholder/no-photo/generic URLs as real images;
- confidence/source/debug labels.

Main quality files:

```text
telegram_bot/quality.py
telegram_bot/renderers.py
telegram_bot/services/facade.py
frontend/src/features/route-navigation/model/qualityGate.ts
services/quality_scoring.py
services/import_pipeline_publication.py
```

## 9. CI

Workflow:

```text
.github/workflows/ci.yml
```

Jobs:

- backend import smoke;
- backend pytest regression with Allure raw results;
- frontend eslint;
- frontend vitest;
- frontend build;
- Telegram notification.

Important backend env in CI:

```env
DATABASE_URL=sqlite:///./ci_test.db
ADMIN_API_TOKEN=ci-admin-token
APP_ENV=test
CITY_GO_TEST_RUN_TYPE=regression
```

Alembic guard:

```text
tests/test_alembic_single_head_new.py
```

When adding migrations, update:

- `KNOWN_HEAD`
- `EXPECTED_COUNT`
- expected metadata table set if new tables were added.

## 10. Deploy

Workflow:

```text
.github/workflows/deploy.yml
```

Run:

```bash
gh workflow run Deploy --ref main
gh run watch <run_id>
```

Deploy sequence:

1. Build backend image.
2. Run backend import smoke inside the built image.
3. Push backend image.
4. Build and push frontend image.
5. SSH into production.
6. Download latest `docker-compose.yml` from `main`.
7. Validate compose config.
8. Pull images from GHCR.
9. Run migrations.
10. Run production schema guard.
11. Recreate backend.
12. Wait for backend health.
13. Recreate frontend.
14. Verify frontend `/build.json` SHA.
15. Recreate bot/import-worker.
16. Verify frontend `/api/health` proxy.
17. Print diagnostics.

Do not re-add heavy `python -c "import main"` inside the already running backend container after deploy. On the current small production server it can be killed with `exit 137`. The import smoke belongs to the build job, where it already exists.

## 11. Minimum Verification Matrix

### Backend-only changes

```bash
.venv/bin/python -m pytest --no-cov -q
git diff --check
```

### Frontend-only changes

```bash
npm --prefix frontend run lint
npm --prefix frontend run test:ci
npm --prefix frontend run build
git diff --check
```

### Route navigation changes

```bash
npm --prefix frontend run test -- routeNavigation routeQualityGate
.venv/bin/python -m pytest --no-cov tests/test_route_detail_navigation_fields_new.py -q
```

### Import/enrichment changes

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_alembic_single_head_new.py \
  tests/test_import_pipeline_foundation_new.py \
  tests/test_import_pipeline_foundation_safety_new.py \
  tests/test_import_pipeline_api_new.py \
  tests/test_import_pipeline_review_queue_new.py \
  tests/test_import_pipeline_photo_safety_new.py -q
```

### Telegram bot changes

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_telegram_bot_rewrite_new.py \
  tests/test_telegram_bot_completion_new.py -q
```

## 12. Known Intentional Boundaries

- Route navigation MVP is manual and frontend-only.
- MapLibre/GPS/OSRM/backend route sessions are not implemented yet.
- Import/enrichment Stage 1 is deterministic and does not require external AI/photo provider secrets in tests.
- CSV enrichment remains a legacy fallback only.
- Telegram bot does not provide a full interactive map; it links to external maps.

## 13. Documentation Update Rule

When changing a subsystem, update docs in the same commit or immediately after:

- README for high-level behavior and commands.
- `docs/operations/current_system_overview.md` for operational impact.
- `docs/architecture/*` for subsystem contracts.
- Tests/CI notes if verification commands change.
