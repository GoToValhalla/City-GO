# Stage 5 projection rollout runbook

## Activation

1. Rebuild `search`, `routing`, and `route_candidate_set` globally or for every source city.
2. Read `/admin/projections/readiness` for each required type and scope.
3. Require `ready=true`, equal counts, compatible versions, fresh completion, and no later failure.
4. Enable one toggle at a time. The backend rejects unsafe activation.
5. Observe `projection_read`, `public_read_projection_unavailable`, and `projection_rebuild` logs.

## Rollback

Disable the affected toggle and verify its legacy API/TMA behavior. Keep the failed rows and job
records for diagnosis. Never delete `PublishedPlaceSnapshot`, never rewrite versions, and never
change publication decisions as part of projection recovery. Retry the rebuild safely, validate
readiness, and reactivate only after the gate passes.

## Operational limits

Rebuild execution is synchronous in the authenticated backend operation. PostgreSQL serializes
rebuild transactions so global and city replacements cannot overlap. SQLite is supported only for
tests and local single-writer development.
