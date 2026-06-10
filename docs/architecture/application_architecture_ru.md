# City Go — архитектура приложения и назначение файлов

Документ описывает **текущую** структуру репозитория (корень = backend-приложение): слои, потоки данных и роль основных модулей.  
`app_backup_before_cleanup/` — архив старых версий, **не используется** в рантайме.

---

## 1. Стек и точки входа

| Компонент | Назначение |
|-----------|------------|
| **FastAPI** | HTTP API, `main.py` собирает роутеры |
| **SQLAlchemy 2.x** | ORM, сессии, миграции Alembic |
| **PostgreSQL + PostGIS** | БД, геозапросы кандидатов маршрута |
| **Pydantic v2** | Схемы запросов/ответов API |
| **Aiogram** | Telegram-бот (`telegram_bot/`, `telegram_bot_main.py`) |
| **Vite/React** | Фронтенд в `frontend/` |

**Точки входа**

- `main.py` — приложение FastAPI, CORS, подключение всех `routers/*`.
- `telegram_bot_main.py` — запуск бота (если используется отдельно от API).

---

## 2. Recommendation pipeline (новый слой)

Линейный поток без изменения порядка после сборки:

```
RequestContext
  → ContextMergeService.merge()
  → CandidateRetrievalService.get_candidates()
  → HardFiltersService.apply()
  → ScoringService.score()
  → RouteAssemblyService.build()
  → TimeAwareService.apply()
  → RouteFinalizeService.finalize()
  → ExplainabilityService.build_route_explanation()  (для API поверх FinalRoute)
```

| Файл | Роль |
|------|------|
| `services/context_merge_service.py` | `RequestContext` + опционально `UserProfile` → `MergedContext` (без БД). |
| `services/candidate_retrieval_service.py` | STEP 2: SQL/PostGIS, пул кандидатов `Place` в радиусе. |
| `services/hard_filters_service.py` | STEP 3: жёсткие отсечения (бюджет, категории, часы и т.д.). |
| `services/scoring_service.py` | STEP 4: мягкие оценки, breakdown по полям `Place`. |
| `services/route_assembly_service.py` | STEP 5: `RoutePoint` (порядок, dwell, `opening_hours` на точке). |
| `services/time_aware_service.py` | STEP 6: walk, arrival/departure, `time_status`, `time_warning`. |
| `services/route_finalize_service.py` | STEP 7: `FinalRoute` + агрегаты (`total_estimated_minutes`, warnings). |
| `services/explainability_service.py` | STEP 8: summary и JSON payload для UI. |
| `services/route_builder_service.py` | Оркестратор шагов 1–7, единая точка входа `build_route()`. |
| `routers/recommendations.py` | **POST `/recommendations/route`** — HTTP вход в pipeline + explainability. |
| `schemas/recommendation_route.py` | Тело запроса для этого endpoint. |

---

## 2.1. User route layer (build + correction)

Stateless слой поверх recommendation pipeline:

```
UserRouteIntent
  → UserRouteBuildService.build()
  → RouteBuilderService.build_route()
  → UserRouteState

UserRouteCorrectRequest
  → UserRouteCorrectService.correct()
  → recalc existing route OR rebuild through RouteBuilderService
  → UserRouteState(revision + 1)
```

| Файл | Роль |
|------|------|
| `schemas/user_route.py` | Контракты `UserRouteIntent`, `UserRouteState`, `UserRouteBuildRequest`, `UserRouteCorrectRequest`. |
| `routers/user_routes.py` | **POST `/v1/user-routes/build`** и **POST `/v1/user-routes/correct`**. |
| `services/user_route_build_service.py` | Строит пользовательский route state через текущий recommendation pipeline. |
| `services/user_route_correct_service.py` | Корректирует route state: `remove_place`, `shorten_route`, `rebuild_from_here`, `avoid_category`. |
| `services/user_route_recalc_service.py` | Пересчитывает существующие точки маршрута: time-aware, budget-fit, finalize. |
| `services/user_route_mapper.py` | Преобразует `FinalRoute` в `UserRouteState`. |

Слой не хранит маршруты в БД: клиент присылает текущий state, backend возвращает новую revision. Persistence, аккаунты и история маршрутов — следующий слой поверх этого контракта.

