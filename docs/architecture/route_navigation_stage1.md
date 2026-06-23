# Route Navigation Stage 1

Stage 1 adds a usable route player for public route detail pages and a backend route-session foundation. The current web UI still uses frontend local state, but the backend now has persisted sessions that the next frontend pass can attach to.

## Scope

Implemented in the public route detail UI:

- Public route detail renders the route navigation player instead of a plain point list.
- Interactive OSM raster-tile map without an extra npm dependency.
- Route polyline, numbered route markers, current point highlighting, visited point state, and user location marker.
- Browser geolocation via `navigator.geolocation.watchPosition`.
- GPS permission/error states and manual fallback when geolocation is denied or unavailable.
- Distance from the last known user position to the current route point.
- Manual state machine: `not_started`, `active`, `completed`.
- Controls: `Начать маршрут`, `Я на месте`, `Следующая`, `Обновить GPS`, `Открыть навигатор`, `Завершить`, `Пройти заново`.
- Persistence in `localStorage` by route id.
- Frontend quality gates before points are allowed into navigation.
- Backend route detail exposes read-only point fields needed by the player.

Implemented in backend session foundation:

- `route_sessions` table.
- `route_session_points` table.
- API to start, read, pause/resume/abandon, check in points, and complete a route session.
- Backend quality gate before points are copied into a session.
- Service-category filtering for route session points.

Not implemented yet:

- Frontend connection to backend route sessions.
- OSRM/walking geometry.
- Off-route detection.
- Voice guidance.
- Offline route package.
- Dedicated MapLibre/vector-tile renderer. Current implementation uses OSM raster tiles as the browser-native MVP map.

## Files

Frontend model:

```text
frontend/src/features/route-navigation/model/types.ts
frontend/src/features/route-navigation/model/state.ts
frontend/src/features/route-navigation/model/storage.ts
frontend/src/features/route-navigation/model/qualityGate.ts
frontend/src/features/route-navigation/model/geo.ts
frontend/src/features/route-navigation/model/useRouteGeolocation.ts
```

Frontend widgets:

```text
frontend/src/widgets/route-navigation/RouteNavigationView.tsx
frontend/src/widgets/route-navigation/RouteNavigationPanel.tsx
frontend/src/widgets/route-navigation/RouteMapPreview.tsx
frontend/src/widgets/route-navigation/RoutePointCard.tsx
frontend/src/widgets/route-navigation/RoutePointMarkers.tsx
frontend/src/widgets/route-navigation/RoutePolyline.tsx
frontend/src/widgets/route-navigation/RouteProgress.tsx
frontend/src/widgets/route-navigation/RouteQualityNotice.tsx
frontend/src/widgets/route-navigation/routeMapMath.ts
```

Page integration:

```text
frontend/src/pages/routes/RouteDetailPage.tsx
frontend/src/pages/routes/RouteDetailPage.css
frontend/src/api/routes/routes.api.ts
```

Backend route detail fields:

```text
schemas/route.py
services/route_service.py
```

Backend route sessions:

```text
models/route_session.py
schemas/route_session.py
services/route_session_service.py
routers/route_sessions.py
migrations/versions/9d0e1f2a3b4c_add_route_sessions.py
```

Tests:

```text
frontend/src/features/route-navigation/model/routeNavigationState_new.test.ts
frontend/src/features/route-navigation/model/routeQualityGate_new.test.ts
frontend/src/widgets/route-navigation/RouteNavigationView_new.test.tsx
tests/test_route_detail_navigation_fields_new.py
tests/test_route_sessions_new.py
```

## Route Detail Data Contract

The public route detail response exposes read-only point fields required by the player:

- `lat`
- `lng`
- `category`
- `address`
- `is_published`
- `is_route_eligible`
- `publication_status`
- `is_active`
- `status`

## Route Session API

Start a persisted session for an editorial route:

```http
POST /routes/{route_id}/sessions
```

Payload:

```json
{
  "user_key": "web:anonymous-or-user-id"
}
```

Read session:

```http
GET /route-sessions/{session_id}
```

Patch session state:

```http
PATCH /route-sessions/{session_id}
```

Payload examples:

```json
{ "status": "paused" }
{ "status": "active", "current_point_index": 1 }
{ "status": "abandoned" }
```

Check in or skip a point:

```http
POST /route-sessions/{session_id}/events/checkin
```

Payload:

```json
{ "point_index": 0, "action": "visit" }
```

or:

```json
{ "point_index": 0, "action": "skip" }
```

Complete session:

```http
POST /route-sessions/{session_id}/complete
```

## State Persistence

Current web UI storage key:

```text
citygo:route-navigation:{routeId}
```

Persisted frontend state remains intentionally lightweight until the UI is connected to backend sessions:

- route id;
- current point index;
- visited point ids/indexes;
- route status.

If stored state is incompatible with the current route points, the frontend should degrade safely instead of blocking the route page.

## Map and Geolocation

The current frontend map uses OSM raster tiles rendered inside the route player. It supports:

- route-fit camera;
- manual pan;
- zoom in/out;
- recenter to route;
- recenter/request user location;
- route polyline overlay;
- route point markers;
- current user marker with accuracy circle;
- distance calculation to the active route point through Haversine.

Geolocation is requested only from explicit user actions: starting the route, pressing `Я на карте`, or pressing `Обновить GPS`. If the browser denies or cannot provide GPS, the player remains usable in manual mode.

## Quality Gate

Frontend and backend session creation both filter navigation points.

Blockers:

- missing place id;
- missing coordinates;
- hidden/unpublished/inactive places;
- `is_route_eligible=false`;
- invalid publication status;
- service categories such as `pharmacy`, `bank`, `police`, `parking`, `fuel`, `transport`, `service`.

If fewer than two valid points remain, route start is disabled in UI and backend session start returns `409 route_has_less_than_two_eligible_points`.

## UX Rules

- Route page must remain useful even if navigation cannot start.
- Start button must be disabled with a clear reason when quality gate fails.
- User can always reset and walk again.
- The route player must not show a fake schematic when coordinates are available; it should render the map layer, route line, route markers, and GPS state.
- Geolocation failure must degrade to manual navigation, not block route progress.

## Verification

Targeted frontend tests:

```bash
npm --prefix frontend run test -- routeNavigation routeQualityGate
```

Targeted backend tests:

```bash
.venv/bin/python -m pytest --no-cov tests/test_route_detail_navigation_fields_new.py tests/test_route_sessions_new.py -q
```

Frontend build checks:

```bash
npm --prefix frontend run lint
npm --prefix frontend run build
```
