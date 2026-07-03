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

## CI policy

No workflow trigger was changed. `00 · CITY GO · CI` remains manual-only through `workflow_dispatch`.
