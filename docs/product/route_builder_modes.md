# CITYGO-165/166/167 · Route Builder Modes and Active Session

## Manual Route Builder

Implemented production path:

- Existing backend route edit endpoints are used from the frontend:
  - `POST /v1/user-routes/{route_id}/update` for ordering;
  - `POST /v1/user-routes/{route_id}/add-place` for adding catalog candidates;
  - `POST /v1/user-routes/{route_id}/replace-place` for replacing a point;
  - `POST /v1/user-routes/correct` with `target_place_id` for remove/replace-like correction.
- `frontend/src/api/recommendations/recommendationRoute.api.ts` exposes `updateUserRouteOrder`, targeted `correctUserRoute`, and replacement calls.
- `RoutePointList.tsx` exposes compact actions: move up/down, replace, remove.
- `GenerateRoutePage.tsx` wires add, remove, replace, and reorder to existing backend services.

## Slot / Constructor Builder

Implemented production path:

- Frontend visible slot editor is implemented in `frontend/src/widgets/recommendation-route/RouteSlotBuilder.tsx`.
- User can:
  - add a slot;
  - choose slot type/category;
  - mark slot required/optional;
  - set optional duration;
  - request candidate options for every slot;
  - select a concrete place for a slot;
  - clear/replace selected place;
  - build a route by scenario order.
- Backend slot build path is implemented in `services/user_route_slot_build_service.py`.
- `UserRouteBuildService` routes `build_mode=constructor` to the slot service instead of treating slots as generic interests.
- Slot matching preserves order and uses selected places first; fallback is limited to related categories.
- If a required slot cannot be filled, the route is returned as honest `partial_route` with slot match explanation.
- Frontend request normalization treats `routeSlots` as optional for non-constructor modes. Empty/missing slots no longer crash auto/category route build forms.

## Active Route Session

Implemented persistent backend path:

- Existing ORM tables are used:
  - `models.route_session.RouteSession`;
  - `models.route_session.RouteSessionPoint`.
- Public endpoints:
  - `POST /v1/user-routes/{route_id}/session/start`;
  - `POST /v1/user-routes/sessions/{session_id}/action`.
- Supported actions:
  - `complete_point`;
  - `skip_point`;
  - `pause`;
  - `resume`;
  - `finish`;
  - `abandon`;
  - `remove_point`.
- Frontend `RouteResultPanel.tsx` calls backend session APIs instead of storing active walk only in local component state.
- UI shows current point, next point, session status, and action result.

## Tests

- `tests/test_user_route_slot_session_and_import_repair.py` covers:
  - ordered slot route build;
  - partial route when required slot cannot be filled;
  - persistent active route session transitions.
- Frontend normalization is protected by recommendation route form tests and by optional slot handling in `RouteRequestForm`, `RouteSlotBuilder`, and `GenerateRoutePage`.

## CI stabilization note

CI #2031 exposed that non-constructor forms could still call route request normalization with missing `routeSlots`. The production contract is now: `routeSlots` is optional unless `build_mode=constructor`; all UI consumers must normalize missing slots to `[]` before counting or flattening.
