# City Go — статус реализации и следующие шаги

Дата ревизии: 2026-06-06.

Этот документ — короткий рабочий срез. Главный source of truth: [`master_technical_spec.md`](master_technical_spec.md). Карта документов: [`README.md`](README.md).

---

## 1. Реализовано

### Backend core

- FastAPI application.
- Env config.
- CORS.
- `/health`.
- `/ready` с DB readiness.
- JSON request logging middleware.
- PostgreSQL / SQLAlchemy / Alembic foundation.
- Router setup через `core/router_setup.py`.
- Release scripts, backup/restore, release checklist.
- Backend quality gate.

### Catalog / discovery

- Cities.
- Categories.
- Tags.
- Places.
- Place tags.
- Place schedules / opening hours.
- Collections.
- Editorial routes.
- Route places.
- Nearby endpoint.
- Open-now endpoint.
- Place search / taxonomy / diagnostics.

### Data import / quality / verification

- Seed import dry-run / real import.
- Place seed validation.
- Import logs.
- Place coverage endpoint.
- Production import wrapper.
- OSM data scripts.
- Image enrichment scripts and validation.
- Place data quality fields.
- Place existence confidence fields.
- Place verification fields.
- Place verification queue/admin endpoints.
- Optional verification scheduler.
- City expansion/import-state groundwork.

### Route layers

Реализованы три route-слоя:

1. **Editorial routes** — `GET /routes/...`.
2. **Legacy itinerary** — `POST /routes/generate`, `POST /routes/replan`.
3. **Product route layer** — `POST /v1/user-routes/build`, `POST /v1/user-routes/correct`, поверх `POST /v1/recommendations/route`.

Recommendation pipeline реализует:
- context merge;
- candidate retrieval;
- validation/hard filters;
- scoring;
- route assembly;
- time-aware logic;
- budget fit;
- warnings;
- quality score / breakdown;
- explanation;
- route analytics;
- user profile from signals.

User route correction поддерживает:
- remove place;
- shorten route;
- rebuild from here;
- avoid category;
- extend route.

### User signals / lightweight personalization

- `POST /user-signals/`.
- `GET /user-signals/{user_id}/summary`.
- `GET /user-signals/{user_id}/profile`.
- Derived profile по сигналам.
- Route scoring может учитывать user_id/profile.

### Telegram bot

- `/start`, `/help`, `/health`.
- City selection.
- Context store.
- Location handling.
- Address handling.
- Route build.
- Route correction.
- Nearby/open-now/coffee/food/walk/dog-friendly scenarios.
- Free text intent layer.
- Backend API clients.
- Friendly errors and structured event logs.

### Frontend

- Vite/React foundation.
- Pages:
  - Home;
  - Places list;
  - Place detail;
  - Open now;
  - Nearby;
  - Routes list;
  - Generate route;
  - Route detail;
  - Admin photo review;
  - Legacy walk route.
- Demo mode.
- Local demo catalog.
- Place cards.
- Route result UI.
- Route warnings/quality badges.
- `extend_route` correction action in UI/demo mode.
- Photo status handling.

### DB-backed route/place UI contract

- Public catalog, nearby, open-now and route points now use the same approved
  public image policy.
- Legacy `places.image_url` is no longer exposed as a route photo; route points
  use approved/active `place_images` only.
- Route request form sends `time_of_day`, so daytime routes are not filtered as
  if the user requested the current night-time window.
- Route request supports `route_time_mode`; default `flexible` prevents current
  clock-based `closed_now` from collapsing planned/flexible routes.
- Route responses distinguish `ready`, `partial_route` and `no_route`; frontend
  renders partial/no-route states explicitly.
- Route quality includes completeness penalty, so one-point routes are not rated
  as excellent routes.
- Route points include `city_slug`; frontend guards against cross-city route
  rendering.
- Backend route build was smoke-tested against the local DB:
  `/v1/user-routes/build` returns a ready route for `zelenogradsk`.
- Current Zelenogradsk image status: no approved/active `place_images` exist for
  the city, so `image_url: null` is the correct API result until the image
  import/review pipeline publishes photos.

