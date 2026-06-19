# City Go — Route Assembly Quality

Дата: 2026-06-05.

## Цель

Маршрут должен быть не списком top-score мест, а прогулкой, которая помещается во время, не делает очевидные возвраты и не повторяет одну категорию слишком много раз.

## Архитектурное решение

- `services/route_assembly_service.py` хранит публичный контракт `RoutePoint` и тонкий `RouteAssemblyService`.
- `services/route_assembly_optimizer.py` выбирает точки рекурсивным greedy-проходом.
- `services/route_geometry.py` считает walk distance/time без внешнего routing provider.
- `services/route_diversity_policy.py` задаёт category limits.
- `services/route_point_factory.py` создаёт `RoutePoint` из `ScoredPlace`.
- `services/route_walk_annotations.py` пересчитывает walk-minutes после loop cleanup.
- `services/route_response_metrics.py` добавляет metadata для API/UI.
- `services/route_adaptive_plan.py` классифицирует scored pool на primary/related/neutral.
- `services/route_quality_gates.py` выставляет route-level status, completeness и warnings.

## Adaptive Planning

- interests являются soft preference и не удаляют кандидатов сами по себе;
- отсутствие выбранных interests строит neutral route по лучшим доступным точкам города;
- `exact_count = 0` расширяет pool через related/neutral и добавляет warning;
- `exact_count = 1` помечает точку как anchor для assembly;
- target size считается по budget, средней длительности визита, оценке переходов, плотности pool и pace;
- длинный budget не заставляет добирать фиксированное число точек, если качественного pool мало.

## Selection

Кандидат попадает в маршрут только если:

- walk time от текущей позиции + visit duration помещаются в remaining budget;
- категория не превысила limit;
- ещё не достигнут `effective_num_stops`.

Assembly score:

```text
candidate.score * 0.7 + value_per_minute * 0.3
```

Так scoring остаётся важным, но длинные места с большим пешим переходом не вытесняют более полезные короткие точки.

## Diversity

Базовые лимиты:

- coffee/cafe: 2;
- food/restaurant: 2;
- walk: 3;
- park: 2;
- culture/museum/gallery: 3;
- evening/bar/pub: 2;
- fallback: 2.

## Loop Cleanup

После selection выполняется локальная проверка тройки точек. Если `A -> C` короче, чем `A -> B`, соседние `B/C` меняются местами. Это не полный TSP, но убирает очевидные backtrack-петли без тяжёлого оптимизатора.

## Response Metadata

`FinalRoute` и HTTP response теперь содержат:

- `total_walk_distance_meters`;
- `time_breakdown.visit_time_minutes`;
- `time_breakdown.walk_time_minutes`;
- `time_breakdown.total_time_minutes`;
- `time_breakdown.budget_utilization`;
- `category_distribution`.
- `route_quality_status`;
- `route_completeness`;
- `matched_interest_count`;
- `total_requested_interests`;
- `expansion_level`;
- `neutral_added_count`;
- `fallback_level`;
- `user_explanation`;
- `debug_trace`.

`RouteBudgetFitService` остаётся страховкой после time-aware pass и не добивает маршрут точками для искусственного заполнения бюджета.