---

## 3. Корень репозитория

| Файл / папка | Назначение |
|--------------|------------|
| `main.py` | FastAPI app, middleware, lifecycle hooks, `include_router` для всех API-модулей. |
| `telegram_bot_main.py` | Точка входа Telegram-бота. |
| `requirements.txt` | Зависимости Python. |
| `README.md` | Общее описание проекта. |
| `alembic.ini`, `migrations/` | Конфиг и ревизии миграций БД. |

---

## 4. `core/`

| Файл | Назначение |
|------|------------|
| `core/config.py` | `pydantic-settings`: URL БД, хост, токены, опциональные ID для фильтров и scheduler re-verification. |
| `core/place_verification_scheduler.py` | Lifecycle adapter для опционального background enqueue stale-мест в verification queue. |
| `core/place_taxonomy.py` | Каноничные списки категорий/тегов для валидации и сидов. |

---

## 5. `db/`

| Файл | Назначение |
|------|------------|
| `db/base.py` | `DeclarativeBase` для ORM-моделей. |
| `db/session.py` | `engine`, `SessionLocal` от `settings.database_url`. |
| `db/dependencies.py` | FastAPI `get_db()` — сессия на запрос, `close()` в `finally`. |

---

## 6. `models/` (ORM, таблицы)

| Файл | Сущность |
|------|----------|
| `models/place.py` | Место: гео, категория, `opening_hours` JSONB, dwell, флаги. |
| `models/city.py` | Город: slug, таймзона, центр. |
| `models/category.py` | Справочник категорий. |
| `models/tag.py` | Справочник тегов. |
| `models/place_tag.py` | Связь место ↔ тег. |
| `models/route.py` | Готовый editorial-маршрут. |
| `models/route_place.py` | Точки внутри маршрута (позиция). |
| `models/collection.py` | Подборка. |
| `models/collection_place.py` | Место в подборке + позиция. |
| `models/place_schedule.py` | Расписание (если используется отдельно от JSON hours). |

---

## 7. `schemas/` (Pydantic, API и контексты)

| Файл | Назначение |
|------|------------|
| `merged_context.py` | `MergedContext`, enum бюджета/темпа, хелперы радиуса/времени. |
| `user_profile.py` | Профиль пользователя для merge и будущего персонализации. |
| `recommendation_route.py` | **Source of truth** для **POST `/recommendations/route`**: тело запроса и модели ответа (`RecommendationRouteRequest`, точки, агрегаты, контейнер ответа). |
| `place.py`, `place_search.py`, `place_query_params.py`, `place_list_params.py` | CRUD/список/поиск мест. |
| `place_search_response.py` | Ответ списка/поиска с пагинацией. |
| `place_seed_*.py`, `place_seed_item.py` | Импорт/валидация seed-данных мест. |
| `place_taxonomy_*.py` | Таксономия и диагностика payload. |
| `city.py`, `category.py`, `tag.py`, `collection*.py`, `route*.py` | Схемы сущностей и связей. |
| `pagination.py`, `sorting.py` | Общие параметры списков. |
| `itinerary.py`, `itinerary_replan.py` | Контракты старого itinerary API. |
| `ai.py` | Запрос к AI-router. |
| `open_now.py`, `nearby.py` | Ответы витрин «рядом» / «открыто сейчас». |
| `request.py` | Устаревший/параллельный контракт (не основной путь recommendations). |

---

## 8. `services/` — доменная логика

### 8.1. Recommendation (новый pipeline)

См. раздел 2; файлы: `route_builder_service`, `context_merge_service`, `candidate_retrieval_service`, `hard_filters_service`, `scoring_service`, `route_assembly_service`, `time_aware_service`, `route_finalize_service`, `explainability_service`.

### 8.2. Места, списки, поиск

| Файл | Назначение |
|------|------------|
| `place_service.py` | Сборка списка мест: фильтры, сортировка, пагинация, total. |
| `place_filters_service.py` | Фильтры по городу/категории/тегу. |
| `place_search_service.py` | Текстовый поиск по полям Place. |
| `place_sorting_service.py` | ORDER BY по whitelist полей. |
| `place_query_params_service.py` | Нормализация объединённых query-параметров. |
| `place_list_params_service.py` | Нормализация list + pagination. |
| `place_search_params_service.py` | Нормализация строки `q`. |
| `place_count_service.py` | `COUNT` без limit/offset. |
| `place_detail_service.py` | Карточка места по slug + теги. |
| `place_search_response_service.py` | Сборка `PlaceSearchResponse`. |

