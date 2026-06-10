# City Go — backend: рабочий реестр файлов

Краткий справочник **по пути → слой → роль → зависимости**.  
Детальный поток сервисов см. `docs/architecture/application_architecture_ru.md` (раздел recommendation pipeline).

---

## Два маршрутных HTTP-слоя (не путать)

| Слой | Назначение |
|------|------------|
| **Новый recommendation pipeline** | Canonical `POST /v1/recommendations/route`; legacy `POST /recommendations/route` отдаёт deprecation headers. Динамический маршрут из кандидатов, оркестрация в `RouteBuilderService`, объяснение в `ExplainabilityService`. Полный путь «HTTP → БД → pipeline» покрывает opt-in интеграционный тест `tests/test_recommendations_route_integration.py` (см. ниже). |
| **Старый itinerary API** | Отдельные контракты и роутер: `routers/itinerary.py`, `schemas/itinerary.py`, `schemas/itinerary_replan.py`. Существует параллельно, **не** заменён новым endpoint. |
| **User route layer** | `POST /v1/user-routes/build` и `POST /v1/user-routes/correct` — stateless build/correction слой для пользовательских маршрутов поверх нового recommendation pipeline. |
| **Frontend demo route layer** | `frontend/src/shared/demo/routes.ts` строит маршрут из локального JSON-каталога, а `categoryLabels.ts` задаёт русские labels и aliases интересов для demo-mode без backend. |
| **Frontend discovery UI** | `components/places/PlaceCard.tsx`, `pages/open-now/*`, `pages/nearby/*` и `pages/places/PlaceDetailPage.tsx` используют общий enriched place contract: фото, часы, длительность, price label, source/confidence и route CTA. |
| **Place image enrichment** | `data/scripts/enrich_catalog_images.py`, `validate_catalog_images.py`, `image_enrichment_rules.py` и `data/scripts/image_pipeline/*` поддерживают честный `image.match_status`, Wikidata/Commons/official/Mapillary stages и verification queue для frontend catalog. |
| **Route pipeline observability** | `services/route_builder_flow.py`, `route_pipeline_trace.py`, `route_filter_policy.py`, `route_filter_reasons.py` и `route_interest_mapping.py` добавляют trace, hard-filter reasons и semantic interests для production route builder. |
| **Route assembly quality** | `services/route_assembly_optimizer.py`, `route_geometry.py`, `route_diversity_policy.py`, `route_point_factory.py`, `route_walk_annotations.py` и `route_response_metrics.py` отвечают за walk-aware budget, diversity constraints, loop cleanup и response metadata. |
| **Route scoring/explanation** | `services/route_base_quality_score.py`, `route_time_context_score.py`, `route_data_confidence_score.py`, `route_popularity_proxy.py` и `route_explanation_reasons.py` дают контекстный score и объяснения выбора точек. |
| **Route correction engine** | `services/user_route_correction_actions.py`, `user_route_correction_policy.py` и `user_route_replacement_loader.py` делают remove+replacement, smart shorten и extend route для `POST /v1/user-routes/correct`. |
| **Route result UX contract** | `services/route_user_warnings.py`, serializers и frontend `RouteWarnings/RouteInsights/RouteDataNotes` переводят backend route fields в понятный пользовательский результат. |
| **Production data refresh** | `scripts/production_place_import.py` и `scripts/refresh_place_images.py` дают безопасный dry-run-first import и no-live/live image refresh без чтения секретов из env. |
| **City expansion registry** | `models/country.py`, `region.py`, `city_candidate.py`, `city_import_scope.py` и `routers/city_expansion.py` отделяют страны/регионы/кандидаты от published cities. |
| **Import audit/state** | `data/scripts/run_due_import_jobs.py`, `data/config/import_targets.json`, `import_batches`, `city_scope_import_state`, `source_observations`, `place_source_presence`, `place_scope_links` дают управляемый cron-import и import memory без удаления production places. |
| **Telegram city selection** | `telegram_bot/handlers/city_selection.py`, `keyboards/city_selection.py` и `selected_city_slug` в context store заставляют пользователя выбрать город до маршрутов/мест. |

