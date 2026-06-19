# Аудит текущей логики маршрутов City Go

Дата: 2026-06-10. Этап: route stabilization + admin visualization + user geolocation.

## 1. Endpoint'ы, строящие маршруты

| Endpoint | Контур | Движок |
|----------|--------|--------|
| `POST /v1/user-routes/build` | Canonical (prod UI) | `RouteBuilderService` → `build_dynamic_route` |
| `POST /v1/recommendations/route` | Canonical | тот же pipeline |
| `POST /routes/generate` | Legacy itinerary | `itinerary_service.generate_itinerary_stub` |
| `POST /routes/replan` | Legacy itinerary | `itinerary_replan_service.replan_itinerary` |
| `POST /admin/routes/dry-run` | Admin debug | `RouteBuilderService` + diagnostics + mini-map payload |

Редакционные `GET /routes/*` — шаблонные маршруты из БД, не динамическая генерация.

## 2. Сервисы pipeline

**Canonical:**
`context_merge` → `candidate_retrieval` → `quality_annotation` → `hard_filter` → `scoring` → `assembly` → `time_ordering` → `time_aware` → `budget_fit` → `finalize`

Ключевые файлы:
- `services/route_builder_flow.py`
- `services/candidate_retrieval_service.py`
- `services/hard_filters_service.py`
- `services/route_assembly_optimizer.py`
- `services/route_quality_score.py`
- `services/route_candidate_diagnostics.py`
- `services/admin_route_dry_run_service.py`
- `frontend/src/pages/routes/GenerateRoutePage.tsx`
- `frontend/src/widgets/recommendation-route/RouteRequestForm.tsx`

**Legacy itinerary:**
- `services/itinerary_candidate_service.py` — выбор кандидатов по городу
- `services/itinerary_scoring_service.py`
- `services/itinerary_route_builder_service.py`
- `services/itinerary_replan_service.py` — replan + stop insertion

## 3. User geolocation UX

Пользовательский route builder поддерживает три источника старта:

```text
city_center
current_location
address
```

Frontend:
- кнопка **От центра города** берёт координаты из `getCurrentCityCoordinates(city.slug)`;
- кнопка **Использовать мою геолокацию** вызывает `navigator.geolocation.getCurrentPosition`;
- координаты текущей геолокации сохраняются в `sessionStorage` под ключом `citygo:last-route-geolocation`;
- при повторном открытии страницы в той же сессии сохранённая геолокация восстанавливается как `current_location`;
- при ошибке браузерной геолокации пользователь видит явный message и может вернуться к центру города;
- координаты не вводятся руками.

Backend:
- route request уже содержит `lat`, `lng`, `start_source` и `start.type`;
- `ContextMergeService` использует `request.location` как стартовую точку;
- fallback на центр города выполняется на frontend до отправки запроса.

Gaps:
- `RequestContext` пока не хранит `start_source` в `MergedContext`;
- нет server-side аналитики источника старта;
- нет live tracking / reroute при уходе с маршрута.

## 4. Откуда берутся места

- Таблица `places`, фильтр `city_id`
- Canonical: geo-radius + SQL conditions в `candidate_retrieval_service`
- Legacy: все места города через `apply_public_place_visibility` и route eligibility

Поля Place, влияющие на маршрут:
- `is_active`, `status`, `is_published`, `is_visible_in_catalog`, `is_route_eligible`
- `category`, `lat`/`lng`, `city_id`
- `price_level`, `opening_hours`, `dog_friendly`, `family_friendly`, `indoor`/`outdoor`
- `address`, `image_url`, `short_description`, `confidence`, validation fields

## 5. Route retrieval quality

`CandidateRetrievalService.get_candidates()` не меняет публичный интерфейс и не меняет SQL-фильтрацию.

Текущий порядок:
1. SQL-загрузка eligible-кандидатов по радиусу.
2. Fallback расширения радиуса, если кандидатов меньше 20.
3. `attach_public_images`.
4. `_pre_rank_candidates`.
5. `balance_candidates_by_category`.

Pre-rank учитывает:
- наличие фото;
- адрес;
- описание;
- opening hours;
- validation/quality;
- route-friendly category;
- food/rest category;
- близость к старту.

Title/name места не используется.

## 6. Route assembly stabilization

`services/route_assembly_optimizer.py` больше не использует безлимитный `relaxed_categories=True`.

Текущая логика:
- перед assembly `route_adaptive_plan` размечает scored pool как primary/related/neutral;
- `relaxation_stage = 0` — обычные category caps;
- следующие relaxation stages ограниченно ослабляют category pressure, если адаптивный target ещё не достигнут;
- при выборе кандидата применяется category pressure, чтобы не набивать маршрут одинаковыми категориями.

Target route size теперь адаптивен: budget, средняя длительность визита, оценка переходов, плотность pool и pace.

`_fill_budget_gap` удалён: route flow больше не добивает маршрут точками для искусственного заполнения бюджета.

## 7. Route quality layer

`services/route_quality_score.py` рассчитывает:
- `quality_score`;
- `quality_status`: `good | acceptable | weak | failed`;
- `quality_breakdown`;
- public warnings.

`FinalRoute` содержит отдельное поле `quality_status`, а user-route response прокидывает его во frontend.

Основные warning-коды:
- `route_failed_no_places`;
- `route_short_due_to_time_budget`;
- `route_short_due_to_low_place_density`;
- `some_places_have_no_address`;
- `some_places_have_no_photo`;
- `some_places_have_weak_description`;
- `route_has_long_walk_segments`;
- `category_diversity_limited`.

## 8. Admin Dry Run

`POST /admin/routes/dry-run` возвращает:
- selected/rejected candidates;
- counts;
- `quality.status`;
- `quality.score_percent`;
- `quality.warnings`;
- `quality.breakdown`;
- coordinates for selected/rejected candidates.

Frontend `/admin/routes/dry-run` показывает:
- quality status;
- warning reasons;
- breakdown;
- selected/rejected tables;
- SVG mini-map selected-точек с numbered markers и линией маршрута.

Мини-карта не зависит от внешних map SDK и не требует Leaflet/Mapbox.

## 9. Почему попадал мусор (аптеки, остановки, служебные POI)

1. Legacy itinerary раньше не применял строгий `is_route_eligible`.
2. `is_route_eligible default=True` — старые seed/OSM записи оставались eligible.
3. Старые bulk actions писали в несуществующее поле `route_enabled`; исправлено на `is_route_eligible`.
4. OSM-категории `health`, `useful`, `transport`, `service` не всегда помечались при импорте legacy-данных.
5. Неверная канонизация: служебный POI мог оказаться как `cafe`/`culture`.

## 10. Admin Data Quality actions

`/admin/routes/data-quality` показывает:
- coverage по фото/адресам/описаниям;
- forbidden categories;
- quality buckets;
- links to affected places;
- action to queue city address refresh.

Backend action exists for forbidden cleanup:
`POST /admin/routes/data-quality/{city_slug}/exclude-forbidden-categories`.

Он выключает `is_route_eligible` для мест города, чья категория входит в `ROUTE_FORBIDDEN_CATEGORIES`.

## 11. Риски и gaps

- Нужен локальный прогон tests/build после текущих изменений.
- UI dry-run mini-map использует упрощённую SVG-линейку по координатам, не реальный walking router.
- Настоящий route polyline по дорогам — future через routing provider adapter.
- City import pipeline есть как queued background job, но качество зависит от worker и enrichment scripts.
- `start_source` пока не попадает в server-side diagnostics.
- Personalization / live edit — без изменений.
