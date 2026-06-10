# Route Foundation Architecture

## Принцип

Маршрут — сценарий + порядок точек + ограничения + состояние + история изменений.

На этапе 1 реализован минимум для **чистого candidate pool** и **объяснимой генерации**. Полные сущности — целевая модель для следующих фаз.

## Целевые сущности (документированы, не все в БД)

### route_templates / route_template_stops
Шаблон сценария: город, тип, длительность, ordered stops со snapshot полями.

### route_instances / route_instance_stops
Конкретный маршрут пользователя или dry-run: статус `planned|active|completed|cancelled|dry_run`, source, snapshots, `selection_reason` / `exclusion_reason`.

### route_segments
Переходы между stops: mode, distance, duration, geometry, provider.

### route_generation_runs / route_generation_candidates (реализовано)
Каждая попытка генерации:
- request payload, status, algorithm_version
- counts: total / eligible / selected
- per-place: eligible, score, selected, rejection/selection reasons

## Текущая реализация (phase 1)

```
Request → RouteBuilderService / itinerary
       → route_eligibility (SQL + evaluate)
       → pipeline (filters, scoring, assembly)
       → finalize
       → record_canonical_generation / record_itinerary_generation
       → route_generation_runs + candidates
```

## Algorithm version

`route_eligibility_v1` — константа в `services/route_eligibility/forbidden_categories.py`.

## Расширение на следующие этапы

| Capability | Зависимость от foundation |
|------------|---------------------------|
| RouteConstructor | `route_instances` + user edits |
| Replan / Recovery | instance stops + events |
| Smart detours | eligible pool + segment geometry |
| Personalization | scoring signals + generation candidates history |
| Admin route debug | dry-run + diagnostics (готово на backend) |

## Retention (рекомендация)

- `route_generation_runs`: 90 дней prod, 30 дней dry-run
- `route_generation_candidates`: cascade delete с run
- Cleanup: отдельный cron/job (не реализован)
