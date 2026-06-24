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
- Docker Compose production deploy через GitHub Actions.
- CI: backend pytest + frontend lint/tests/build + Allure raw results.

Основной актуальный operational overview: `docs/operations/current_system_overview.md`.
Операционный центр админки: `docs/admin_operational_center.md`.

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

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

### Docker production-like

```bash
cp .env.example .env
docker compose up --build
```

Адреса:

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### Docker dev

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## Проверки перед push

Минимальный targeted набор после backend/frontend изменений:

```bash
.venv/bin/python -m pytest --no-cov -q
npm --prefix frontend run lint
npm --prefix frontend run test:ci
npm --prefix frontend run build
git diff --check
```

Для route navigation:

```bash
npm --prefix frontend run test -- routeNavigation routeQualityGate
.venv/bin/python -m pytest --no-cov \
  tests/test_route_detail_navigation_fields_new.py \
  tests/test_route_sessions_new.py \
  tests/test_alembic_single_head_new.py -q
```

Для import/enrichment pipeline:

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_alembic_single_head_new.py \
  tests/test_import_pipeline_foundation_new.py \
  tests/test_import_pipeline_foundation_safety_new.py \
  tests/test_import_pipeline_api_new.py \
  tests/test_import_pipeline_review_queue_new.py \
  tests/test_import_pipeline_photo_safety_new.py -q
```

Для Telegram bot:

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_telegram_bot_rewrite_new.py \
  tests/test_telegram_bot_completion_new.py -q
```

## Deploy

Deploy workflow: `.github/workflows/deploy.yml`.

Запуск:

```bash
gh workflow run Deploy --ref main
gh run watch <run_id>
```

Workflow делает:

1. build backend image;
2. backend import smoke inside image;
3. push backend image;
4. build/push frontend image;
5. на сервере скачивает актуальный `docker-compose.yml` из `main`;
6. pull images;
7. migrations;
8. production schema guard;
9. backend health;
10. frontend health + `/build.json` SHA guard;
11. restart bot/import-worker;
12. proxy health.

Production import-smoke внутри уже работающего backend-контейнера намеренно не выполняется: на маленьком сервере это может дать `exit 137` из-за OOM. Import-smoke остаётся на build этапе image.

## Миграции

Правила:

- один Alembic head;
- при добавлении миграции обновить `tests/test_alembic_single_head_new.py` (`KNOWN_HEAD`, `EXPECTED_COUNT`);
- новые модели должны быть импортированы в `models/__init__.py` и `migrations/env.py`;
- production deploy использует `alembic upgrade heads`.

## Документация

Актуальные документы:

- `README.md` — главный вход.
- `docs/operations/current_system_overview.md` — операционная карта системы.
- `docs/architecture/import_enrichment_pipeline_stage1.md` — import/enrichment pipeline.
- `docs/architecture/route_navigation_stage1.md` — route navigation MVP.
- `docs/architecture/telegram_bot.md` — Telegram bot.
- `docs/data-foundation-p1.md` — Data Foundation P1.

При крупных изменениях нужно обновлять минимум README + соответствующий doc в `docs/architecture` или `docs/operations`.
