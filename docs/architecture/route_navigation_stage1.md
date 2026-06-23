# Route Navigation Stage 1

Stage 1 adds a frontend-only route player for public route detail pages. It is already merged into `main` and deployed as the first usable route navigation experience.

## Scope

Implemented:

- Public route detail renders the route navigation player instead of a plain point list.
- Deterministic SVG/HTML route schematic with numbered points and straight polyline segments.
- Current point highlighting.
- Visited point state.
- Manual state machine: `not_started`, `active`, `completed`.
- Controls: `Начать маршрут`, `Я на месте`, `Следующая`, `Завершить`, `Пройти заново`.
- Persistence in `localStorage` by route id.
- Frontend quality gates before points are allowed into navigation.
- Backend route detail exposes read-only point fields needed by the player.

Not implemented in Stage 1:

- MapLibre renderer.
- GPS/current user location.
- OSRM/walking geometry.
- Backend route sessions/history.
- Off-route detection.
- Voice guidance.
- Offline route package.

## Files

Frontend model:

```text
frontend/src/features/route-navigation/model/types.ts
frontend/src/features/route-navigation/model/state.ts
frontend/src/features/route-navigation/model/storage.ts
frontend/src/features/route-navigation/model/qualityGate.ts
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

Backend response fields:

```text
schemas/route.py
services/route_service.py
```

Tests:

```text
frontend/src/features/route-navigation/model/routeNavigationState_new.test.ts
frontend/src/features/route-navigation/model/routeQualityGate_new.test.ts
frontend/src/widgets/route-navigation/RouteNavigationView_new.test.tsx
tests/test_route_detail_navigation_fields_new.py
```

## Data Contract

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

No backend route session or tracking table is created in Stage 1. The frontend owns the navigation state.

## State Persistence

Storage key:

```text
citygo:route-navigation:{routeId}
```

Persisted state is intentionally lightweight:

- route id;
- current point index;
- visited point ids/indexes;
- route status.

If stored state is incompatible with the current route points, the frontend should degrade safely instead of blocking the route page.

## Quality Gate

The frontend filters navigation points before rendering markers:

- missing place id;
- missing coordinates;
- hidden/unpublished/inactive places;
- `is_route_eligible=false`;
- invalid publication status;
- service categories such as `pharmacy`, `bank`, `police`, `parking`, `fuel`, `transport`, `service`.

If fewer than two valid points remain, route start is disabled and the UI explains the blockers.

## UX Rules

- Route page must remain useful even if navigation cannot start.
- Start button must be disabled with a clear reason when quality gate fails.
- User can always reset and walk again.
- The schematic is a temporary renderer; do not add complex map-specific behavior to it. Put map behavior into Stage 2 MapLibre components.

## Verification

Targeted frontend tests:

```bash
npm --prefix frontend run test -- routeNavigation routeQualityGate
```

Targeted backend test:

```bash
.venv/bin/python -m pytest --no-cov tests/test_route_detail_navigation_fields_new.py -q
```

Full frontend guard:

```bash
npm --prefix frontend run lint
npm --prefix frontend run test:ci
npm --prefix frontend run build
```

## Stage 2 Candidates

- Replace SVG renderer internals with MapLibre.
- Add optional GPS current position.
- Add user location marker and recenter control.
- Add route camera modes: overview, follow user, point focus, free pan.
- Add OSRM/polyline walking geometry with straight-line fallback.
- Persist user route sessions on backend.
- Add off-route detection and recovery CTA.
- Add offline/text-only route fallback.