---

## `schemas/user_route.py`, `routers/user_routes.py`

| Поле | Значение |
|------|----------|
| **Путь** | `schemas/user_route.py`, `routers/user_routes.py` |
| **Слой** | Pydantic + HTTP |
| **Роль** | Source of truth для пользовательского route state: build возвращает `UserRouteState`, correct принимает текущий state и действие, возвращает новую revision. |
| **Endpoints** | `POST /v1/user-routes/build`, `POST /v1/user-routes/correct`. |
| **Correction actions** | `remove_place`, `shorten_route`, `rebuild_from_here`, `avoid_category`, `extend_route`. |
| **SoT / вспомогательный** | SoT для clients, UI и Telegram, которым нужен управляемый пользовательский маршрут без persistence. |

---

## `services/user_route_*`

| Файл | Роль |
|------|------|
| `services/user_route_build_service.py` | Вызывает `RouteBuilderService` и маппит `FinalRoute` в `UserRouteState`. |
| `services/user_route_correct_service.py` | Оркестрирует корректировки: пересчёт текущего state или rebuild через recommendation pipeline. |
| `services/user_route_recalc_service.py` | Для текущих точек пересчитывает time-aware, budget-fit и finalize. |
| `services/user_route_context.py` | Маппинг `UserRouteIntent` → `RequestContext`, иммутабельные updates/merge списков. |
| `services/user_route_mapper.py` | Маппинг `FinalRoute` → `UserRouteState`. |
| `services/user_route_place_loader.py` | DB-загрузка places из текущего route state. |
| `services/route_user_warnings.py` | Чистый mapper route-level warning strings и `places_with_warnings` в пользовательские warning objects. |

---

## `schemas/recommendation_route.py`

| Поле | Значение |
|------|----------|
| **Путь** | `schemas/recommendation_route.py` |
| **Слой** | Pydantic, контракты HTTP |
| **Роль** | **Source of truth** для тела запроса и структуры ответа `POST /recommendations/route`: `RecommendationRouteRequest`, `RecommendationRoutePointResponse`, `RecommendationRouteResponse`. |
| **Шаг pipeline** | Не шаг алгоритма; граница API. Поля запроса маппятся в `RequestContext` в роутере. |
| **Зависимости** | `pydantic` |
| **Возвращает / производит** | Валидированные DTO; в ответе в т.ч. **`warnings: list[str]`** и `quality_score` / `quality_breakdown` из `FinalRoute`. JSON собирает роутер (`model_validate` по dict с ISO-строками для времён). |
| **Debug** | При `X-Debug: true` ответ может содержать `_trace` со stage counts/durations/reasons. |
| **SoT / вспомогательный** | **SoT** для схем этого endpoint. |

---

## `routers/recommendations.py`

| Поле | Значение |
|------|----------|
| **Путь** | `routers/recommendations.py` |
| **Слой** | HTTP (FastAPI `APIRouter`) |
| **Роль** | **Entry point** нового recommendation pipeline в API: приём JSON → `RequestContext` → `RouteBuilderService().build_route(db, request, profile=None)` → `ExplainabilityService().build_route_explanation(final_route)` → ответ `RecommendationRouteResponse`; legacy path получает deprecation headers. |
| **Шаг pipeline** | Оркестрация **после** HTTP: внутри `build_route` — шаги 1–7 (merge → … → finalize); затем шаг 8 — explainability над `FinalRoute`. |
| **Зависимости** | `get_db`, `schemas.recommendation_route`, `RequestContext`, `RouteBuilderService`, `ExplainabilityService`, типы `RoutePoint` / `FinalRoute` для сериализации. |
| **Возвращает / производит** | JSON: `route_id`, `points`, агрегаты, **`warnings`**, `quality_score`, `quality_breakdown` из `FinalRoute` (`_serialize_final_route`), `explanation` (dict из explainability). |
| **SoT / вспомогательный** | Тонкий HTTP-слой; схемы — в `schemas/recommendation_route.py`, бизнес-логика — в `services/*`. |
| **Проверка «как в проде»** | Интеграционный тест `tests/test_recommendations_route_integration.py`: реальный `app` из `main`, без моков pipeline и БД, только при `RUN_RECOMMENDATIONS_INTEGRATION=1` и `DATABASE_URL` на PostgreSQL. |

