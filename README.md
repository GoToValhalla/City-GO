# City GO

City GO — городской travel/local guide: публичный каталог мест, готовые маршруты, ручной route player, админка качества данных, Telegram-бот и автоматический import/enrichment pipeline.

Пилотные сценарии:

- турист выбирает город, смотрит места и маршруты;
- пользователь открывает маршрут и проходит его по точкам в вебе;
- Telegram-бот даёт быстрый доступ к городам, маршрутам, местам, поиску, избранному и лёгкому прохождению маршрута;
- админ импортирует/обогащает город без CSV-ручного конвейера;
- quality gates скрывают OSM-мусор, служебные категории и ненадёжные поля из пользовательских сценариев.

## Текущий статус

В проде и в `main` сейчас есть:

- FastAPI backend + PostgreSQL/PostGIS-ready schema + Alembic migrations.
- React/Vite frontend с публичными страницами, админкой и route navigation MVP.
- Backend route sessions foundation для сохранения прогресса маршрута.
- Telegram-бот на `aiogram 3` с webhook/polling entrypoint.
- Admin import/enrichment pipeline foundation.
- Field-level confidence, review queue, photo candidates, route eligibility diagnostics.
- Data Coverage Assurance foundation: must-have POI registry, coverage gap detection, scope-aware assurance, acceptance verdict and readiness gate.
- Docker Compose production deploy через GitHub Actions.
- CI: backend pytest + frontend lint/tests/build + Allure raw results.

Основной актуальный operational overview: `docs/operations/current_system_overview.md`.
Операционный центр админки: `docs/admin_operational_center.md`.
Data Coverage Assurance: `docs/architecture/data_coverage_assurance.md`.

## Стек

- Python 3.11
- FastAPI
- SQLAlchemy 2.0
- Alembic
- PostgreSQL 16
- Pydantic v2
- aiogram 3.x
- React / Vite / TypeScript
- Docker Compose
- GitHub Actions

## Подсистемы

### Backend API

Ключевые зоны:

- `routers/` — FastAPI routers.
- `services/` — бизнес-логика, route building, import pipeline, quality gates.
- `models/` — SQLAlchemy ORM.
- `schemas/` — Pydantic contracts.
- `migrations/versions/` — Alembic chain. Guard ожидает один head.

Главные публичные endpoints:

```http
GET /cities/
GET /cities/by-slug/{slug}
GET /places/
GET /places/{place_id}
GET /routes/{route_id}
POST /routes/{route_id}/sessions
GET /route-sessions/{session_id}
POST /route-sessions/{session_id}/events/checkin
POST /v1/user-routes/build
GET /open-now
GET /nearby
```

Legacy route generator остаётся, но новый пользовательский flow должен идти через:

```http
POST /v1/user-routes/build
```

### Route Building

Текущая цепочка:

```text
POST /v1/user-routes/build
→ UserRouteBuildService
→ RouteBuilderService
→ RouteEngine
→ InstantRouteStrategy
→ build_dynamic_route
→ candidate_retrieval
→ hard_filters
→ scoring
→ adaptive_plan
→ assembly
→ quality_gates
→ UserRouteState
```

`RouteEngine` — точка расширения под будущие стратегии:

- `InstantRouteStrategy` — маршрут сейчас;
- `PlannedRouteStrategy` — маршрут на дату/время;
- `RecomputeRouteStrategy` — перестроение активного маршрута.

### Route Navigation MVP

Публичная route detail страница теперь использует route player:

- frontend state machine: `not_started`, `active`, `completed`;
- SVG/HTML схема маршрута с прямыми сегментами;
- кнопки: `Начать маршрут`, `Я на месте`, `Следующая`, `Завершить`, `Пройти заново`;
- current web persistence: `localStorage` ключ `citygo:route-navigation:{routeId}`;
- backend route sessions foundation: `route_sessions`, `route_session_points`, check-in/complete API;
- frontend/backend quality gates отбрасывают точки без координат, hidden/unpublished/inactive, `is_route_eligible=false`, service/bank/police/transport/pharmacy/etc.

