# MASTER TECHNICAL SPEC — City Go

Дата ревизии: 2026-06-06.

Этот документ — главный source of truth по продукту и техническому устройству City Go. Старые краткие документы `technical_spec.md` и `project_status.md` перенесены в `docs/archive/`.

---

## 1. Цель продукта

City Go — recommendation-driven city/travel platform, которая начинается как городской гид по Зеленоградску и постепенно развивается в персональный travel assistant.

Ближайшая цель продукта:
- быстро подобрать места;
- показать, что рядом;
- показать, что открыто сейчас;
- собрать маршрут под интересы, время, бюджет и стартовую точку;
- честно показывать ограничения данных: freshness, confidence, warnings;
- работать в web и Telegram как разные поверхности одного backend-ядра.

Стратегическая цель:
- персонализированные маршруты;
- active route session;
- live editing маршрута на ходу;
- route recovery;
- smart detours;
- route personalization;
- позже: payments, business owner flow, social/community, gamification, travel planning between cities.

---

## 2. Главные принципы

1. **БД — источник правды.** AI и route builder не имеют права выдумывать места, адреса, расписания, маршруты или факты.
2. **Quality over coverage.** Лучше меньше точек, но честнее и полезнее.
3. **No fake certainty.** UI/API должны показывать warnings, confidence и data limitations.
4. **One core, multiple surfaces.** Web, Telegram и будущий mobile используют одно backend-ядро, но разные UX-сценарии.
5. **Route product layer first.** Новую разработку маршрутов вести через `user-routes` + recommendation pipeline, а не через legacy itinerary.
6. **Legacy не удалять без решения.** Старый itinerary-слой остаётся как историческая база и fallback/testing area.

---

## 3. Текущее состояние по фактическому коду

### 3.1. Backend core — реализовано

Есть:
- FastAPI application;
- env config;
- CORS;
- `/health`;
- `/ready` с DB readiness;
- JSON request logging middleware;
- PostgreSQL / SQLAlchemy / Alembic foundation;
- router setup через `core/router_setup.py`;
- release scripts;
- backup/restore scripts;
- backend quality gate.

### 3.2. Core catalog modules — реализовано

Есть backend API и модели для:
- cities;
- categories;
- tags;
- places;
- place tags;
- schedules/opening hours;
- collections;
- collection places;
- editorial routes;
- route places.

Основные сценарии:
- `GET /cities/`, `/cities/{city_id}`, `/cities/by-slug/{slug}`;
- `GET /categories/`, `/categories/{category_id}`, `/categories/by-code/{code}`;
- `GET /tags/`, `/tags/{tag_id}`, `/tags/by-code/{code}`;
- `GET /places/`, `/places/{place_id}`, `/places/by-slug/{slug}`;
- `GET /collections/`, `/collections/{collection_id}`, `/collections/by-slug/{slug}`;
- `GET /routes/`, `/routes/{route_id}`, `/routes/by-slug/{slug}`;
- `GET /nearby/`;
- `GET /open-now/`.

### 3.3. Data quality / verification — частично реализовано

В `places` реализованы поля:
- `source`;
- `source_url`;
- `confidence`;
- `last_verified_at`;
- `status`;
- `existence_confidence_score`;
- `existence_confidence_level`;
- `verification_status`;
- `verification_source`;
- `verification_method`;
- `verified_at`;
- `verified_by`;
- `needs_recheck_at`;
- `verification_comment`.

Есть place verification API, queue/admin endpoints, recheck flow и optional scheduler.

Ещё не закрыто полностью:
- conflict resolution между источниками;
- rollback/revert плохих обновлений;
- полноценный data governance workflow;
- отображение freshness/confidence во всех UI-поверхностях;
- единая source confidence policy для всех типов данных.

### 3.4. City/data pipeline — частично реализовано

Есть:
- OSM/import scripts;
- place seed dry-run/import;
- validation tooling;
- place coverage endpoint;
- production import wrapper;
- image enrichment scripts;
- city expansion/import-state groundwork.