---

## `main.py`, `core/cors.py`, `core/readiness.py`, `db/session.py`

| Поле | Значение |
|------|----------|
| **Роль** | Production foundation: `/health`, `/ready` с DB check, env-based CORS, DB pool settings (`pool_pre_ping`, `pool_size`, `max_overflow`, `pool_recycle`). |
| **Request logging** | `core/request_logging.py`: JSON event на каждый HTTP request (`method`, `path`, `status_code`, `duration_ms`). |
| **Router setup** | `core/router_setup.py`: подключение всех routers вынесено из `main.py`. |
| **Публичный API** | `POST /v1/recommendations/route` — canonical; старый `/recommendations/route` сохранён как deprecated alias. |
| **Тесты** | `tests/test_app_readiness.py`, `tests/test_cors_config.py`, `tests/test_recommendations_route_v1_router.py`, `tests/test_recommendations_route_deprecation.py`. |

---

## `tests/test_recommendations_route_router.py`

| Поле | Значение |
|------|----------|
| **Путь** | `tests/test_recommendations_route_router.py` |
| **Слой** | Автотесты |
| **Роль** | Smoke `POST /recommendations/route`: **без** реальной БД, PostGIS и полного pipeline; `TestClient` на минимальном `FastAPI` + только `recommendations` router. |
| **Шаг pipeline** | Не выполняется реально — `RouteBuilderService` и `ExplainabilityService` подменяются `unittest.mock.patch`. |
| **Зависимости** | `FastAPI`, `TestClient`, `patch` / `MagicMock`, `get_db` override, фикстуры `RoutePoint` / `FinalRoute` для возврата из мока. |
| **Возвращает / производит** | Проверки: `200`, `route_id`, `points`, **`warnings`** (список строк из мока `FinalRoute`), `explanation` с ключом `summary`. |
| **SoT / вспомогательный** | Вспомогательный контроль контракта API. |

---

## `tests/test_recommendations_route_integration.py`

| Поле | Значение |
|------|----------|
| **Путь** | `tests/test_recommendations_route_integration.py` |
| **Слой** | Автотесты (integration) |
| **Роль** | Интеграционная проверка **нового** endpoint `POST /recommendations/route`: один запрос проходит через реальный `TestClient`, реальный `app` из `main`, реальную сессию БД и **полный** recommendation pipeline (без подмены сервисов). |
| **Шаг pipeline** | Выполняются все шаги, которые вызывает роутер: `build_route` → `build_route_explanation`. |
| **Зависимости** | `pytest`, `fastapi.testclient.TestClient`, `main.app`, `core.config.settings` (проверка `postgresql` в `DATABASE_URL`). **Не** используются `patch`, `MagicMock`, моки БД или pipeline. |
| **Включение** | Opt-in: переменная окружения `RUN_RECOMMENDATIONS_INTEGRATION=1`; без неё и без PostgreSQL в `DATABASE_URL` тесты **skipped** (как у DB smoke для retrieval). |
| **Инфраструктура** | Требуется рабочий PostgreSQL (и данные кандидатов в зоне координат теста); отдельная тестовая БД не описывается в этом файле — используется та же связка, что и для прочих DB-smoke сценариев. |
| **Возвращает / производит** | Happy path / cold start: `200`, структура ответа, поле **`warnings`** (наличие и тип `list`, без assert на текст — зависит от БД); плюс `422` без `lat`/`lng`. |
| **SoT / вспомогательный** | Регрессия «сквозного» поведения API + БД + pipeline; контракт JSON по-прежнему детализируется в `tests/test_recommendations_route_router.py`. |