Подробнее: `docs/architecture/route_navigation_stage1.md`.

Следующий технический шаг: подключить веб route player к backend sessions, затем MapLibre + GPS.

### Import / Enrichment Pipeline

CSV больше не является основным сценарием. Основной flow:

```text
Admin → start city pipeline
→ import_job_steps
→ source_observations
→ place_field_confidence
→ place_photo_candidates
→ review_queue_items
→ publication decisions
```

Admin endpoints:

```http
POST /admin/place-enrichment/pipeline/{city_slug}/run
GET /admin/place-enrichment/jobs/{job_id}/steps
GET /admin/place-enrichment/places/{place_id}/confidence
GET /admin/place-enrichment/review-queue
POST /admin/place-enrichment/review-queue/{item_id}/resolve
POST /admin/place-enrichment/photo-candidates/{candidate_id}/approve
POST /admin/place-enrichment/photo-candidates/{candidate_id}/reject
POST /admin/place-enrichment/photo-candidates/{candidate_id}/set-primary
```

Подробнее: `docs/architecture/import_enrichment_pipeline_stage1.md`.

### Data Coverage Assurance

Must-have coverage is a separate readiness layer. A city cannot be considered ready only because the raw import finished.

Core files:

- `models/known_missing_poi.py` — operational registry of expected POI.
- `data/config/known_missing_poi.json` — versioned seed data.
- `services/data_coverage_contract.py` — shared statuses, gap reasons, scope aliases and acceptance rules.
- `services/data_coverage_assurance.py` — scope-aware and source-observation-aware assurance pass.
- `services/osm_import_taxonomy.py` — global OSM taxonomy mapper.
- `data/scripts/import_city_osm_v2.py` — coverage-aware import wrapper.
- `routers/admin_coverage_gaps.py` — admin API.
- `frontend/src/pages/admin/AdminCoverageGapsPage.tsx` — admin dashboard.

Admin endpoints:

```http
GET /admin/coverage-gaps
GET /admin/coverage-gaps/cities/{city_slug}
POST /admin/coverage-gaps/sync
POST /admin/coverage-gaps/refresh
PATCH /admin/coverage-gaps/{gap_id}
```

Подробнее: `docs/architecture/data_coverage_assurance.md`.

### Telegram Bot

Код живёт в `telegram_bot/`.

Реализовано:

- `/start`, выбор города, главное меню;
- маршруты, карточка маршрута, список точек;
- route mode внутри Telegram через редактируемые сообщения;
- места по категориям, карточка места;
- места рядом через Telegram location;
- открыто сейчас только с reliable hours;
- поиск текстом + no-result analytics;
- избранное;
- back-stack;
- short callback ids, чтобы не превышать лимит Telegram 64 байта;
- soft rate limit;
- webhook endpoint: `POST /telegram-bot/webhook`;
- admin analytics: `GET /admin/telegram-bot/analytics`.

Бот принимает токен из `BOT_TOKEN` или fallback `TELEGRAM_BOT_TOKEN`.

Подробнее: `docs/architecture/telegram_bot.md`.

### Data Quality Gates

Пользовательские поверхности не должны показывать:

- `node/way/relation`, `OSM 123`, `Культурное место OSM ...`;
- service/bank/atm/police/mvd/transport/pharmacy/hospital/military/cemetery/industrial/fuel/parking;
- low/stale/conflict opening hours в `Открыто сейчас`;
- generic/placeholder/no-photo images как реальные фото;
- debug/confidence/source labels.

Критичные файлы:

- `telegram_bot/quality.py`
- `services/quality_scoring.py`
- `services/import_pipeline_publication.py`
- `frontend/src/features/route-navigation/model/qualityGate.ts`
- `services/route_session_service.py`

## Запуск локально

### Backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn main:app --reload
```