### 8.3. Сиды и таксономия

| Файл | Назначение |
|------|------------|
| `place_seed_validation_service.py` | Валидация одного seed-элемента. |
| `place_seed_bulk_validation_service.py` | Пакетная валидация. |
| `place_seed_dry_run_service.py` | Dry-run импорта. |
| `place_seed_import_summary_service.py` | Сводка импорта. |
| `place_taxonomy_service.py` | Проверка значений против канона. |
| `place_taxonomy_response_service.py` | Ответ со списками канона. |
| `place_taxonomy_payload_service.py` | Нормализация payload таксономии. |
| `place_taxonomy_diagnostics_service.py` | Невалидные значения в payload. |
| `place_taxonomy_diagnostics_response_service.py` | Обёртка ответа диагностики. |

### 8.4. Справочники и связи

| Файл | Назначение |
|------|------------|
| `city_service.py`, `category_service.py`, `tag_service.py` | Чтение справочников. |
| `route_service.py` | Маршруты с `route_places` и точками. |
| `route_place_service.py` | Связи route ↔ place. |
| `collection_place_service.py` | Связи collection ↔ place. |
| `collection_service.py` | **Внимание:** в репозитории может дублировать/ломать импорты с itinerary — проверять перед запуском `main`. |
| `place_tag_service.py` | CRUD связей place-tag. |

### 8.5. Витрины и AI

| Файл | Назначение |
|------|------------|
| `nearby_service.py` | Места в радиусе (Haversine в Python). |
| `open_now_service.py` | «Открыто сейчас» по городу и расписанию. |
| `ai_service.py` | Разбор текстового запроса + вызовы read-only сервисов. |
| `ai_dictionaries.py` | Словари ключевых слов для AI. |

### 8.6. Itinerary (отдельный слой, не recommendation)

| Файл | Назначение |
|------|------------|
| `itinerary_service.py` | Генерация черновика itinerary (кандидаты, скоринг, сборка). |
| `itinerary_candidate_service.py` | Выборка кандидатов под старый сценарий. |
| `itinerary_scoring_service.py` | Ранжирование кандидатов. |
| `itinerary_route_builder_service.py` | Сборка порядка точек. |
| `itinerary_time_service.py` | Часы, окна, `is_place_open_at` (используется и новым pipeline). |
| `itinerary_time_estimator.py` | Оценки времени и расстояний для itinerary. |
| `itinerary_text_parser.py` | Разбор текста намерений. |
| `itinerary_explanation_service.py` | Тексты причин для itinerary. |
| `itinerary_replan_service.py` | Перестроение маршрута. |
| `start_context_resolver.py` | Стартовая точка из place_id / geo / города. |

### 8.7. Прочее

| Файл | Назначение |
|------|------------|
| `pagination_service.py`, `sorting_service.py` | Нормализация limit/offset и сортировки. |
| `__init__.py` | Заглушка для совместимости импортов. |

---

## 9. `routers/` (HTTP)

| Файл | Префикс / назначение |
|------|----------------------|
| `recommendations.py` | **`/recommendations`** — POST `/route` новый pipeline. |
| `places.py` | `/places` — CRUD и список мест. |
| `place_search.py` | `/places/search` — поиск с `q`. |
| `cities.py` | `/cities`. |
| `categories.py` | `/categories`. |
| `tags.py` | `/tags`. |
| `place_tags.py` | `/place-tags`. |
| `routes.py` | `/routes` — editorial-маршруты. |
| `route_places.py` | `/route-places`. |
| `collections.py` | `/collections`. |
| `collection_places.py` | `/collection-places`. |
| `nearby.py` | `/nearby`. |
| `open_now.py` | `/open-now`. |
| `place_taxonomy.py` | `/place-taxonomy`. |
| `place_taxonomy_diagnostics.py` | `/place-taxonomy/diagnostics`. |
| `place_seed_dry_run.py` | `/place-seed/dry-run`. |
| `place_seed_validation.py` | `/place-seed/validate`. |
| `itinerary.py` | **`/routes`** (generate/replan) — старый itinerary API. |
| `ai.py` | `/ai`. |

