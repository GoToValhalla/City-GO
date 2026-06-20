# City Go — Route Pipeline Observability and Safety

Дата: 2026-06-05.

## Цель

Route pipeline должен быть проверяемым: команда видит, сколько кандидатов прошло каждый этап, почему места были отброшены, какие score попали в верхушку и где маршрут деградировал.

## Архитектурное решение

- `RouteBuilderService` остаётся точкой входа и хранит зависимости pipeline.
- `services/route_builder_flow.py` выполняет поток `context -> retrieval -> hard_filters -> scoring -> interest_matching -> adaptive_plan -> assembly -> time_ordering -> time_aware -> budget_fit -> quality_gates -> finalize -> final`.
- `services/route_pipeline_trace.py` собирает stage trace и пишет structured JSON log.
- `services/route_filter_policy.py` собирает `FilterReport`, а `route_filter_reasons.py` хранит чистые функции причин отбраковки.
- `FinalRoute.pipeline_trace` хранит trace внутри backend.
- `routers/recommendations.py` отдаёт `_trace` только при `X-Debug: true`.

## Hard Filters

`HardFiltersService.apply_with_report()` возвращает `FilterReport`:

- `kept` — кандидаты, прошедшие фильтр;
- `rejected` — пары `place_id/reason`;
- `reason_counts` — агрегат причин для trace;
- `strict_kept_count` / `relaxed_kept_count` — где видно, сработал ли relaxed fallback.

Fallback ослабляет budget. Он не возвращает:

- `closed` / `temporarily_closed`;
- `is_active=false`;
- места без координат;
- явно исключённые места и категории;
- closed-now;
- unknown hours только если контекст явно требует `require_known_hours=true`.

## Semantic Interests

`services/route_interest_mapping.py` переводит широкие интересы пользователя в категории:

- `архитектура`, `история` -> `culture`, `museum`, `walk`;
- `еда` -> `food`, `restaurant`, `coffee`;
- `природа`, `море` -> `park`, `walk`, `outdoor`;
- `вечер` -> `evening`, `bar`, `food`;
- `семья`, `дети` -> `family`, `park`, `indoor`.

Это boost в scoring, не hard filter. Если интересы пустые, компонент остаётся нейтральным.
Если интерес совпадает с `avoided_categories`, он удаляется на этапе merge и попадает в
`interest_removed_due_to_avoidance`, чтобы запрещённая категория не стала route anchor.

## Debug Contract

Пример запроса:

```bash
curl -H "X-Debug: true" -X POST /v1/recommendations/route
```

Пример `_trace`:

```json
[
  {"stage": "candidate_retrieval", "count": 108, "duration_ms": 12},
  {"stage": "hard_filter", "kept_count": 91, "reasons": {"status": 2}},
  {"stage": "scoring", "top3_scores": [0.87, 0.82, 0.79]}
]
```

`debug_trace` в UI обязан показывать полную цепочку даже при пустом маршруте
или ошибке сборки. Канонические блоки:

- `context` — параметры запроса и нормализованный route context.
- `city_stats` — общий объём мест города и пригодность к маршрутам.
- `retrieval` — счётчики извлечения кандидатов, fallback и sample ids.
- `hard_filters` — вход/выход, причины отбраковки и sample removed.
- `interest_matching` — точные, related и neutral совпадения интересов.
- `adaptive_plan` — target points, expansion level и user explanation.
- `pool_expansion` — расширение пула до related/neutral кандидатов.
- `scoring` — диапазон score и top scored candidates.
- `assembly` — выбранные/отклонённые точки, fallback triggers и причины отказа первой точки.
- `time_ordering` — порядок точек до и после time ordering.
- `time_aware` — вход/выход time-aware pass и removed count.
- `budget_fit` — соответствие маршрута time budget и снятые budget точки.
- `quality_gates` — warnings, failed gates и пользовательское объяснение.
- `finalize` — финальная сериализация route object.
- `final` — итоговые ids, длительность, дистанция и `failure_stage`.

Если после hard filters/scoring есть кандидаты, но assembly вернул 0, flow включает
minimal fallback из top scored candidates. Он не нарушает explicit exclusions/status/coords,
потому что работает только с уже отфильтрованным scored pool, и отдаёт partial/minimal route
с warning вместо тихого no-route.

## Тесты

- `tests/test_hard_filters_service.py` — safety-фильтры и причины.
- `tests/test_scoring_service.py` — semantic interests.
- `tests/test_route_builder_pipeline_smoke.py` — trace на полном smoke-flow.
- `tests/test_route_pipeline_stability_new.py` — conflict interests, minimal fallback и failure stage.
- `tests/test_recommendations_route_router.py` — `_trace` только по debug header.
