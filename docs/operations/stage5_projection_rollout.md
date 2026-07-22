# Stage 5 projection rollout runbook

Use the manual `04 · CITY GO · Stage 5 Production Operations` workflow for every production
operation. It is serialized, targets the protected `production` environment, and calls only the
authenticated admin APIs. Mutations require `CONFIRM_STAGE5_PRODUCTION_MUTATION`.

`status`, `readiness`, and `rebuild` accept `global` or a positive numeric `city_id` scope.
Projection toggles are global by design, so enable/disable operations reject city scope.

## Activation

1. Run `rebuild`. It first appends a versioned `PublishedPlaceSnapshot` generation from canonical
   `Place` state, then rebuilds `search`, `routing`, and `route_candidate_set` from that source.
2. Read `/admin/projections/readiness` for each required type and scope.
3. Require `ready=true`, equal counts, compatible versions, fresh completion, and no later failure.
4. Enable one toggle at a time. The backend rejects unsafe activation.
5. Observe `projection_read`, `public_read_projection_unavailable`, and `projection_rebuild` logs.

## Rollback

Disable the affected toggle and verify its legacy API/TMA behavior. Keep the failed rows and job
records for diagnosis. Never delete `PublishedPlaceSnapshot`, never rewrite versions, and never
change publication decisions as part of projection recovery. Retry the rebuild safely, validate
readiness, and reactivate only after the gate passes.

Use `disable_all` for the mandatory rollback drill. Disable operations intentionally do not depend
on projection readiness, so rollback remains available when a projection is missing or stale.

## Operational limits

Rebuild execution is synchronous in the authenticated backend operation. PostgreSQL serializes
rebuild transactions so global and city replacements cannot overlap. SQLite is supported only for
tests and local single-writer development.
