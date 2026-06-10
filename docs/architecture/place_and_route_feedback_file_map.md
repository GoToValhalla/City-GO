# City Go — place/photo verification and route feedback files

## Backend

| File | Responsibility |
|------|----------------|
| `services/geocoding_service.py` | Sync Geoapify client for typed route start address. Returns `GeoPoint` or `None` without breaking route build. |
| `services/user_route_build_service.py` | Resolves typed `start_address` before calling `RouteBuilderService`. Keeps fallback to client coordinates. |
| `schemas/user_route.py` | User route request/response contract. Includes start context fields used by web and Telegram clients. |
| `schemas/recommendation_route.py` | Recommendation route request/response contract. Mirrors start context for canonical recommendation endpoint. |
| `schemas/route_feedback.py` | Request/response schemas for route rating from UI and Telegram. |
| `routers/route_feedback.py` | Stores route rating as `UserSignal(signal_type='route_feedback')`. |
| `services/place_public_image_service.py` | Selects public image and returns image confidence metadata. |
| `services/place_read_service.py` | Adds public photo metadata and confidence fields to `PlaceRead`. |
| `services/place_public_visibility.py` | Hides technical categories and known non-tourist titles from public catalog, Telegram, open-now and route candidate queries. |
| `routers/place_verification.py` | Admin endpoints for confirming whether a place exists, is closed, not found, moved, duplicated or needs recheck. |
| `data/scripts/cleanup_bad_places.py` | Dry-run-first cleanup script for technical/non-tourist places that should not be public catalog items. |

## Frontend

| File | Responsibility |
|------|----------------|
| `frontend/src/pages/places/PlaceDetailPage.tsx` | Shows photo/place confidence and local review buttons for photo/place checks. |
| `frontend/src/entities/place/model/types.ts` | Frontend place contract with image and place confidence metadata. |
| `frontend/src/api/recommendations/recommendationRoute.api.ts` | Calls route build/correction and sends route feedback. |
| `frontend/src/widgets/recommendation-route/RouteResultPanel.tsx` | Shows route rating buttons and sends feedback. |
| `frontend/src/features/routes/model/recommendationRouteForm.ts` | Builds route request with start context. |
| `frontend/src/widgets/recommendation-route/RouteRequestForm.tsx` | Allows current geolocation or typed address as route start. |

## Tests

| File | Coverage |
|------|----------|
| `tests/test_route_feedback_new.py` | POST `/route-feedback/`: stores signal and validates rating bounds. |
| `tests/test_geocoding_service_new.py` | Geoapify parsing and missing-key fallback. |
| `tests/test_cleanup_bad_places_new.py` | Detection of technical/non-tourist places before hiding them. |
| `tests/test_user_route_start_context_new.py` | `UserRouteBuildRequest` accepts typed address and geolocation start sources. |

## Local verification commands

```bash
python -m compileall models schemas services routers data/scripts
python -m pytest tests/test_route_feedback_new.py tests/test_geocoding_service_new.py tests/test_cleanup_bad_places_new.py tests/test_user_route_start_context_new.py -q
```