Ещё нужно:
- прогонять live import/refresh в production/staging;
- довести Зеленоградск до стабильного coverage gate;
- расширять editorial coverage для прогулок/парков/кофе/еды/культуры/family/dog-friendly;
- настроить регулярный refresh/reverification в окружении.

---

## 4. Route architecture — важное разделение

В проекте сейчас три route-слоя.

### 4.1. Editorial routes

Назначение: готовые маршруты из БД.

Endpoints:
- `GET /routes/`;
- `GET /routes/{route_id}`;
- `GET /routes/by-slug/{slug}`;
- `GET /route-places/`.

Статус: реализовано.

Использовать для:
- curated маршрутов;
- showcase;
- fallback;
- route detail pages.

Не использовать как ядро персонального route builder.

### 4.2. Legacy itinerary layer

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

Умеет:
- query parsing;
- базовые constraints;
- start context;
- candidate retrieval;
- soft scoring;
- ordered route;
- time/distance estimation;
- basic replan.

Ограничения:
- не главный source of truth для новой route-разработки;
- address хранится как `raw_address`, но не геокодится;
- нет map point selection;
- нет active route session;
- нет полноценного live editing.

### 4.3. Recommendation pipeline

Canonical endpoint:
- `POST /v1/recommendations/route`.

Legacy alias:
- `POST /recommendations/route` с deprecation headers.

Файлы:
- `routers/recommendations.py`;
- `schemas/recommendation_route.py`;
- `services/route_builder_service.py`;
- `services/explainability_service.py`;
- `services/recommendation_route_serializer.py`;
- `services/route_*`.

Статус: реализовано.

Умеет:
- context merge;
- candidate retrieval;
- validation/hard filters;
- scoring;
- route assembly;
- time-aware layer;
- budget-fit;
- warnings;
- quality score / breakdown;
- explanation;
- route analytics;
- user signal profile boost.

### 4.4. User route layer — текущий продуктовый приоритет

Endpoints:
- `POST /v1/user-routes/build`;
- `POST /v1/user-routes/correct`.

Файлы:
- `routers/user_routes.py`;
- `schemas/user_route.py`;
- `services/user_route_build_service.py`;
- `services/user_route_correct_service.py`;
- `services/user_route_*`.

Статус: реализовано как stateless route state/correction layer.

Correction actions:
- `remove_place`;
- `shorten_route`;
- `rebuild_from_here`;
- `avoid_category`;
- `extend_route`.

Следующий шаг по маршрутам:
- сделать Active Route Session;
- добавить partial tail rebuild;
- учитывать visited/skipped/current position/remaining time;
- развить Live Route Editing поверх этого слоя.

---

## 5. Start context и построение маршрута

Поддерживаемые сейчас источники:
- `place_id`;
- device geo/current location;
- legacy `lat/lng`;
- city anchor fallback.

Частично/не реализовано:
- typed address без координат — пока не geocoding, только raw address;
- selected map point — нет map UI/provider foundation;
- reverse geocoding — нет;
- routing provider/polyline — нет.

Планируемые стартовые сценарии:
1. Пользователь дал геолокацию — строим от неё.
2. Пользователь указал адрес — нужен geocoding → координаты → route build.
3. Пользователь выбрал точку на карте — frontend передаёт координаты → route build.
4. Пользователь выбрал place из каталога — route build от `place_id`.
5. Пользователь не дал старт — fallback на city center с warning.
6. Пользователь уже в active route — rebuild от current position, а не от старта.

---

## 6. Frontend

Статус: реализована product UI foundation.

Есть страницы:
- `/` Home;
- `/places` Places list;
- `/places/:slug` Place detail;
- `/open-now`;
- `/nearby`;
- `/routes` Routes list;
- `/routes/generate` Generate route;
- `/routes/:slug` Route detail;
- `/admin/photo-review` Photo review;
- `/walk-route` legacy.

Есть:
- demo mode;
- local catalog data;
- place cards;
- route result UI;
- quality/warning badges;
- route correction action `extend_route`;
- photo status handling.