---

## `services/place_validation_service.py`

| Поле | Значение |
|------|----------|
| **Путь** | `services/place_validation_service.py` |
| **Слой** | Сервис доменной логики (аннотация качества данных) |
| **Роль** | `validate_place(place)` → `{"is_valid": bool, "issues": list[str]}` по координатам, `opening_hours`, `average_visit_duration_minutes`, `category`, `price_level`. Места **не** отсекаются на этом шаге. |
| **Шаг pipeline** | Вызывается из `RouteBuilderService` **сразу после** STEP 2 (retrieval): на каждый кандидат вешается `place.validation = validate_place(place)` до hard filters и scoring. |
| **Зависимости** | `itinerary_time_service.parse_time_string` (проверка строк времени в JSON часов). |
| **Связь со scoring** | `ScoringService` читает `place.validation["issues"]` → компонент **`data_quality`** в `breakdown` → итоговый score (коррекция ранжирования, не hard filter). |
| **Связь с finalize** | Часть кодов `issues` (только **visit_duration**) агрегируется в **`FinalRoute.warnings`** на шаге finalize — **одна** route-level строка-сводка, не список мест. |
| **SoT / вспомогательный** | SoT по **кодам** строк в `issues` для штрафов в scoring и для порога поднятия в `warnings` в finalize. |

---

## `services/scoring_service.py`

| Поле | Значение |
|------|----------|
| **Путь** | `services/scoring_service.py` |
| **Слой** | Сервис доменной логики (шаг 4 pipeline) |
| **Роль** | Мягкий скоринг: `breakdown` по осям interest / distance / context / popularity (бюджет) / novelty и **`data_quality`**; итог — взвешенная сумма в `_combine_scores`. |
| **Цепочка** | `place.validation` → `issues` → **`data_quality`** → влияет на **ranking** (сортировка в `score()`). |
| **Источник data_quality** | Если на объекте места есть `place.validation` (dict) с ключом `issues` (список строк) — по известным кодам issues вычисляется оценка в **[0, 1]** (штрафы суммируются, результат обрезается снизу нулём). Если `validation` нет или `issues` пуст — **нейтрально 1.0**, поведение совместимо с тестами без навешанной валидации. |
| **Связь с retrieval** | `place.validation` выставляет оркестратор **после retrieval**, до hard filters; scoring только **читает** атрибут. |
| **Hard filter** | **Нет**: низкий `data_quality` не удаляет место из пула — это отдельная ответственность `HardFiltersService`. |
| **Зависимости** | `MergedContext`, `Place`, `is_place_open_at` (контекстный сигнал по часам «сейчас»). |
| **SoT / вспомогательный** | SoT по весам компонентов и маппингу кодов `issues` → штрафам внутри `_data_quality_score`. |

---

## `services/route_finalize_service.py`

| Поле | Значение |
|------|----------|
| **Путь** | `services/route_finalize_service.py` |
| **Слой** | Сервис доменной логики (шаг 7 pipeline) |
| **Роль** | `finalize(route, ctx)` → **`FinalRoute`**: метрики, `has_warnings` / `warning_count` / `places_with_warnings`, `quality_score` / `quality_breakdown`, плюс **`warnings: list[str]`** — человекочитаемые **route-level** предупреждения. |
| **Поле warnings** | Список **уникальных** строк для всего маршрута (не «по одной на место»); summary-уровень для UI/API, не замена `places_with_warnings`. |
| **Агрегация** | **Time-aware:** по `time_status` ≠ `ok` → `places_with_warnings` (id мест) и вклад в `has_warnings` / `warning_count`. **Validation:** только коды **visit_duration** в `RoutePoint.validation["issues"]` → при наличии добавляется одна сводная строка в `warnings` (прочие issues в список не поднимаются). |
| **Зависимости** | `MergedContext`, `RoutePoint` (в т.ч. опциональное поле `validation`, проброшенное из `route_assembly_service`). |
| **SoT / вспомогательный** | Тексты route-level сообщений для validation заданы в этом модуле; тесты `tests/test_route_finalize_service.py` сверяют контракт. |

