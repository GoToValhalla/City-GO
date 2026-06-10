# City Go — Route Generation Status & Roadmap

Дата ревизии: 2026-06-06.

Этот документ фиксирует актуальную карту маршрутов. Главный вывод ревизии: в проекте есть три разных route-слоя, и для новой продуктовой разработки главным должен быть `user-routes` + recommendation pipeline, а не legacy itinerary.

---

## 1. Route-слои

### 1.1. Editorial routes

Назначение: готовые маршруты из БД.

Endpoints:
- `GET /routes/`;
- `GET /routes/{route_id}`;
- `GET /routes/by-slug/{slug}`;
- `GET /route-places/`.

Использовать для:
- curated routes;
- showcase;
- fallback;
- route detail pages.

Не использовать как персональный route builder.

### 1.2. Legacy itinerary

Endpoints:
- `POST /routes/generate`;
- `POST /routes/replan`.

Файлы:
- `routers/itinerary.py`;
- `schemas/itinerary.py`;
- `schemas/itinerary_replan.py`;
- `services/itinerary_*`;
- `services/start_context_resolver.py`.

Статус: реализовано, но legacy.

Что умеет:
- text parser;
- базовые constraints;
- time mode/time budget;
- start context;
- candidate retrieval;
- soft scoring;
- ordered route;
- duration/distance estimation;
- базовый replan.

Ограничения:
- не главный SoT для дальнейшей route-разработки;
- address без geocoding;
- нет map point selection;
- нет active session;
- нет полноценного live editing.

### 1.3. Recommendation pipeline

Canonical endpoint:
- `POST /v1/recommendations/route`.

Legacy alias:
- `POST /recommendations/route`.

Файлы:
- `routers/recommendations.py`;
- `schemas/recommendation_route.py`;
- `services/route_builder_service.py`;
- `services/explainability_service.py`;
- `services/recommendation_route_serializer.py`;
- `services/route_*`.

Статус: реализовано.

Что умеет:
- context merge;
- candidate retrieval;
- validation;
- hard filters;
- scoring;
- route assembly;
- time-aware logic;
- budget fit;
- warnings;
- quality score;
- explanation;
- analytics;
- user profile from signals.

### 1.4. User route layer

Endpoints:
- `POST /v1/user-routes/build`;
- `POST /v1/user-routes/correct`.

Файлы:
- `routers/user_routes.py`;
- `schemas/user_route.py`;
- `services/user_route_build_service.py`;
- `services/user_route_correct_service.py`;
- `services/user_route_*`.

Статус: реализовано как stateless product route layer.

Correction actions:
- `remove_place`;
- `shorten_route`;
- `rebuild_from_here`;
- `avoid_category`;
- `extend_route`.

Это основной кандидат на главный продуктовый route flow для web/Telegram.

---

## 2. Поддерживаемые стартовые сценарии

### Реализовано

1. Start from current location / geo coordinates.
2. Start from place_id.
3. Start from legacy lat/lng.
4. Fallback to city anchor.

### Частично

1. Typed address — поле принимается/сохраняется как raw address, но координаты не вычисляются.

### Не реализовано

1. Map point selection.
2. Geocoding.
3. Reverse geocoding.
4. Routing provider.
5. Route polyline rendering.

---

## 3. Что уже работает в route logic

- Candidate retrieval from DB.
- Public visibility filters.
- Hard filters for invalid/closed/inactive/no-coordinate/excluded places.
- Soft scoring.
- Semantic-ish interests mapping.
- Category diversity.
- Time budget handling.
- Time-aware opening checks.
- Budget trim/subset handling.
- Route warnings.
- User-facing warning objects.
- Quality score / breakdown.
- Explanation summary/points/warnings/data limitations.
- Route analytics.
- Basic correction actions.
- Telegram route build/correction client flow.
- Frontend route result and correction action for `extend_route`.

---

## 4. Что ещё не сделано

### 4.1. Start / map

- Address geocoding.
- Selected map point.
- Map renderer.
- Tiles/provider decision.
- Routing provider/polyline.

### 4.2. Active Route Session

Нужно сделать маршрут активной сессией, а не просто JSON-ответом.

Нужно хранить:
- active_route_id;
- user_id/session_id;
- current route state;
- current position;
- visited places;
- skipped places;
- remaining time;
- current step;
- warnings;
- correction history.

### 4.3. Live Route Editing

Нужно реализовать stateful действия:
- add place;
- remove place;
- skip current place;
- replace place;
- shorten route;
- extend route;
- rebuild rest from current position.

Ключевое требование: не пересобирать весь маршрут без необходимости. Предпочтительно делать partial tail rebuild.

### 4.4. Route Recovery

Нужно:
- определить, что пользователь отклонился от маршрута;
- предложить вернуться;
- перестроить остаток;
- пропустить текущую точку;
- пересчитать remaining route.

### 4.5. Smart Detours

Нужно:
- предложить кафе/точку/укрытие/видовую точку рядом;
- учитывать текущую позицию;
- учитывать оставшееся время;
- не ломать основной сценарий маршрута.

### 4.6. Route Personalization

Нужно:
- учитывать часто пропускаемые категории;
- учитывать предпочитаемый темп;
- учитывать интересы;
- учитывать completed route feedback;
- применять decay и tags affinity.

---

## 5. Приоритетный roadmap

### P0 — стабилизировать главный route flow

1. Принять `POST /v1/user-routes/build` как основной route build endpoint.
2. Принять `POST /v1/user-routes/correct` как основной correction endpoint.
3. Проверить, что frontend/Telegram используют правильный слой.
4. Legacy `/routes/generate` оставить без активного развития.

### P0 — закрыть стартовые кейсы

1. Current geolocation — уже есть, проверить сквозной UI/Telegram flow.
2. Address — добавить geocoding.
3. Selected map point — добавить map UI и передачу координат.
4. Place card start — использовать `place_id` или координаты места.
5. City fallback — показывать warning.

### P1 — Active Route Session

1. Добавить session schema/model/service.
2. Добавить endpoints для start/get/update/end session.
3. Хранить visited/skipped/current position.
4. Делать partial tail rebuild.

### P1 — Live Route Editing

1. Расширить correction contract под active session.
2. Добавить skip/replace/add nearby.
3. Перестраивать только хвост маршрута.
4. Отдать понятные warnings/explanation.

### P1 — Map UX

1. Выбор точки старта на карте.
2. Отображение точек маршрута.
3. Timeline рядом с картой.
4. Позже — polyline provider.

### P2 — Recovery / Detours / Personalization

1. Route recovery.
2. Smart detours.
3. Route personalization.
4. Weather-aware rebuild.
5. End route summary.

---

## 6. Что не делать сейчас

- Не переписывать весь route builder с нуля.
- Не удалять legacy itinerary без отдельного решения.
- Не строить full map/routing provider раньше выбора provider.
- Не начинать social/gamification/payments до стабилизации route/session слоя.
