# City GO — Production Verification Suite v1

Date: 2026-07-02
Status: implementation contract
Jira: CITYGO-157

## Problem

CI proves that the repository commit passes tests. It does not prove that production is alive after deploy.

Before this suite, the deployment workflow checked only the deployed build metadata and backend readiness on the server. That is useful, but it does not cover public frontend load, authenticated admin endpoints, compact failed-check reporting, or route smoke checks.

## Goal

After every successful production deploy, run automatic smoke checks and send a short Telegram summary.

The user should not have to open every admin tab manually to discover 400/500 errors.

## Important auth boundary

The smoke suite does not change admin authentication.

It does not create, rotate, print, fetch, or expose admin tokens.

No one should copy `ADMIN_API_TOKEN` from a phone. If the secret already exists in GitHub, admin smoke uses it automatically. If the secret is missing, admin checks are reported as `skipped` and the public smoke still runs.

## Production URL resolution

The user should not have to configure a production URL from a phone just to get a smoke summary.

Resolution order:

1. Use `PRODUCTION_BASE_URL` when configured.
2. If it is absent, use existing deploy secret `SSH_HOST` as `http://<SSH_HOST>`.
3. If both are absent, create a `⚠️ production_base_url: skipped` summary instead of failing before summary creation.

This prevents fallback messages such as `smoke workflow did not produce summary` for configuration-only cases.

## Implementation

Files:

- `.github/workflows/production-smoke.yml`
- `scripts/production_smoke.py`
- `tests/test_production_smoke_script.py`

## Workflow

`Production Smoke` is triggered by:

- `workflow_dispatch` for manual runs;
- `workflow_run` after successful `Production Deploy`.

Preferred secret:

- `PRODUCTION_BASE_URL`

Fallback existing deploy secret:

- `SSH_HOST`

Optional existing secret:

- `ADMIN_API_TOKEN`

Optional variables:

- `CITY_GO_ROUTE_SMOKE_ENABLED`
- `CITY_GO_ROUTE_SMOKE_CITY_ID`
- `CITY_GO_ROUTE_SMOKE_LAT`
- `CITY_GO_ROUTE_SMOKE_LNG`

Telegram notification uses existing secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Checks

### Public checks

- `build` — GET `/build.json`, validates deployed commit prefix when expected SHA is provided.
- `backend_ready` — GET `/ready`.
- `frontend` — GET `/`.

### Authenticated admin checks

Admin checks are visible in the smoke summary every time.

When `ADMIN_API_TOKEN` exists as a GitHub Secret, admin checks run with `Authorization: Bearer <ADMIN_API_TOKEN>`.

When the secret is absent, admin checks are reported as `skipped`:

- `admin_system_health` — GET `/admin/system-health`.
- `admin_quality` — GET `/admin/quality`.
- `admin_taxonomy_categories` — GET `/admin/taxonomy/categories?limit=1`.

Smoke summary does not include authenticated response bodies.

### Optional route smoke

Enabled only when `CITY_GO_ROUTE_SMOKE_ENABLED=true`.

- `route_quick` — POST `/v1/user-routes/build`.

The request uses current API build mode `auto`, because Route Builder v2 currently provides the contract layer while the existing route executor remains the production path.

## Telegram summary format

Success example:

```text
✅ CITY GO · PRODUCTION SMOKE
Commit: c56c844
✅ build: ok · sha_c56c844
✅ backend_ready: ok · http_200
✅ frontend: ok · http_200
✅ admin_system_health: ok · http_200
```

Skipped target example:

```text
⚠️ CITY GO · PRODUCTION SMOKE
Commit: c56c844
⚠️ production_base_url: skipped · PRODUCTION_BASE_URL or SSH_HOST is required
Skipped checks:
- production_base_url: PRODUCTION_BASE_URL or SSH_HOST is required
```

Skipped admin example:

```text
⚠️ CITY GO · PRODUCTION SMOKE
Commit: c56c844
✅ build: ok · sha_c56c844
✅ backend_ready: ok · http_200
✅ frontend: ok · http_200
⚠️ admin_quality: skipped · ADMIN_API_TOKEN secret is not configured
Skipped checks:
- admin_quality: ADMIN_API_TOKEN secret is not configured
```

Failure example:

```text
❌ CITY GO · PRODUCTION SMOKE
Commit: c56c844
✅ build: ok · sha_c56c844
❌ admin_quality: failed · http_500
Failed checks:
- admin_quality: http_500
```

## Invariants

- Production deploy is not equivalent to production verification.
- Smoke must always produce a summary, even when configuration is incomplete.
- Admin smoke is optional and uses only an already configured GitHub Secret.
- Missing admin secret is a skipped check, not a reason to ask the user for a token.
- Failed checks must be named directly.
- Telegram output must stay short.
- Response bodies from admin endpoints must not be sent to Telegram.
- Route smoke is optional until route test data is stable.

## What still needs follow-up

1. Run `Production Smoke` again after this fix.
2. Confirm whether URL resolution uses `PRODUCTION_BASE_URL`, `SSH_HOST`, or `production_base_url: skipped`.
3. Confirm whether admin checks are `ok` or `skipped`.
4. Decide whether route smoke should be enabled immediately.
5. If enabled, configure route smoke city/coordinates variables.
6. Add deeper API-level tests for Route Builder v2 endpoints.
7. Add frontend Playwright smoke for user flows and admin screens.
8. Promote smoke failures into deploy-blocking release policy after initial stabilization.