---

## Time-aware route quality

| Файл | Роль |
|------|------|
| `services/route_time_ordering_service.py` | Перед time-aware pass поднимает nearby-точки, закрывающиеся в течение 90 минут; дальние urgent-точки не форсируются. |
| `services/time_aware_service.py` | Оркестрирует walk/arrival/departure annotation и выставляет `time_status` / `time_warning`. |
| `services/time_aware_math.py` | Чистые расчёты walking minutes и fallback visit duration. |
| `services/time_aware_hours.py` | Opening-hours решения: status/warning, legacy status и small wait-gap до 20 минут. |

---

## `tests/test_scoring_service.py`

| Поле | Значение |
|------|----------|
| **Путь** | `tests/test_scoring_service.py` |
| **Слой** | Автотесты (`unittest`) |
| **Роль** | Покрытие осей скоринга и интеграции `ScoringService.score`: сортировка, ключи `breakdown`, в т.ч. **`data_quality`**. |
| **data_quality** | Отдельный класс тестов: место с `place.validation = {"issues": [...]}` получает **меньший** итоговый score, чем идентичное без issues; два issues (мягкие коды из валидатора) — **ниже**, чем одно; в `breakdown` обязательно есть ключ `"data_quality"`. |
| **Зависимости** | `unittest`, `SimpleNamespace`, `patch` на `is_place_open_at` там, где нужна детерминированность `context`. |
| **Запуск** | `python3.11 -m unittest tests.test_scoring_service -v` (см. секцию прогонов). |
| **SoT / вспомогательный** | Регрессия scoring и связки validation → ranking. |

---

## Участие сервисов в новом API-потоке

| Файл | Связь с `POST /recommendations/route` |
|------|----------------------------------------|
| `services/route_builder_service.py` | Роутер вызывает `build_route()` — **оркестратор**: merge → retrieval → **validation** (`place.validation`) → filters → scoring → assembly → time-aware → **finalize** (в т.ч. **route-level validation warnings** в `FinalRoute.warnings`) → `FinalRoute`. |
| `services/candidate_retrieval_service.py` | SQL retrieval кандидатов; теперь дополнительно фильтрует `cities.launch_status='published'` и не берёт places из unpublished import scopes. |
| `services/route_builder_flow.py` | Выполняет production-flow маршрута и наполняет `FinalRoute.pipeline_trace`. |
| `services/route_pipeline_trace.py` | Stage trace helpers и structured JSON log для route build. |
| `services/route_filter_policy.py` | Чистая политика hard filters + `FilterReport` с причинами отбраковки. |
| `services/route_filter_reasons.py` | Чистые функции причин hard filter: status, coordinates, excluded ids/categories, hours и budget. |
| `services/route_interest_mapping.py` | Semantic mapping широких интересов в категории/tags для scoring boost. |
| `services/route_assembly_optimizer.py` | Выбирает точки с учётом score, value/minute, walk time, remaining budget и category limits. |
| `services/route_geometry.py` | Haversine distance и walk-time approximation для сборки маршрута без внешнего routing provider. |
| `services/route_diversity_policy.py` | Category limits и distribution helpers. |
| `services/route_response_metrics.py` | `total_walk_distance_meters`, `time_breakdown`, `category_distribution` для ответа. |
| `services/route_base_quality_score.py` | Базовая полнота данных места: координаты, часы, duration, фото, описание. |
| `services/route_time_context_score.py` | Категория места относительно `time_of_day`. |
| `services/route_data_confidence_score.py` | Confidence + stale penalty в отдельном score-компоненте. |
| `services/route_popularity_proxy.py` | Proxy известности места по открытым source-сигналам. |
| `services/route_explanation_reasons.py` | `reason`, `match_type`, `score_components`, `data_notes` для explainability. |
| `services/user_route_correction_actions.py` | Action-level transformation текущих places перед recalc. |
| `services/user_route_correction_policy.py` | Pure correction policy: value/minute, excluded ids, same category. |
| `services/user_route_replacement_loader.py` | Replacement/extend DB lookup с safety-фильтрами. |
| `services/candidate_category_budget.py` | После SQL retrieval чередует кандидатов по категориям, чтобы diversity появлялся до scoring/assembly. |
| `services/place_validation_service.py` | После retrieval: `validate_place` → `place.validation`; далее **scoring** (`data_quality` / ranking) и **finalize** (агрегат `warnings` для visit_duration). |
| `services/scoring_service.py` | `score()`: `breakdown["data_quality"]` из `place.validation["issues"]` — влияние на ranking; вес небольшой (коррекция, не отсев). |
| `services/route_pipeline_warnings.py` | Собирает honest route-level warnings до finalize: empty candidate pool, all filtered, assembly failure, missing/malformed opening hours. |
| `services/route_quality_warnings.py` | Собирает route-level warnings качества композиции: слишком короткий или слишком однотипный маршрут. |
| `services/route_quality_score.py` | Считает числовой `quality_score` 0..1 и breakdown: diversity, budget_fit, data_completeness, warning_health. |
| `services/route_budget_fit_service.py` | После time-aware: сохраняет order-preserving subset маршрута в `effective_time_budget_minutes`; oversized средняя точка может быть пропущена, если следующие помещаются. |
| `services/route_finalize_service.py` | `finalize()`: метрики + `quality_score` + `warnings` (time + pipeline + validation visit_duration) + существующие поля предупреждений по точкам; empty route сохраняет route-level warnings. |
| `services/route_user_warnings.py` | После finalize: превращает технические warning strings в `user_warnings` для API/UI без изменения route decision logic. |
| `services/explainability_service.py` | Роутер вызывает `build_route_explanation(final_route)` — **после** finalize; результат кладётся в `explanation` ответа, включая `warnings`, `data_limitations` и `quality_score`. |
| `services/route_analytics_service.py` | Persistent observability: пишет `route_build_events`, считает summary по quality score, warning rate, latency и source. |

