# City Go — Route Scoring and Explanation

Дата: 2026-06-05.

## Цель

Scoring должен выбирать не просто ближайшие места, а релевантные точки под интересы, время дня и качество данных. Explanation должен объяснять реальную причину выбора каждой точки.

## Scoring Components

`ScoringService` теперь отдаёт расширенный `breakdown`:

- `base_quality` — координаты, часы, duration, фото, описание;
- `interest` — semantic interests mapping;
- `time_context` — соответствие категории времени суток;
- `data_confidence` — confidence + stale penalty;
- `popularity_proxy` — открытые признаки известности: Wikidata/OSM/source/image/description;
- `context`, `data_quality`, `personalization` — существующие сигналы;
- `distance`, `popularity`, `novelty` остаются в breakdown для диагностики.

Distance больше не входит в итоговый score, чтобы не создавать proximity bias. География учитывается в assembly.

## Formula

```text
final_score =
  base_quality       * 0.18
  interest           * 0.27
  time_context       * 0.18
  data_confidence    * 0.14
  popularity_proxy   * 0.08
  context            * 0.07
  data_quality       * 0.04
  personalization    * 0.04
```

## Explanation

`RoutePoint` хранит `scoring_breakdown`. `ExplainabilityService` использует его для:

- `reason` — человекочитаемая причина;
- `match_type` — `interest`, `time_context`, `data_confidence`, `base_quality`, `popularity_proxy`, `proximity` или `default`;
- `score_components` — краткий компонентный breakdown для UI/debug;
- `data_notes` — понятные ограничения данных по маршруту.

Старые поля `summary`, `warnings`, `data_limitations` и `points[].reason` сохранены.