Не реализовано:
- Login/Register;
- Personal account;
- полноценный map UI;
- selected map point для маршрута;
- active route session UI;
- route recovery UI;
- smart detours UI;
- payment/entitlement UI;
- business owner UI;
- social/community UI.

---

## 7. Telegram bot

Статус: Phase 1+ реализован как lite/conversational слой.

Есть:
- `/start`, `/help`, `/health`;
- city selection;
- selected city context;
- menu;
- location handling;
- address handling;
- route build;
- route correction;
- nearby/open-now/coffee/food/walk/dog-friendly сценарии;
- free text intent layer;
- backend API clients;
- friendly errors;
- structured event logs.

Telegram не должен копировать web. Он остаётся быстрым клиентом к backend для сценариев:
- что рядом;
- что открыто;
- построить маршрут;
- скорректировать маршрут;
- найти место по простому интенту.

---

## 8. User signals / personalization

Реализовано:
- `POST /user-signals/`;
- `GET /user-signals/{user_id}/summary`;
- `GET /user-signals/{user_id}/profile`;
- модель `user_signals`;
- service для summary/derived profile;
- route scoring может использовать derived profile.

Частично:
- персонализация есть на уровне signals/profile/scoring, но без полноценного аккаунта.

Не реализовано:
- auth;
- users как полноценная identity модель;
- personal account;
- favorites UI как стабильный пользовательский продукт;
- decay по времени;
- negative feedback с весами;
- tags affinity;
- post-route feedback flow;
- retention notifications.

---

## 9. AI / search / recommendations

Реализовано:
- rule-based AI query MVP;
- retrieval/orchestration на собственной БД;
- route recommendation pipeline;
- route explanation;
- semantic-ish interests mapping для маршрутов.

Не реализовано:
- semantic vector search;
- полноценный LLM orchestration;
- ranked places/routes/collections как отдельные recommendation endpoints;
- next best actions;
- next destination;
- AI с памятью пользователя как единый продуктовый слой.

---

## 10. Security / auth / payments / business / social

Не реализовано:
- Login/Register;
- unified identity layer;
- entitlement layer;
- payments/subscriptions;
- Telegram account linking;
- business owner claim flow;
- business dashboard;
- social/community;
- gamification.

Планировать позже, после usable web product + route engine + personalization foundation.

---

## 11. Roadmap

### Phase A — stabilize product route flow

Приоритет:
- выбрать `user-routes/build + correct` как главный route flow для продукта;
- не развивать legacy itinerary как основной слой;
- закрыть address geocoding;
- добавить selected map point;
- улучшить route quality/time budget;
- добавить partial tail rebuild.

### Phase B — Active Route Session

Сделать маршрут активной сессией:
- active route id/state;
- current position;
- visited places;
- skipped places;
- remaining time;
- warnings;
- next step;
- correction history.

### Phase C — Live Route Editing / Recovery / Detours

Добавить:
- remove/skip/add/replace/shorten/extend на ходу;
- route recovery при отклонении;
- smart detours рядом;
- weather-aware rebuild later.

### Phase D — Personalization foundation

Добавить:
- auth/users;
- personal account;
- favorites/history/visited/completed routes UI;
- stronger derived profile;
- decay/tags affinity;
- feedback after route.

### Phase E — Data governance / production readiness

Довести:
- production data refresh;
- city coverage gates;
- freshness/confidence everywhere;
- source conflict resolution;
- rollback/revert;
- observability and staging smoke.

### Phase F — Monetization and expansion

Позже:
- payments/entitlements;
- Telegram account linking;
- business owner flow;
- social/community;
- gamification;
- next destination/travel planning.

---

## 12. Out of scope сейчас

Не делать сейчас:
- full booking engine;
- full social feed;
- business dashboard;
- payments;
- mobile app;
- gamification;
- travel planning between cities;
- full routing provider/polyline engine до выбора provider;
- semantic vector search без стабильного data layer.

---

## 13. Правило обновления документа

После значимой фичи обновлять:
1. статус модуля;
2. список реализованных endpoints/files;
3. ограничения;
4. следующий шаг;
5. если документ устарел — переносить в `docs/archive/`, а не держать рядом с SoT.
