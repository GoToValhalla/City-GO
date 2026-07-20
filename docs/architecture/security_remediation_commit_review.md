# Security remediation architecture review (2026-07-21)

## Boundary model

Public writes fall into three classes: admin Bearer protected, anonymous
ownership-token protected, or intentionally unauthenticated creation/telemetry.
Anonymous credentials are transported only in the named `X-*` headers, returned
once at creation, SHA-256 hashed at rest, and compared in constant time. Signed
user-route state is the authority for route mutations; client `user_id` is
analytics metadata only.

Public entity reads must use the canonical publication helpers:
`apply_public_place_visibility`, `get_public_route_*`, active collection plus
published-city filters, or published destination filters. Public response
schemas must not contain administrative publication/debug fields.

## Public AI intent inventory

| Intent | Entrypoint | Reader | Visibility/publication gate | Returned schema | Exposure/escalation |
|---|---|---|---|---|---|
| `place_detail` | `POST /ai/query` | `get_place_detail_by_slug` | `apply_public_place_visibility` | public place detail | no admin state; read-only |
| `places_filtered` | `POST /ai/query` | `get_places(public_only=True)` | `apply_public_place_visibility` | public place summary | no admin state; read-only |
| `collections` | `POST /ai/query` | `get_collections_by_city_id` | active collection and published active city | public collection summary | no `is_active`; read-only |
| `routes` | `POST /ai/query` | `get_public_routes_by_city_id` | editorial route and place publication gates | public route summary | no `is_active`; read-only |
| `open_now` | `POST /ai/query` | `get_open_now_places` | canonical place visibility and trusted hours | public place card plus hours | no admin reader; read-only |
| `nearby` | `POST /ai/query` | `get_nearby_places` | canonical place visibility | public place card plus distance | no admin reader; read-only |

`PUBLIC_AI_INTENTS` is the access-classification registry. Its architecture test
enumerates all six active intents and requires explicit reader, gate, and schema
metadata. Unclassified/unknown queries return `status=rejected` with no results.

## Rate limiting

The deployment contract is one backend worker (`WEB_CONCURRENCY=1`). The store
is process-local, lock-protected, and capped at 10,000 client/rule keys; oldest
keys are evicted at the bound and expired events are removed on access. All
active public writes are architecture-tested for rule coverage, including
aliases. A startup warning is emitted when `WEB_CONCURRENCY > 1`; no shared
store already exists in this project, so multi-process aggregate enforcement is
intentionally not claimed.

`X-Forwarded-For` is accepted only from `TRUSTED_PROXY_CIDRS`. Compose trusts
only its Docker bridge range; direct clients cannot select a forged limiter key.

## Migration b7e4f1a9082c

The migration uses Alembic transactional DDL and guarded column/index creation.
Legacy `route_drafts.session_token` is hashed and cleared in the same `UPDATE`.
An injected trigger failure proves the whole migration rolls back, including DDL
and `alembic_version`. Rerun at head is a no-op. Downgrade is supported for the
revision-owned hash columns/indexes only; it cannot restore deliberately erased
plaintext secrets and therefore is a schema rollback, not credential recovery.