Itinerary-сервисы и роутер **не** вызываются из `routers/recommendations.py`.

---

## Участие сервисов в coverage/import потоке мест

| Файл | Роль |
|------|------|
| `routers/place_seed_import.py` | HTTP endpoint `POST /place-seed/import/`: dry-run или real import seed-мест. |
| `routers/place_import_logs.py` | HTTP endpoint `GET /place-import-logs/summary`: агрегат persistent import logs. |
| `routers/place_coverage.py` | HTTP endpoint `GET /place-coverage/{city_slug}`: отчёт покрытия города местами. |
| `scripts/check_place_coverage_gate.py` | Release CLI gate: читает coverage endpoint и валит релиз, если MVP-пороги не выполнены. |
| `scripts/production_place_import.py` | Dry-run-first wrapper для production seed import; real запись включается только флагом `--real`. |
| `scripts/refresh_place_images.py` | Wrapper image pipeline: no-live validation по умолчанию, live enrichment через `--live` и явный Mapillary token argument. |
| `routers/place_verification.py` | HTTP endpoints для re-verification queue: enqueue stale places и pending queue. |
| `core/place_verification_scheduler.py` | FastAPI lifecycle edge для опционального background scheduler re-verification enqueue. |
| `services/place_seed_import_service.py` | Оркестратор нормализации, дедупликации, validation и write-plan/upsert. |
| `schemas/place_seed_item.py` | Seed item contract; включает coverage-поля `opening_hours`, `average_visit_duration_minutes`, `price_level`, `last_verified_at`. |
| `data/scripts/collect_osm_zelenogradsk.py` | Автосбор OSM через Overpass: расширенный query, raw snapshot и генерация import payload без внешних Python-зависимостей. |
| `data/scripts/fetch_osm_zelenogradsk.py` | Backward-compatible wrapper на `collect_osm_zelenogradsk.py`. |
| `data/scripts/osm_seed_builder.py` | Преобразует raw OSM Зеленоградска в `POST /place-seed/import/` payload с текущей taxonomy, default duration и hours fallback. |
| `data/seeds/place_import/zelenogradsk_osm.json` | Сгенерированный OSM import payload: 107 валидных мест. |
| `data/seeds/place_import/zelenogradsk_editorial_walks.json` | Editorial walk payload для закрытия прогулочной категории без автосбора закрытых источников. |
| `services/place_seed_normalization_service.py` | Чистая нормализация title/slug/city/category/source полей. |
| `services/place_seed_dedup_service.py` | Убирает дубли внутри payload по slug и возвращает duplicate diagnostics. |
| `services/place_seed_write_service.py` | Создаёт или обновляет `Place` по slug; dry-run использует тот же план действий без записи. |
| `services/place_import_log_service.py` | Пишет `place_import_events` для каждого импорта и считает summary: total, created, updated, invalid, dry-run count. |
| `services/place_staleness_policy.py` | Нормализует `status`, считает tiered staleness (30 дней dynamic, 90 дней static), запрещает `closed` / `temporarily_closed` места в маршрутах. |
| `services/place_verification_service.py` | Создаёт pending verification tasks для stale-мест, не дублирует уже pending задачи. |
| `services/place_verification_scheduler_service.py` | Чистый batch-runner scheduled enqueue: парсит city slugs, считает interval seconds и изолирует ошибку одного города от остальных. |
| `services/place_coverage_gate_service.py` | Чистая оценка coverage report против release thresholds: total, ratios и обязательные категории. |
| `services/place_coverage_service.py` | Считает total, заполненность координат/часов/visit duration/source, active/stale/temp-closed/closed counts, average confidence, категории и route-ready score. |

