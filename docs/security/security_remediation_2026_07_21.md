# Security remediation — breaking API notes (2026-07-21)

Consolidated fail-closed lockdown of public privileged writes, anonymous
ownership, public visibility contracts, abuse controls, and deploy safety.

## Breaking API changes

1. Public Place writes removed
   - Removed: POST/PUT/DELETE `/places`
   - Use: `/admin/places*` with Bearer admin token

2. Verification and city-expansion are admin-only
   - `/v1/verification/*` requires admin Bearer
   - `/city-expansion/*` requires admin Bearer
   - `/place-seed/import|dry-run|validate` require admin Bearer

3. Route draft ownership
   - Server issues `ownership_token` once on POST `/routes/random`
   - Subsequent calls require header `X-Route-Draft-Session`
   - Missing/wrong token → non-disclosing 404 (not 422)
   - Tokens stored as SHA-256 digests only

4. Editorial route sessions
   - Create returns `ownership_token` once
   - Later ops require header `X-Route-Session`

5. User signals / history / feedback
   - Client `user_id` is never ownership proof
   - Use header `X-Anonymous-Session`
   - Summary/profile: `/user-signals/summary` and `/profile`
   - History: `/route-analytics/users/me/history`

6. GET user-route alternatives removed as fake empty list
   - Returns 410; use POST with signed state

7. Public debug reports
   - Response no longer includes `admin_url` or `telegram_error`

8. Public recommendations
   - `X-Debug` no longer exposes pipeline `_trace`

## Deploy notes

- `docker-compose.yml` requires `DATABASE_URL`, `POSTGRES_*` from env
- Backend healthcheck probes `/ready`
- Alembic head after this change: `b7e4f1a9082c`
- Production startup requires `ADMIN_API_TOKEN`,
  `USER_ROUTE_STATE_SECRET`, and `BOT_WEBHOOK_SECRET`
  when a bot token is configured
- Backend abuse controls are process-local and bounded to 10,000 keys. Compose
  runs one worker. A multi-worker setting emits a startup warning because no
  shared limiter store is currently available.
- Proxy-derived client IPs are used only when the immediate peer belongs to
  `TRUSTED_PROXY_CIDRS`; Compose supplies its Docker bridge CIDR.

## Verification additions

- Compose static contract: env-only DB password, `/ready`, and no migration
  command mutation of `alembic_version`.
- PostgreSQL migration integration: clean upgrade, legacy backfill, atomic
  failure rollback, safe rerun, and schema downgrade.
- Public AI intent registry: every intent has an explicit reader, publication
  gate, and public schema classification; unknown intent is rejected.
- Public write architecture: every active unauthenticated/anonymous write route
  must match a rate-limit rule, including aliases.

See `docs/architecture/security_remediation_commit_review.md` for the complete
boundary and intent inventory.
