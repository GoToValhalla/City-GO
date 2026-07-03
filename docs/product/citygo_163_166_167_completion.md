# CITYGO-163/166/167 Completion Note

Date: 2026-07-03

This note records the follow-up implementation that completed the previously deferred parts of the route/data loop batch.

## CITYGO-163

Completed now:

- `PlaceAutoRepairService` is integrated into active admin import/enrichment jobs.
- Import job details include `auto_repair` summary.
- Light import snapshot includes `auto_repair` summary.
- Import alert payload includes `auto_repair` summary.
- Tests cover the import hook storing repair summary.

Main files:

- `services/admin_city_import_job_service.py`
- `services/place_auto_repair_service.py`
- `tests/test_user_route_slot_session_and_import_repair.py`

Stabilized after CI:

- Auto-repair review backlog no longer changes successful job status to `success_with_warnings` by itself.
- Photo enrichment can finish as `success` with zero created photos while still exposing details and auto-repair summary.
- Full import status is tied to import/source warnings, not auto-repair `needs_review` count.

## CITYGO-166

Completed now:

- Visible slot constructor UI is implemented.
- Slot options endpoint is used from the frontend.
- Backend slot route build preserves slot order.
- Selected place per slot is respected when valid.
- Missing required slot returns honest partial route.
- Slot match explanations are returned in `explanation.slot_matches`.

Main files:

- `frontend/src/widgets/recommendation-route/RouteSlotBuilder.tsx`
- `frontend/src/widgets/recommendation-route/RouteRequestForm.tsx`
- `services/user_route_slot_build_service.py`
- `services/user_route_build_service.py`
- `services/route_builder_v2_service.py`

Stabilized after CI:

- `routeSlots` is optional outside constructor mode.
- Frontend consumers normalize missing slots to `[]`, so auto/category route forms do not crash when the user has not opened the constructor.
- Slot plan test contract now includes explicit `slot_id`, `category`, `duration`, and `selected_place_id` fields.

## CITYGO-167

Completed now:

- Active route session uses existing persistent tables instead of local-only frontend state.
- Public start/action endpoints are exposed under `/v1/user-routes`.
- Frontend active route controls call backend session APIs.
- Tests cover session start, complete point, pause, and finish.

Main files:

- `models/route_session.py`
- `services/user_route_session_service.py`
- `routers/user_routes.py`
- `frontend/src/widgets/recommendation-route/RouteResultPanel.tsx`
- `tests/test_user_route_slot_session_and_import_repair.py`

## Related stabilization outside 163/166/167

- Route quality thresholds are documented in `docs/product/route_quality_engine.md`.
- Production route smoke contract is documented in `docs/ops/production_route_smoke.md`.
- Mobile route result UX is documented in `docs/product/mobile_route_ux.md`.
- Auto-repair job status contract is documented in `docs/product/place_data_quality_auto_repair.md`.

## CI policy

No workflow trigger was changed. `00 · CITY GO · CI` remains manual-only through `workflow_dispatch`.