---

## User signals

| Файл | Роль |
|------|------|
| `models/user_signal.py` | Таблица `user_signals`: user, signal type, entity, payload, timestamp. |
| `routers/user_signals.py` | `POST /user-signals/` и `GET /user-signals/{user_id}/summary`. |
| `services/user_signal_service.py` | Запись сигналов и агрегат по signal/entity типам. |
| `services/user_profile_from_signals_service.py` | Маппит derived signal profile в `UserProfile` для recommendation pipeline. |
| `services/personalization_score.py` | Чистый personalization score для scoring: liked boost, visited penalty, category affinity. |
| `services/user_route_history_service.py` | Возвращает user route history из `route_build_events.user_id`. |

---

## Backend quality gate

| Файл | Роль |
|------|------|
| `scripts/backend_quality_gate.py` | Custom backend linter: file length, module file count, cyclomatic complexity and pytest coverage floor. |
| `scripts/backend_quality_baseline.txt` | Explicit baseline for existing legacy violations; new files/modules are checked strictly. |
| `docs/architecture/backend_quality_gate.md` | Architecture note and baseline policy for the custom quality gate. |

---

## Frontend route builder

| Файл | Роль |
|------|------|
| `frontend/src/components/ui/AppHeader.tsx` | Общий app-shell header для продуктовой навигации City Go. |
| `frontend/src/styles/responsive.css` | Layout/navigation responsive layer. |
| `frontend/src/styles/home.css` | Home hero, search and primary CTA styling. |
| `frontend/src/styles/visuals.css` | Home panorama carousel, route preview and photo-first visual patterns. |
| `frontend/src/styles/actions.css` | Quick action scenario grid on Home. |
| `frontend/src/styles/places.css` | Places grids, list panel and state styling. |
| `frontend/src/styles/cards.css` | Shared stat/place card styling. |
| `frontend/src/shared/demo/*` | Frontend demo data and local algorithms for places, open-now, nearby and route builder when `VITE_USE_BACKEND` is not enabled. |
| `frontend/public/data/zelenogradsk_places.json` | Large frontend demo catalog: 108 places generated from local OSM + editorial seed for pre-DB product testing. |
| `frontend/src/widgets/home/LocationCarousel.tsx` | Horizontal panorama carousel for featured city locations. |
| `frontend/src/widgets/recommendation-route/RouteHeroPreview.tsx` | Photo-based route builder preview in the shared app-shell. |
| `frontend/src/api/recommendations/recommendationRoute.api.ts` | API client для `/v1/user-routes/build` и `/v1/user-routes/correct`. |
| `frontend/src/pages/routes/GenerateRoutePage.tsx` | Route builder screen: form state, submit, correction actions. |
| `frontend/src/widgets/recommendation-route/RouteResultPanel.tsx` | Result summary, quality metric, warnings and correction buttons. |

