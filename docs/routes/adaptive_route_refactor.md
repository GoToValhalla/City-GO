# Adaptive Route Refactor

Дата: 2026-06-20

## Audit перед изменениями

- `interests` были мягкими в `ScoringService`, но backend `ContextMergeService` скрыто добавлял `["walk"]`, а frontend тоже отправлял `walk` по умолчанию.
- Fixed minimum points использовался в `route_quality_score.minimum_points_for_budget`, assembly backfill и debug flow.
- Budget gap fill в `route_builder_flow` мог добирать точки после первичной сборки, чтобы занять бюджет.
- Assembly имел emergency fallback из scored pool, если optimizer вернул пустой маршрут.
- Budget fit уже сохранял первую точку, если она превышала бюджет, но не давал отдельной route metadata.
- Retrieval расширял радиус/city-wide, а hard filters имели fallback relaxation, но это было видно только в trace, не в route-level metadata.

## Архитектура

Добавлен adaptive plan между scoring и assembly:

`scoring -> interest_matching -> pool_expansion -> assembly -> budget_fit -> quality_gates -> final_response`

`services/route_adaptive_plan.py`:

- делит scored pool на `primary`, `related`, `neutral`;
- считает `target_points` по budget, visit duration, travel estimate, pool size и pace;
- формирует `expansion_level`, `neutral_added_count`, warnings и `user_explanation`.

`services/route_quality_gates.py`:

- маркирует `route_quality_status`;
- считает `route_completeness`;
- ловит `algorithm_error` для cities с `>=100` eligible places и пустым route;
- проверяет single anchor, data deficit, budget zero и explicit exclusions.

## Hard vs Soft

Hard constraints:

- city scope / active route-eligible candidates;
- valid coordinates;
- `excluded_place_ids`;
- `avoided_categories`;
- active/not deleted place state.

Soft preferences:

- `interests`;
- diversity;
- opening hours outside strict `now` mode;
- score threshold;
- first walk distance;
- pace mode.

## Что удалено

- Hidden backend `DEFAULT_ROUTE_INTERESTS = ["walk"]`.
- Hidden frontend default `walk`.
- Emergency assembly fallback в route flow.
- Budget gap fill после primary budget fit.
- Fixed pressure на minimum points в assembly backfill.

## Response Metadata

Ответ маршрута теперь явно несет:

- `route_quality_status`;
- `route_completeness`;
- `matched_interest_count`;
- `total_requested_interests`;
- `expansion_level`;
- `expanded_category_count`;
- `neutral_added_count`;
- `fallback_level`;
- `user_explanation`;
- `debug_trace`.

## Known Limits

- Candidate retrieval radius/city-wide expansion остается в текущем retrieval service и только отражается в trace.
- Формула adaptive target намеренно консервативна и не использует реальный routing provider.
- `quality_score` сохранен обратно совместимым; новая бизнес-оценка находится в `route_quality_status`.