Зависимость: `Depends(get_db)` из `db.dependencies`.

---

## 10. `tests/`

Юнит- и smoke-тесты по доменам: `places`, `place_search`, `place_seed`, таксономия, **pipeline** (`test_route_builder_pipeline_smoke`, `test_context_merge_service`, `test_hard_filters_service`, `test_route_assembly_service`, `test_scoring_service`, `test_time_aware_service`, `test_route_finalize_service`, `test_explainability_service`, `test_candidate_retrieval_db_smoke`), **recommendations router** (`test_recommendations_route_router` с изолированным FastAPI при необходимости). Часть тестов `test_itinerary_*` может отставать от сигнатур сервисов — при изменении itinerary прогонять и синхронизировать отдельно.

---

## 11. `telegram_bot/`

| Путь | Назначение |
|------|------------|
| `handlers/` | Хендлеры команд и состояний (меню, адрес, локация, health, построение и коррекция маршрута). |
| `keyboards/` | Клавиатуры. |
| `states/` | FSM-состояния (например адрес). |
| `services/` | Сообщения, контекст пользователя/адреса/route state с DB persistence и memory fallback, клиент user-routes API, форматирование маршрута, безопасные backend request logs. |

Главный usable-сценарий бота: пользователь нажимает **«Собрать маршрут»** или пишет запрос свободным текстом, бот берёт город из текстового запроса, последнюю геолокацию, сохранённый ручной адрес (пока как приближённый старт от центра распознанного поддерживаемого города) или fallback на центр `DEFAULT_CITY_SLUG`, вызывает `POST /v1/user-routes/build`, сохраняет route state в `telegram_user_contexts` и memory fallback, обогащает точки названиями через `/places/{id}` и возвращает короткий HTML-ответ. **«Что рядом»** использует явную геолокацию, сохранённый адрес или явно указанный город в тексте (`что рядом в Зеленоградске`), но не подставляет default city без пользовательского контекста. Городовые кнопки вроде **«Что открыто»**, **«Где кофе»**, **«Куда погулять»** берут `city_slug` из сохранённого адреса и только без контекста падают назад на `DEFAULT_CITY_SLUG`; те же сценарии доступны свободным текстом вроде `где кофе в Зеленоградске`, при этом явно распознанный город из текста приоритетнее сохранённого адреса. Кнопки и текстовые коррекции вызывают `POST /v1/user-routes/correct`: сделать маршрут короче, убрать первую точку, перестроить от текущей геолокации/центра города или избегать категории.

---

## 12. `frontend/`

Клиент (Vite + React): UI City Go, вызовы backend по HTTP.

---

## 13. `data/`

| Путь | Назначение |
|------|------------|
| `data/seeds/` | JSON и прочие сиды. |
| `data/raw/` | Сырые выгрузки (OSM и т.д.). |
| `data/scripts/` | Утилиты: загрузка сидов, валидация, обзор мест. |

---

## 14. `scripts/`

Служебные скрипты разового запуска (например минимальный seed).

---

## 15. `docs/`

Продуктовая и техническая документация: [`README.md`](../README.md) (карта каталога), `master_technical_spec.md`, `change_history.md`, `architecture/`, `itinerary/`, `reference/`.

---

## 16. `api/routes/recommendation.py`

Черновик с импортами `app.schemas.request` / `app.services.pipeline` — **не подключён** к `main.py`, **не** используется в прод-API. Рабочий HTTP-вход recommendation pipeline: **`routers/recommendations.py`** (`POST /recommendations/route`).

---

## 17. `app_backup_before_cleanup/`

Снимок старой структуры (дубли сервисов). Не подключать к `main.py`.

---

## 18. Краткая схема зависимостей слоёв

```
HTTP (routers)  →  services  →  models/schemas
                     ↓
                  db.session
                     ↓
                 PostgreSQL
```

---

*Документ можно дополнять при появлении новых роутеров или выноса `collection_service` в согласованное состояние с `collections` API.*
