# Production readiness and route QA

## Production database incident contract

A production deploy is successful only when all of the following are true after backend and bot have started, and `import-worker` has been confirmed stopped:

1. PostgreSQL container is `Up` and `pg_isready -U postgres -d city_guide` succeeds.
2. Backend `GET /ready` executes `SELECT 1` and returns HTTP 200.
3. Frontend proxy `GET /api/ready` returns HTTP 200.
4. Authenticated smoke requests for admin places, taxonomy categories and import jobs complete within 15 seconds.
5. `import-worker` is not running; queued import jobs remain queued.
6. Alembic reports the expected current revision.

`GET /health` is only a process liveness check. It must not be used as a database readiness gate.

On failure, deployment and scheduled production health checks collect:

- `docker compose ps`;
- db/backend/import-worker logs;
- disk and memory state;
- PostgreSQL connection count, active/waiting sessions and long-running queries;
- `pg_isready` and Alembic state.

Runtime connection pools are intentionally separated: the public backend receives the largest pool, while bot and import-worker use small pools so background processing cannot consume every PostgreSQL connection. Import-worker still must not auto-start on the current low-memory production host; heavy imports wait for a separate worker-safety fix. PostgreSQL has `restart: unless-stopped`.

## Immediate recovery

Run the existing `Prod DB Repair` workflow, then run `Production Deploy`. The new deploy must stay red if `/ready` or the critical admin endpoint smoke fails.

Do not start region imports or bulk enrichment while production readiness is failing.

## Place data rules

- Technical titles ending in `OSM <number>` are unresolved source records. They are excluded from routes and rendered with a category label instead of the raw title.
- Missing descriptions first use sourced Wikidata or official-site text. If no sourced text exists, the import pipeline creates a factual draft only from fields already stored on the place.
- Generated drafts use low confidence and always enter review; they are not treated as verified editorial copy.
- Infrastructure is classified explicitly. Banks, ATMs, pharmacies, shopping centres, police/MVD, hospitals and clinics must not remain in generic `service` when the title or source tags are unambiguous.

## Remote route QA target

The current admin dry-run explains candidate selection but its SVG is not a real street map. The target Route QA Lab must add:

- a MapLibre map with pedestrian route geometry from OSRM, Valhalla or GraphHopper;
- comparison of straight-line and routed distance;
- checks for water crossings, inaccessible areas, long segments, backtracking, duplicate points, technical names and category-policy violations;
- quality evidence links for every point;
- scenario batches for 60/120/180/240 minutes and tourist, family, food, coffee, practical and accessibility contexts;
- regression snapshots and diffs between route-engine versions;
- operator approval/rejection with audit history.

A route with unresolved technical POIs or critical geometry findings cannot be published.

## Kaliningrad region import identity

Same-named settlements are identified by administrative and source identity, not by name alone:

`country_code + region_id + source_type + source_external_id`

Human-readable slugs receive a region suffix only when a collision exists. `osm_relation_id`, Wikidata QID, region relation and slug aliases are retained. Every coordinate must be checked against the region/import-scope polygon before assignment.
