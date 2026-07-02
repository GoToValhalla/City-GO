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

Implemented contract layer:

- Frontend route slot type includes:
  - `slot_id`;
  - `type` / `category`;
  - `required`;
  - `duration`;
  - `selected_place_id`.
- Existing backend `RouteBuilderV2` already has slot mode and structured slot options endpoints; this pass keeps the production path instead of duplicating a new builder.

## Active Route Session

Implemented frontend-safe active walk layer in `RouteResultPanel.tsx`:

- statuses: `planned`, `active`, `paused`, `completed`, `abandoned` contract documented; current UI uses planned/active/paused/completed;
- current point and next point are shown;
- actions: `Начать маршрут`, `Я на месте`, `Пропустить`, `Пауза/Продолжить`, `Завершить маршрут`;
- timestamps are stored in local component state.

## Remaining

- Backend persistence for active route sessions is not added in this pass. Current active session is local frontend state by design, because no existing persistent session table was identified in the route layer during this pass.
- Slot builder needs a dedicated visible slot editor UI beyond the contract layer and existing structured backend endpoints.