---

## Прогон тестов (зафиксировано при обновлении документа)

### Команды: recommendations endpoint и pipeline smoke

Из корня репозитория:

```bash
# Контракт роутера + моки сервисов (быстро, без БД)
python3.11 -m pytest tests/test_recommendations_route_router.py -v
```

```bash
# Сквозной pipeline в памяти: реальные шаги после merge, мок только на выдачу кандидатов (STEP 2)
python3.11 -m pytest tests/test_route_builder_pipeline_smoke.py -v
```

```bash
# То же smoke-модуль через unittest (как в исходном docstring файла)
python3.11 -m unittest tests.test_route_builder_pipeline_smoke -v
```

```bash
# Интеграция: реальный FastAPI app из main, реальная БД, без моков pipeline (нужны PostgreSQL и флаг)
RUN_RECOMMENDATIONS_INTEGRATION=1 python3.11 -m pytest tests/test_recommendations_route_integration.py -v
```

Без `RUN_RECOMMENDATIONS_INTEGRATION=1` файл `tests/test_recommendations_route_integration.py` даёт **skipped** тесты — это ожидаемо для CI/локали без намеренного прогона.

### Команды: scoring и pipeline smoke (unittest)

```bash
python3.11 -m unittest tests.test_scoring_service -v
python3.11 -m unittest tests.test_route_builder_pipeline_smoke -v
```

---

Выполнено из корня репозитория (широкий набор unit/smoke без интеграции recommendations и без устаревших `test_itinerary_*`):

```bash
python3.11 -m pytest tests/test_recommendations_route_router.py tests/test_route_builder_pipeline_smoke.py tests/test_context_merge_service.py tests/test_hard_filters_service.py tests/test_route_assembly_service.py tests/test_scoring_service.py tests/test_time_aware_service.py tests/test_route_finalize_service.py tests/test_explainability_service.py tests/test_candidate_retrieval_db_smoke.py -q
```

**Результат (последний прогон):** `53 passed, 1 skipped` за ~1.7 s (без тестов, импортирующих `main.app`, и без устаревших `test_itinerary_*`, пока их не выровняли под текущие схемы).

Отдельно при необходимости:

```bash
python3.11 -m pytest tests/test_recommendations_route_router.py -q
python3.11 -m pytest tests/test_route_builder_pipeline_smoke.py -q
python3.11 -m pytest tests/test_explainability_service.py -q
python3.11 -m pytest tests/test_context_merge_service.py tests/test_hard_filters_service.py tests/test_route_assembly_service.py -q
```

---

## Place enrichment (admin)

| Путь | Слой | Роль |
|------|------|------|
| `routers/place_enrichment.py` | HTTP | 7 admin endpoints: export, batches, download, preview, apply |
| `services/place_enrichment_service.py` | Service | Export orchestration + audit |
| `services/place_enrichment_batch/` | Service | `active/` / `archive/` batch paths и meta |
| `services/place_enrichment_import/` | Service | Parse enriched CSV, preview, apply to Place |
| `schemas/place_enrichment.py` | Schema | Request/response DTO |
| `data/scripts/run_place_enrichment_export.py` | CLI | Auto export после deploy (`--git-artifact`) |
| `data/scripts/import_place_enrichment_csv.py` | CLI | `--preview` / `--apply` |

Документация: `docs/architecture/place_data_enrichment.md`.