---

## 2. Частично реализовано

### Route engine

Есть работающий route builder и correction layer, но ещё нет полноценного active route session.

Осталось:
- partial tail rebuild;
- visited/skipped/current position handling;
- active route state;
- correction history;
- smarter route recovery;
- smart detours.

### Start context

Есть:
- geolocation/current location;
- `place_id`;
- legacy lat/lng;
- city anchor fallback.

Осталось:
- typed address geocoding;
- selected map point UI;
- reverse geocoding;
- routing provider/polyline.

### Personalization

Есть:
- user signals;
- derived profile;
- route scoring personalization.

Осталось:
- auth;
- users/identity model;
- personal account;
- favorites/history UI;
- decay;
- tags affinity;
- post-route feedback.

### Data governance

Есть:
- quality fields;
- verification queue;
- confidence/status fields.
- public image contract for user-facing payloads.

Осталось:
- source conflict resolution;
- rollback/revert;
- full audit/history workflow;
- freshness/confidence badges everywhere;
- operational recheck process in production.
- production image import/review for Zelenogradsk places.

---

## 3. Не реализовано

- Map foundation.
- Map point selection.
- Geocoding/reverse geocoding.
- Routing provider/polyline engine.
- Active Route Session.
- Live Route Editing as stateful session.
- Route Recovery.
- Smart Detours.
- Weather-aware rebuild.
- Login/Register.
- Personal account.
- Payments/subscriptions/entitlements.
- Telegram account linking.
- Business owner claim/dashboard.
- Social/community.
- Gamification.
- Next destination / travel planning across cities.
- Semantic vector search.
- Full LLM orchestration.

---

## 4. Документация после ревизии

Оставлены как основные:
- `docs/README.md`;
- `docs/master_technical_spec.md`;
- `docs/implementation_status_and_next_steps.md`;
- `docs/route_generation_status_and_roadmap.md`;
- `docs/architecture/application_architecture_ru.md`;
- `docs/architecture/backend_file_map.md`.

Перенесены в архив:
- `docs/archive/technical_spec.md`;
- `docs/archive/project_status.md`;
- `docs/archive/project_structure.md`.

Причина: эти документы дублировали или искажали актуальный статус.

---

## 5. Ближайший порядок работ

### P0 — привести route flow к одному продуктово-понятному контуру

1. Зафиксировать `POST /v1/user-routes/build` как основной route build endpoint для web/Telegram.
2. Зафиксировать `POST /v1/user-routes/correct` как основной correction endpoint.
3. Legacy `/routes/generate` и `/routes/replan` оставить, но не развивать как главный слой.
4. Проверить frontend и Telegram, что они ходят в нужный слой.

### P0 — старт маршрута

1. Добавить geocoding для typed address.
2. Добавить selected map point на frontend.
3. Передавать координаты выбранной точки в route build.
4. Показывать warning, если старт fallback на city center.

### P1 — Active Route Session

1. Ввести active route session model/API.
2. Хранить current route state.
3. Хранить visited/skipped places.
4. Хранить remaining time/current position.
5. Делать partial tail rebuild.

### P1 — Live Route Editing

1. Add place.
2. Remove place.
3. Skip current place.
4. Replace place.
5. Shorten route.
6. Extend route.
7. Rebuild from current position.

### P1 — Product UI

1. Map foundation.
2. Route timeline.
3. Route correction history.
4. Clear warnings/explanations.
5. Better route quality explanation.

### P2 — Personalization foundation

1. Auth/users.
2. Personal account.
3. Favorites/history/completed routes.
4. Better profile derivation.
5. Feedback after route.

### P2 — Production readiness

1. Live data refresh process.
2. Staging smoke.
3. Route quality metrics.
4. Import quality metrics.
5. Coverage gates per city.

---

## 6. Не делать сейчас

- Payments.
- Business owner dashboard.
- Social/community.
- Gamification.
- Full mobile app.
- Booking engine.
- Next destination planning.
- Full semantic/vector search.
